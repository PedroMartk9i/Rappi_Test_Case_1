"""
Test de StealthyFetcher contra las 3 plataformas.
Ejecuta cada test en un subproceso separado para evitar conflictos de asyncio.
"""

import subprocess
import sys
import json
import time
from pathlib import Path
from datetime import datetime, timezone

PYTHON = sys.executable
DATA_DIR = Path("data/raw")
DATA_DIR.mkdir(parents=True, exist_ok=True)

TEST_LAT = 19.4326
TEST_LON = -99.1942


def run_stealthy_test(platform: str, url: str) -> dict:
    """Ejecutar test de StealthyFetcher en subproceso aislado."""
    script = f'''
import sys, json, time, traceback
sys.stdout.reconfigure(encoding="utf-8")

result = {{"platform": "{platform}", "url": "{url}", "method": "StealthyFetcher"}}
try:
    from scrapling.fetchers import StealthyFetcher
    print(f"[{platform}] Lanzando StealthyFetcher...", flush=True)
    print(f"[{platform}] URL: {url}", flush=True)

    page = StealthyFetcher.fetch("{url}", headless=True, network_idle=True, timeout=60000)

    if page:
        page_text = page.text if hasattr(page, "text") else str(page)
        page_html = str(page.html) if hasattr(page, "html") else ""
        content_len = len(page_text) if page_text else 0
        html_len = len(page_html) if page_html else 0

        print(f"[{platform}] Content text length: {{content_len}}", flush=True)
        print(f"[{platform}] HTML length: {{html_len}}", flush=True)

        result["content_length"] = content_len
        result["html_length"] = html_len
        result["success"] = True

        # Guardar muestra
        sample_path = "data/raw/sample_{platform}_stealthy.html"
        with open(sample_path, "w", encoding="utf-8") as f:
            f.write(page_html[:50000] if page_html else page_text[:50000] if page_text else "EMPTY")
        print(f"[{platform}] Muestra HTML guardada: {{sample_path}}", flush=True)

        # Buscar precios
        try:
            prices = page.css("[class*=\\"price\\"], [class*=\\"Price\\"], [data-qa*=\\"price\\"]")
            result["price_elements"] = len(prices)
            print(f"[{platform}] Elementos de precio: {{len(prices)}}", flush=True)
            for i, p in enumerate(prices[:10]):
                txt = p.text[:100] if hasattr(p, "text") and p.text else ""
                print(f"[{platform}]   Precio {{i}}: {{txt}}", flush=True)
        except Exception as e:
            print(f"[{platform}] Error buscando precios: {{e}}", flush=True)

        # Buscar productos
        try:
            products = page.css("[class*=\\"product\\"], [class*=\\"Product\\"], [class*=\\"menu-item\\"], [class*=\\"MenuItem\\"]")
            result["product_elements"] = len(products)
            print(f"[{platform}] Elementos de producto: {{len(products)}}", flush=True)
            for i, p in enumerate(products[:5]):
                txt = p.text[:200] if hasattr(p, "text") and p.text else ""
                print(f"[{platform}]   Producto {{i}}: {{txt}}", flush=True)
        except Exception as e:
            print(f"[{platform}] Error buscando productos: {{e}}", flush=True)

        # Buscar delivery info
        try:
            delivery = page.css("[class*=\\"deliver\\"], [class*=\\"Deliver\\"], [class*=\\"eta\\"], [class*=\\"time\\"]")
            result["delivery_elements"] = len(delivery)
            print(f"[{platform}] Elementos delivery: {{len(delivery)}}", flush=True)
            for i, d in enumerate(delivery[:5]):
                txt = d.text[:100] if hasattr(d, "text") and d.text else ""
                print(f"[{platform}]   Delivery {{i}}: {{txt}}", flush=True)
        except Exception as e:
            pass

        # Buscar links a McDonald's
        try:
            mcdonalds = page.css("a[href*=\\"mcdonald\\"], a[href*=\\"mcdonalds\\"]")
            result["mcdonalds_links"] = len(mcdonalds)
            print(f"[{platform}] Links a McDonald's: {{len(mcdonalds)}}", flush=True)
            for i, link in enumerate(mcdonalds[:5]):
                href = link.attrib.get("href", "") if hasattr(link, "attrib") else ""
                txt = link.text[:100] if hasattr(link, "text") and link.text else ""
                print(f"[{platform}]   Link {{i}}: {{href}} | {{txt}}", flush=True)
        except Exception as e:
            pass

        # Page title
        try:
            title = page.css("title")
            if title:
                result["page_title"] = title[0].text[:200] if title[0].text else ""
                print(f"[{platform}] Page title: {{result['page_title']}}", flush=True)
        except:
            pass

        # Detectar bloqueos
        text_lower = (page_text or "").lower()
        blocked_signals = ["captcha", "challenge", "blocked", "access denied", "cloudflare", "robot"]
        result["blocked_signals"] = [s for s in blocked_signals if s in text_lower]
        if result["blocked_signals"]:
            print(f"[{platform}] BLOQUEO detectado: {{result['blocked_signals']}}", flush=True)

    else:
        result["success"] = False
        print(f"[{platform}] StealthyFetcher retorno None", flush=True)

except Exception as e:
    result["success"] = False
    result["error"] = str(e)
    result["traceback"] = traceback.format_exc()
    print(f"[{platform}] ERROR: {{e}}", flush=True)

print(f"RESULT_JSON:{{json.dumps(result)}}", flush=True)
'''

    print(f"\n{'='*60}")
    print(f"TESTING: {platform.upper()} via StealthyFetcher")
    print(f"URL: {url}")
    print(f"{'='*60}")

    try:
        proc = subprocess.run(
            [PYTHON, "-c", script],
            capture_output=True, text=True, timeout=120,
            encoding="utf-8", errors="replace",
        )

        output = proc.stdout + proc.stderr
        print(output)

        # Extraer resultado JSON
        for line in output.split("\n"):
            if line.startswith("RESULT_JSON:"):
                return json.loads(line[len("RESULT_JSON:"):])

        return {"platform": platform, "success": False, "error": "No result JSON found", "output": output[:1000]}

    except subprocess.TimeoutExpired:
        print(f"[{platform}] TIMEOUT (120s)")
        return {"platform": platform, "success": False, "error": "Timeout 120s"}
    except Exception as e:
        print(f"[{platform}] Error subproceso: {e}")
        return {"platform": platform, "success": False, "error": str(e)}


