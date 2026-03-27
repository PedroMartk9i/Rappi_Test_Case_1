"""
Entry point — orquesta el pipeline completo de scraping competitivo.

Uso:
    python main.py                  # Ejecutar scraping + análisis
    python main.py --scrapers-only  # Solo scraping (sin análisis)
    python main.py --analysis-only  # Solo análisis (datos existentes)
    python main.py --demo           # Generar datos demo + análisis
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from config import ADDRESSES, PRODUCTS, PLATFORMS
from scrapers import RappiScraper, UberEatsScraper, DidiFoodScraper
from scrapers.base import ScrapedItem
from pipeline.normalizer import normalize
from pipeline.exporter import to_csv, to_json
from analysis.comparator import compare_platforms
from analysis.report_generator import generate_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def run_scrapers() -> list[ScrapedItem]:
    """Ejecutar todos los scrapers y recolectar resultados."""
    all_items: list[ScrapedItem] = []

    scrapers = [
        RappiScraper(),
        UberEatsScraper(),
        DidiFoodScraper(),
    ]

    for scraper in scrapers:
        logger.info(f"{'='*50}")
        logger.info(f"Iniciando scraper: {scraper.platform}")
        logger.info(f"{'='*50}")

        try:
            items = scraper.scrape_all(ADDRESSES, PRODUCTS)
            all_items.extend(items)
            available = sum(1 for i in items if i.available)
            logger.info(f"[{scraper.platform}] Resultado: {available}/{len(items)} productos disponibles")
        except Exception as e:
            logger.error(f"[{scraper.platform}] Error fatal: {e}")
            # Registrar todos los productos como no disponibles
            for address in ADDRESSES:
                for product in PRODUCTS:
                    all_items.append(ScrapedItem(
                        platform=scraper.platform,
                        address_id=address.id,
                        address_name=address.name,
                        address_type=address.zone_type,
                        product_id=product.id,
                        product_name=product.name,
                        available=False,
                    ))

    return all_items


def generate_demo_data() -> list[ScrapedItem]:
    """
    Genera datos de demostración realistas para poder ejecutar el
    pipeline completo cuando el scraping está bloqueado.

    Los precios están basados en rangos reales de McDonald's CDMX.
    """
    import random
    random.seed(42)

    items: list[ScrapedItem] = []

    # Precios base por producto (MXN) — calibrados con datos REALES
    # extraídos de Uber Eats McDonald's Polanco el 2026-03-27:
    #   Big Mac: $145, McTrío Big Mac: $169, McNuggets 10: $155,
    #   Coca-Cola mediana: $65, Agua Ciel 600ml: $39
    base_prices = {
        "big_mac": (139, 149),
        "combo_mediano": (165, 179),
        "nuggets_10": (149, 159),
        "coca_600": (59, 69),
        "agua_1l": (35, 45),
    }

    # Factores por plataforma — Rappi ~5% más caro que UE (hipótesis)
    # DiDi Food cerró en México 2023 — incluido como ejercicio de diseño
    platform_factors = {
        "rappi": {"price_mult": 1.05, "delivery_base": (29, 49), "service_pct": 0.15, "time": (25, 45)},
        "ubereats": {"price_mult": 1.0, "delivery_base": (0, 29), "service_pct": 0.12, "time": (20, 40)},
        "didifood": {"price_mult": 0.95, "delivery_base": (15, 35), "service_pct": 0.10, "time": (30, 50)},
    }

    # Factor de zona (premium más caro en delivery)
    zone_delivery_mult = {"premium": 0.9, "media": 1.0, "popular": 1.3}

    for address in ADDRESSES:
        for product in PRODUCTS:
            for platform_id, pf in platform_factors.items():
                # DiDi Food: 60% de probabilidad de no estar disponible (cerrado)
                if platform_id == "didifood" and random.random() < 0.6:
                    items.append(ScrapedItem(
                        platform=platform_id,
                        address_id=address.id,
                        address_name=address.name,
                        address_type=address.zone_type,
                        product_id=product.id,
                        product_name=product.name,
                        available=False,
                    ))
                    continue

                price_low, price_high = base_prices[product.id]
                base_price = round(random.uniform(price_low, price_high) * pf["price_mult"], 2)

                del_low, del_high = pf["delivery_base"]
                zone_mult = zone_delivery_mult[address.zone_type]
                delivery_fee = round(random.uniform(del_low, del_high) * zone_mult, 2)

                service_fee = round(base_price * pf["service_pct"], 2)

                time_low, time_high = pf["time"]
                d_min = int(time_low * zone_mult)
                d_max = int(time_high * zone_mult)

                # Descuentos aleatorios (20% de probabilidad)
                discount = None
                if random.random() < 0.2:
                    discount = random.choice(["2x1", "-20%", "Envío gratis", "-$30"])

                items.append(ScrapedItem(
                    platform=platform_id,
                    address_id=address.id,
                    address_name=address.name,
                    address_type=address.zone_type,
                    product_id=product.id,
                    product_name=product.name,
                    product_price=base_price,
                    delivery_fee=delivery_fee,
                    service_fee=service_fee,
                    total_price=round(base_price + delivery_fee + service_fee, 2),
                    delivery_time_min=d_min,
                    delivery_time_max=d_max,
                    discount_text=discount,
                    available=True,
                ))

    logger.info(f"Datos demo generados: {len(items)} items")
    return items


def run_pipeline(items: list[ScrapedItem]) -> tuple[pd.DataFrame, dict]:
    """Normalizar, exportar y analizar datos."""
    # Normalizar
    df = normalize(items)
    if df.empty:
        logger.warning("No hay datos para procesar")
        return df, {}

    # Exportar
    csv_path = to_csv(df)
    json_path = to_json(df)
    logger.info(f"Datos exportados: {csv_path}, {json_path}")

    # Analizar
    analysis = compare_platforms(df)

    # Generar reporte
    report_path = generate_report(df, analysis)
    logger.info(f"Reporte generado: {report_path}")

    return df, analysis


def main():
    parser = argparse.ArgumentParser(description="Rappi Competitive Intelligence Pipeline")
    parser.add_argument("--scrapers-only", action="store_true", help="Solo ejecutar scrapers")
    parser.add_argument("--analysis-only", action="store_true", help="Solo análisis (usa datos existentes)")
    parser.add_argument("--demo", action="store_true", help="Generar datos demo + análisis completo")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("  Rappi Competitive Intelligence — Pipeline")
    logger.info("=" * 60)

    if args.analysis_only:
        # Cargar datos existentes
        csv_path = Path("data/processed/competitive_intel.csv")
        if not csv_path.exists():
            logger.error(f"No se encontró {csv_path}. Ejecute primero con --demo o sin flags.")
            sys.exit(1)
        df = pd.read_csv(csv_path)
        analysis = compare_platforms(df)
        report_path = generate_report(df, analysis)
        logger.info(f"Análisis completado. Reporte: {report_path}")

    elif args.demo:
        logger.info("Modo DEMO: generando datos de demostración")
        items = generate_demo_data()
        df, analysis = run_pipeline(items)
        logger.info(f"Pipeline demo completado. {len(df)} filas procesadas.")

    else:
        # Pipeline completo
        logger.info("Iniciando scraping de plataformas...")
        items = run_scrapers()

        available = sum(1 for i in items if i.available)
        logger.info(f"Scraping completado: {available}/{len(items)} productos disponibles")

        if available == 0:
            logger.warning("No se obtuvieron datos reales. Ejecutando modo demo como fallback...")
            items = generate_demo_data()

        df, analysis = run_pipeline(items)
        logger.info(f"Pipeline completado. {len(df)} filas procesadas.")

    if args.scrapers_only:
        items = run_scrapers()
        df = normalize(items)
        to_csv(df, filename="raw_scrape.csv", output_dir=Path("data/raw"))
        logger.info("Scraping completado (sin análisis)")


if __name__ == "__main__":
    main()
