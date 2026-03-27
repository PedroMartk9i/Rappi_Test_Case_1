"""
Generador de reportes: Markdown con insights + gráficos Plotly.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

logger = logging.getLogger(__name__)

REPORTS_DIR = Path("reports")


def generate_report(df: pd.DataFrame, analysis: dict) -> Path:
    """
    Genera reporte completo con:
    - 5 insights (Finding / Impact / Recommendation)
    - 3 gráficos Plotly exportados como PNG
    - Archivo Markdown consolidado
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # Generar gráficos
    charts = _generate_charts(df, analysis, timestamp)

    # Generar insights
    insights = _generate_insights(df, analysis)

    # Escribir reporte Markdown
    report_path = REPORTS_DIR / f"competitive_report_{timestamp}.md"
    _write_markdown(report_path, insights, charts, df, analysis)

    logger.info(f"Reporte generado: {report_path}")
    return report_path


def _generate_charts(df: pd.DataFrame, analysis: dict, timestamp: str) -> list[dict]:
    """Genera 3 gráficos Plotly y los guarda como PNG."""
    charts = []
    available_df = df[df["available"]].copy()

    if available_df.empty:
        logger.warning("No hay datos disponibles para generar gráficos")
        return charts

    # Gráfico 1: Precio promedio por plataforma
    try:
        platform_summary = analysis.get("platform_summary", pd.DataFrame())
        if not platform_summary.empty:
            fig1 = px.bar(
                platform_summary,
                x="platform",
                y=["avg_product_price", "avg_delivery_fee", "avg_service_fee"],
                title="Desglose de Costos Promedio por Plataforma",
                labels={"value": "Precio (MXN)", "platform": "Plataforma", "variable": "Componente"},
                barmode="stack",
                color_discrete_map={
                    "avg_product_price": "#FF6B35",
                    "avg_delivery_fee": "#004E89",
                    "avg_service_fee": "#1A936F",
                },
            )
            # Renombrar trazas en la leyenda
            name_map = {"avg_product_price": "Precio producto", "avg_delivery_fee": "Envío", "avg_service_fee": "Servicio"}
            for trace in fig1.data:
                if trace.name in name_map:
                    trace.name = name_map[trace.name]
            fig1.update_layout(legend_title_text="Componente")
            chart1_path = REPORTS_DIR / f"chart_cost_breakdown_{timestamp}.png"
            fig1.write_image(str(chart1_path), width=800, height=500)
            charts.append({"title": "Desglose de costos por plataforma", "path": chart1_path.name})
    except Exception as e:
        logger.warning(f"Error generando gráfico 1: {e}")

    # Gráfico 2: Precios por zona y plataforma (heatmap)
    try:
        zone_data = analysis.get("zone_comparison", pd.DataFrame())
        if not zone_data.empty:
            pivot = zone_data.pivot_table(
                index="address_name", columns="platform",
                values="avg_product_price", aggfunc="mean",
            )
            fig2 = px.imshow(
                pivot,
                title="Precio Promedio de Productos por Zona y Plataforma",
                labels=dict(x="Plataforma", y="Zona", color="Precio (MXN)"),
                color_continuous_scale="RdYlGn_r",
                aspect="auto",
            )
            chart2_path = REPORTS_DIR / f"chart_zone_heatmap_{timestamp}.png"
            fig2.write_image(str(chart2_path), width=800, height=600)
            charts.append({"title": "Heatmap de precios por zona", "path": chart2_path.name})
    except Exception as e:
        logger.warning(f"Error generando gráfico 2: {e}")

    # Gráfico 3: Comparación de fees por tipo de zona
    try:
        fee_data = analysis.get("fee_analysis", pd.DataFrame())
        if not fee_data.empty:
            fig3 = px.bar(
                fee_data,
                x="address_type",
                y="avg_delivery_fee",
                color="platform",
                barmode="group",
                title="Fee de Envío Promedio por Tipo de Zona y Plataforma",
                labels={
                    "avg_delivery_fee": "Fee de Envío (MXN)",
                    "address_type": "Tipo de Zona",
                    "platform": "Plataforma",
                },
                color_discrete_sequence=["#FF6B35", "#004E89", "#1A936F"],
            )
            chart3_path = REPORTS_DIR / f"chart_fees_by_zone_{timestamp}.png"
            fig3.write_image(str(chart3_path), width=800, height=500)
            charts.append({"title": "Fees por tipo de zona", "path": chart3_path.name})
    except Exception as e:
        logger.warning(f"Error generando gráfico 3: {e}")

    return charts


