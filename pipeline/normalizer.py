"""
Normalización de datos: List[ScrapedItem] → pd.DataFrame con columnas
calculadas (total_price, delivery_time_avg).
"""

import logging
import pandas as pd

from scrapers.base import ScrapedItem

logger = logging.getLogger(__name__)


def normalize(items: list[ScrapedItem]) -> pd.DataFrame:
    """
    Convierte lista de ScrapedItems a DataFrame normalizado.

    Columnas calculadas:
    - total_price: product_price + delivery_fee + service_fee
    - delivery_time_avg: promedio de min y max
    """
    if not items:
        logger.warning("No hay items para normalizar")
        return pd.DataFrame()

    records = [item.to_dict() for item in items]
    df = pd.DataFrame(records)

    # Calcular total_price donde no exista
    mask = df["total_price"].isna()
    df.loc[mask, "total_price"] = (
        df.loc[mask, "product_price"].fillna(0)
        + df.loc[mask, "delivery_fee"].fillna(0)
        + df.loc[mask, "service_fee"].fillna(0)
    )
    # Si product_price es NaN, total_price también debería serlo
    df.loc[df["product_price"].isna(), "total_price"] = None

    # Calcular delivery_time_avg
    df["delivery_time_avg"] = (
        df[["delivery_time_min", "delivery_time_max"]]
        .mean(axis=1)
        .round(1)
    )

    # Ordenar columnas
    col_order = [
        "platform", "address_id", "address_name", "address_type",
        "product_id", "product_name", "restaurant",
        "product_price", "delivery_fee", "service_fee", "total_price",
        "delivery_time_min", "delivery_time_max", "delivery_time_avg",
        "discount_text", "available", "scrape_timestamp",
    ]
    df = df[[c for c in col_order if c in df.columns]]

    # Tipos
    numeric_cols = ["product_price", "delivery_fee", "service_fee", "total_price"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    logger.info(f"DataFrame normalizado: {len(df)} filas, {len(df.columns)} columnas")
    return df
