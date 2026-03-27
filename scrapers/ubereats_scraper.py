"""
Scraper para Uber Eats México.

Estrategia probada (2026-03-27):
1. Playwright Chromium con aceptación automática de cookies.
2. Ingresar dirección para obtener feed geolocalizado.
3. Navegar al store de McDonald's y extraer precios del menú.

Hallazgos de scraping real:
- HTTP directo retorna SPA vacía (4 bytes).
- Playwright con cookie handling funciona correctamente.
- Store URL pattern: /mx/store/mcdonalds-{zona}/{store_id}
- Precios extraíbles del texto renderizado del menú.
"""

import json
import logging
import re
import time

from config import Address, Product, PLATFORMS, SCRAPING_CONFIG
from scrapers.base import BaseScraper, ScrapedItem

logger = logging.getLogger(__name__)

UBEREATS_CONFIG = PLATFORMS["ubereats"]

# Store IDs conocidos (descubiertos durante scraping real)
KNOWN_STORES = {
    "polanco": {"path": "/mx/store/mcdonalds-polanco/GMcH3w_vX4CtLxBPRICeWA", "name": "McDonald's (Polanco)"},
}


class UberEatsScraper(BaseScraper):
    def __init__(self):
        super().__init__(platform="ubereats")
        self._current_address: Address | None = None
        self._browser = None
        self._context = None
        self._page = None

    def set_location(self, address: Address) -> bool:
        """Configurar ubicación en Uber Eats via Playwright."""
        self._current_address = address
        logger.info(f"[UberEats] Ubicación configurada: {address.name}")
        return True

    def scrape_product(self, address: Address, product: Product) -> ScrapedItem | None:
        """
        Scrape a single product from Uber Eats McDonald's.

        Strategy:
        1. Try Playwright browser (proven method)
        2. Navigate to McDonald's store for the given location
        3. Extract prices from rendered menu
        """
        item = self._try_playwright_scrape(address, product)
        if item:
            return item

        logger.warning(f"[UberEats] No se pudo obtener {product.name} en {address.name}")
        return None

    def _try_playwright_scrape(self, address: Address, product: Product) -> ScrapedItem | None:
        """Scraping con Playwright Chromium — método probado."""
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    locale="es-MX",
                    geolocation={"latitude": address.lat, "longitude": address.lon},
                    permissions=["geolocation"],
                    user_agent=SCRAPING_CONFIG["user_agent"],
                    viewport={"width": 1920, "height": 1080},
                )
                page = context.new_page()

                # Paso 1: Landing + aceptar cookies
                page.goto("https://www.ubereats.com/mx", timeout=30000, wait_until="domcontentloaded")
                time.sleep(2)

                try:
                    accept = page.query_selector("button:has-text('Aceptar')")
                    if accept:
                        accept.click()
                        time.sleep(1)
                except Exception:
                    pass

                # Paso 2: Ingresar dirección
                try:
                    addr_input = page.query_selector("input[placeholder*='direcci'], input[placeholder*='Ingresa']")
                    if addr_input:
                        addr_input.click()
                        time.sleep(1)
                        addr_input.fill(address.street)
                        time.sleep(3)
                        suggestion = page.wait_for_selector(
                            "[data-testid*='suggestion'], li[role='option']",
                            timeout=5000,
                        )
                        if suggestion:
                            suggestion.click()
                            time.sleep(3)
                except Exception as e:
                    logger.debug(f"[UberEats] Error ingresando dirección: {e}")

                # Paso 3: Buscar McDonald's
                search_url = (
                    f"https://www.ubereats.com/mx/search"
                    f"?q=McDonald%27s&pl={address.lat}%2C{address.lon}"
                )
                page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
                time.sleep(5)

                # Buscar link al store de McDonald's
                store_links = page.query_selector_all("a[href*='mcdonalds'], a[href*='store']")
                store_url = None
                for link in store_links[:10]:
                    href = link.get_attribute("href") or ""
                    if "mcdonalds" in href.lower() and "/store/" in href:
                        store_url = href if href.startswith("http") else f"https://www.ubereats.com{href}"
                        break

                if not store_url:
                    # Intentar store conocido
                    known = KNOWN_STORES.get(address.id)
                    if known:
                        store_url = f"https://www.ubereats.com{known['path']}"

                if not store_url:
                    logger.warning(f"[UberEats] No se encontró store de McDonald's en {address.name}")
                    browser.close()
                    return None

                # Paso 4: Navegar al store y extraer datos
                page.goto(store_url, timeout=45000, wait_until="domcontentloaded")
                time.sleep(8)

                body_text = page.inner_text("body")

                # Extraer precio del producto
                item = self._extract_product_from_text(body_text, address, product)

                # Extraer delivery info
                delivery_fee = self._extract_delivery_fee(body_text)
                delivery_time = self._extract_delivery_time(body_text)

                if item:
                    item.delivery_fee = delivery_fee
                    if delivery_time:
                        item.delivery_time_min, item.delivery_time_max = delivery_time

                browser.close()
                return item

        except Exception as e:
            logger.error(f"[UberEats] Playwright error: {e}")
            return None

    def _extract_product_from_text(self, text: str, address: Address, product: Product) -> ScrapedItem | None:
        """Extraer precio de un producto del texto del menú."""
        lines = text.split("\n")

        for i, line in enumerate(lines):
            line_lower = line.strip().lower()
            if not line_lower:
                continue

            # Buscar match exacto del producto
            matched = False
            if product.id == "big_mac" and "big mac" in line_lower and "tocino" not in line_lower and "mctrío" not in line_lower and "combo" not in line_lower:
                matched = True
            elif product.id == "combo_mediano" and ("mctrío mediano big mac" in line_lower or "mctrio mediano big mac" in line_lower):
                matched = True
            elif product.id == "nuggets_10" and "mcnuggets de pollo 10" in line_lower:
                matched = True
            elif product.id == "coca_600" and "coca-cola mediana" in line_lower:
                matched = True
            elif product.id == "agua_1l" and "agua" in line_lower and ("ciel" in line_lower or "600" in line_lower or "1" in line_lower):
                matched = True

            if matched:
                # Buscar precio en contexto cercano
                context = " ".join(l.strip() for l in lines[max(0, i-1):i+3] if l.strip())
                prices = re.findall(r"\$\s*(\d{1,4}(?:\.\d{2})?)", context)

                if prices:
                    price = float(prices[0])
                    return ScrapedItem(
                        platform="ubereats",
                        address_id=address.id,
                        address_name=address.name,
                        address_type=address.zone_type,
                        product_id=product.id,
                        product_name=product.name,
                        product_price=price,
                        available=True,
                    )

        return None

    @staticmethod
    def _extract_delivery_fee(text: str) -> float | None:
        match = re.search(r"(?:envío|delivery|fee)[:\s]*\$\s*(\d+(?:\.\d{2})?)", text, re.I)
        if match:
            return float(match.group(1))
        return None

    @staticmethod
    def _extract_delivery_time(text: str) -> tuple[int, int] | None:
        match = re.search(r"(\d+)\s*[-–]\s*(\d+)\s*min", text)
        if match:
            return int(match.group(1)), int(match.group(2))
        return None
