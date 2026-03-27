"""
Análisis comparativo entre plataformas de delivery.

Genera métricas agregadas por plataforma, zona y producto para
identificar patrones de pricing y competitividad.
"""

import logging
import pandas as pd

logger = logging.getLogger(__name__)


def compare_platforms(df: pd.DataFrame) -> dict:
    """
    Ejecutar análisis comparativo completo.

    Retorna diccionario con DataFrames de cada análisis:
    - platform_summary: métricas promedio por plataforma
    - zone_comparison: precios por zona y plataforma
    - product_comparison: precios por producto y plataforma
    - fee_analysis: análisis de fees por plataforma y zona
    - availability: disponibilidad por plataforma y zona
    """
    if df.empty:
        logger.warning("DataFrame vacío, no se puede realizar análisis")
        return {}

    available_df = df[df["available"]].copy()

    results = {
        "platform_summary": _platform_summary(available_df),
        "zone_comparison": _zone_comparison(available_df),
        "product_comparison": _product_comparison(available_df),
        "fee_analysis": _fee_analysis(available_df),
        "availability": _availability_analysis(df),
    }

    logger.info("Análisis comparativo completado")
    return results


def _platform_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Métricas promedio por plataforma."""
    if df.empty:
        return pd.DataFrame()

    return df.groupby("platform").agg(
        avg_product_price=("product_price", "mean"),
        avg_delivery_fee=("delivery_fee", "mean"),
        avg_service_fee=("service_fee", "mean"),
        avg_total_price=("total_price", "mean"),
        avg_delivery_time=("delivery_time_avg", "mean"),
        product_count=("product_id", "count"),
    ).round(2).reset_index()


def _zone_comparison(df: pd.DataFrame) -> pd.DataFrame:
    """Precio promedio por zona y plataforma."""
    if df.empty:
        return pd.DataFrame()

    return df.groupby(["address_type", "address_name", "platform"]).agg(
        avg_product_price=("product_price", "mean"),
        avg_total_price=("total_price", "mean"),
        avg_delivery_fee=("delivery_fee", "mean"),
    ).round(2).reset_index()


def _product_comparison(df: pd.DataFrame) -> pd.DataFrame:
    """Precios por producto y plataforma."""
    if df.empty:
        return pd.DataFrame()

    return df.groupby(["product_name", "platform"]).agg(
        avg_price=("product_price", "mean"),
        min_price=("product_price", "min"),
        max_price=("product_price", "max"),
        zones_available=("address_id", "nunique"),
    ).round(2).reset_index()


def _fee_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Análisis de fees por plataforma y tipo de zona."""
    if df.empty:
        return pd.DataFrame()

    return df.groupby(["platform", "address_type"]).agg(
        avg_delivery_fee=("delivery_fee", "mean"),
        avg_service_fee=("service_fee", "mean"),
        avg_total_fees=("delivery_fee", lambda x: (x.fillna(0) + df.loc[x.index, "service_fee"].fillna(0)).mean()),
    ).round(2).reset_index()


def _availability_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Disponibilidad por plataforma y zona."""
    return df.groupby(["platform", "address_name"]).agg(
        total_products=("product_id", "count"),
        available_products=("available", "sum"),
        availability_rate=("available", "mean"),
    ).round(2).reset_index()
