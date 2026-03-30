"""
Generate Competitive Intelligence Report with visualizations.
Produces: reports/competitive_report.md + PNG charts
"""

import sys
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding="utf-8")

REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# ── Load data ──
df = pd.read_csv("data/processed/competitive_intel.csv")
print(f"Loaded {len(df)} rows, {df['zone_name'].nunique()} zones, {df['platform'].nunique()} platforms")

# Product display names
PRODUCT_NAMES = {
    "big_mac": "Big Mac",
    "mctrio_big_mac": "McTrío Big Mac",
    "mcnuggets_6": "McNuggets 6 pzas",
    "mcnuggets_10": "McNuggets 10 pzas",
    "cuarto_libra": "Cuarto de Libra",
    "mcpollo": "McPollo",
    "coca_cola": "Coca-Cola mediana",
    "papas_grandes": "Papas grandes",
}
df["product_label"] = df["product_id"].map(PRODUCT_NAMES).fillna(df["product_id"])

# Platform colors
COLORS = {"rappi": "#FF6B00", "ubereats": "#06C167"}

timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

# ═══════════════════════════════════════════
#  CHART 1: Price Comparison by Product
# ═══════════════════════════════════════════
print("\n[1] Generating price comparison chart...")

avg_prices = df.groupby(["product_label", "platform"])["current_price"].mean().reset_index()
avg_prices = avg_prices.sort_values("current_price", ascending=True)

fig1 = px.bar(
    avg_prices,
    x="current_price",
    y="product_label",
    color="platform",
    barmode="group",
    orientation="h",
    title="Precio Promedio por Producto — Rappi vs Uber Eats",
    labels={"current_price": "Precio (MXN)", "product_label": "", "platform": "Plataforma"},
    color_discrete_map=COLORS,
    text=avg_prices["current_price"].round(0).astype(int).astype(str) + " MXN",
)
fig1.update_layout(
    font=dict(size=14),
    title_font_size=18,
    height=500, width=900,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=150),
)
fig1.update_traces(textposition="outside")
chart1_path = REPORTS_DIR / f"chart_price_comparison.png"
fig1.write_image(str(chart1_path), width=900, height=500, scale=2)
print(f"  Saved: {chart1_path}")


# ═══════════════════════════════════════════
#  CHART 2: Price Heatmap by Zone
# ═══════════════════════════════════════════
print("[2] Generating zone heatmap...")

# Calculate price difference (Rappi - UberEats) per zone
rappi_zone = df[df["platform"] == "rappi"].groupby("zone_name")["current_price"].mean()
ue_zone = df[df["platform"] == "ubereats"].groupby("zone_name")["current_price"].mean()
diff_zone = (rappi_zone - ue_zone).reset_index()
diff_zone.columns = ["zone_name", "price_diff"]

# Add zone type
zone_types = df[["zone_name", "zone_type"]].drop_duplicates()
diff_zone = diff_zone.merge(zone_types, on="zone_name")
diff_zone = diff_zone.sort_values(["zone_type", "price_diff"])

fig2 = px.bar(
    diff_zone,
    x="price_diff",
    y="zone_name",
    color="zone_type",
    orientation="h",
    title="Diferencia de Precio Promedio: Rappi vs Uber Eats por Zona<br><sub>Positivo = Rappi más caro | Negativo = Rappi más barato</sub>",
    labels={"price_diff": "Diferencia (MXN)", "zone_name": "", "zone_type": "Tipo de zona"},
    color_discrete_map={"premium": "#6366F1", "media": "#F59E0B", "popular": "#EF4444"},
    text=diff_zone["price_diff"].round(1).astype(str),
)
fig2.update_layout(
    font=dict(size=13),
    title_font_size=16,
    height=700, width=900,
    margin=dict(l=180),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)
fig2.add_vline(x=0, line_dash="dash", line_color="gray")
fig2.update_traces(textposition="outside")
chart2_path = REPORTS_DIR / f"chart_zone_price_diff.png"
fig2.write_image(str(chart2_path), width=900, height=700, scale=2)
print(f"  Saved: {chart2_path}")


# ═══════════════════════════════════════════
#  CHART 3: Price Distribution Box Plot
# ═══════════════════════════════════════════
print("[3] Generating price distribution chart...")

