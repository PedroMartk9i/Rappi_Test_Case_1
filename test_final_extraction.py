"""
Extraccion final de precios reales.
Foco en Uber Eats McDonald's Polanco + Rappi con direccion manual.
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
TEST_LAT = 19.4326
TEST_LON = -99.1942

all_data = {"timestamp": datetime.now(timezone.utc).isoformat(), "platforms": {}}


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def extract_prices(text):
    return re.findall(r"\$\s*(\d{1,4}(?:[.,]\d{2})?)", text)


def scrape_ubereats_mcdonalds():
    """Navegar directo al store de McDonald's Polanco en Uber Eats."""
    log("=" * 60)
    log("UBER EATS - McDonald's Polanco (directo)")
    log("=" * 60)

    products_found = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            locale="es-MX",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
        )
        page = context.new_page()

        # Paso 1: Landing + aceptar cookies
        log("[1] Navegando a UE landing...")
        page.goto("https://www.ubereats.com/mx", timeout=30000, wait_until="domcontentloaded")
        time.sleep(3)

        try:
            accept = page.query_selector("button:has-text('Aceptar')")
            if accept:
                accept.click()
                time.sleep(1)
        except:
            pass

        # Paso 2: Ingresar direccion
        log("[2] Ingresando direccion Polanco...")
        try:
            addr_input = page.query_selector("input[placeholder*='direcci'], input[placeholder*='Ingresa']")
            if addr_input:
                addr_input.click()
                time.sleep(1)
                addr_input.fill("Av. Presidente Masaryk 360, Polanco")
                time.sleep(3)

                # Esperar sugerencias y click en la primera
                suggestion = page.wait_for_selector(
                    "[data-testid*='suggestion'], [id*='suggestion'], li[role='option'], [class*='AddressSuggestion']",
                    timeout=5000,
                )
                if suggestion:
                    suggestion.click()
                    time.sleep(3)
        except Exception as e:
            log(f"  Direccion error: {e}")

        # Paso 3: Navegar directo al store
        log("[3] Navegando al store de McDonald's Polanco...")
        store_url = "https://www.ubereats.com/mx/store/mcdonalds-polanco/GMcH3w_vX4CtLxBPRICeWA"

        try:
            page.goto(store_url, timeout=45000, wait_until="domcontentloaded")
            time.sleep(8)  # Esperar carga completa de menu

            ss = DATA_DIR / "screenshot_ubereats_mcdonalds_menu.png"
            page.screenshot(path=str(ss), full_page=False)
            log(f"  Screenshot: {ss}")

            body_text = page.inner_text("body")
            content = page.content()
            log(f"  Text length: {len(body_text)}")

            (DATA_DIR / "ubereats_mcdonalds_menu.html").write_text(content[:150000], encoding="utf-8")

            # Extraer TODOS los precios
            prices = extract_prices(body_text)
            log(f"  Precios totales encontrados: {len(prices)}")
            log(f"  Precios: {prices[:30]}")

            # Buscar productos target
            target = {
                "Big Mac": ["big mac"],
                "McCombo Mediano": ["combo mediano", "mccombo", "combo big mac"],
                "McNuggets 10": ["nuggets 10", "mcnuggets 10", "nuggets"],
                "Coca-Cola": ["coca-cola", "coca cola", "refresco"],
                "Agua": ["agua"],
            }

            lines = body_text.split("\n")
            for i, line in enumerate(lines):
                line_clean = line.strip()
                if not line_clean or len(line_clean) > 300:
                    continue

                for prod_name, keywords in target.items():
                    if any(kw in line_clean.lower() for kw in keywords):
                        # Buscar precio en esta linea y las siguientes
                        context_text = " ".join(l.strip() for l in lines[max(0,i-1):i+3] if l.strip())
                        context_prices = extract_prices(context_text)

                        log(f"  >> {prod_name}: {line_clean[:100]} | precios_ctx: {context_prices}")
                        products_found.append({
                            "platform": "ubereats",
                            "product": prod_name,
                            "text": line_clean[:200],
                            "prices_context": context_prices,
                            "line_num": i,
                        })

            # Buscar delivery info
            delivery_patterns = [
                r"(?:entrega|delivery|envio|envío).*?(\d+)\s*[-–]\s*(\d+)\s*min",
                r"(\d+)\s*[-–]\s*(\d+)\s*min",
                r"(?:fee|costo|cargo).*?\$\s*(\d+(?:\.\d{2})?)",
            ]
            for pat in delivery_patterns:
                matches = re.findall(pat, body_text, re.I)
                if matches:
                    log(f"  Delivery match ({pat[:30]}...): {matches[:5]}")

            # Scroll down para cargar mas productos
            log("[4] Scrolling para cargar mas menu...")
            for scroll in range(3):
                page.mouse.wheel(0, 2000)
                time.sleep(2)

            body_text_full = page.inner_text("body")
            if len(body_text_full) > len(body_text):
                log(f"  Nuevo text length: {len(body_text_full)} (+{len(body_text_full)-len(body_text)})")
                new_prices = extract_prices(body_text_full)
                log(f"  Nuevos precios: {new_prices[:30]}")

                # Buscar productos en el texto ampliado
                new_lines = body_text_full.split("\n")
                for i, line in enumerate(new_lines):
                    line_clean = line.strip()
                    if not line_clean or len(line_clean) > 300:
                        continue
                    for prod_name, keywords in target.items():
                        if any(kw in line_clean.lower() for kw in keywords):
                            ctx = " ".join(l.strip() for l in new_lines[max(0,i-1):i+3] if l.strip())
                            ctx_prices = extract_prices(ctx)
                            already = any(
                                p["product"] == prod_name and p["text"] == line_clean[:200]
                                for p in products_found
                            )
                            if not already and ctx_prices:
                                log(f"  >> (scroll) {prod_name}: {line_clean[:100]} | {ctx_prices}")
                                products_found.append({
                                    "platform": "ubereats",
                                    "product": prod_name,
                                    "text": line_clean[:200],
                                    "prices_context": ctx_prices,
                                })

            # Screenshot final con menu scrolleado
            ss2 = DATA_DIR / "screenshot_ubereats_mcdonalds_scrolled.png"
            page.screenshot(path=str(ss2), full_page=False)

        except Exception as e:
            log(f"  Error: {e}")

        browser.close()

    all_data["platforms"]["ubereats"] = {"products": products_found}
    return products_found


