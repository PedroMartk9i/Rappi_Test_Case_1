"""
Test de scraping real v2 — Usa Playwright Chromium directamente + Fetcher HTTP.
Cada plataforma se prueba con múltiples estrategias y se documentan hallazgos.
"""

import json
import os
import re
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

# Fix Windows encoding
os.environ["PYTHONIOENCODING"] = "utf-8"
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from scrapling.fetchers import Fetcher

DATA_DIR = Path("data/raw")
DATA_DIR.mkdir(parents=True, exist_ok=True)

TEST_LAT = 19.4326
TEST_LON = -99.1942

all_results = {
    "test_timestamp": datetime.now(timezone.utc).isoformat(),
    "platforms": {},
}


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def save_sample(name, content, max_chars=10000):
    path = DATA_DIR / f"sample_{name}.html"
    path.write_text(content[:max_chars], encoding="utf-8")
    log(f"  Muestra guardada: {path}")


def extract_prices_from_text(text):
    """Extraer precios en formato $XX.XX del texto."""
    return re.findall(r"\$\s*(\d{1,4}(?:[.,]\d{2})?)", text)


# ═══════════════════════════════════════════════════════════
# RAPPI
# ═══════════════════════════════════════════════════════════
def test_rappi():
    log("=" * 60)
    log("TEST: RAPPI")
    log("=" * 60)

    results = {"attempts": [], "findings": [], "data": []}

    # Intento 1: HTTP a la página de restaurantes
    log("\n[Rappi] 1/4: Fetcher HTTP - pagina restaurantes")
    try:
        url = "https://www.rappi.com.mx/restaurantes"
        response = Fetcher.get(url, stealthy_headers=True, follow_redirects=True, timeout=30)
        status = response.status
        text = response.text or ""
        log(f"  Status: {status}, Length: {len(text)}")

        if len(text) < 100:
            log(f"  Contenido: {repr(text)}")
            results["findings"].append("Rappi retorna respuesta minima via HTTP (SPA, requiere JS)")

        results["attempts"].append({"url": url, "status": status, "length": len(text)})
    except Exception as e:
        log(f"  Error: {e}")
        results["attempts"].append({"url": url, "error": str(e)})

    time.sleep(3)

    # Intento 2: API microservicios de Rappi
    log("\n[Rappi] 2/4: Fetcher HTTP - API microservicios")
    api_endpoints = [
        ("store-search", f"https://www.rappi.com.mx/api/web-gateway/web/stores-router/search?lat={TEST_LAT}&lng={TEST_LON}&query=mcdonalds&is_prime=false"),
        ("pns-global-search", f"https://www.rappi.com.mx/api/pns-global-search-api/v1/unified-search?lat={TEST_LAT}&lng={TEST_LON}&query=mcdonalds"),
        ("dynamic-mkt", f"https://www.rappi.com.mx/api/dynamic-mkt-gateway-api/api/web-gateway/web/dynamic/context/content/storeslist_v2?lat={TEST_LAT}&lng={TEST_LON}"),
        ("restaurants-category", f"https://www.rappi.com.mx/api/web-gateway/web/dynamic/context/content/restaurants?lat={TEST_LAT}&lng={TEST_LON}"),
    ]

    for name, api_url in api_endpoints:
        try:
            log(f"  Probando: {name}")
            headers = {
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "es-MX,es;q=0.9",
                "Referer": "https://www.rappi.com.mx/restaurantes",
                "X-Guest-API-Key": "token",
            }
            response = Fetcher.get(api_url, stealthy_headers=True, follow_redirects=True, timeout=15)
            status = response.status
            text = response.text or ""
            log(f"    Status: {status}, Length: {len(text)}")

            # Intentar parsear como JSON
            is_json = False
            try:
                data = json.loads(text)
                is_json = True
                keys = list(data.keys()) if isinstance(data, dict) else f"array[{len(data)}]"
                log(f"    JSON keys: {keys}")
                save_sample(f"rappi_api_{name}", json.dumps(data, indent=2, ensure_ascii=False))
            except (json.JSONDecodeError, ValueError):
                if text:
                    log(f"    No es JSON. Preview: {text[:150]}")

            results["attempts"].append({
                "url": api_url, "name": name, "status": status,
                "length": len(text), "is_json": is_json,
            })

        except Exception as e:
            log(f"    Error: {e}")
            results["attempts"].append({"url": api_url, "name": name, "error": str(e)})

        time.sleep(3)

    # Intento 3: Playwright Chromium directo
    log("\n[Rappi] 3/4: Playwright Chromium - pagina restaurantes")
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                locale="es-MX",
                geolocation={"latitude": TEST_LAT, "longitude": TEST_LON},
                permissions=["geolocation"],
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            )
            page = context.new_page()

            # Capturar requests de API
            api_responses = []
            def handle_response(response):
                if "api" in response.url and response.status == 200:
                    try:
                        body = response.text()
                        if body and len(body) > 100:
                            api_responses.append({
                                "url": response.url[:200],
                                "status": response.status,
                                "length": len(body),
                                "preview": body[:300],
                            })
                    except:
                        pass

            page.on("response", handle_response)

            url = f"https://www.rappi.com.mx/restaurantes?lat={TEST_LAT}&lng={TEST_LON}&term=mcdonalds"
            log(f"  Navegando a: {url}")
            page.goto(url, timeout=45000, wait_until="networkidle")
            time.sleep(5)  # Esperar carga dinámica

            # Screenshot
            screenshot_path = DATA_DIR / "screenshot_rappi.png"
            page.screenshot(path=str(screenshot_path), full_page=False)
            log(f"  Screenshot guardado: {screenshot_path}")

            # Contenido
            content = page.content()
            text = page.inner_text("body")
            log(f"  HTML length: {len(content)}, Text length: {len(text)}")
            save_sample("rappi_playwright", content)

            # Buscar precios
            prices_found = extract_prices_from_text(text)
            log(f"  Precios encontrados en texto: {prices_found[:20]}")

            # Buscar McDonald's
            mcdonalds_mentions = len(re.findall(r"mcdonald", text, re.I))
            log(f"  Menciones McDonald's: {mcdonalds_mentions}")

            # Buscar elementos con data attributes
            price_els = page.query_selector_all("[class*='price'], [class*='Price'], [data-qa*='price']")
            log(f"  Elementos de precio en DOM: {len(price_els)}")

            product_els = page.query_selector_all("[class*='product'], [class*='Product'], [class*='store'], [class*='Store']")
            log(f"  Elementos de producto/store en DOM: {len(product_els)}")

            # API requests interceptados
            log(f"  API responses capturadas: {len(api_responses)}")
            for i, ar in enumerate(api_responses[:10]):
                log(f"    API {i}: {ar['url'][:100]} (status={ar['status']}, len={ar['length']})")

            if api_responses:
                save_sample("rappi_intercepted_apis", json.dumps(api_responses, indent=2, ensure_ascii=False))
                results["findings"].append(f"Se interceptaron {len(api_responses)} API responses internas")

            results["attempts"].append({
                "method": "Playwright Chromium",
                "html_length": len(content),
                "text_length": len(text),
                "prices_found": prices_found[:20],
                "mcdonalds_mentions": mcdonalds_mentions,
                "price_elements": len(price_els),
                "product_elements": len(product_els),
                "api_responses_captured": len(api_responses),
                "success": True,
            })

            browser.close()

    except Exception as e:
        log(f"  Error: {e}")
        log(f"  {traceback.format_exc()}")
        results["attempts"].append({"method": "Playwright Chromium", "error": str(e)})

    # Intento 4: Buscar URL directa de McDonald's en Rappi
    log("\n[Rappi] 4/4: Playwright - McDonald's page directa")
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                locale="es-MX",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            )
            page = context.new_page()

            # Probar diferentes URLs conocidas de McDonald's en Rappi
            mcdonalds_urls = [
                f"https://www.rappi.com.mx/restaurantes/900043937-mcdonalds?lat={TEST_LAT}&lng={TEST_LON}",
                f"https://www.rappi.com.mx/tiendas/mcdonalds?lat={TEST_LAT}&lng={TEST_LON}",
            ]

            for mcd_url in mcdonalds_urls:
                log(f"  Probando: {mcd_url[:80]}...")
                try:
                    page.goto(mcd_url, timeout=30000, wait_until="domcontentloaded")
                    time.sleep(3)
                    text = page.inner_text("body")
                    prices = extract_prices_from_text(text)
                    log(f"    Text length: {len(text)}, Precios: {prices[:10]}")

                    if prices:
                        save_sample("rappi_mcdonalds_direct", page.content())
                        results["findings"].append(f"McDonald's directo: precios encontrados: {prices[:10]}")
                        results["data"].extend(prices[:10])
                        break
                except Exception as e:
                    log(f"    Error: {e}")

            browser.close()

    except Exception as e:
        log(f"  Error: {e}")

    all_results["platforms"]["rappi"] = results
    return results


