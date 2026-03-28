# Reporte de Inteligencia Competitiva — Delivery CDMX

**Fecha de generación:** 2026-03-28 15:47 UTC
**Datos recolectados:** 148/150 puntos de datos disponibles
**Plataformas:** rappi, ubereats, didifood
**Zonas monitoreadas:** 10

---

## Resumen Ejecutivo

### Métricas por Plataforma

| Plataforma | Precio Producto | Fee Envío | Fee Servicio | Total | Tiempo Entrega |
|:-----------|:---------------:|:---------:|:------------:|:-----:|:--------------:|
| didifood | $107.58 | $26.57 | $10.76 | $144.91 | 42 min |
| rappi | $120.35 | $40.68 | $18.05 | $179.08 | 37 min |
| ubereats | $114.02 | $15.35 | $13.68 | $143.06 | 32 min |

---

## Insights Estratégicos

### Insight 1: Diferencia de precio total entre plataformas

**Finding:** ubereats es la plataforma más económica con un costo total promedio de $143.06 MXN, mientras que rappi es 25.2% más cara ($179.08 MXN).

**Impact:** Los consumidores sensibles al precio migrarán hacia la plataforma más barata, especialmente en zonas populares.

**Recommendation:** Rappi debería evaluar su estructura de precios contra el líder en costo para mantener competitividad.

### Insight 2: Peso de fees sobre precio total en didifood

**Finding:** En didifood, los fees (envío + servicio) representan ~25.8% del costo total del pedido.

**Impact:** Fees altos reducen la conversión de usuarios que comparan plataformas antes de ordenar.

**Recommendation:** Implementar estrategias de absorción de fees (membresías, mínimos de compra) para mejorar percepción de valor.

### Insight 3: Diferenciación de precios por zona socioeconómica

**Finding:** Los precios en zonas premium son 1.4% más altos que en zonas populares.

**Impact:** La diferenciación geográfica de precios indica estrategias de pricing dinámico basadas en disposición a pagar.

**Recommendation:** Analizar elasticidad de demanda por zona para optimizar precios sin sacrificar volumen.

### Insight 4: Velocidad de entrega como diferenciador competitivo

**Finding:** ubereats ofrece los tiempos de entrega más rápidos (32 min promedio).

**Impact:** Los tiempos de entrega influyen directamente en la satisfacción y retención de usuarios.

**Recommendation:** Invertir en optimización logística (dark stores, rutas inteligentes) en zonas con tiempos altos.

### Insight 5: Cobertura geográfica de plataformas

**Finding:** rappi tiene la mejor cobertura (100%) mientras que didifood cubre solo 96% de las zonas monitoreadas.

**Impact:** Zonas sin cobertura representan oportunidad de mercado no capturada.

**Recommendation:** Expandir cobertura en zonas populares donde la demanda potencial es alta pero la oferta es limitada.

---

## Visualizaciones

### Desglose de costos por plataforma
![Desglose de costos por plataforma](chart_cost_breakdown_20260328_154718.png)

### Heatmap de precios por zona
![Heatmap de precios por zona](chart_zone_heatmap_20260328_154718.png)

### Fees por tipo de zona
![Fees por tipo de zona](chart_fees_by_zone_20260328_154718.png)

---

## Metodología

- **Herramientas:** Python + Scrapling (stealth browser) + Pandas + Plotly
- **Rate limiting:** 3s entre requests, máx. 3 reintentos, timeout 30s
- **Zonas:** 10 direcciones representativas de CDMX (premium, media, popular)
- **Productos:** 5 items de McDonald's como benchmark
- **Ética:** User-Agent transparente, sin saturación de servidores, uso exclusivo para reclutamiento
