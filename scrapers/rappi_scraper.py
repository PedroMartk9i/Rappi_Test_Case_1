"""
Scraper para Rappi México.

Hallazgos de scraping real (2026-03-27):
- HTTP Fetcher retorna SPA vacía (4 bytes "None").
- APIs internas (`/api/web-gateway/...`) retornan 403/405 sin token.
- Guest token disponible en: services.mxgrability.rappi.com/api/rocket/v2/guest/passport/
- La API pns-global-search responde 405 (requiere POST).
- Playwright navega exitosamente a /ciudad-de-mexico/restaurantes/delivery/706-mcdonald-s
- **Blocker**: Rappi requiere login/signup para ver menú con precios.

Estrategia:
1. Obtener guest token via API passport.
2. Intentar POST a pns-global-search-api con token.
3. Fallback: Playwright Chromium con dirección manual.
4. Si requiere login: registrar intento y marcar como bloqueado.
"""

import json
import logging
import re

from config import Address, Product, PLATFORMS, SCRAPING_CONFIG
from scrapers.base import BaseScraper, ScrapedItem

logger = logging.getLogger(__name__)

RAPPI_CONFIG = PLATFORMS["rappi"]

# Endpoints descubiertos durante scraping real
RAPPI_APIS = {
    "passport": "https://services.mxgrability.rappi.com/api/rocket/v2/guest/passport/",
    "guest": "https://services.mxgrability.rappi.com/api/rocket/v2/guest",
    "search": "https://services.mxgrability.rappi.com/api/pns-global-search-api/v1/unified-search",
    "recent": "https://services.mxgrability.rappi.com/api/pns-global-search-api/v1/unified-recent-top-searches",
}

# Store paths descubiertos
MCDONALDS_STORE_PATH = "/ciudad-de-mexico/restaurantes/delivery/706-mcdonald-s"


