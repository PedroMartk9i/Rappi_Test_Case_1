"""
Scraper para DiDi Food México.

Hallazgos de scraping real (2026-03-27):
- didifood.com redirige (302) a forsale.dynadot.com — dominio en venta.
- food.didiglobal.com → DNS resolution failed.
- page.didifood.com → DNS resolution failed.
- DiDi Food cerró operaciones en México en 2023.

Conclusión: El scraper está implementado con la arquitectura correcta
como ejercicio de diseño, pero detecta automáticamente que la plataforma
no está operativa y falla gracefully.
"""

import json
import logging
import re

from config import Address, Product, PLATFORMS, SCRAPING_CONFIG
from scrapers.base import BaseScraper, ScrapedItem

logger = logging.getLogger(__name__)

DIDI_CONFIG = PLATFORMS["didifood"]


class DidiFoodScraper(BaseScraper):
    def __init__(self):
        super().__init__(platform="didifood")
        self._current_address: Address | None = None
        self._platform_available: bool | None = None  # None = no verificado aún

    def set_location(self, address: Address) -> bool:
        self._current_address = address
        logger.info(f"[DiDiFood] Ubicación configurada: {address.name}")
        return True

    def _check_platform_status(self) -> bool:
        """
        Verificar si DiDi Food está operativo.
        Descubierto en scraping real: el dominio redirige a una página de venta.
        """
        if self._platform_available is not None:
            return self._platform_available

        try:
            from scrapling.fetchers import Fetcher

            response = Fetcher.get(
                DIDI_CONFIG["base_url"],
                stealthy_headers=True,
                follow_redirects=True,
                timeout=15,
            )

            if response:
                final_url = str(response.url) if hasattr(response, "url") else ""
                text = (response.text or "").lower()

                # Detectar dominio en venta o redirect a servicio tercero
                if any(indicator in final_url.lower() for indicator in [
                    "forsale", "dynadot", "sedo", "afternic", "godaddy",
                ]):
                    logger.warning(
                        "[DiDiFood] Dominio en venta (redirige a %s) — "
                        "plataforma cerrada en México", final_url[:80]
                    )
                    self._platform_available = False
                    return False

                # Detectar página de cierre
                if any(phrase in text for phrase in [
                    "ya no está disponible", "servicio cerrado",
                    "no longer available", "service closed", "ceased operations",
                ]):
                    logger.warning("[DiDiFood] Plataforma indica servicio cerrado")
                    self._platform_available = False
                    return False

                # Si responde normalmente, plataforma podría estar activa
                self._platform_available = response.status == 200 and len(text) > 100
                return self._platform_available

        except Exception as e:
            logger.warning(f"[DiDiFood] No se puede verificar plataforma: {e}")
            self._platform_available = False

        return False

    def scrape_product(self, address: Address, product: Product) -> ScrapedItem | None:
        # Verificar si la plataforma está operativa
        if not self._check_platform_status():
            logger.info(
                "[DiDiFood] Plataforma no disponible en México (cerrada 2023). "
                "Registrando intento."
            )
            return None

        item = self._try_api_scrape(address, product)
        if item:
            return item

        item = self._try_browser_scrape(address, product)
        if item:
            return item

        logger.warning(f"[DiDiFood] No se pudo obtener {product.name} en {address.name}")
        return None

    def _try_api_scrape(self, address: Address, product: Product) -> ScrapedItem | None:
        """Intentar obtener datos via API de DiDi Food."""
        try:
            from scrapling.fetchers import Fetcher

            api_url = (
                f"{DIDI_CONFIG['base_url']}/api/v1/search"
                f"?keyword={DIDI_CONFIG['restaurant_query']}"
                f"&lat={address.lat}&lng={address.lon}"
            )

            response = Fetcher.get(
                api_url,
                timeout=self.timeout,
                stealthy_headers=True,
                follow_redirects=True,
            )

            if response and response.status == 200:
                data = json.loads(response.text)
                return self._parse_api_response(data, address, product)
            elif response and response.status in (404, 403, 503):
                logger.warning(f"[DiDiFood] Plataforma no accesible (HTTP {response.status})")
                self._platform_available = False

        except Exception as e:
            logger.debug(f"[DiDiFood] API scrape falló: {e}")

        return None

    def _try_browser_scrape(self, address: Address, product: Product) -> ScrapedItem | None:
        """Intentar scraping con Playwright Chromium."""
        try:
            from playwright.sync_api import sync_playwright
            import time

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    locale="es-MX",
                    user_agent=SCRAPING_CONFIG["user_agent"],
                )
                page = context.new_page()

                url = (
                    f"{DIDI_CONFIG['base_url']}/search"
                    f"?keyword=McDonald%27s"
                    f"&lat={address.lat}&lng={address.lon}"
                )
                page.goto(url, timeout=30000, wait_until="domcontentloaded")
                time.sleep(3)

                # Verificar si la página es válida
                current_url = page.url
                if any(x in current_url.lower() for x in ["forsale", "dynadot", "sedo"]):
                    logger.warning("[DiDiFood] Redirigido a página de venta de dominio")
                    self._platform_available = False
                    browser.close()
                    return None

                body_text = page.inner_text("body")

                # Buscar producto en el texto
                lines = body_text.split("\n")
                for i, line in enumerate(lines):
                    if any(kw in line.lower() for kw in product.keywords):
                        ctx = " ".join(l.strip() for l in lines[max(0,i-1):i+3])
                        prices = re.findall(r"\$\s*(\d{1,4}(?:\.\d{2})?)", ctx)
                        if prices:
                            browser.close()
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

                browser.close()

        except Exception as e:
            logger.debug(f"[DiDiFood] Browser scrape falló: {e}")
            self._platform_available = False

        return None

    def _parse_api_response(self, data: dict, address: Address, product: Product) -> ScrapedItem | None:
        """Parsear respuesta de API de DiDi Food."""
        try:
            stores = data.get("data", {}).get("stores", data.get("stores", []))
            for store in stores:
                if "mcdonald" not in store.get("name", "").lower():
                    continue

                products_list = store.get("products", [])
                for p in products_list:
                    p_name = p.get("name", "").lower()
                    if any(kw in p_name for kw in product.keywords):
                        return ScrapedItem(
                            platform="didifood",
                            address_id=address.id,
                            address_name=address.name,
                            address_type=address.zone_type,
                            product_id=product.id,
                            product_name=product.name,
                            restaurant=store.get("name", "McDonald's"),
                            product_price=self._to_float(p.get("price")),
                            delivery_fee=self._to_float(store.get("delivery_fee")),
                            service_fee=self._to_float(store.get("service_fee")),
                            delivery_time_min=store.get("delivery_time_min"),
                            delivery_time_max=store.get("delivery_time_max"),
                            available=True,
                        )
        except Exception as e:
            logger.debug(f"[DiDiFood] Error parseando API: {e}")
        return None

    @staticmethod
    def _to_float(value) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