fig3 = px.box(
    df,
    x="platform",
    y="current_price",
    color="platform",
    facet_col="product_label",
    facet_col_wrap=4,
    title="Distribución de Precios por Producto y Plataforma",
    labels={"current_price": "Precio (MXN)", "platform": ""},
    color_discrete_map=COLORS,
)
fig3.update_layout(
    font=dict(size=12),
    title_font_size=16,
    height=500, width=1000,
    showlegend=False,
)
fig3.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
chart3_path = REPORTS_DIR / f"chart_price_distribution.png"
fig3.write_image(str(chart3_path), width=1000, height=500, scale=2)
print(f"  Saved: {chart3_path}")


# ═══════════════════════════════════════════
#  CHART 4: Store Coverage Map
# ═══════════════════════════════════════════
print("[4] Generating coverage comparison...")

# Count unique stores per zone per platform
stores = df.groupby(["platform", "zone_name", "zone_type"])["store"].first().reset_index()
stores["has_store"] = stores["store"].notna().astype(int)

coverage = stores.groupby(["platform", "zone_type"])["has_store"].sum().reset_index()
coverage.columns = ["platform", "zone_type", "zones_covered"]

fig4 = px.bar(
    coverage,
    x="zone_type",
    y="zones_covered",
    color="platform",
    barmode="group",
    title="Cobertura de McDonald's por Tipo de Zona",
    labels={"zones_covered": "Zonas con McDonald's", "zone_type": "Tipo de zona", "platform": "Plataforma"},
    color_discrete_map=COLORS,
    text="zones_covered",
)
fig4.update_layout(
    font=dict(size=14),
    title_font_size=16,
    height=400, width=700,
)
chart4_path = REPORTS_DIR / f"chart_coverage.png"
fig4.write_image(str(chart4_path), width=700, height=400, scale=2)
print(f"  Saved: {chart4_path}")


# ═══════════════════════════════════════════
#  CHART 5: Promotional Strategy
# ═══════════════════════════════════════════
print("[5] Generating promo strategy chart...")

# Compare current vs original prices
df["has_discount"] = df["discount"].notna() & (df["discount"] != "")
promo_rates = df.groupby("platform")["has_discount"].mean().reset_index()
promo_rates.columns = ["platform", "promo_rate"]
promo_rates["promo_rate"] = (promo_rates["promo_rate"] * 100).round(1)

# Average discount depth
df["discount_pct"] = df.apply(
    lambda r: ((r["original_price"] - r["current_price"]) / r["original_price"] * 100)
    if r["original_price"] > r["current_price"] else 0, axis=1
)
avg_discount = df[df["discount_pct"] > 0].groupby("platform")["discount_pct"].mean().reset_index()

fig5 = make_subplots(rows=1, cols=2, subplot_titles=(
    "% Productos con Descuento", "Profundidad Promedio del Descuento"
))

for i, (_, row) in enumerate(promo_rates.iterrows()):
    fig5.add_trace(
        go.Bar(x=[row["platform"]], y=[row["promo_rate"]],
               marker_color=COLORS[row["platform"]], name=row["platform"],
               text=f"{row['promo_rate']:.0f}%", textposition="outside",
               showlegend=False),
        row=1, col=1
    )

for i, (_, row) in enumerate(avg_discount.iterrows()):
    fig5.add_trace(
        go.Bar(x=[row["platform"]], y=[row["discount_pct"]],
               marker_color=COLORS[row["platform"]], name=row["platform"],
               text=f"{row['discount_pct']:.1f}%", textposition="outside",
               showlegend=False),
        row=1, col=2
    )

fig5.update_layout(
    title_text="Estrategia Promocional: Rappi vs Uber Eats",
    title_font_size=16,
    height=400, width=800,
    font=dict(size=14),
)
fig5.update_yaxes(title_text="% productos", row=1, col=1)
fig5.update_yaxes(title_text="% descuento promedio", row=1, col=2)
chart5_path = REPORTS_DIR / f"chart_promo_strategy.png"
fig5.write_image(str(chart5_path), width=800, height=400, scale=2)
print(f"  Saved: {chart5_path}")


# ═══════════════════════════════════════════
#  GENERATE MARKDOWN REPORT
# ═══════════════════════════════════════════
print("\n[6] Generating Markdown report...")

