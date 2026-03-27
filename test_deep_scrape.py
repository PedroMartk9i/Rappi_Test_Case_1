"""
Scraping profundo: navegar al menu de McDonald's en Rappi y Uber Eats
para extraer precios reales de productos.
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

os.environ["PYTHONIOENCODING"] = "utf-8"
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from playwright.sync_api import sync_playwright

DATA_DIR = Path("data/raw")
DATA_DIR.mkdir(parents=True, exist_ok=True)

TEST_LAT = 19.4326
TEST_LON = -99.1942

extracted_data = {"timestamp": datetime.now(timezone.utc).isoformat(), "platforms": {}}


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def extract_prices(text):
    return re.findall(r"\$\s*(\d{1,4}(?:[.,]\d{2})?)", text)


# ═══════════════════════════════════════════════════════════
# RAPPI - Navegacion profunda al menu de McDonald's
# ═══════════════════════════════════════════════════════════
def deep_scrape_rappi():
    log("=" * 60)
    log("RAPPI - Deep Scrape: Menu McDonald's")
    log("=" * 60)

    rappi_data = {"store_info": {}, "products": [], "screenshots": [], "api_data": []}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            locale="es-MX",
            geolocation={"latitude": TEST_LAT, "longitude": TEST_LON},
            permissions=["geolocation"],
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
        )
        page = context.new_page()

        # Interceptar APIs internas
        api_data_captured = []
        def capture_api(response):
            url = response.url
            if response.status == 200 and any(k in url for k in [
                "store", "menu", "product", "catalog", "restaurant",
                "mxgrability", "web-gateway", "search"
            ]):
                try:
                    body = response.text()
                    if body and len(body) > 50:
                        try:
                            jdata = json.loads(body)
                            api_data_captured.append({
                                "url": url[:300],
                                "data": jdata,
                            })
                        except json.JSONDecodeError:
                            pass
                except:
                    pass

        page.on("response", capture_api)

        # Paso 1: Ir a Rappi restaurantes
        log("\n[1] Navegando a pagina de restaurantes...")
        page.goto(
            f"https://www.rappi.com.mx/restaurantes?lat={TEST_LAT}&lng={TEST_LON}",
            timeout=45000,
            wait_until="networkidle",
        )
        time.sleep(3)

        # Paso 2: Buscar y hacer click en McDonald's
        log("[2] Buscando McDonald's en la pagina...")

        # Intentar click en el icono de McDonald's en "Los 10 mas elegidos"
        mcdonalds_link = None
        try:
            # Buscar links que contengan mcdonalds
            all_links = page.query_selector_all("a")
            for link in all_links:
                href = link.get_attribute("href") or ""
                text = link.inner_text() or ""
                if "mcdonald" in href.lower() or "mcdonald" in text.lower():
                    log(f"  Encontrado link: {href[:80]} | {text[:50]}")
                    mcdonalds_link = link
                    break

            if not mcdonalds_link:
                # Buscar por texto visible
                mcdonalds_link = page.query_selector("text=McDonald's")

            if mcdonalds_link:
                log("  Haciendo click en McDonald's...")
                mcdonalds_link.click()
                time.sleep(5)
                page.wait_for_load_state("networkidle", timeout=15000)
            else:
                log("  No se encontro link directo a McDonald's")
                # Intentar buscar
                search_input = page.query_selector("input[type='search'], input[type='text'], [data-qa*='search']")
                if search_input:
                    log("  Usando barra de busqueda...")
                    search_input.click()
                    search_input.fill("McDonald's")
                    time.sleep(2)
                    page.keyboard.press("Enter")
                    time.sleep(5)

        except Exception as e:
            log(f"  Error buscando McDonald's: {e}")

        # Screenshot del estado actual
        ss1 = DATA_DIR / "screenshot_rappi_mcdonalds.png"
        page.screenshot(path=str(ss1), full_page=False)
        rappi_data["screenshots"].append(str(ss1))
        log(f"  Screenshot: {ss1}")

        # Paso 3: Extraer informacion de la pagina actual
        log("[3] Extrayendo datos de la pagina...")
        current_url = page.url
        log(f"  URL actual: {current_url}")

        body_text = page.inner_text("body")
        content = page.content()
        log(f"  Text length: {len(body_text)}")

        # Buscar precios
        prices = extract_prices(body_text)
        log(f"  Precios encontrados: {prices[:30]}")

        # Guardar HTML
        save_path = DATA_DIR / "rappi_mcdonalds_page.html"
        save_path.write_text(content[:100000], encoding="utf-8")

        # Buscar nombres de productos y precios cercanos
        log("[4] Buscando productos especificos...")

        target_products = [
            ("Big Mac", ["big mac"]),
            ("McCombo", ["combo", "mccombo"]),
            ("McNuggets", ["nugget", "mcnugget"]),
            ("Coca-Cola", ["coca-cola", "coca cola"]),
            ("Agua", ["agua"]),
        ]

        # Buscar en todo el texto visible
        lines = body_text.split("\n")
        for line in lines:
            line_clean = line.strip()
            if not line_clean:
                continue
            for prod_name, keywords in target_products:
                if any(kw in line_clean.lower() for kw in keywords):
                    line_prices = extract_prices(line_clean)
                    if line_prices or len(line_clean) < 200:
                        log(f"  >> {prod_name}: {line_clean[:150]}")
                        rappi_data["products"].append({
                            "product": prod_name,
                            "text": line_clean[:200],
                            "prices": line_prices,
                        })

        # Intentar buscar mas especificamente en el DOM
        try:
            # Rappi suele usar divs con el nombre del producto y precio
            all_text_nodes = page.query_selector_all("span, p, div, h1, h2, h3, h4")
            product_context = []

            for node in all_text_nodes[:500]:  # Limitar para no tardar demasiado
                try:
                    txt = node.inner_text().strip()
                    if not txt or len(txt) > 500:
                        continue

                    for prod_name, keywords in target_products:
                        if any(kw in txt.lower() for kw in keywords):
                            # Buscar precio en el padre
                            try:
                                parent = node.evaluate_handle("el => el.parentElement")
                                parent_text = parent.evaluate("el => el.innerText")
                                parent_prices = extract_prices(parent_text)
                                if parent_prices:
                                    log(f"  DOM >> {prod_name}: ${parent_prices[0]} | ctx: {parent_text[:100]}")
                                    rappi_data["products"].append({
                                        "product": prod_name,
                                        "price": parent_prices[0],
                                        "context": parent_text[:200],
                                        "source": "dom_parent",
                                    })
                            except:
                                pass
                except:
                    continue

        except Exception as e:
            log(f"  Error en DOM search: {e}")

        # Paso 5: Analizar APIs capturadas
        log(f"\n[5] APIs capturadas: {len(api_data_captured)}")
        for i, api in enumerate(api_data_captured):
            url = api["url"]
            data = api["data"]
            log(f"  API {i}: {url[:100]}")

            # Buscar datos de productos en las APIs
            json_str = json.dumps(data, ensure_ascii=False).lower()
            for prod_name, keywords in target_products:
                if any(kw in json_str for kw in keywords):
                    log(f"    >> Contiene referencia a: {prod_name}")

            # Guardar APIs relevantes
            if any(k in url for k in ["store", "menu", "product", "catalog", "restaurant"]):
                api_path = DATA_DIR / f"rappi_api_{i}.json"
                api_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
                rappi_data["api_data"].append({"url": url, "file": str(api_path)})

        # Paso 6: Info de delivery
        log("\n[6] Buscando info de delivery/fees...")
        delivery_keywords = ["envio", "delivery", "gratis", "fee", "tiempo", "min"]
        for line in lines:
            line_clean = line.strip().lower()
            if any(kw in line_clean for kw in delivery_keywords) and len(line_clean) < 200:
                log(f"  Delivery: {line.strip()[:150]}")
                rappi_data["store_info"]["delivery_info"] = rappi_data["store_info"].get("delivery_info", [])
                rappi_data["store_info"]["delivery_info"].append(line.strip()[:200])

        browser.close()

    extracted_data["platforms"]["rappi"] = rappi_data
    return rappi_data


# ═══════════════════════════════════════════════════════════
# UBER EATS - Con manejo de cookies y direccion
# ═══════════════════════════════════════════════════════════
def deep_scrape_ubereats():
    log("\n" + "=" * 60)
    log("UBER EATS - Deep Scrape con cookie handling")
    log("=" * 60)

    ue_data = {"store_info": {}, "products": [], "screenshots": [], "api_data": []}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            locale="es-MX",
            geolocation={"latitude": TEST_LAT, "longitude": TEST_LON},
            permissions=["geolocation"],
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
        )
        page = context.new_page()

        # Interceptar APIs
        api_data_captured = []
        def capture_api(response):
            url = response.url
            if response.status == 200 and any(k in url for k in [
                "getStoreV1", "getFeed", "search", "eats/v1", "eats/v2",
            ]):
                try:
                    body = response.text()
                    if body and len(body) > 100:
                        try:
                            api_data_captured.append({
                                "url": url[:300],
                                "data": json.loads(body),
                            })
                        except json.JSONDecodeError:
                            pass
                except:
                    pass

        page.on("response", capture_api)

        # Paso 1: Ir a Uber Eats
        log("\n[1] Navegando a Uber Eats...")
        page.goto("https://www.ubereats.com/mx", timeout=45000, wait_until="networkidle")
        time.sleep(3)

        # Paso 2: Aceptar cookies
        log("[2] Manejando cookie consent...")
        try:
            accept_btn = page.query_selector("button:has-text('Aceptar'), button:has-text('Accept')")
            if accept_btn:
                accept_btn.click()
                log("  Cookies aceptadas")
                time.sleep(2)
            else:
                log("  No se encontro boton de cookies")
        except Exception as e:
            log(f"  Error con cookies: {e}")

        # Paso 3: Ingresar direccion
        log("[3] Ingresando direccion...")
        try:
            addr_input = page.query_selector(
                "input[placeholder*='direcci'], input[placeholder*='address'], "
                "input[data-testid*='address'], input[aria-label*='direcci']"
            )
            if addr_input:
                addr_input.click()
                time.sleep(1)
                addr_input.fill("Av. Presidente Masaryk 360, Polanco, Ciudad de Mexico")
                time.sleep(3)

                # Seleccionar primera sugerencia
                suggestion = page.query_selector("[data-testid*='suggestion'], [class*='suggestion'], li[role='option']")
                if suggestion:
                    suggestion.click()
                    log("  Direccion seleccionada")
                    time.sleep(3)
                else:
                    # Enter
                    page.keyboard.press("Enter")
                    time.sleep(3)

                # Hacer click en "Buscar comida" o similar
                search_btn = page.query_selector("button:has-text('Buscar'), button:has-text('Search'), button[type='submit']")
                if search_btn:
                    search_btn.click()
                    time.sleep(5)

            else:
                log("  No se encontro input de direccion")

        except Exception as e:
            log(f"  Error ingresando direccion: {e}")

        ss1 = DATA_DIR / "screenshot_ubereats_step1.png"
        page.screenshot(path=str(ss1), full_page=False)
        ue_data["screenshots"].append(str(ss1))
        log(f"  Screenshot: {ss1}")

        # Paso 4: Buscar McDonald's
        log("[4] Buscando McDonald's...")
        current_url = page.url
        log(f"  URL actual: {current_url}")

        try:
            # Intentar buscar via URL directa
            page.goto(
                f"https://www.ubereats.com/mx/search?q=McDonalds&pl={TEST_LAT},{TEST_LON}",
                timeout=30000,
                wait_until="networkidle",
            )
            time.sleep(5)
        except Exception as e:
            log(f"  Error navegando a busqueda: {e}")

        ss2 = DATA_DIR / "screenshot_ubereats_search.png"
        page.screenshot(path=str(ss2), full_page=False)
        ue_data["screenshots"].append(str(ss2))

        body_text = page.inner_text("body")
        content = page.content()
        log(f"  Text length: {len(body_text)}")

        prices = extract_prices(body_text)
        log(f"  Precios: {prices[:20]}")

        mcdonalds_count = len(re.findall(r"mcdonald", body_text, re.I))
        log(f"  Menciones McDonald's: {mcdonalds_count}")

        save_path = DATA_DIR / "ubereats_search_page.html"
        save_path.write_text(content[:100000], encoding="utf-8")

        # Buscar links a McDonald's stores
        store_links = page.query_selector_all("a[href*='store'], a[href*='mcdonalds']")
        log(f"  Store links encontrados: {len(store_links)}")
        for link in store_links[:5]:
            href = link.get_attribute("href") or ""
            text = link.inner_text()[:80] or ""
            log(f"    Link: {href[:100]} | {text}")

            if "mcdonald" in href.lower() or "mcdonald" in text.lower():
                try:
                    log(f"  Navegando a store: {href[:80]}")
                    full_url = href if href.startswith("http") else f"https://www.ubereats.com{href}"
                    page.goto(full_url, timeout=30000, wait_until="networkidle")
                    time.sleep(5)

                    ss3 = DATA_DIR / "screenshot_ubereats_mcdonalds.png"
                    page.screenshot(path=str(ss3), full_page=False)
                    ue_data["screenshots"].append(str(ss3))

                    store_text = page.inner_text("body")
                    store_content = page.content()
                    store_prices = extract_prices(store_text)
                    log(f"    Store text: {len(store_text)} chars")
                    log(f"    Store precios: {store_prices[:20]}")

                    save_path = DATA_DIR / "ubereats_mcdonalds_store.html"
                    save_path.write_text(store_content[:100000], encoding="utf-8")

                    # Buscar productos en el store
                    for line in store_text.split("\n"):
                        line_clean = line.strip()
                        if any(kw in line_clean.lower() for kw in ["big mac", "combo", "nugget", "coca", "agua"]):
                            lp = extract_prices(line_clean)
                            if lp or len(line_clean) < 150:
                                log(f"      Producto: {line_clean[:120]}")
                                ue_data["products"].append({
                                    "text": line_clean[:200],
                                    "prices": lp,
                                })

                    break
                except Exception as e:
                    log(f"    Error navegando a store: {e}")

        # APIs capturadas
        log(f"\n[5] APIs capturadas: {len(api_data_captured)}")
        for i, api in enumerate(api_data_captured[:10]):
            log(f"  API {i}: {api['url'][:100]}")
            api_path = DATA_DIR / f"ubereats_api_{i}.json"
            api_path.write_text(json.dumps(api["data"], indent=2, ensure_ascii=False), encoding="utf-8")

        browser.close()

    extracted_data["platforms"]["ubereats"] = ue_data
    return ue_data


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    log("=" * 60)
    log("  DEEP SCRAPE - Extraccion de precios reales")
    log(f"  Ubicacion: Polanco ({TEST_LAT}, {TEST_LON})")
    log("=" * 60)

    deep_scrape_rappi()
    time.sleep(5)

    deep_scrape_ubereats()

    # Guardar resultados
    results_path = DATA_DIR / "deep_scrape_results.json"
    results_path.write_text(
        json.dumps(extracted_data, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    log(f"\n{'='*60}")
    log("RESUMEN:")
    log(f"{'='*60}")
    for platform, data in extracted_data["platforms"].items():
        prods = data.get("products", [])
        log(f"\n  {platform.upper()}: {len(prods)} productos encontrados")
        for prod in prods[:15]:
            log(f"    - {prod.get('product', prod.get('text', '')[:60])} | prices: {prod.get('prices', prod.get('price', 'N/A'))}")

    log(f"\nResultados: {results_path}")