def _generate_insights(df: pd.DataFrame, analysis: dict) -> list[dict]:
    """
    Genera 5 insights basados en los datos con formato:
    Finding / Impact / Recommendation.
    """
    insights = []
    available_df = df[df["available"]].copy()
    platform_summary = analysis.get("platform_summary", pd.DataFrame())
    zone_comparison = analysis.get("zone_comparison", pd.DataFrame())
    fee_analysis = analysis.get("fee_analysis", pd.DataFrame())
    availability = analysis.get("availability", pd.DataFrame())

    # Insight 1: Plataforma más económica
    if not platform_summary.empty:
        cheapest = platform_summary.loc[platform_summary["avg_total_price"].idxmin()]
        most_expensive = platform_summary.loc[platform_summary["avg_total_price"].idxmax()]
        diff_pct = ((most_expensive["avg_total_price"] - cheapest["avg_total_price"]) / cheapest["avg_total_price"] * 100)
        insights.append({
            "title": "Diferencia de precio total entre plataformas",
            "finding": f"{cheapest['platform']} es la plataforma más económica con un costo total promedio de ${cheapest['avg_total_price']:.2f} MXN, "
                       f"mientras que {most_expensive['platform']} es {diff_pct:.1f}% más cara (${most_expensive['avg_total_price']:.2f} MXN).",
            "impact": "Los consumidores sensibles al precio migrarán hacia la plataforma más barata, especialmente en zonas populares.",
            "recommendation": "Rappi debería evaluar su estructura de precios contra el líder en costo para mantener competitividad.",
        })

    # Insight 2: Impacto de fees en el costo total
    if not platform_summary.empty:
        for _, row in platform_summary.iterrows():
            if row["avg_product_price"] and row["avg_product_price"] > 0:
                fee_share = ((row["avg_delivery_fee"] or 0) + (row["avg_service_fee"] or 0)) / row["avg_total_price"] * 100
                insights.append({
                    "title": f"Peso de fees sobre precio total en {row['platform']}",
                    "finding": f"En {row['platform']}, los fees (envío + servicio) representan ~{fee_share:.1f}% del costo total del pedido.",
                    "impact": "Fees altos reducen la conversión de usuarios que comparan plataformas antes de ordenar.",
                    "recommendation": "Implementar estrategias de absorción de fees (membresías, mínimos de compra) para mejorar percepción de valor.",
                })
                break  # Solo un insight de este tipo

    # Insight 3: Variación de precios por tipo de zona
    if not zone_comparison.empty:
        zone_avg = zone_comparison.groupby("address_type")["avg_product_price"].mean()
        if len(zone_avg) > 1:
            premium_avg = zone_avg.get("premium", 0)
            popular_avg = zone_avg.get("popular", 0)
            if popular_avg > 0:
                zone_diff = ((premium_avg - popular_avg) / popular_avg * 100)
                insights.append({
                    "title": "Diferenciación de precios por zona socioeconómica",
                    "finding": f"Los precios en zonas premium son {zone_diff:.1f}% {'más altos' if zone_diff > 0 else 'más bajos'} que en zonas populares.",
                    "impact": "La diferenciación geográfica de precios indica estrategias de pricing dinámico basadas en disposición a pagar.",
                    "recommendation": "Analizar elasticidad de demanda por zona para optimizar precios sin sacrificar volumen.",
                })

    # Insight 4: Tiempos de entrega
    if not platform_summary.empty and "avg_delivery_time" in platform_summary.columns:
        fastest = platform_summary.loc[platform_summary["avg_delivery_time"].idxmin()]
        insights.append({
            "title": "Velocidad de entrega como diferenciador competitivo",
            "finding": f"{fastest['platform']} ofrece los tiempos de entrega más rápidos ({fastest['avg_delivery_time']:.0f} min promedio).",
            "impact": "Los tiempos de entrega influyen directamente en la satisfacción y retención de usuarios.",
            "recommendation": "Invertir en optimización logística (dark stores, rutas inteligentes) en zonas con tiempos altos.",
        })

    # Insight 5: Cobertura y disponibilidad
    if not availability.empty:
        avg_availability = availability.groupby("platform")["availability_rate"].mean()
        best_coverage = avg_availability.idxmax()
        worst_coverage = avg_availability.idxmin()
        insights.append({
            "title": "Cobertura geográfica de plataformas",
            "finding": f"{best_coverage} tiene la mejor cobertura ({avg_availability[best_coverage]*100:.0f}%) "
                       f"mientras que {worst_coverage} cubre solo {avg_availability[worst_coverage]*100:.0f}% de las zonas monitoreadas.",
            "impact": "Zonas sin cobertura representan oportunidad de mercado no capturada.",
            "recommendation": "Expandir cobertura en zonas populares donde la demanda potencial es alta pero la oferta es limitada.",
        })

    # Asegurar exactamente 5 insights
    while len(insights) < 5:
        insights.append({
            "title": "Oportunidad de datos adicionales",
            "finding": "Los datos recolectados son insuficientes para generar este insight con confianza estadística.",
            "impact": "Se requiere mayor volumen de datos para validar hipótesis de pricing.",
            "recommendation": "Ampliar la frecuencia de scraping (diario, horarios pico vs valle) para capturar patrones temporales.",
        })

    return insights[:5]


