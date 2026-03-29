"""
Multi-zone scraper: Uber Eats (guest) + Rappi (via authenticated session).
Scrapes McDonald's prices across 25 CDMX zones.

Usage:
    python scrape_multi_zone.py                  # Both platforms
    python scrape_multi_zone.py --ubereats-only  # Only Uber Eats (no login needed)
    python scrape_multi_zone.py --rappi-only     # Only Rappi (needs Chromium session)
"""

import sys
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

from playwright.sync_api import sync_playwright
from config import ADDRESSES

# Target products to extract (case-insensitive match)
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

OUTPUT_DIR = Path("data/processed")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def match_product(name: str) -> str | None:
    """Match a product name to a target product ID."""
    name_lower = name.lower().strip()
    for prod_id, keywords in TARGET_PRODUCTS.items():
        for kw in keywords:
            if kw in name_lower:
                return prod_id
    return None


def extract_products_from_page(page) -> list[dict]:
    """Extract product names and prices from a menu page."""
    products = page.evaluate(r"""() => {
        const items = [];
        const cards = document.querySelectorAll('[data-qa*="product"], [data-testid*="menu-item"], li[class*="menu"], div[class*="menu-item"]');

        for (const card of cards) {
            const text = (card.innerText || '').trim();
            if (!text || text.length > 400) continue;

            const lines = text.split('\n').map(l => l.trim()).filter(l => l);
            const name = lines[0] || '';
            if (name.length < 3 || name.length > 80) continue;

            const prices = [];
            let discount = null;

            for (const line of lines.slice(1)) {
                if (line.match(/^-\d+%$/)) {
                    discount = line;
                } else if (line.match(/^\$\s*[\d,.]+$/)) {
                    prices.push(parseFloat(line.replace('$','').replace(',','').trim()));
                }
            }

            if (prices.length === 0) continue;

            items.push({
                name: name,
                currentPrice: prices[0],
                originalPrice: prices.length > 1 && discount ? prices[1] : prices[0],
                discount: discount,
            });
        }

        const seen = new Set();
        return items.filter(item => {
            if (seen.has(item.name)) return false;
            seen.add(item.name);
            return true;
        });
    }""")
    return products


def extract_delivery_info_text(page) -> dict:
    """Extract delivery fee and time from page text."""
    body = page.inner_text("body")[:2000]
    info = {}

    if "gratis" in body.lower()[:600] or "free" in body.lower()[:600]:
        info["delivery_fee"] = 0.0
    else:
        fee = re.search(r"(?:envío|delivery|fee)[:\s]*\$?\s*(\d+(?:\.\d+)?)", body[:600], re.I)
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


# ──────────────────────────────────────────────
#  UBER EATS (guest access)
# ──────────────────────────────────────────────

def make_ubereats_search_url(address) -> str:
    """Build Uber Eats search URL with embedded address coordinates."""
    payload = {
        "address": address.street,
        "reference": "",
        "referenceType": "google_places",
        "latitude": address.lat,
        "longitude": address.lon,
    }
    encoded = base64.b64encode(json.dumps(payload).encode()).decode()
    return f"https://www.ubereats.com/mx/search?pl={urllib.parse.quote(encoded)}&q=McDonald%27s"


def scrape_ubereats_zone(page, address, is_first: bool = False) -> dict:
    """Scrape Uber Eats McDonald's for a single zone via direct URL."""
    result = {
        "platform": "ubereats",
        "zone_id": address.id,
        "zone_name": address.name,
        "zone_type": address.zone_type,
        "address": address.street,
        "store": None,
        "delivery_info": {},
        "products": [],
        "error": None,
    }

    try:
        # Navigate directly to McDonald's search for this address
        search_url = make_ubereats_search_url(address)
        page.goto(search_url, timeout=25000, wait_until="domcontentloaded")
        time.sleep(5)

        # Find first McDonald's store link
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
            result["error"] = "No McDonald's found in this zone"
            return result

        if not store_url.startswith("http"):
            store_url = f"https://www.ubereats.com{store_url}"

        page.goto(store_url, timeout=25000, wait_until="domcontentloaded")
        time.sleep(5)

        # Get store name from URL
        store_name_match = re.search(r"/store/([^/]+)/", page.url)
        result["store"] = store_name_match.group(1) if store_name_match else "unknown"

        # Extract delivery info
        result["delivery_info"] = extract_delivery_info_text(page)

        # Scroll to load menu
        for _ in range(8):
            page.mouse.wheel(0, 800)
            time.sleep(0.5)

        # Extract products
        all_products = extract_products_from_page(page)
        if not all_products:
            # Fallback: parse from body text
            body = page.inner_text("body")
            lines = body.split("\n")
            for i, line in enumerate(lines):
                line = line.strip()
                if not line or len(line) > 80 or line.startswith("$"):
                    continue
                for j in range(i+1, min(i+3, len(lines))):
                    pm = re.match(r"^\$\s*(\d[\d,.]*)", lines[j].strip())
                    if pm:
                        all_products.append({
                            "name": line,
                            "currentPrice": float(pm.group(1).replace(",", "")),
                            "originalPrice": float(pm.group(1).replace(",", "")),
                            "discount": None,
                        })
                        break

        result["products"] = all_products

    except Exception as e:
        result["error"] = str(e)[:200]

    return result