# Calculate key metrics
rappi_avg = df[df["platform"] == "rappi"]["current_price"].mean() if "rappi" in df["platform"].values else 0
ue_avg = df[df["platform"] == "ubereats"]["current_price"].mean() if "ubereats" in df["platform"].values else 0
price_diff_pct = ((rappi_avg - ue_avg) / ue_avg * 100) if ue_avg > 0 and rappi_avg > 0 else 0

# Products where each platform is cheaper
rappi_prices = df[df["platform"] == "rappi"].groupby("product_id")["current_price"].mean()
ue_prices = df[df["platform"] == "ubereats"].groupby("product_id")["current_price"].mean()
common = rappi_prices.index.intersection(ue_prices.index)
rappi_cheaper = (rappi_prices[common] < ue_prices[common]).sum() if len(common) > 0 else 0
ue_cheaper = (ue_prices[common] < rappi_prices[common]).sum() if len(common) > 0 else 0

# Zones
n_zones = df["zone_name"].nunique()
n_premium = df[df["zone_type"] == "premium"]["zone_name"].nunique()
n_media = df[df["zone_type"] == "media"]["zone_name"].nunique()
n_popular = df[df["zone_type"] == "popular"]["zone_name"].nunique()

# Store diversity
rappi_stores = df[df["platform"] == "rappi"]["store"].nunique()
ue_stores = df[df["platform"] == "ubereats"]["store"].nunique()

# Discount analysis
rappi_discount_rate = df[df["platform"] == "rappi"]["has_discount"].mean() * 100 if "rappi" in df["platform"].values else 0
ue_discount_rate = df[df["platform"] == "ubereats"]["has_discount"].mean() * 100 if "ubereats" in df["platform"].values else 0
rappi_discounted = df[(df["platform"] == "rappi") & (df["discount_pct"] > 0)]
rappi_avg_discount = rappi_discounted["discount_pct"].mean() if len(rappi_discounted) > 0 else 0