def scrape_rappi_mcdonalds():
    """Navegar a Rappi McDonald's con direccion ingresada."""
    log("\n" + "=" * 60)
    log("RAPPI - McDonald's con direccion manual")
    log("=" * 60)

    products_found = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            locale="es-MX",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
        )
        page = context.new_page()

        # Ir directo a la pagina de McDonald's
        log("[1] Navegando a McDonald's en Rappi...")
        page.goto(
            "https://www.rappi.com.mx/ciudad-de-mexico/restaurantes/delivery/706-mcdonald-s",
            timeout=45000,
            wait_until="domcontentloaded",
        )
        time.sleep(3)

        # Ingresar direccion
        log("[2] Ingresando direccion...")
        try:
            addr_input = page.query_selector(
                "input[placeholder*='direcci'], input[placeholder*='quieres'], "
                "input[type='text'], input[name*='address']"
            )
            if addr_input:
                log(f"  Input encontrado: placeholder='{addr_input.get_attribute('placeholder')}'")
                addr_input.click()
                time.sleep(1)
                addr_input.fill("Av. Presidente Masaryk 360, Polanco")
                time.sleep(3)

                # Seleccionar sugerencia
                try:
                    suggestion = page.wait_for_selector(
                        "[class*='suggestion'], [class*='Suggestion'], [class*='address-item'], "
                        "[class*='autocomplete'] li, [role='option']",
                        timeout=5000,
                    )
                    if suggestion:
                        suggestion.click()
                        log("  Direccion seleccionada")
                        time.sleep(5)
                except:
                    page.keyboard.press("Enter")
                    time.sleep(5)

            else:
                log("  No se encontro input de direccion")
                # Intentar buscar boton de ubicacion
                loc_btn = page.query_selector(
                    "button:has-text('ubicaci'), a:has-text('ubicaci'), "
                    "[class*='location'], [data-qa*='location']"
                )
                if loc_btn:
                    log("  Encontrado boton de ubicacion")
                    loc_btn.click()
                    time.sleep(3)

        except Exception as e:
            log(f"  Error: {e}")

        ss = DATA_DIR / "screenshot_rappi_after_address.png"
        page.screenshot(path=str(ss), full_page=False)
        log(f"  Screenshot: {ss}")

        # Verificar si cargaron tiendas
        log("[3] Verificando tiendas disponibles...")
        body_text = page.inner_text("body")
        content = page.content()
        log(f"  Text length: {len(body_text)}")

        (DATA_DIR / "rappi_after_address.html").write_text(content[:150000], encoding="utf-8")

        # Buscar links a sucursales de McDonald's
        store_links = page.query_selector_all("a[href*='900'], a[href*='mcdonald']")
        log(f"  Links a sucursales: {len(store_links)}")

        for link in store_links[:3]:
            href = link.get_attribute("href") or ""
            text = (link.inner_text() or "")[:80]
            log(f"    Link: {href[:80]} | {text}")

            if "/restaurantes/" in href and href != page.url:
                try:
                    full_url = href if href.startswith("http") else f"https://www.rappi.com.mx{href}"
                    log(f"  [4] Navegando a sucursal: {full_url[:80]}")
                    page.goto(full_url, timeout=30000, wait_until="domcontentloaded")
                    time.sleep(8)

                    store_text = page.inner_text("body")
                    store_content = page.content()
                    log(f"    Store text: {len(store_text)} chars")

                    prices = extract_prices(store_text)
                    log(f"    Precios: {prices[:30]}")

                    ss2 = DATA_DIR / "screenshot_rappi_store.png"
                    page.screenshot(path=str(ss2), full_page=False)
                    log(f"    Screenshot: {ss2}")

                    (DATA_DIR / "rappi_store_page.html").write_text(store_content[:150000], encoding="utf-8")

                    # Buscar productos
                    target = {
                        "Big Mac": ["big mac"],
                        "McCombo": ["combo", "mccombo"],
                        "McNuggets": ["nugget", "mcnugget"],
                        "Coca-Cola": ["coca-cola", "coca cola"],
                        "Agua": ["agua"],
                    }

                    lines = store_text.split("\n")
                    for i, line in enumerate(lines):
                        lc = line.strip()
                        if not lc or len(lc) > 300:
                            continue
                        for prod_name, kws in target.items():
                            if any(kw in lc.lower() for kw in kws):
                                ctx = " ".join(l.strip() for l in lines[max(0,i-1):i+3] if l.strip())
                                ctx_p = extract_prices(ctx)
                                log(f"    >> {prod_name}: {lc[:100]} | {ctx_p}")
                                products_found.append({
                                    "platform": "rappi",
                                    "product": prod_name,
                                    "text": lc[:200],
                                    "prices_context": ctx_p,
                                })

                    # Scroll para mas productos
                    for _ in range(3):
                        page.mouse.wheel(0, 2000)
                        time.sleep(2)

                    store_text_full = page.inner_text("body")
                    if len(store_text_full) > len(store_text):
                        log(f"    Scroll: {len(store_text_full)} chars (+{len(store_text_full)-len(store_text)})")

                    break  # Solo primera sucursal

                except Exception as e:
                    log(f"    Error: {e}")

        browser.close()

    all_data["platforms"]["rappi"] = {"products": products_found}
    return products_found


if __name__ == "__main__":
    log("=" * 60)
    log("  FINAL EXTRACTION - Precios reales")
    log("=" * 60)

    ue_products = scrape_ubereats_mcdonalds()
    time.sleep(3)
    rappi_products = scrape_rappi_mcdonalds()

    # Guardar
    results_path = DATA_DIR / "final_extraction_results.json"
    results_path.write_text(
        json.dumps(all_data, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    log(f"\n{'='*60}")
    log("RESUMEN DE EXTRACCION:")
    log(f"{'='*60}")
    for platform, data in all_data["platforms"].items():
        prods = data.get("products", [])
        log(f"\n{platform.upper()}: {len(prods)} matches")
        for prod in prods:
            log(f"  {prod['product']}: {prod['text'][:80]} | precios: {prod.get('prices_context', [])}")

    log(f"\nResultados: {results_path}")