# ──────────────────────────────────────────────
#  RAPPI (requires authenticated Chromium session)
# ──────────────────────────────────────────────

def scrape_rappi_zone(page, address) -> dict:
    """Scrape Rappi McDonald's for a single zone using authenticated session."""
    result = {
        "platform": "rappi",
        "zone_id": address.id,
        "zone_name": address.name,
        "zone_type": address.zone_type,
        "address": address.street,
        "store": None,
        "delivery_info": {},
        "products": [],
        "error": None,
    }

    try:
        # Change delivery address in Rappi
        # Navigate to main page and change address
        page.goto("https://www.rappi.com.mx", timeout=20000, wait_until="domcontentloaded")
        time.sleep(3)

        # Click on the address bar/selector at top
        addr_btn = page.locator(
            "[data-qa='address-selector'], "
            "[class*='address'], "
            "button:has-text('Calle'), button:has-text('Av'), "
            "[class*='AddressBar'], [class*='location']"
        ).first

        if addr_btn and addr_btn.is_visible():
            addr_btn.click()
            time.sleep(2)

        # Look for address input
        addr_input = page.locator(
            "input[placeholder*='direcci'], input[placeholder*='Busca tu direcci'], "
            "input[placeholder*='ubica'], input[data-qa*='address-input']"
        ).first

        if addr_input and addr_input.is_visible():
            addr_input.click()
            time.sleep(0.5)
            addr_input.fill("")
            time.sleep(0.3)
            addr_input.fill(address.street)
            time.sleep(3)

            # Click suggestion
            sug = page.locator(
                "[class*='suggestion'], [class*='Suggestion'], "
                "[data-qa*='suggestion'], [role='option']"
            ).first
            if sug and sug.is_visible():
                sug.click()
                time.sleep(3)
            else:
                page.keyboard.press("ArrowDown")
                time.sleep(0.3)
                page.keyboard.press("Enter")
                time.sleep(3)

            # Confirm address if there's a confirm button
            confirm = page.locator(
                "button:has-text('Confirmar'), button:has-text('Guardar'), "
                "button:has-text('Aceptar')"
            ).first
            if confirm and confirm.is_visible():
                confirm.click()
                time.sleep(3)

        # Search for McDonald's
        page.goto(
            "https://www.rappi.com.mx/restaurantes/busqueda?term=McDonald%27s",
            timeout=20000, wait_until="domcontentloaded"
        )
        time.sleep(4)

        # Find McDonald's store link
        mc_link = page.locator("a[href*='mcdonalds']").first
        if mc_link and mc_link.is_visible():
            href = mc_link.get_attribute("href") or ""
            if not href.startswith("http"):
                href = f"https://www.rappi.com.mx{href}"
            page.goto(href, timeout=20000, wait_until="domcontentloaded")
            time.sleep(4)

            store_match = re.search(r"restaurantes/\d+-(.+)", page.url)
            result["store"] = store_match.group(1) if store_match else "mcdonalds"

            # Extract delivery info
            result["delivery_info"] = extract_delivery_info_text(page)

            # Scroll to load menu
            for _ in range(8):
                page.mouse.wheel(0, 800)
                time.sleep(0.5)

            # Extract products
            result["products"] = extract_products_from_page(page)
        else:
            result["error"] = "No McDonald's found in search results"

    except Exception as e:
        result["error"] = str(e)[:200]

    return result


# ──────────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────────

