"""
PedidosYa exploration - check if guest browsing works.
"""

import sys
import time
import re
import json

sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright


def explore():
    api_responses = []

    def handle_response(response):
        url = response.url
        if any(kw in url.lower() for kw in ["search", "store", "menu", "restaurant", "vendor", "mcdonald", "catalog"]):
            try:
                body = response.text()
            except Exception:
                body = "<binary>"
            api_responses.append({"status": response.status, "url": url[:200], "body": body[:1000]})

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
        page.on("response", handle_response)

        # Step 1: Landing page
        print("[1] Navegando a PedidosYa Mexico...")
        page.goto("https://www.pedidosya.com.mx/", timeout=30000, wait_until="domcontentloaded")
        time.sleep(5)

        page.screenshot(path="data/raw/screenshot_pedidosya_landing.png")
        body = page.inner_text("body")
        print(f"  URL: {page.url}")
        print(f"  Texto (400): {body[:400]}")
        print("---")

        # Check for address input
        print("\n[2] Buscando input de direccion...")
        inputs = page.locator("input:visible").all()
        print(f"  Inputs: {len(inputs)}")
        for inp in inputs:
            tp = inp.get_attribute("type") or ""
            ph = inp.get_attribute("placeholder") or ""
            print(f"    type={tp} placeholder='{ph}'")

        # Try entering address
        addr_input = None
        for selector in [
            "input[placeholder*='direcci']",
            "input[placeholder*='Direcci']",
            "input[placeholder*='address']",
            "input[placeholder*='calle']",
            "input[placeholder*='ubica']",
            "input[placeholder*='Busca']",
            "input[placeholder*='busca']",
            "input[type='text']",
            "input[type='search']",
        ]:
            el = page.locator(f"{selector}:visible").first
            if el and el.is_visible():
                addr_input = el
                print(f"  Found: {selector}")
                break

        if addr_input:
            addr_input.click()
            time.sleep(1)
            addr_input.fill("Masaryk 360, Polanco, Ciudad de Mexico")
            time.sleep(3)

            # Look for suggestions
            suggestions = page.locator("[class*='suggestion'], [class*='Suggestion'], [role='option'], [class*='autocomplete'], [class*='result'], li[class*='item']").all()
            print(f"  Sugerencias: {len(suggestions)}")
            for s in suggestions[:5]:
                try:
                    if s.is_visible():
                        text = s.inner_text()[:60]
                        print(f"    '{text}'")
                except Exception:
                    pass

            if suggestions:
                for s in suggestions:
                    if s.is_visible():
                        s.click()
                        time.sleep(5)
                        print("  Sugerencia clickeada!")
                        break
            else:
                # Try pressing Enter
                page.keyboard.press("Enter")
                time.sleep(5)

        page.screenshot(path="data/raw/screenshot_pedidosya_after_address.png")
        print(f"\n[3] Despues de direccion:")
        print(f"  URL: {page.url}")
        body = page.inner_text("body")
        print(f"  Texto (400): {body[:400]}")

        # Check if we got redirected to login
        if "login" in page.url.lower() or "registr" in body.lower()[:200]:
            print("\n  BLOCKER: Requiere login!")
        else:
            print("\n  Posible acceso guest!")

        # Search for McDonald's
        print("\n[4] Buscando McDonald's...")
        search_input = page.locator("input[placeholder*='Busca'], input[placeholder*='busca'], input[type='search']:visible, input[placeholder*='restaurant']:visible").first
        if search_input and search_input.is_visible():
            search_input.click()
            time.sleep(1)
            search_input.fill("McDonald's")
            time.sleep(2)
            page.keyboard.press("Enter")
            time.sleep(5)
            print(f"  URL: {page.url}")
        else:
            # Try navigating directly
            print("  No search input, trying direct navigation...")
            # Try common URL patterns
            for url in [
                "https://www.pedidosya.com.mx/cadenas/mcdonalds-702",
                "https://www.pedidosya.com.mx/restaurantes/ciudad-de-mexico?q=mcdonalds",
                "https://www.pedidosya.com.mx/restaurantes/ciudad-de-mexico/mcdonalds",
            ]:
                try:
                    page.goto(url, timeout=15000, wait_until="domcontentloaded")
                    time.sleep(5)
                    text = page.inner_text("body")
                    if "mcdonald" in text.lower() or "$" in text:
                        print(f"  Found at: {url}")
                        break
                except Exception:
                    continue

        page.screenshot(path="data/raw/screenshot_pedidosya_search.png")
        body = page.inner_text("body")
        print(f"\n[5] Resultados:")
        print(f"  URL: {page.url}")
        print(f"  Texto (500): {body[:500]}")

        # Look for prices
        prices = re.findall(r'\$\s*(\d[\d,.]*)', body)
        if prices:
            print(f"\n  PRECIOS ENCONTRADOS: {prices[:30]}")

        # Look for McDonald's links
        mc_links = page.locator("a[href*='mcdonald'], a[href*='mcdonalds']").all()
        print(f"\n[6] Links McDonald's: {len(mc_links)}")
        for link in mc_links[:5]:
            href = link.get_attribute("href") or ""
            text = ""
            try:
                text = link.inner_text()[:50]
            except Exception:
                pass
            print(f"  href={href[:80]} text='{text}'")

        # Click first McDonald's link
        if mc_links:
            try:
                href = mc_links[0].get_attribute("href") or ""
                if href and not href.startswith("http"):
                    href = f"https://www.pedidosya.com.mx{href}"
                if href:
                    page.goto(href, timeout=20000, wait_until="domcontentloaded")
                else:
                    mc_links[0].click()
                time.sleep(8)

                page.screenshot(path="data/raw/screenshot_pedidosya_mcdonalds.png")
                menu_text = page.inner_text("body")
                menu_prices = re.findall(r'\$\s*(\d[\d,.]*)', menu_text)

                print(f"\n[7] McDonald's menu:")
                print(f"  URL: {page.url}")
                print(f"  Precios: {menu_prices[:30]}")
                print(f"  Texto (500): {menu_text[:500]}")

                # Find products
                lines = menu_text.split("\n")
                for pn, kws in {
                    "Big Mac": ["big mac"],
                    "McTrio/McCombo": ["mctrio", "mccombo", "combo"],
                    "McNuggets": ["nuggets", "mcnuggets"],
                    "Coca-Cola": ["coca-cola", "coca cola"],
                    "Agua": ["agua"],
                }.items():
                    for i, line in enumerate(lines):
                        ll = line.strip().lower()
                        if any(kw in ll for kw in kws):
                            ctx = " | ".join(l.strip() for l in lines[max(0,i-1):i+4] if l.strip())
                            cp = re.findall(r'\$\s*(\d[\d,.]*)', ctx)
                            print(f"\n  {pn}: {ctx[:150]}")
                            if cp:
                                print(f"    -> {cp}")
                            break

                # Save data
                with open("data/raw/pedidosya_extracted_data.json", "w", encoding="utf-8") as f:
                    json.dump({
                        "platform": "pedidosya",
                        "store": "McDonald's",
                        "url": page.url,
                        "total_prices": len(menu_prices),
                        "all_prices": menu_prices[:100],
                        "menu_text": menu_text[:10000],
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    }, f, ensure_ascii=False, indent=2)
                print(f"\n  Datos guardados en pedidosya_extracted_data.json")

            except Exception as e:
                print(f"  Error navegando a McDonald's: {e}")

        # Check intercepted API responses
        print(f"\n[8] API responses interceptadas: {len(api_responses)}")
        for r in api_responses[:10]:
            print(f"  [{r['status']}] {r['url'][:100]}")
            print(f"    {r['body'][:200]}")

        browser.close()


if __name__ == "__main__":
    explore()