def _write_markdown(path: Path, insights: list[dict], charts: list[dict], df: pd.DataFrame, analysis: dict) -> None:
    """Escribir reporte en formato Markdown."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    available_count = df["available"].sum() if not df.empty else 0
    total_count = len(df)

    lines = [
        "# Reporte de Inteligencia Competitiva — Delivery CDMX",
        "",
        f"**Fecha de generación:** {timestamp}",
        f"**Datos recolectados:** {available_count}/{total_count} puntos de datos disponibles",
        f"**Plataformas:** {', '.join(df['platform'].unique()) if not df.empty else 'N/A'}",
        f"**Zonas monitoreadas:** {df['address_name'].nunique() if not df.empty else 0}",
        "",
        "---",
        "",
        "## Resumen Ejecutivo",
        "",
    ]

    # Platform summary table
    platform_summary = analysis.get("platform_summary", pd.DataFrame())
    if not platform_summary.empty:
        lines.append("### Métricas por Plataforma")
        lines.append("")
        lines.append("| Plataforma | Precio Producto | Fee Envío | Fee Servicio | Total | Tiempo Entrega |")
        lines.append("|:-----------|:---------------:|:---------:|:------------:|:-----:|:--------------:|")
        for _, row in platform_summary.iterrows():
            lines.append(
                f"| {row['platform']} "
                f"| ${row.get('avg_product_price', 'N/A'):.2f} "
                f"| ${row.get('avg_delivery_fee', 0):.2f} "
                f"| ${row.get('avg_service_fee', 0):.2f} "
                f"| ${row.get('avg_total_price', 'N/A'):.2f} "
                f"| {row.get('avg_delivery_time', 'N/A'):.0f} min |"
            )
        lines.append("")

    # Insights
    lines.extend(["---", "", "## Insights Estratégicos", ""])
    for i, insight in enumerate(insights, 1):
        lines.extend([
            f"### Insight {i}: {insight['title']}",
            "",
            f"**Finding:** {insight['finding']}",
            "",
            f"**Impact:** {insight['impact']}",
            "",
            f"**Recommendation:** {insight['recommendation']}",
            "",
        ])

    # Charts
    if charts:
        lines.extend(["---", "", "## Visualizaciones", ""])
        for chart in charts:
            lines.extend([
                f"### {chart['title']}",
                f"![{chart['title']}]({chart['path']})",
                "",
            ])

    # Methodology
    lines.extend([
        "---",
        "",
        "## Metodología",
        "",
        "- **Herramientas:** Python + Scrapling (stealth browser) + Pandas + Plotly",
        "- **Rate limiting:** 3s entre requests, máx. 3 reintentos, timeout 30s",
        "- **Zonas:** 10 direcciones representativas de CDMX (premium, media, popular)",
        "- **Productos:** 5 items de McDonald's como benchmark",
        "- **Ética:** User-Agent transparente, sin saturación de servidores, uso exclusivo para reclutamiento",
        "",
    ])

    path.write_text("\n".join(lines), encoding="utf-8")
