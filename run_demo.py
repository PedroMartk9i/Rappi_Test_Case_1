"""
Rappi Competitive Intelligence — Live Demo Script

This script:
1. Verifies Rappi session is active (via CDP on port 9222)
2. Scrapes Uber Eats across all zones (guest access, no login needed)
3. Scrapes Rappi across all zones (using authenticated session)
4. Combines data and generates insights report with charts

Usage:
    1. Run launch_browser.bat first
    2. Log into Rappi manually in the browser
    3. Run: python run_demo.py

Options:
    python run_demo.py --zones 5      # Quick demo with 5 zones
    python run_demo.py --zones 10     # Medium demo
    python run_demo.py --zones 25     # Full scrape (default)
    python run_demo.py --skip-rappi   # Only Uber Eats (no login needed)
"""

import sys
import os
import json
import time
import re
import csv
import base64
import argparse
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
os.environ["PYTHONIOENCODING"] = "utf-8"

from playwright.sync_api import sync_playwright
from config import ADDRESSES

# ── Config ──
TARGET_PRODUCTS = {
    "big_mac": ["big mac"],
    "mctrio_big_mac": ["mctrío mediano big mac", "mctrio mediano big mac"],
    "mcnuggets_6": ["mcnuggets de pollo 6", "nuggets de pollo 6 pzas", "nuggets 6"],
    "mcnuggets_10": ["mcnuggets de pollo 10", "nuggets de pollo 10 pzas", "nuggets 10"],
    "cuarto_libra": ["cuarto de libra con queso"],
    "mcpollo": ["mcpollo"],
    "coca_cola": ["coca-cola mediana", "coca cola mediana"],
    "papas_grandes": ["papas grandes"],
}

PRODUCT_NAMES = {
    "big_mac": "Big Mac",
    "mctrio_big_mac": "McTrio Big Mac",
    "mcnuggets_6": "McNuggets 6 pzas",
    "mcnuggets_10": "McNuggets 10 pzas",
    "cuarto_libra": "Cuarto de Libra",
    "mcpollo": "McPollo",
    "coca_cola": "Coca-Cola mediana",
    "papas_grandes": "Papas grandes",
}

OUTPUT_DIR = Path("data/processed")
REPORTS_DIR = Path("reports")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def match_product(name: str) -> str | None:
    name_lower = name.lower().strip()
    for prod_id, keywords in TARGET_PRODUCTS.items():
        for kw in keywords:
            if kw in name_lower:
                return prod_id
    return None


def extract_products_from_page(page) -> list[dict]:
    return page.evaluate(r"""() => {
        const items = [];
        const cards = document.querySelectorAll('[data-qa*="product"], [data-testid*="menu-item"]');
        for (const card of cards) {
            const text = (card.innerText || '').trim();
            if (!text || text.length > 400) continue;
            const lines = text.split('\n').map(l => l.trim()).filter(l => l);
            const name = lines[0] || '';
            if (name.length < 3 || name.length > 80) continue;
            const prices = [];
            let discount = null;
            for (const line of lines.slice(1)) {
                if (line.match(/^-\d+%$/)) discount = line;
                else if (line.match(/^\$\s*[\d,.]+$/))
                    prices.push(parseFloat(line.replace('$','').replace(',','').trim()));
            }
            if (prices.length === 0) continue;
            items.push({
                name, currentPrice: prices[0],
                originalPrice: prices.length > 1 && discount ? prices[1] : prices[0],
                discount,
            });
        }
        const seen = new Set();
        return items.filter(item => { if (seen.has(item.name)) return false; seen.add(item.name); return true; });
    }""")


def extract_delivery_info(page) -> dict:
    body = page.inner_text("body")[:2000]
    info = {}
    if "gratis" in body.lower()[:600] or "free" in body.lower()[:600]:
        info["delivery_fee"] = 0.0
    else:
        fee = re.search(r"(?:envío|delivery)[:\s]*\$?\s*(\d+(?:\.\d+)?)", body[:600], re.I)
        if fee:
            info["delivery_fee"] = float(fee.group(1))
    time_match = re.search(r"(\d+)\s*[-–]\s*(\d+)\s*min", body[:600])
    if time_match:
        info["time_min"] = int(time_match.group(1))
        info["time_max"] = int(time_match.group(2))
    else:
        single = re.search(r"(\d+)\s*min", body[:600])
        if single:
            info["time_min"] = int(single.group(1))
    rating = re.search(r"(\d\.\d)\s*[\(⭐]", body[:600])
    if rating:
        info["rating"] = float(rating.group(1))
    return info


def fallback_text_extraction(page) -> list[dict]:
    body = page.inner_text("body")
    lines = body.split("\n")
    items = []
    for i, line in enumerate(lines):
        line = line.strip()
        if not line or len(line) > 80 or line.startswith("$"):
            continue
        for j in range(i+1, min(i+3, len(lines))):
            pm = re.match(r"^\$\s*(\d[\d,.]*)", lines[j].strip())
            if pm:
                items.append({
                    "name": line,
                    "currentPrice": float(pm.group(1).replace(",", "")),
                    "originalPrice": float(pm.group(1).replace(",", "")),
                    "discount": None,
                })
                break
    return items


