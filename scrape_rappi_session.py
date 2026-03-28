"""Connect to existing Rappi browser session and extract McDonald's prices."""
import sys
import json

sys.stdout.reconfigure(encoding='utf-8')

from playwright.sync_api import sync_playwright


def main():
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://localhost:9222")
        page = browser.contexts[0].pages[0]

        print(f"URL: {page.url}")

        # Extract structured product data
        products = page.evaluate(r"""() => {
            const items = [];
            const cards = document.querySelectorAll('[data-qa*="product"]');
            for (const card of cards) {
                const text = (card.innerText || '').trim();
                if (!text || text.length > 300) continue;

                const lines = text.split('\n').map(l => l.trim()).filter(l => l);
                const name = lines[0] || '';

                // Skip category headers
                const headers = ['Populares','Ofertas Pro','Big Mac + Coca','McTrios Comida',
                    'Cajita Feliz','Tu Fav','A La Carta Comida','Postres','Bebidas',
                    'Mc para Todos'];
                if (headers.includes(name)) continue;

                const prices = [];
                let discount = null;
                let description = '';

                for (const line of lines.slice(1)) {
                    if (line.match(/^-\d+%$/)) {
                        discount = line;
                    } else if (line.match(/^\$\s*[\d,.]+$/)) {
                        prices.push(parseFloat(line.replace('$','').replace(',','').trim()));
                    } else if (!description && line.length > 15) {
                        description = line;
                    }
                }

                let currentPrice, originalPrice;
                if (discount && prices.length >= 2) {
                    currentPrice = prices[0];
                    originalPrice = prices[1];
                } else if (prices.length >= 1) {
                    currentPrice = prices[0];
                    originalPrice = prices[0];
                } else {
                    continue;
                }

                items.push({
                    name: name,
                    description: description.substring(0, 150),
                    currentPrice: currentPrice,
                    originalPrice: originalPrice,
                    discount: discount,
                });
            }

            // Deduplicate by name
            const seen = new Set();
            return items.filter(item => {
                if (seen.has(item.name)) return false;
                seen.add(item.name);
                return true;
            });
        }""")

        print(f"\nProducts extracted: {len(products)}")
        print(f"\n{'PRODUCTO':<45} {'PRECIO':>10} {'ORIGINAL':>10} {'DESC':>8}")
        print("-" * 80)
        for prod in products:
            print(f"{prod['name'][:44]:<45} ${prod['currentPrice']:>8.2f} ${prod['originalPrice']:>8.2f} {prod.get('discount') or '':>8}")

        # Save
        data = {
            "platform": "rappi",
            "store": "McDonalds - San Pedro de los Pinos",
            "address": "Avenida Patriotismo No 229, Benito Juarez, CDMX",
            "delivery_fee": 0,
            "delivery_fee_note": "Gratis (envio gratis)",
            "delivery_time_min": 15,
            "rating": 4.6,
            "products": products,
            "url": page.url,
        }
        with open("data/raw/rappi_mcdonalds_prices.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print("\nSaved to data/raw/rappi_mcdonalds_prices.json")


if __name__ == "__main__":
    main()