# ═══════════════════════════════════════════════════════════
# UBER EATS
# ═══════════════════════════════════════════════════════════
def test_ubereats():
    log("\n" + "=" * 60)
    log("TEST: UBER EATS")
    log("=" * 60)

    results = {"attempts": [], "findings": [], "data": []}

    # Intento 1: HTTP directo
    log("\n[UberEats] 1/3: Fetcher HTTP")
    try:
        url = f"https://www.ubereats.com/mx/search?q=McDonald%27s&pl={TEST_LAT}%2C{TEST_LON}"
        response = Fetcher.get(url, stealthy_headers=True, follow_redirects=True, timeout=30)
        status = response.status
        text = response.text or ""
        log(f"  Status: {status}, Length: {len(text)}")

        if "cloudflare" in text.lower() or len(text) < 100:
            results["findings"].append("UberEats protegido por Cloudflare o retorna SPA vacía")
            log("  Cloudflare/SPA detectado")

        results["attempts"].append({"url": url, "status": status, "length": len(text)})
        save_sample("ubereats_fetcher", text)
    except Exception as e:
        log(f"  Error: {e}")
        results["attempts"].append({"url": url, "error": str(e)})

    time.sleep(3)

    # Intento 2: Playwright Chromium
    log("\n[UberEats] 2/3: Playwright Chromium - busqueda")
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                locale="es-MX",
                geolocation={"latitude": TEST_LAT, "longitude": TEST_LON},
                permissions=["geolocation"],
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            )
            page = context.new_page()

            api_responses = []
            def handle_response(response):
                if any(x in response.url for x in ["getSearchSuggestions", "getFeed", "getStoreV1", "eats"]) and response.status == 200:
                    try:
                        body = response.text()
                        if body and len(body) > 100:
                            api_responses.append({
                                "url": response.url[:200],
                                "status": response.status,
                                "length": len(body),
                                "preview": body[:500],
                            })
                    except:
                        pass

            page.on("response", handle_response)

            url = f"https://www.ubereats.com/mx/search?q=McDonald%27s&pl={TEST_LAT}%2C{TEST_LON}"
            log(f"  Navegando a: {url}")
            page.goto(url, timeout=45000, wait_until="networkidle")
            time.sleep(5)

            screenshot_path = DATA_DIR / "screenshot_ubereats.png"
            page.screenshot(path=str(screenshot_path), full_page=False)
            log(f"  Screenshot guardado: {screenshot_path}")

            content = page.content()
            text = page.inner_text("body")
            log(f"  HTML length: {len(content)}, Text length: {len(text)}")
            save_sample("ubereats_playwright", content)

            prices_found = extract_prices_from_text(text)
            log(f"  Precios encontrados: {prices_found[:20]}")

            mcdonalds_mentions = len(re.findall(r"mcdonald", text, re.I))
            log(f"  Menciones McDonald's: {mcdonalds_mentions}")

            # Buscar store cards de UE
            cards = page.query_selector_all("[data-testid*='store'], [data-testid*='search-result'], a[href*='store']")
            log(f"  Store cards: {len(cards)}")

            fee_els = page.query_selector_all("[class*='fee'], [class*='Fee'], [class*='delivery']")
            log(f"  Fee elements: {len(fee_els)}")

            log(f"  API responses capturadas: {len(api_responses)}")
            for ar in api_responses[:5]:
                log(f"    {ar['url'][:100]}")

            if api_responses:
                save_sample("ubereats_intercepted_apis", json.dumps(api_responses, indent=2, ensure_ascii=False))

            results["attempts"].append({
                "method": "Playwright Chromium",
                "html_length": len(content),
                "text_length": len(text),
                "prices_found": prices_found[:20],
                "mcdonalds_mentions": mcdonalds_mentions,
                "store_cards": len(cards),
                "success": True,
            })

            browser.close()

    except Exception as e:
        log(f"  Error: {e}")
        results["attempts"].append({"method": "Playwright Chromium", "error": str(e)})

    # Intento 3: URL directa de store
    log("\n[UberEats] 3/3: Playwright - McDonald's store directo")
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                locale="es-MX",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            )
            page = context.new_page()

            store_url = f"https://www.ubereats.com/mx/store/mcdonalds-polanco/store-id?pl={TEST_LAT},{TEST_LON}"
            log(f"  Probando URL directa...")
            try:
                page.goto("https://www.ubereats.com/mx/search?q=McDonalds", timeout=30000, wait_until="domcontentloaded")
                time.sleep(3)
                text = page.inner_text("body")
                prices = extract_prices_from_text(text)
                log(f"    Text: {len(text)} chars, Precios: {prices[:10]}")

                if prices:
                    results["data"].extend(prices[:10])
                    results["findings"].append(f"Precios extraidos de UberEats: {prices[:10]}")
            except Exception as e:
                log(f"    Error: {e}")

            browser.close()

    except Exception as e:
        log(f"  Error: {e}")

    all_results["platforms"]["ubereats"] = results
    return results