# ═══════════════════════════════════
#  UBER EATS SCRAPER (guest access)
# ═══════════════════════════════════

def scrape_ubereats(page, address) -> dict:
    result = {
        "platform": "ubereats", "zone_id": address.id,
        "zone_name": address.name, "zone_type": address.zone_type,
        "address": address.street, "store": None,
        "delivery_info": {}, "products": [], "error": None,
    }
    try:
        payload = json.dumps({
            "address": address.street, "reference": "",
            "referenceType": "google_places",
            "latitude": address.lat, "longitude": address.lon,
        })
        encoded = base64.b64encode(payload.encode()).decode()
        url = f"https://www.ubereats.com/mx/search?pl={urllib.parse.quote(encoded)}&q=McDonald%27s"
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        time.sleep(5)

        mclinks = page.locator("a[href*='mcdonalds']").all()
        store_url = None
        for link in mclinks[:5]:
            href = link.get_attribute("href") or ""
            if "store" in href:
                store_url = href
                break
        if not store_url and mclinks:
            store_url = mclinks[0].get_attribute("href")
        if not store_url:
            result["error"] = "No McDonald's found"
            return result

        if not store_url.startswith("http"):
            store_url = f"https://www.ubereats.com{store_url}"
        page.goto(store_url, timeout=25000, wait_until="domcontentloaded")
        time.sleep(5)

        m = re.search(r"/store/([^/]+)/", page.url)
        result["store"] = m.group(1) if m else "unknown"
        result["delivery_info"] = extract_delivery_info(page)

        for _ in range(8):
            page.mouse.wheel(0, 800)
            time.sleep(0.5)

        result["products"] = extract_products_from_page(page) or fallback_text_extraction(page)
    except Exception as e:
        result["error"] = str(e)[:200]
    return result


# ═══════════════════════════════════
#  RAPPI SCRAPER (authenticated CDP)
# ═══════════════════════════════════

def scrape_rappi(page, address) -> dict:
    result = {
        "platform": "rappi", "zone_id": address.id,
        "zone_name": address.name, "zone_type": address.zone_type,
        "address": address.street, "store": None,
        "delivery_info": {}, "products": [], "error": None,
    }
    try:
        page.goto("https://www.rappi.com.mx/restaurantes/busqueda?term=McDonald%27s",
                   timeout=20000, wait_until="domcontentloaded")
        time.sleep(4)

        mc_link = page.locator("a[href*='mcdonalds']").first
        if mc_link and mc_link.is_visible():
            href = mc_link.get_attribute("href") or ""
            if not href.startswith("http"):
                href = f"https://www.rappi.com.mx{href}"
            page.goto(href, timeout=20000, wait_until="domcontentloaded")
            time.sleep(4)

            m = re.search(r"restaurantes/\d+-(.+)", page.url)
            result["store"] = m.group(1) if m else "mcdonalds"
            result["delivery_info"] = extract_delivery_info(page)

            for _ in range(8):
                page.mouse.wheel(0, 800)
                time.sleep(0.5)

            result["products"] = extract_products_from_page(page) or fallback_text_extraction(page)
        else:
            result["error"] = "No McDonald's in search results"
    except Exception as e:
        result["error"] = str(e)[:200]
    return result


# ═══════════════════════════════════
#  CSV BUILDER
# ═══════════════════════════════════

def build_csv(results: list[dict], path: Path) -> list[dict]:
    rows = []
    for r in results:
        if r["error"]:
            continue
        matched = {}
        for prod in r["products"]:
            pid = match_product(prod["name"])
            if pid and pid not in matched:
                matched[pid] = prod
        for pid, info in matched.items():
            rows.append({
                "platform": r["platform"], "zone_id": r["zone_id"],
                "zone_name": r["zone_name"], "zone_type": r["zone_type"],
                "store": r.get("store", ""),
                "product_id": pid, "product_name": info["name"],
                "current_price": info["currentPrice"],
                "original_price": info.get("originalPrice", info["currentPrice"]),
                "discount": info.get("discount", ""),
                "delivery_fee": r["delivery_info"].get("delivery_fee", ""),
                "delivery_time_min": r["delivery_info"].get("time_min", ""),
                "delivery_time_max": r["delivery_info"].get("time_max", ""),
                "rating": r["delivery_info"].get("rating", ""),
            })
    if rows:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
    return rows


# ═══════════════════════════════════
#  REPORT GENERATOR
# ═══════════════════════════════════

def generate_report(csv_path: Path):
    """Run the insights report generator."""
    print("\n  Generating insights report...")
    import subprocess
    result = subprocess.run(
        [sys.executable, "generate_insights_report.py"],
        capture_output=True, text=True, encoding="utf-8",
        cwd=str(Path(__file__).parent),
    )
    if result.returncode == 0:
        print("  Report generated successfully!")
        for line in result.stdout.strip().split("\n"):
            if "Saved" in line or "DONE" in line:
                print(f"  {line.strip()}")
    else:
        print(f"  Error: {result.stderr[:300]}")


