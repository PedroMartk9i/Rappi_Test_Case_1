"""Navigate to Uber Eats McDonald's and extract prices."""
import sys
import json
import time
import re

sys.stdout.reconfigure(encoding='utf-8')

from playwright.sync_api import sync_playwright


def main():
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        page = context.new_page()

        # Step 1: Go to Uber Eats homepage
        print("[1] Navigating to Uber Eats MX...")
        page.goto("https://www.ubereats.com/mx", timeout=30000, wait_until="domcontentloaded")
        time.sleep(5)
        page.screenshot(path="data/raw/screenshot_ubereats_step1.png")

        # Step 2: Find and fill address input
        print("[2] Looking for address input...")
        # Uber Eats has an address input on the landing page
        inputs = page.locator("input:visible").all()
        print(f"  Visible inputs: {len(inputs)}")
        for inp in inputs:
            ph = inp.get_attribute("placeholder") or ""
            aid = inp.get_attribute("id") or ""
            print(f"    placeholder='{ph}' id='{aid}'")

        # Try the address field
        addr = page.locator("input[placeholder*='direcci'], input[placeholder*='address'], input[placeholder*='Ingresa'], input[id*='location-typeahead']").first
        if not addr or not addr.is_visible():
            # Try any visible text input
            addr = page.locator("input[type='text']:visible").first

        if addr and addr.is_visible():
            print("[3] Filling address...")
            addr.click()
            time.sleep(1)
            addr.fill("Patriotismo 229, San Pedro de los Pinos")
            time.sleep(3)

            page.screenshot(path="data/raw/screenshot_ubereats_step2_suggestions.png")

            # Click suggestion
            sug = page.locator("[data-testid*='suggestion'], li[role='option'], [id*='typeahead'] li, [class*='suggestion'], [class*='Suggestion']").first
            if sug and sug.is_visible():
                sug.click()
                time.sleep(2)
                print("[3b] Clicked suggestion")
            else:
                # Try any list item that appeared
                options = page.locator("ul li, [role='listbox'] [role='option']").all()
                print(f"  Options found: {len(options)}")
                for opt in options[:5]:
                    txt = opt.inner_text()[:60]
                    print(f"    '{txt}'")
                if options:
                    options[0].click()
                    time.sleep(2)

            # Click "Find Food" or "Buscar comida" button
            time.sleep(2)
            find_btn = page.locator("button:has-text('Buscar'), button:has-text('Find'), button:has-text('comida'), a:has-text('Buscar')").first
            if find_btn and find_btn.is_visible():
                find_btn.click()
                time.sleep(5)
                print("[3c] Clicked search button")
        else:
            print("[3] No address input found")

        page.screenshot(path="data/raw/screenshot_ubereats_step3.png")
        print(f"[4] URL: {page.url}")

        # Step 3: Now search for McDonald's
        time.sleep(3)
        print("[5] Looking for search...")

        # Try the search input
        search = page.locator("input[placeholder*='Search'], input[placeholder*='Busca'], input[placeholder*='busca'], input[aria-label*='search'], input[aria-label*='Search']").first
        if search and search.is_visible():
            search.click()
            time.sleep(1)
            search.fill("McDonald's")
            time.sleep(2)
            page.keyboard.press("Enter")
            time.sleep(5)
            print("[5b] Searched for McDonald's")
        else:
            # Try clicking any search icon or link
            search_link = page.locator("a[href*='search'], [data-testid*='search']").first
            if search_link and search_link.is_visible():
                search_link.click()
                time.sleep(3)
                search = page.locator("input:visible").first
                if search:
                    search.fill("McDonald's")
                    time.sleep(2)
                    page.keyboard.press("Enter")
                    time.sleep(5)

        page.screenshot(path="data/raw/screenshot_ubereats_step4_search.png")
        print(f"[6] URL: {page.url}")

        # Find McDonald's store link
        mcdonalds_links = page.locator("a[href*='mcdonalds'], a[href*='mcdonald']").all()
        print(f"[7] McDonald's links: {len(mcdonalds_links)}")

        store_url = None
        for link in mcdonalds_links[:10]:
            href = link.get_attribute("href") or ""
            text = ""
            try:
                text = link.inner_text()[:80]
            except:
                pass
            print(f"  '{text}' -> {href[:120]}")
            if "store" in href and not store_url:
                store_url = href

        # If no store link, try clicking on the first McDonald's result
        if not store_url and mcdonalds_links:
            print("[8] Clicking first McDonald's link...")
            mcdonalds_links[0].click()
            time.sleep(5)
        elif store_url:
            if not store_url.startswith("http"):
                store_url = f"https://www.ubereats.com{store_url}"
            print(f"[8] Navigating to: {store_url[:120]}")
            page.goto(store_url, timeout=30000, wait_until="domcontentloaded")
            time.sleep(5)

        page.screenshot(path="data/raw/screenshot_ubereats_step5_store.png")
        print(f"[9] Store URL: {page.url}")

        # Scroll to load menu
        for i in range(12):
            page.mouse.wheel(0, 800)
            time.sleep(0.8)

        # Scroll back up to get delivery info
        page.mouse.wheel(0, -10000)
        time.sleep(2)

        body = page.inner_text("body")

        # Extract delivery info from top of page
        delivery_info = {}
        fee_match = re.search(r'\$(\d+(?:\.\d+)?)\s*(?:Delivery Fee|delivery fee|envío|de envío)', body, re.I)
        if fee_match:
            delivery_info['delivery_fee'] = float(fee_match.group(1))

        free_delivery = "gratis" in body[:500].lower() or "free delivery" in body[:500].lower()
        if free_delivery:
            delivery_info['delivery_fee'] = 0
            delivery_info['note'] = 'Free delivery'

        time_match = re.search(r'(\d+)\s*[-–]\s*(\d+)\s*min', body[:1000])
        if time_match:
            delivery_info['time_min'] = int(time_match.group(1))
            delivery_info['time_max'] = int(time_match.group(2))

        rating_match = re.search(r'(\d\.\d)\s*\((\d+[+k]*)\)', body[:1000])
        if rating_match:
            delivery_info['rating'] = float(rating_match.group(1))
            delivery_info['reviews'] = rating_match.group(2)

        print(f"[10] Delivery info: {delivery_info}")

        # Scroll down again to get all menu items
        for i in range(12):
            page.mouse.wheel(0, 800)
            time.sleep(0.5)

        body = page.inner_text("body")

        # Parse menu items from text
        lines = body.split('\n')
        menu_items = []

        for i, line in enumerate(lines):
            line = line.strip()
            if not line or len(line) < 3 or len(line) > 100:
                continue

            # Look for price in next few lines
            price_found = None
            desc = ""
            for j in range(i+1, min(i+4, len(lines))):
                next_line = lines[j].strip()
                price_match = re.match(r'^\$\s*(\d[\d,.]*)', next_line)
                if price_match:
                    val = next_line.replace('$', '').replace(',', '').strip()
                    try:
                        price_found = float(val)
                    except:
                        pass
                    break
                elif len(next_line) > 20 and not next_line.startswith('$') and not desc:
                    desc = next_line[:150]

            if price_found and price_found > 10 and not line.startswith('$') and not re.match(r'^\d', line):
                menu_items.append({
                    "name": line,
                    "description": desc,
                    "currentPrice": price_found,
                })

        # Deduplicate
        seen = set()
        unique_items = []
        for item in menu_items:
            if item['name'] not in seen:
                seen.add(item['name'])
                unique_items.append(item)

        print(f"\n[11] Menu items: {len(unique_items)}")
        print(f"\n{'PRODUCTO':<50} {'PRECIO':>10}")
        print("-" * 65)
        for item in unique_items:
            print(f"{item['name'][:49]:<50} ${item['currentPrice']:>8.2f}")

        # Save
        data = {
            "platform": "ubereats",
            "store": "McDonald's",
            "address_zone": "San Pedro de los Pinos, Benito Juarez, CDMX",
            "delivery_info": delivery_info,
            "products": unique_items,
            "url": page.url,
        }
        with open("data/raw/ubereats_mcdonalds_prices.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"\nSaved to data/raw/ubereats_mcdonalds_prices.json")
        page.close()


if __name__ == "__main__":
    main()