# ═══════════════════════════════════════════════════════════
# DIDI FOOD
# ═══════════════════════════════════════════════════════════
def test_didifood():
    log("\n" + "=" * 60)
    log("TEST: DIDI FOOD")
    log("=" * 60)

    results = {"attempts": [], "findings": [], "data": []}

    # Intento 1: HTTP
    log("\n[DiDiFood] 1/2: Fetcher HTTP")
    try:
        url = "https://www.didifood.com/es-MX"
        response = Fetcher.get(url, stealthy_headers=True, follow_redirects=True, timeout=30)
        status = response.status
        text = response.text or ""
        final_url = str(response.url) if hasattr(response, 'url') else url

        log(f"  Status: {status}, Length: {len(text)}")
        log(f"  Final URL: {final_url}")

        if "forsale" in final_url.lower() or "dynadot" in text.lower():
            results["findings"].append("didifood.com dominio en venta - DiDi Food cerro operaciones en Mexico")
            log("  HALLAZGO: Dominio en venta (forsale.dynadot.com)")
        elif "didi" in text.lower() and "food" in text.lower():
            log("  Pagina de DiDi Food cargada")

        save_sample("didifood_fetcher", text)
        results["attempts"].append({"url": url, "status": status, "length": len(text), "final_url": final_url})
    except Exception as e:
        log(f"  Error: {e}")
        results["attempts"].append({"url": url, "error": str(e)})

    time.sleep(3)

    # Intento 2: Probar dominio alternativo
    log("\n[DiDiFood] 2/2: URLs alternativas")
    alt_urls = [
        "https://food.didiglobal.com/es-MX",
        "https://page.didifood.com/es-MX",
    ]
    for alt_url in alt_urls:
        try:
            log(f"  Probando: {alt_url}")
            response = Fetcher.get(alt_url, stealthy_headers=True, follow_redirects=True, timeout=15)
            status = response.status
            text = response.text or ""
            log(f"    Status: {status}, Length: {len(text)}")
            results["attempts"].append({"url": alt_url, "status": status, "length": len(text)})
        except Exception as e:
            log(f"    Error: {e}")
            results["attempts"].append({"url": alt_url, "error": str(e)})
        time.sleep(3)

    if not results["findings"]:
        results["findings"].append("DiDi Food: plataforma no accesible en Mexico")

    all_results["platforms"]["didifood"] = results
    return results


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    log("=" * 60)
    log("  SCRAPING REAL v2 - Competitive Intelligence")
    log(f"  Ubicacion: Polanco, CDMX ({TEST_LAT}, {TEST_LON})")
    log("=" * 60)

    # Verificar Playwright
    try:
        from playwright.sync_api import sync_playwright
        log("Playwright disponible")
    except ImportError:
        log("ERROR: Playwright no instalado. Ejecutar: pip install playwright && playwright install chromium")
        sys.exit(1)

    test_rappi()
    time.sleep(5)

    test_ubereats()
    time.sleep(5)

    test_didifood()

    # Guardar resultados
    results_path = DATA_DIR / "scraping_test_results_v2.json"
    results_path.write_text(
        json.dumps(all_results, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    log(f"\n{'='*60}")
    log("RESUMEN FINAL:")
    log(f"{'='*60}")
    for platform, data in all_results["platforms"].items():
        findings = data.get("findings", [])
        log(f"\n  {platform.upper()}:")
        for f in findings:
            log(f"    - {f}")
        if not findings:
            log("    (sin hallazgos significativos)")

    log(f"\nResultados: {results_path}")
    log(f"Screenshots: {DATA_DIR}/screenshot_*.png")
    log(f"Muestras HTML: {DATA_DIR}/sample_*.html")