# ═══════════════════════════════════
#  MAIN
# ═══════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Rappi Competitive Intelligence Demo")
    parser.add_argument("--zones", type=int, default=25, help="Number of zones to scrape (default: 25)")
    parser.add_argument("--skip-rappi", action="store_true", help="Skip Rappi (no login needed)")
    parser.add_argument("--skip-ubereats", action="store_true", help="Skip Uber Eats")
    args = parser.parse_args()

    zones = ADDRESSES[:args.zones]
    do_rappi = not args.skip_rappi
    do_ubereats = not args.skip_ubereats

    print("""
 ============================================================
  RAPPI COMPETITIVE INTELLIGENCE SYSTEM
  Live Demo
 ============================================================
""")
    print(f"  Zones:     {len(zones)}")
    print(f"  Platforms: {'Uber Eats ' if do_ubereats else ''}{'+ Rappi' if do_rappi else ''}")
    print(f"  Products:  {len(TARGET_PRODUCTS)} McDonald's items")
    print()

    all_results = []
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    with sync_playwright() as p:

        # ── STEP 1: Verify Rappi session ──
        rappi_page = None
        if do_rappi:
            print("  [STEP 1] Connecting to Rappi session (port 9222)...")
            try:
                rappi_browser = p.chromium.connect_over_cdp("http://localhost:9222")
                rappi_page = rappi_browser.contexts[0].pages[0]
                current_url = rappi_page.url
                if "login" in current_url:
                    print("  WARNING: Still on login page. Please log in first!")
                    print(f"  Current URL: {current_url}")
                    print("  Waiting 30 seconds for login...")
                    time.sleep(30)
                    if "login" in rappi_page.url:
                        print("  Still not logged in. Skipping Rappi.")
                        do_rappi = False
                    else:
                        print("  Login detected! Continuing...")
                else:
                    print(f"  Connected! URL: {current_url[:80]}")
            except Exception as e:
                print(f"  Could not connect: {e}")
                print("  Run launch_browser.bat first and log into Rappi.")
                print("  Continuing with Uber Eats only...\n")
                do_rappi = False

        # ── STEP 2: Scrape Uber Eats ──
        if do_ubereats:
            print(f"\n  [STEP 2] Scraping Uber Eats ({len(zones)} zones)...")
            print(f"  {'─'*50}")

            ue_browser = p.chromium.launch(headless=False)
            ue_ctx = ue_browser.new_context(
                locale="es-MX",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                viewport={"width": 1920, "height": 1080},
            )
            ue_page = ue_ctx.new_page()

            for i, addr in enumerate(zones):
                print(f"    [{i+1}/{len(zones)}] {addr.name:25s} ({addr.zone_type:8s})", end=" ", flush=True)
                result = scrape_ubereats(ue_page, addr)
                n = sum(1 for pr in result["products"] if match_product(pr["name"]))
                if result["error"]:
                    print(f"ERROR: {result['error'][:50]}")
                else:
                    print(f"OK ({n} products matched)")
                all_results.append(result)
                time.sleep(2)

            ue_browser.close()

        # ── STEP 3: Scrape Rappi ──
        if do_rappi and rappi_page:
            print(f"\n  [STEP 3] Scraping Rappi ({len(zones)} zones)...")
            print(f"  {'─'*50}")

            for i, addr in enumerate(zones):
                print(f"    [{i+1}/{len(zones)}] {addr.name:25s} ({addr.zone_type:8s})", end=" ", flush=True)
                result = scrape_rappi(rappi_page, addr)
                n = sum(1 for pr in result["products"] if match_product(pr["name"]))
                if result["error"]:
                    print(f"ERROR: {result['error'][:50]}")
                else:
                    print(f"OK ({n} products matched)")
                all_results.append(result)
                time.sleep(2)

        # ── STEP 4: Build CSV ──
        print(f"\n  [STEP 4] Building dataset...")
        csv_path = OUTPUT_DIR / "competitive_intel.csv"
        rows = build_csv(all_results, csv_path)
        print(f"    {len(rows)} data points saved to {csv_path}")

        # Save raw JSON
        raw_path = Path(f"data/raw/demo_results_{ts}.json")
        with open(raw_path, "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)

    # ── STEP 5: Generate Report ──
    print(f"\n  [STEP 5] Generating insights report...")
    generate_report(csv_path)

    # ── Summary ──
    print(f"""
 ============================================================
  DEMO COMPLETE
 ============================================================

  Data:    {csv_path}
  Report:  reports/competitive_report.md
  Charts:  reports/chart_*.png

  Summary:
""")
    for platform in ["ubereats", "rappi"]:
        p_results = [r for r in all_results if r["platform"] == platform]
        if p_results:
            ok = sum(1 for r in p_results if not r["error"])
            total = sum(len(r["products"]) for r in p_results)
            print(f"    {platform:>10}: {ok}/{len(p_results)} zones, {total} products")

    print(f"\n    Total data points: {len(rows)}")
    print()


if __name__ == "__main__":
    main()
