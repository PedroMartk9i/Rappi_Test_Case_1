"""
Test 3 alternative food delivery platforms in Mexico:
1. Manzana Verde - healthy meals
2. Tomato.mx - regional platform
3. Veloz - low-commission alternative
"""

import sys
import time
import re
import json

sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright


def test_platform(page, name, url, search_term="McDonald's"):
    """Test a single platform for guest access and prices."""
    result = {
        "name": name,
        "url": url,
        "accessible": False,
        "guest_mode": False,
        "has_restaurants": False,
        "has_prices": False,
        "has_mcdonalds": False,
        "prices": [],
        "notes": "",
    }

    print(f"\n{'='*60}")
    print(f"  {name} — {url}")
    print(f"{'='*60}")

    try:
        page.goto(url, timeout=20000, wait_until="domcontentloaded")
        time.sleep(5)
    except Exception as e:
        result["notes"] = f"Error loading: {str(e)[:80]}"
        print(f"  ERROR: {result['notes']}")
        return result

    result["accessible"] = True
    final_url = page.url
    print(f"  URL final: {final_url}")

    page.screenshot(path=f"data/raw/screenshot_{name.lower().replace(' ','_')}_landing.png")
    body = page.inner_text("body")
    print(f"  Texto (300): {body[:300]}")

    # Check for login requirement
    if "login" in final_url.lower() or "registr" in final_url.lower():
        result["notes"] = "Redirige a login"
        print(f"  -> Redirige a login")
        return result

    # Check if it shows restaurants/food content
    food_keywords = ["restaurante", "menu", "comida", "pedir", "delivery", "envio", "platillo", "orden"]
    if any(kw in body.lower() for kw in food_keywords):
        result["has_restaurants"] = True
        print(f"  -> Contenido de comida detectado")

    # Look for inputs (address/search)
    inputs = page.locator("input:visible").all()
    print(f"  Inputs visibles: {len(inputs)}")
    for inp in inputs[:5]:
        tp = inp.get_attribute("type") or ""
        ph = inp.get_attribute("placeholder") or ""
        print(f"    type={tp} placeholder='{ph}'")

    # Try address input
    for sel in ["input[placeholder*='direcci']", "input[placeholder*='ubica']",
                "input[placeholder*='Busca']", "input[placeholder*='busca']",
                "input[type='search']", "input[type='text']"]:
        addr = page.locator(f"{sel}:visible").first
        if addr and addr.is_visible():
            try:
                addr.click()
                time.sleep(0.5)
                addr.fill("Polanco, Ciudad de Mexico")
                time.sleep(3)
                # Try selecting suggestion
                sug = page.locator("[class*='suggestion'], [role='option'], [class*='result'], [class*='item']").first
                if sug and sug.is_visible():
                    sug.click()
                    time.sleep(3)
                else:
                    page.keyboard.press("Enter")
                    time.sleep(3)
                print(f"  Direccion ingresada")
            except Exception:
                pass
            break

    # Check for login redirect after address
    if "login" in page.url.lower() or "registr" in page.url.lower():
        result["notes"] = "Requiere login despues de direccion"
        print(f"  -> Requiere login despues de ingresar direccion")
        page.screenshot(path=f"data/raw/screenshot_{name.lower().replace(' ','_')}_login.png")
        return result

    result["guest_mode"] = True
    body = page.inner_text("body")

    # Check prices
    prices = re.findall(r'\$\s*(\d[\d,.]*)', body)
    if prices:
        result["has_prices"] = True
        result["prices"] = prices[:30]
        print(f"  PRECIOS: {prices[:20]}")

    # Search for McDonald's or any fast food
    print(f"\n  Buscando '{search_term}'...")
    search = page.locator("input[placeholder*='Busca'], input[placeholder*='busca'], input[type='search']:visible").first
    if search and search.is_visible():
        try:
            search.click()
            time.sleep(0.5)
            search.fill(search_term)
            time.sleep(2)
            page.keyboard.press("Enter")
            time.sleep(5)
            body = page.inner_text("body")
            prices = re.findall(r'\$\s*(\d[\d,.]*)', body)
            if prices:
                result["has_prices"] = True
                result["prices"] = prices[:30]
                print(f"  Precios despues de busqueda: {prices[:20]}")

            if "mcdonald" in body.lower():
                result["has_mcdonalds"] = True
                print(f"  McDonald's encontrado!")

            page.screenshot(path=f"data/raw/screenshot_{name.lower().replace(' ','_')}_search.png")
        except Exception as e:
            print(f"  Error buscando: {e}")

    # Look for restaurant links/cards
    restaurants = page.locator("a[href*='restaurante'], a[href*='store'], a[href*='menu'], [class*='card'], [class*='restaurant']").all()
    print(f"  Elementos restaurant/card: {len(restaurants)}")
    if restaurants:
        result["has_restaurants"] = True
        for r in restaurants[:3]:
            try:
                text = r.inner_text()[:60]
                href = r.get_attribute("href") or ""
                print(f"    '{text}' -> {href[:60]}")
            except Exception:
                pass

    # Final screenshot
    page.screenshot(path=f"data/raw/screenshot_{name.lower().replace(' ','_')}_final.png")
    body = page.inner_text("body")
    result["notes"] = body[:300]

    return result


def run():
    platforms = [
        ("Manzana Verde", "https://www.manzanaverde.la/"),
        ("Manzana Verde MX", "https://www.manzanaverde.la/mx/"),
        ("Tomato", "https://www.tomato.mx/"),
        ("Veloz", "https://www.veloz.app/"),
        ("Veloz MX", "https://veloz.com.mx/"),
    ]

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

        results = []
        for name, url in platforms:
            result = test_platform(page, name, url)
            results.append(result)

        browser.close()

    # Summary
    print(f"\n\n{'='*60}")
    print(f"  RESUMEN")
    print(f"{'='*60}")
    for r in results:
        status = []
        if not r["accessible"]: status.append("NO ACCESIBLE")
        elif not r["guest_mode"]: status.append("REQUIERE LOGIN")
        else:
            if r["has_prices"]: status.append("PRECIOS")
            if r["has_mcdonalds"]: status.append("McDONALDS")
            if r["has_restaurants"]: status.append("RESTAURANTES")
            if not status: status.append("GUEST OK (sin datos)")

        print(f"  {r['name']:20s} | {', '.join(status)}")
        if r["prices"]:
            print(f"  {'':20s} | Precios: {r['prices'][:10]}")

    # Save results
    with open("data/raw/alt_platforms_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    run()
