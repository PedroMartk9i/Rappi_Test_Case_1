"""
Scraper para DiDi Food México.

CORRECCIÓN (2026-03-28):
- El dominio CORRECTO es didi-food.com (con guión), NO didifood.com
- didifood.com (sin guión) es un dominio en venta — NO pertenece a DiDi
- DiDi Food opera activamente en México con 30M+ usuarios y 52K+ restaurantes

Hallazgos de scraping real (2026-03-28):
- Landing page carga correctamente en didi-food.com/es-MX
- Se detectó input "Ingresar dirección de entrega" + botón "Buscar comida"
- La geolocalización resolvió la dirección a "Eugenio Sue 116, Polanco"
- BLOCKER: Al hacer click en "Buscar comida", redirige a login (page.didiglobal.com)
- DiDi Food requiere cuenta/login para ver restaurantes y precios

Estrategia:
1. Playwright Chromium para navegar al menú de McDonald's
2. Ingresar dirección y buscar store
3. Si requiere login: registrar intento y marcar como bloqueado
"""

import json
import logging
import re
import time

from config import Address, Product, PLATFORMS, SCRAPING_CONFIG
from scrapers.base import BaseScraper, ScrapedItem

logger = logging.getLogger(__name__)

DIDI_CONFIG = PLATFORMS["didifood"]


class DidiFoodScraper(BaseScraper):
    def __init__(self):
        super().__init__(platform="didifood")
        self._current_address: Address | None = None

    def set_location(self, address: Address) -> bool:
        self._current_address = address
        logger.info(f"[DiDiFood] Ubicación configurada: {address.name}")
        return True

    def scrape_product(self, address: Address, product: Product) -> ScrapedItem | None:
        """
        Scrape a single product from DiDi Food McDonald's.
        Strategy: Playwright Chromium with address input.
        """
        item = self._try_playwright_scrape(address, product)
        if item:
            return item

        logger.warning(f"[DiDiFood] No se pudo obtener {product.name} en {address.name}")
        return None

    def _try_playwright_scrape(self, address: Address, product: Product) -> ScrapedItem | None:
        """Scraping con Playwright Chromium."""
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

                # Navegar a DiDi Food
                url = f"{DIDI_CONFIG['base_url']}"
                logger.info(f"[DiDiFood] Navegando a: {url}")
                page.goto(url, timeout=30000, wait_until="domcontentloaded")
                time.sleep(3)

                # Aceptar cookies si hay
                try:
                    accept = page.query_selector(
                        "button:has-text('Aceptar'), button:has-text('Accept'), "
                        "button:has-text('Entendido'), button:has-text('OK')"
                    )
                    if accept:
                        accept.click()
                        time.sleep(1)
                except Exception:
                    pass

                # Ingresar dirección
                try:
                    addr_input = page.query_selector(
                        "input[placeholder*='direcci'], input[placeholder*='ubica'], "
                        "input[placeholder*='address'], input[type='text']"
                    )
                    if addr_input:
                        addr_input.click()
                        time.sleep(1)
                        addr_input.fill(address.street)
                        time.sleep(3)

                        suggestion = page.wait_for_selector(
                            "[class*='suggestion'], [class*='Suggestion'], "
                            "li[role='option'], [class*='autocomplete']",
                            timeout=5000,
                        )
                        if suggestion:
                            suggestion.click()
                            time.sleep(3)
                except Exception as e:
                    logger.debug(f"[DiDiFood] Error ingresando dirección: {e}")

                # Buscar McDonald's
                try:
                    search_input = page.query_selector(
                        "input[placeholder*='Busca'], input[placeholder*='busca'], "
                        "input[placeholder*='Search'], input[type='search']"
                    )
                    if search_input:
                        search_input.click()
                        time.sleep(1)
                        search_input.fill("McDonald's")
                        time.sleep(2)
                        page.keyboard.press("Enter")
                        time.sleep(5)
                except Exception as e:
                    logger.debug(f"[DiDiFood] Error buscando: {e}")

                # Buscar link a store de McDonald's
                store_links = page.query_selector_all(
                    "a[href*='mcdonalds'], a[href*='mcdonald'], "
                    "a[href*='store'], [class*='store-card']"
                )
                if store_links:
                    for link in store_links[:5]:
                        href = link.get_attribute("href") or ""
                        text = (link.inner_text() or "").lower()
                        if "mcdonald" in href.lower() or "mcdonald" in text:
                            full_url = href if href.startswith("http") else f"https://www.didi-food.com{href}"
                            logger.info(f"[DiDiFood] Navegando a store: {full_url[:80]}")
                            page.goto(full_url, timeout=30000, wait_until="domcontentloaded")
                            time.sleep(5)
                            break

                # Extraer datos del menú
                body_text = page.inner_text("body")
                item = self._extract_product_from_text(body_text, address, product)

                # Extraer delivery info
                if item:
                    delivery_fee = self._extract_delivery_fee(body_text)
                    delivery_time = self._extract_delivery_time(body_text)
                    item.delivery_fee = delivery_fee
                    if delivery_time:
                        item.delivery_time_min, item.delivery_time_max = delivery_time

                browser.close()
                return item

        except Exception as e:
            logger.error(f"[DiDiFood] Playwright error: {e}")
            return None

    def _extract_product_from_text(self, text: str, address: Address, product: Product) -> ScrapedItem | None:
        """Extraer precio de un producto del texto del menú."""
        lines = text.split("\n")

        for i, line in enumerate(lines):
            line_lower = line.strip().lower()
            if not line_lower:
                continue

            # Match product by keywords
            if not any(kw in line_lower for kw in product.keywords):
                continue

            # Buscar precio en contexto cercano
            context = " ".join(l.strip() for l in lines[max(0, i - 1):i + 3] if l.strip())
            prices = re.findall(r"\$\s*(\d{1,4}(?:\.\d{2})?)", context)

            if prices:
                return ScrapedItem(
                    platform="didifood",
                    address_id=address.id,
                    address_name=address.name,
                    address_type=address.zone_type,
                    product_id=product.id,
                    product_name=product.name,
                    product_price=float(prices[0]),
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
