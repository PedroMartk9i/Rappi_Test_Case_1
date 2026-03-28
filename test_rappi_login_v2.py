"""
Rappi login v2 - Fixed: click "Recibir código por SMS" button.

Usage:
  python test_rappi_login_v2.py                    # Step 1: request code
  python test_rappi_login_v2.py --code 123456      # Step 2: enter code and scrape
"""

import sys
import time
import re
import json
import argparse

sys.stdout.reconfigure(encoding='utf-8')

from playwright.sync_api import sync_playwright

STATE_FILE = "data/raw/rappi_login_state.json"


def step1_request_code():
    """Navigate to Rappi login, enter phone, click SMS button."""

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            locale="es-MX",
            geolocation={"latitude": 19.4326, "longitude": -99.1942},
            permissions=["geolocation"],
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
        )
        page = context.new_page()

        # Navigate to Rappi login
        print("[1] Navegando a Rappi login...")
        page.goto("https://www.rappi.com.mx/login", timeout=30000, wait_until="domcontentloaded")
        time.sleep(5)

        # Click "Continuar con tu celular"
        print("[2] Click 'Continuar con tu celular'...")
        celular_btn = page.get_by_text("Celular", exact=False).first
        if celular_btn and celular_btn.is_visible():
            celular_btn.click()
            time.sleep(3)
            print("  OK")

        # Change country to Colombia
        print("[3] Cambiando pais a Colombia...")
        plus52 = page.get_by_text("+52", exact=False).first
        if plus52 and plus52.is_visible():
            box = plus52.bounding_box()
            if box and box["height"] < 60:
                plus52.click()
                time.sleep(2)
                colombia = page.get_by_text("Colombia", exact=False)
                for i in range(colombia.count()):
                    el = colombia.nth(i)
                    if el.is_visible():
                        cbox = el.bounding_box()
                        if cbox and cbox["height"] < 60:
                            el.click()
                            time.sleep(1)
                            print("  Colombia (+57) seleccionado!")
                            break

        # Enter phone
        print("[4] Ingresando telefono...")
        phone = page.locator("input[type='tel']:visible").first
        if phone:
            phone.click()
            time.sleep(0.3)
            phone.type("3108532310", delay=80)
            time.sleep(1)
            print(f"  Phone: {phone.input_value()}")

        page.screenshot(path="data/raw/screenshot_rappi_v2_phone.png")

        # Click "Recibir código por SMS"
        print("[5] Click 'Recibir codigo por SMS'...")
        sms_btn = page.get_by_text("Recibir c", exact=False).first
        if not sms_btn or not sms_btn.is_visible():
            sms_btn = page.get_by_role("button", name="SMS").first
        if not sms_btn or not sms_btn.is_visible():
            sms_btn = page.locator("button:has-text('SMS')").first

        if sms_btn and sms_btn.is_visible():
            sms_btn.click()
            print("  SMS button clicked!")
            time.sleep(8)
        else:
            print("  ERROR: No SMS button found")
            # Fallback: try clicking the green button area
            buttons = page.locator("button:visible").all()
            for btn in buttons:
                text = btn.inner_text()
                if "SMS" in text or "digo" in text:
                    btn.click()
                    print(f"  Fallback: clicked '{text}'")
                    time.sleep(8)
                    break

        # Check result
        page.screenshot(path="data/raw/screenshot_rappi_v2_after_sms.png")
        print(f"\n[6] Despues de enviar SMS:")
        print(f"  URL: {page.url}")
        body_text = page.inner_text("body")
        print(f"  Texto (400 chars): {body_text[:400]}")

        # Check for code input
        inputs = page.locator("input:visible").all()
        print(f"\n[7] Inputs visibles: {len(inputs)}")
        for inp in inputs:
            tp = inp.get_attribute("type") or ""
            ph = inp.get_attribute("placeholder") or ""
            ml = inp.get_attribute("maxlength") or ""
            print(f"  type={tp} placeholder='{ph}' maxlength={ml}")

        if any(kw in body_text.lower() for kw in ["codigo", "code", "verificaci", "ingresa el"]):
            print("\n  EXITO: Codigo SMS enviado! Esperando codigo del usuario...")
        else:
            print("\n  Revisar screenshot para ver estado actual")

        # Save state
        context.storage_state(path=STATE_FILE)
        print(f"  Estado guardado en {STATE_FILE}")
        print(f"\n  Cuando tengas el codigo, ejecuta:")
        print(f"  python test_rappi_login_v2.py --code XXXXXX")

        browser.close()


