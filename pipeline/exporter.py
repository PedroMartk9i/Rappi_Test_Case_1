"""
Exportación de datos normalizados a CSV y JSON.
"""

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_DIR = Path("data/processed")


def to_csv(df: pd.DataFrame, filename: str = "competitive_intel.csv", output_dir: Path = DEFAULT_OUTPUT_DIR) -> Path:
    """Exportar DataFrame a CSV."""
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / filename
    df.to_csv(filepath, index=False, encoding="utf-8-sig")
    logger.info(f"CSV exportado: {filepath} ({len(df)} filas)")
    return filepath


def to_json(df: pd.DataFrame, filename: str = "competitive_intel.json", output_dir: Path = DEFAULT_OUTPUT_DIR) -> Path:
    """Exportar DataFrame a JSON."""
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / filename
    df.to_json(filepath, orient="records", force_ascii=False, indent=2)
    logger.info(f"JSON exportado: {filepath} ({len(df)} filas)")
    return filepath