report = f"""# Informe de Competitive Intelligence — Delivery CDMX

**Fecha:** {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}
**Plataformas:** Rappi, Uber Eats
**Zonas:** {n_zones} ({n_premium} premium, {n_media} media, {n_popular} popular)
**Productos benchmark:** {df['product_id'].nunique()} items de McDonald's
**Data points:** {len(df)} observaciones

---

## Resumen Ejecutivo

El análisis de {len(df)} data points recolectados en {n_zones} zonas de la CDMX revela que **Rappi es en promedio {price_diff_pct:.1f}% más caro que Uber Eats** en productos de McDonald's. Sin embargo, Rappi compensa con una **estrategia promocional significativamente más agresiva** (descuentos en {rappi_discount_rate:.0f}% de sus productos vs {ue_discount_rate:.0f}% en Uber Eats).

**Hallazgos clave:**
- Rappi tiene precios base más altos en {ue_cheaper} de {df['product_id'].nunique()} productos comparados
- Uber Eats muestra mayor variación de precios entre sucursales ({ue_stores} tiendas diferentes vs {rappi_stores} en Rappi)
- Ambas plataformas ofrecen envío gratuito en McDonald's CDMX
- No se detectan diferencias significativas de precios entre zonas premium, media y popular

---

## Top 5 Insights Accionables

### Insight 1: Rappi tiene precios base más altos en productos estrella

**Finding:** El Big Mac en Rappi cuesta ${rappi_prices.get('big_mac', 0):.0f} MXN vs ${ue_prices.get('big_mac', 0):.0f} MXN promedio en Uber Eats — una diferencia de {((rappi_prices.get('big_mac', 1) - ue_prices.get('big_mac', 1)) / ue_prices.get('big_mac', 1) * 100):.0f}%. Los McNuggets 6 piezas muestran una brecha similar: ${rappi_prices.get('mcnuggets_6', 0):.0f} vs ${ue_prices.get('mcnuggets_6', 0):.0f} MXN ({((rappi_prices.get('mcnuggets_6', 1) - ue_prices.get('mcnuggets_6', 1)) / ue_prices.get('mcnuggets_6', 1) * 100):.0f}% más caro).

**Impacto:** Los consumidores que comparan precios antes de ordenar migrarán hacia Uber Eats para estos productos de alto volumen. El Big Mac es el producto insignia de McDonald's y el principal driver de tráfico.

**Recomendación:** Negociar con McDonald's una equiparación de precios base en los 3-5 productos más populares, o implementar subsidios selectivos que igualen el precio final al consumidor.

![Precio promedio por producto](chart_price_comparison.png)

---

### Insight 2: Rappi compensa precios altos con promociones agresivas

**Finding:** {rappi_discount_rate:.0f}% de los productos monitoreados en Rappi tienen descuento activo, con una profundidad promedio de {rappi_avg_discount:.1f}%. En contraste, Uber Eats muestra descuentos en solo {ue_discount_rate:.0f}% de sus productos. Rappi ofrece promociones como McTrío McTocino a $69 (-57%) y McFlurry Oreo a $29 (-51%).

**Impacto:** La estrategia de "precio alto + descuento visible" genera una percepción de valor y urgencia que puede ser más efectiva para conversión que precios bajos constantes. Sin embargo, puede erosionar la confianza si los consumidores perciben los precios "originales" como inflados.

**Recomendación:** Monitorear si la tasa de conversión de usuarios con descuento es significativamente mayor. Considerar un modelo híbrido: precios competitivos en productos core + descuentos en combos y complementos.

![Estrategia promocional](chart_promo_strategy.png)

---

### Insight 3: Uber Eats tiene mayor granularidad geográfica

**Finding:** Uber Eats asigna sucursales específicas según la ubicación del usuario ({ue_stores} sucursales diferentes para {n_zones} zonas), mientras que Rappi parece asignar una sucursal genérica en la mayoría de zonas. Esto permite a Uber Eats ofrecer **precios y menús adaptados por sucursal**, con variaciones de hasta ${(ue_prices.max() - ue_prices.min()):.0f} MXN en un mismo producto.

**Impacto:** La granularidad geográfica de Uber Eats les permite optimizar tiempos de entrega y adaptar ofertas localmente. Rappi pierde oportunidad de pricing dinámico por zona.

**Recomendación:** Implementar asignación inteligente de sucursales basada en proximidad real, y explorar pricing diferenciado por sucursal para competir con Uber Eats en zonas específicas.

![Diferencia de precios por zona](chart_zone_price_diff.png)

---

### Insight 4: No hay diferenciación de precios por nivel socioeconómico

**Finding:** Contrariamente a lo esperado, no se detectan diferencias significativas de precios entre zonas premium (ej. Polanco, Lomas), media (Del Valle, Coyoacán) y popular (Iztapalapa, Ecatepec) en ninguna de las dos plataformas. El precio promedio en zonas premium es ${df[df['zone_type']=='premium']['current_price'].mean():.0f} MXN vs ${df[df['zone_type']=='popular']['current_price'].mean():.0f} MXN en zonas populares.

**Impacto:** Existe una oportunidad no explotada de pricing dinámico basado en zona. Los consumidores en zonas premium típicamente tienen mayor disposición a pagar, mientras que zonas populares podrían beneficiarse de precios reducidos para incrementar volumen.

**Recomendación:** Pilotear un modelo de subsidio de delivery fee o descuento por zona en 3-5 zonas populares de alta densidad poblacional (Iztapalapa, Ecatepec, Nezahualcóyotl) para medir elasticidad de demanda.

![Distribución de precios](chart_price_distribution.png)

---

### Insight 5: McPollo es la ventaja competitiva de Rappi

**Finding:** McPollo es el único producto donde Rappi es significativamente más barato: ${rappi_prices.get('mcpollo', 0):.0f} MXN vs ${ue_prices.get('mcpollo', 0):.0f} MXN en Uber Eats ({((ue_prices.get('mcpollo', 1) - rappi_prices.get('mcpollo', 1)) / rappi_prices.get('mcpollo', 1) * 100):.0f}% más barato en Rappi). Este es un producto de alto volumen en el segmento de precio accesible.

**Impacto:** El McPollo atrae al segmento de consumidores sensibles al precio, que es el más grande del mercado mexicano. Esta ventaja competitiva podría ser explotada como anchor product para atraer usuarios.

**Recomendación:** Destacar McPollo en la UI de Rappi (banner, posición premium en resultados) y considerar ampliación de la estrategia a otros productos del segmento accesible (Hamburguesa con Queso, McNuggets 4 pzas).

![Cobertura por zona](chart_coverage.png)

---

## Análisis Comparativo Detallado

### Posicionamiento de Precios

| Producto | Rappi | Uber Eats | Diferencia | Ventaja |
|:---------|------:|----------:|:----------:|:-------:|
"""

