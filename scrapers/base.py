"""
Base scraper: ScrapedItem dataclass y BaseScraper ABC.
"""

import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

from config import Address, Product, SCRAPING_CONFIG

logger = logging.getLogger(__name__)


@dataclass
class ScrapedItem:
    platform: str
    address_id: str
    address_name: str
    address_type: str  # premium / media / popular
    product_id: str
    product_name: str
    restaurant: str = "McDonald's"
    product_price: float | None = None
    delivery_fee: float | None = None
    service_fee: float | None = None
    total_price: float | None = None
    delivery_time_min: int | None = None
    delivery_time_max: int | None = None
    discount_text: str | None = None
    available: bool = True
    scrape_timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


class BaseScraper(ABC):
    """Clase abstracta que define la interfaz para todos los scrapers."""

    def __init__(self, platform: str):
        self.platform = platform
        self.rate_limit = SCRAPING_CONFIG["rate_limit_seconds"]
        self.max_retries = SCRAPING_CONFIG["max_retries"]
        self.timeout = SCRAPING_CONFIG["timeout_seconds"]
        self._last_request_time: float = 0

    def _rate_limit_wait(self) -> None:
        """Esperar entre requests para respetar rate limiting."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit:
            wait = self.rate_limit - elapsed
            logger.debug(f"Rate limit: esperando {wait:.1f}s")
            time.sleep(wait)
        self._last_request_time = time.time()

    def _retry(self, func, *args, **kwargs):
        """Ejecutar función con reintentos."""
        for attempt in range(1, self.max_retries + 1):
            try:
                self._rate_limit_wait()
                return func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"[{self.platform}] Intento {attempt}/{self.max_retries} falló: {e}")
                if attempt == self.max_retries:
                    logger.error(f"[{self.platform}] Todos los reintentos fallaron para {func.__name__}")
                    return None
                time.sleep(self.rate_limit * attempt)  # backoff
        return None

    @abstractmethod
    def set_location(self, address: Address) -> bool:
        """Configurar la dirección de entrega en la plataforma."""
        ...

    @abstractmethod
    def scrape_product(self, address: Address, product: Product) -> ScrapedItem | None:
        """Scrapear un producto específico desde una dirección."""
        ...

    def scrape_all(self, addresses: list[Address], products: list[Product]) -> list[ScrapedItem]:
        """Scrapear todos los productos en todas las direcciones."""
        results: list[ScrapedItem] = []
        for address in addresses:
            logger.info(f"[{self.platform}] Scrapeando zona: {address.name}")
            location_set = self._retry(self.set_location, address)
            if not location_set:
                logger.warning(f"[{self.platform}] No se pudo configurar ubicación: {address.name}")
                for product in products:
                    results.append(ScrapedItem(
                        platform=self.platform,
                        address_id=address.id,
                        address_name=address.name,
                        address_type=address.zone_type,
                        product_id=product.id,
                        product_name=product.name,
                        available=False,
                    ))
                continue

            for product in products:
                logger.info(f"  → Producto: {product.name}")
                item = self._retry(self.scrape_product, address, product)
                if item:
                    results.append(item)
                else:
                    results.append(ScrapedItem(
                        platform=self.platform,
                        address_id=address.id,
                        address_name=address.name,
                        address_type=address.zone_type,
                        product_id=product.id,
                        product_name=product.name,
                        available=False,
                    ))

        logger.info(f"[{self.platform}] Scraping completado: {len(results)} items")
        return results