if __name__ == "__main__":
    print("=" * 60)
    print("  STEALTHY FETCHER TESTS — Scraping Real")
    print(f"  {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    all_results = {}

    # Test Rappi
    rappi_result = run_stealthy_test(
        "rappi",
        f"https://www.rappi.com.mx/restaurantes?lat={TEST_LAT}&lng={TEST_LON}&term=mcdonalds",
    )
    all_results["rappi"] = rappi_result
    time.sleep(5)

    # Test Uber Eats
    ubereats_result = run_stealthy_test(
        "ubereats",
        f"https://www.ubereats.com/mx/search?q=McDonald%27s&pl={TEST_LAT}%2C{TEST_LON}",
    )
    all_results["ubereats"] = ubereats_result
    time.sleep(5)

    # Test DiDi Food
    didifood_result = run_stealthy_test(
        "didifood",
        "https://www.didifood.com/es-MX",
    )
    all_results["didifood"] = didifood_result

    # Guardar resultados
    results_path = DATA_DIR / "stealthy_test_results.json"
    results_path.write_text(
        json.dumps(all_results, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    print(f"\n{'='*60}")
    print("RESUMEN FINAL:")
    print(f"{'='*60}")
    for platform, result in all_results.items():
        status = "OK" if result.get("success") else "FAIL"
        blocked = result.get("blocked_signals", [])
        error = result.get("error", "")
        print(f"  {platform}: {status}", end="")
        if blocked:
            print(f" (blocked: {blocked})", end="")
        if error:
            print(f" (error: {error[:80]})", end="")
        print()

    print(f"\nResultados guardados en: {results_path}")