class RappiScraper(BaseScraper):
    def __init__(self):
        super().__init__(platform="rappi")
        self._current_address: Address | None = None
        self._guest_token: str | None = None
        self._login_required = False

    def set_location(self, address: Address) -> bool:
        """
        En Rappi, la ubicación se pasa como parámetro en la URL o en los
        headers de la API. No requiere un paso separado de 'set location'.
        """
        self._current_address = address
        logger.info(f"[Rappi] Ubicación configurada: {address.name} ({address.lat}, {address.lon})")
        return True

    def scrape_product(self, address: Address, product: Product) -> ScrapedItem | None:
        """
        Intenta obtener información del producto de McDonald's en Rappi.

        Estrategia 1: API interna con guest token
        Estrategia 2: Playwright Chromium con navegación al menú
        """
        if self._login_required:
            logger.info("[Rappi] Login requerido (detectado previamente), saltando")
            return None

        item = self._try_api_scrape(address, product)
        if item:
            return item

        item = self._try_playwright_scrape(address, product)
        if item:
            return item

        logger.warning(f"[Rappi] No se pudo obtener {product.name} en {address.name}")
        return None

    def _obtain_guest_token(self) -> str | None:
        """Obtener token de invitado via API passport."""
        if self._guest_token:
            return self._guest_token

        try:
            from scrapling.fetchers import Fetcher

            response = Fetcher.get(
                RAPPI_APIS["passport"],
                stealthy_headers=True,
                follow_redirects=True,
                timeout=15,
            )
            if response and response.status == 200 and response.text:
                data = json.loads(response.text)
                token = data.get("token") or data.get("access_token")
                if token:
                    self._guest_token = token
                    logger.info("[Rappi] Guest token obtenido")
                    return token
        except Exception as e:
            logger.debug(f"[Rappi] Error obteniendo guest token: {e}")

        return None

    def _try_api_scrape(self, address: Address, product: Product) -> ScrapedItem | None:
        """Intentar obtener datos via API interna de Rappi."""
        try:
            from scrapling.fetchers import Fetcher

            # Intentar con guest token
            token = self._obtain_guest_token()

            api_url = (
                f"{RAPPI_CONFIG['base_url']}/api/web-gateway/web/stores-router/search"
                f"?lat={address.lat}&lng={address.lon}"
                f"&query={RAPPI_CONFIG['restaurant_query']}"
                f"&is_prime=false"
            )

            response = Fetcher.get(
                api_url,
                timeout=self.timeout,
                stealthy_headers=True,
                follow_redirects=True,
            )

            if response and response.status == 200 and response.text:
                data = json.loads(response.text)
                return self._parse_api_response(data, address, product)
            elif response and response.status in (403, 401):
                logger.debug(f"[Rappi] API retornó {response.status} — requiere auth")

        except Exception as e:
            logger.debug(f"[Rappi] API scrape falló: {e}")

        return None

    def _try_playwright_scrape(self, address: Address, product: Product) -> ScrapedItem | None:
        """Scraping con Playwright Chromium — navegar al menú de McDonald's."""
        try:
            from playwright.sync_api import sync_playwright
            import time

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

                # Navegar a McDonald's en Rappi
                url = f"https://www.rappi.com.mx{MCDONALDS_STORE_PATH}"
                page.goto(url, timeout=30000, wait_until="domcontentloaded")
                time.sleep(3)

                # Ingresar dirección
                try:
                    addr_input = page.query_selector(
                        "input[placeholder*='quieres'], input[placeholder*='direcci']"
                    )
                    if addr_input:
                        addr_input.click()
                        time.sleep(1)
                        addr_input.fill(address.street)
                        time.sleep(3)

                        suggestion = page.wait_for_selector(
                            "[class*='suggestion'], [class*='Suggestion'], [role='option']",
                            timeout=5000,
                        )
                        if suggestion:
                            suggestion.click()
                            time.sleep(5)
                except Exception:
                    pass

                # Verificar si redirige a login
                current_url = page.url
                if "/login" in current_url or "/signup" in current_url:
                    logger.warning("[Rappi] Redirigido a login — precios no disponibles sin cuenta")
                    self._login_required = True
                    browser.close()
                    return None

                # Intentar extraer datos del menú
                body_text = page.inner_text("body")
                item = self._extract_product_from_text(body_text, address, product)

                browser.close()
                return item

        except Exception as e:
            logger.debug(f"[Rappi] Playwright scrape falló: {e}")

        return None

    def _extract_product_from_text(self, text: str, address: Address, product: Product) -> ScrapedItem | None:
        """Extraer precio de un producto del texto renderizado."""
        lines = text.split("\n")
        for i, line in enumerate(lines):
            line_lower = line.strip().lower()
            if not any(kw in line_lower for kw in product.keywords):
                continue

            context = " ".join(l.strip() for l in lines[max(0, i-1):i+3] if l.strip())
            prices = re.findall(r"\$\s*(\d{1,4}(?:\.\d{2})?)", context)

            if prices:
                return ScrapedItem(
                    platform="rappi",
                    address_id=address.id,
                    address_name=address.name,
                    address_type=address.zone_type,
                    product_id=product.id,
                    product_name=product.name,
                    product_price=float(prices[0]),
                    available=True,
                )

        return None

    def _parse_api_response(self, data: dict, address: Address, product: Product) -> ScrapedItem | None:
        """Parsear respuesta de la API de Rappi buscando el producto."""
        try:
            stores = data.get("stores", data.get("data", {}).get("stores", []))
            for store in stores:
                store_name = store.get("name", "").lower()
                if "mcdonald" not in store_name:
                    continue

                products = store.get("products", store.get("menu", {}).get("products", []))
                for p in products:
                    p_name = p.get("name", "").lower()
                    if any(kw in p_name for kw in product.keywords):
                        price = p.get("price", p.get("real_price"))
                        delivery_fee = store.get("delivery_fee", store.get("delivery", {}).get("fee"))
                        service_fee = store.get("service_fee")
                        delivery_time = store.get("delivery_time", store.get("eta"))

                        d_min, d_max = self._parse_delivery_time(delivery_time)

                        return ScrapedItem(
                            platform="rappi",
                            address_id=address.id,
                            address_name=address.name,
                            address_type=address.zone_type,
                            product_id=product.id,
                            product_name=product.name,
                            restaurant=store.get("name", "McDonald's"),
                            product_price=self._to_float(price),
                            delivery_fee=self._to_float(delivery_fee),
                            service_fee=self._to_float(service_fee),
                            delivery_time_min=d_min,
                            delivery_time_max=d_max,
                            discount_text=p.get("discount_text"),
                            available=True,
                        )
        except Exception as e:
            logger.debug(f"[Rappi] Error parseando API response: {e}")

        return None

    @staticmethod
    def _extract_price(text: str | None) -> float | None:
        """Extraer precio numérico de texto como '$89.00' o '89'."""
        if not text:
            return None
        numbers = re.findall(r"[\d,]+\.?\d*", text.replace(",", ""))
        return float(numbers[0]) if numbers else None

    @staticmethod
    def _to_float(value) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_delivery_time(value) -> tuple[int | None, int | None]:
        """Parsear tiempo de entrega de formatos como '25-35 min', 25, '25'."""
        if value is None:
            return None, None
        if isinstance(value, (int, float)):
            return int(value), int(value)
        text = str(value)
        numbers = re.findall(r"\d+", text)
        if len(numbers) >= 2:
            return int(numbers[0]), int(numbers[1])
        elif len(numbers) == 1:
            return int(numbers[0]), int(numbers[0])
        return None, None