def step2_enter_code(code: str):
    """Enter verification code and scrape McDonald's menu."""

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            locale="es-MX",
            geolocation={"latitude": 19.4326, "longitude": -99.1942},
            permissions=["geolocation"],
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            storage_state=STATE_FILE,
        )
        page = context.new_page()

        # Navigate to Rappi (should have cookies)
        print(f"[1] Navegando a Rappi con sesion guardada...")
        page.goto("https://www.rappi.com.mx/login", timeout=30000, wait_until="domcontentloaded")
        time.sleep(5)

        print(f"  URL: {page.url}")
        body = page.inner_text("body")
        print(f"  Texto (300): {body[:300]}")

        # Check if we're on the code entry page already
        if "codigo" not in body.lower() and "code" not in body.lower():
            print("  No estamos en la pagina de codigo, re-enviando...")
            # Re-do phone flow
            celular_btn = page.get_by_text("Celular", exact=False).first
            if celular_btn and celular_btn.is_visible():
                celular_btn.click()
                time.sleep(3)

            # Change to Colombia
            plus = page.get_by_text("+52", exact=False).first
            if plus and plus.is_visible():
                box = plus.bounding_box()
                if box and box["height"] < 60:
                    plus.click()
                    time.sleep(2)
                    col = page.get_by_text("Colombia", exact=False)
                    for i in range(col.count()):
                        el = col.nth(i)
                        if el.is_visible():
                            cbox = el.bounding_box()
                            if cbox and cbox["height"] < 60:
                                el.click()
                                time.sleep(1)
                                break

            phone = page.locator("input[type='tel']:visible").first
            if phone:
                phone.type("3108532310", delay=80)
                time.sleep(1)

            sms_btn = page.locator("button:has-text('SMS')").first
            if sms_btn and sms_btn.is_visible():
                sms_btn.click()
                time.sleep(8)

            body = page.inner_text("body")

        # Enter the verification code
        print(f"\n[2] Ingresando codigo: {code}")
        page.screenshot(path="data/raw/screenshot_rappi_code_page.png")

        inputs = page.locator("input:visible").all()
        print(f"  Inputs visibles: {len(inputs)}")

        # Check for OTP-style (multiple single-digit inputs)
        single_inputs = []
        for inp in inputs:
            ml = inp.get_attribute("maxlength") or ""
            tp = inp.get_attribute("type") or ""
            if ml == "1" or (tp == "tel" and not inp.input_value()):
                single_inputs.append(inp)

        if len(single_inputs) >= 4:
            print(f"  OTP pattern: {len(single_inputs)} inputs")
            for i, digit in enumerate(code):
                if i < len(single_inputs):
                    single_inputs[i].click()
                    single_inputs[i].fill(digit)
                    time.sleep(0.2)
            print("  Codigo ingresado (OTP)")
        elif len(inputs) == 1:
            inputs[0].click()
            inputs[0].type(code, delay=100)
            print("  Codigo ingresado (single input)")
        else:
            # Try to find the right input
            for inp in inputs:
                ph = (inp.get_attribute("placeholder") or "").lower()
                tp = inp.get_attribute("type") or ""
                if "codigo" in ph or "code" in ph or tp in ["number", "tel"]:
                    inp.click()
                    inp.type(code, delay=100)
                    print(f"  Codigo ingresado (placeholder match)")
                    break
            else:
                # Last resort: type into first input
                if inputs:
                    inputs[0].click()
                    inputs[0].type(code, delay=100)
                    print("  Codigo ingresado (first input fallback)")

        time.sleep(3)

        # Try clicking verify button if there is one
        for text in ["Verificar", "Confirmar", "Continuar", "Validar", "Ingresar", "Enviar"]:
            btn = page.locator(f"button:has-text('{text}'):visible").first
            if btn:
                btn.click()
                print(f"  Clicked '{text}'")
                break

        # Wait for navigation
        print("  Esperando login...")
        time.sleep(10)

        # Check result
        page.screenshot(path="data/raw/screenshot_rappi_after_code.png")
        current_url = page.url
        print(f"\n[3] Resultado:")
        print(f"  URL: {current_url}")

        if "/login" not in current_url and "/signup" not in current_url:
            print("  LOGIN EXITOSO!")

            # Save auth state
            context.storage_state(path="data/raw/rappi_auth_state.json")

            # Navigate to McDonald's
            print("\n[4] Navegando a McDonald's...")
            page.goto("https://www.rappi.com.mx/restaurantes/706-mcdonald-s",
                      timeout=30000, wait_until="domcontentloaded")
            time.sleep(8)

            page.screenshot(path="data/raw/screenshot_rappi_mcdonalds_logged.png")

            # Enter address if prompted
            try:
                addr_input = page.locator("input[placeholder*='direcci'], input[placeholder*='quieres'], input[placeholder*='Busca']").first
                if addr_input and addr_input.is_visible():
                    addr_input.click()
                    time.sleep(1)
                    addr_input.fill("Masaryk 360, Polanco")
                    time.sleep(3)
                    suggestion = page.locator("[class*='suggestion'], [role='option'], [class*='Suggestion']").first
                    if suggestion and suggestion.is_visible():
                        suggestion.click()
                        time.sleep(5)
            except Exception:
                pass

            # Get menu text
            menu_text = page.inner_text("body")
            page.screenshot(path="data/raw/screenshot_rappi_mcdonalds_menu_logged.png")

            # Extract all prices
            prices = re.findall(r'\$\s*(\d{1,4}(?:\.\d{2})?)', menu_text)
            print(f"\n[5] Precios encontrados: {len(prices)}")
            if prices:
                print(f"  Todos: {prices[:40]}")

            # Find specific products
            print(f"\n[6] Productos objetivo:")
            targets = {
                "Big Mac": ["big mac", "bigmac"],
                "McTrio/McCombo Big Mac": ["mctrio", "mccombo", "combo.*big mac", "trio.*big mac"],
                "McNuggets 10 pzas": ["nuggets 10", "mcnuggets 10"],
                "Coca-Cola 600ml": ["coca-cola 600", "coca cola 600", "coca-cola mediana"],
                "Agua": ["agua 1l", "agua 1 litro", "agua ciel", "agua natural"],
            }

            lines = menu_text.split("\n")
            extracted = {}
            for product_name, keywords in targets.items():
                for i, line in enumerate(lines):
                    line_lower = line.strip().lower()
                    if any(re.search(kw, line_lower) for kw in keywords):
                        ctx_lines = lines[max(0,i-1):i+4]
                        context = " | ".join(l.strip() for l in ctx_lines if l.strip())
                        ctx_prices = re.findall(r'\$\s*(\d{1,4}(?:\.\d{2})?)', context)
                        print(f"\n  {product_name}:")
                        print(f"    Contexto: {context[:150]}")
                        if ctx_prices:
                            print(f"    Precios: {ctx_prices}")
                            extracted[product_name] = {"prices": ctx_prices, "context": context[:200]}
                        break

            # Save everything
            with open("data/raw/rappi_extracted_data.json", "w", encoding="utf-8") as f:
                json.dump({
                    "platform": "rappi",
                    "store": "McDonald's",
                    "url": page.url,
                    "all_prices": prices[:100],
                    "products": extracted,
                    "menu_text": menu_text[:8000],
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                }, f, ensure_ascii=False, indent=2)
            print(f"\n  Datos guardados en data/raw/rappi_extracted_data.json")

            # Also try navigating to specific McDonald's Polanco
            print("\n[7] Intentando McDonald's Polanco directamente...")
            page.goto("https://www.rappi.com.mx/restaurantes/900903236-mcdonald-s---polanco",
                      timeout=30000, wait_until="domcontentloaded")
            time.sleep(8)
            page.screenshot(path="data/raw/screenshot_rappi_mcdonalds_polanco.png")
            polanco_text = page.inner_text("body")
            polanco_prices = re.findall(r'\$\s*(\d{1,4}(?:\.\d{2})?)', polanco_text)
            if polanco_prices:
                print(f"  Precios Polanco: {polanco_prices[:30]}")

        else:
            body = page.inner_text("body")
            print(f"  Aun en login: {body[:400]}")
            # Check for errors
            if "incorrecto" in body.lower() or "invalido" in body.lower() or "expirado" in body.lower():
                print("  NOTA: Codigo incorrecto o expirado")

        browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--code", type=str, help="Verification code received via SMS")
    args = parser.parse_args()

    if args.code:
        step2_enter_code(args.code)
    else:
        step1_request_code()