def build_comparison_csv(all_results: list[dict], path: Path):
    """Build a CSV comparing target products across zones and platforms."""
    rows = []
    for result in all_results:
        if result["error"]:
            continue

        # Match products to targets
        matched = {}
        for prod in result["products"]:
            prod_id = match_product(prod["name"])
            if prod_id and prod_id not in matched:
                matched[prod_id] = prod

        for prod_id, prod_info in matched.items():
            row = {
                "platform": result["platform"],
                "zone_id": result["zone_id"],
                "zone_name": result["zone_name"],
                "zone_type": result["zone_type"],
                "store": result.get("store", ""),
                "product_id": prod_id,
                "product_name": prod_info["name"],
                "current_price": prod_info["currentPrice"],
                "original_price": prod_info.get("originalPrice", prod_info["currentPrice"]),
                "discount": prod_info.get("discount", ""),
                "delivery_fee": result["delivery_info"].get("delivery_fee", ""),
                "delivery_time_min": result["delivery_info"].get("time_min", ""),
                "delivery_time_max": result["delivery_info"].get("time_max", ""),
                "rating": result["delivery_info"].get("rating", ""),
            }
            rows.append(row)

    if rows:
        fieldnames = list(rows[0].keys())
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"\n  CSV saved: {path} ({len(rows)} rows)")

    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ubereats-only", action="store_true")
    parser.add_argument("--rappi-only", action="store_true")
    args = parser.parse_args()

    do_ubereats = not args.rappi_only
    do_rappi = not args.ubereats_only

    all_results = []
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    print(f"{'='*60}")
    print(f"  MULTI-ZONE SCRAPER — {len(ADDRESSES)} zones")
    print(f"  Platforms: {'Uber Eats' if do_ubereats else ''} {'Rappi' if do_rappi else ''}")
    print(f"{'='*60}")

    with sync_playwright() as p:
        # ── UBER EATS (independent browser, guest access) ──
        if do_ubereats:
            print(f"\n{'─'*60}")
            print("  UBER EATS (guest access)")
            print(f"{'─'*60}")

            browser_ue = p.chromium.launch(headless=False)
            ctx_ue = browser_ue.new_context(
                locale="es-MX",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
            )
            page_ue = ctx_ue.new_page()

            for i, addr in enumerate(ADDRESSES):
                print(f"\n  [{i+1}/{len(ADDRESSES)}] {addr.name} ({addr.zone_type})...", end=" ", flush=True)
                result = scrape_ubereats_zone(page_ue, addr, is_first=(i == 0))
                n_products = len(result["products"])
                n_matched = sum(1 for prod in result["products"] if match_product(prod["name"]))

                if result["error"]:
                    print(f"ERROR: {result['error'][:60]}")
                else:
                    fee = result["delivery_info"].get("delivery_fee", "?")
                    print(f"OK — {n_products} products ({n_matched} matched), fee=${fee}")

                all_results.append(result)
                time.sleep(2)  # Rate limiting

            browser_ue.close()

        # ── RAPPI (connect to authenticated session) ──
        if do_rappi:
            print(f"\n{'─'*60}")
            print("  RAPPI (authenticated session on port 9222)")
            print(f"{'─'*60}")

            try:
                browser_r = p.chromium.connect_over_cdp("http://localhost:9222")
                page_r = browser_r.contexts[0].pages[0]

                for i, addr in enumerate(ADDRESSES):
                    print(f"\n  [{i+1}/{len(ADDRESSES)}] {addr.name} ({addr.zone_type})...", end=" ", flush=True)
                    result = scrape_rappi_zone(page_r, addr)
                    n_products = len(result["products"])
                    n_matched = sum(1 for prod in result["products"] if match_product(prod["name"]))

                    if result["error"]:
                        print(f"ERROR: {result['error'][:60]}")
                    else:
                        fee = result["delivery_info"].get("delivery_fee", "?")
                        print(f"OK — {n_products} products ({n_matched} matched), fee=${fee}")

                    all_results.append(result)
                    time.sleep(2)

            except Exception as e:
                print(f"\n  Could not connect to Rappi session: {e}")
                print("  Make sure Chromium is running with --remote-debugging-port=9222")

    # Save raw results
    raw_path = Path(f"data/raw/multizone_results_{timestamp}.json")
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\n  Raw JSON: {raw_path}")

    # Build comparison CSV
    csv_path = OUTPUT_DIR / f"competitive_intel_{timestamp}.csv"
    rows = build_comparison_csv(all_results, csv_path)

    # Also save as latest
    latest_csv = OUTPUT_DIR / "competitive_intel.csv"
    build_comparison_csv(all_results, latest_csv)

    # Summary
    print(f"\n{'='*60}")
    print(f"  SUMMARY")
    print(f"{'='*60}")
    for platform in ["ubereats", "rappi"]:
        p_results = [r for r in all_results if r["platform"] == platform]
        if not p_results:
            continue
        success = sum(1 for r in p_results if not r["error"])
        total_products = sum(len(r["products"]) for r in p_results)
        print(f"  {platform:>10}: {success}/{len(p_results)} zones OK, {total_products} products total")

    print(f"\n  Total data points: {len(rows) if rows else 0}")
    print(f"  Output: {csv_path}")


if __name__ == "__main__":
    main()