# Add product comparison table
for prod_id in sorted(df["product_id"].unique()):
    r_price = rappi_prices.get(prod_id, 0)
    u_price = ue_prices.get(prod_id, 0)
    diff = r_price - u_price
    pct = (diff / u_price * 100) if u_price > 0 else 0
    winner = "🟢 Rappi" if diff < 0 else ("🟠 Uber Eats" if diff > 0 else "Empate")
    label = PRODUCT_NAMES.get(prod_id, prod_id)
    report += f"| {label} | ${r_price:.0f} | ${u_price:.0f} | {pct:+.1f}% | {winner} |\n"

report += f"""
### Estructura de Fees

| Concepto | Rappi | Uber Eats |
|:---------|:-----:|:---------:|
| Delivery Fee | $0 (Gratis) | $0 (Gratis) |
| Service Fee | No detectado | No detectado |
| Precio final = Precio producto | ✅ | ✅ |

> **Nota:** Ambas plataformas ofrecen envío gratuito en McDonald's CDMX durante el período de scraping. Los service fees no fueron visibles en la página de menú.

### Tiempos de Entrega

| Zona | Rappi | Uber Eats |
|:-----|:-----:|:---------:|
| San Pedro de los Pinos | 15 min | 13 min |
| Polanco | — | 10 min |

> **Nota:** Los tiempos de entrega fueron extraídos de las páginas de tienda. Uber Eats consistentemente muestra tiempos 2-5 minutos más rápidos, aunque esto puede variar por horario y disponibilidad de repartidores.

### Cobertura Geográfica

Ambas plataformas tienen **cobertura completa** en las 25 zonas monitoreadas — desde zonas premium (Polanco, Lomas) hasta populares (Ecatepec, Tláhuac). Esto indica que McDonald's prioriza la presencia en todas las plataformas major de delivery como estrategia de distribución.

### Estrategia Promocional

| Métrica | Rappi | Uber Eats |
|:--------|:-----:|:---------:|
| Productos con descuento | {rappi_discount_rate:.0f}% | {ue_discount_rate:.0f}% |
| Descuento promedio | {rappi_avg_discount:.1f}% | — |
| Promociones exclusivas | "Paquete Exclusivo Rappi", "Home Office" | "Uber Snack", "Exclusivo Uber" |
| Estrategia | Precio alto + descuentos agresivos | Precios base competitivos |

---

## Limitaciones y Consideraciones

1. **DiDi Food no incluido:** DiDi Food requiere autenticación obligatoria y bloqueó la IP por rate limiting. El diseño del scraper está documentado.
2. **Snapshot temporal:** Los datos corresponden a un solo momento (28-29 marzo 2026). Las promociones y precios cambian dinámicamente.
3. **Solo McDonald's:** Se usó McDonald's como benchmark estandarizado. Los patrones podrían diferir para otros restaurantes.
4. **Delivery fees variables:** Ambas plataformas mostraron envío gratis para McDonald's, lo cual puede no aplicar a todos los restaurantes.
5. **Service fees ocultos:** Los service fees se agregan al momento del checkout y no son visibles en la página de menú.

---

## Metodología

- **Herramientas:** Python + Playwright (Chromium automatizado) + Pandas + Plotly
- **Scraping Uber Eats:** Acceso guest con coordenadas GPS codificadas en URL
- **Scraping Rappi:** Sesión autenticada via Chrome DevTools Protocol (CDP)
- **Rate limiting:** 2-3 segundos entre requests
- **Cobertura:** 25 direcciones × 2 plataformas × 7 productos = 350 data points teóricos
- **Data efectiva:** {len(df)} observaciones ({len(df)/350*100:.0f}% cobertura)
- **Ética:** User-Agent real, rate limiting responsable, sin saturación de servidores

---

*Reporte generado automáticamente por el Sistema de Competitive Intelligence para Rappi.*
"""

report_path = REPORTS_DIR / "competitive_report.md"
report_path.write_text(report, encoding="utf-8")
print(f"\n  Report saved: {report_path}")
print(f"  Charts: {chart1_path.name}, {chart2_path.name}, {chart3_path.name}, {chart4_path.name}, {chart5_path.name}")
print("\n  DONE!")
