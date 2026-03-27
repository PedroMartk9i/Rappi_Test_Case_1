# Rappi Competitive Intelligence System

Sistema automatizado de scraping que recolecta y compara precios de delivery en **Rappi**, **Uber Eats** y **DiDi Food** en 10 zonas de CDMX, genera análisis comparativo y un informe con insights accionables.

## Quick Start

```bash
# 1. Clonar e instalar dependencias
git clone https://github.com/PedroMartk9i/Rappi_Test_Case_1.git
cd Rappi_Test_Case_1
pip install -r requirements.txt

# 2. Instalar browsers para scraping
python -m playwright install chromium
scrapling install          # Instala Camoufox (stealth browser)
python -m camoufox fetch   # Descarga binarios de Camoufox

# 3. Ejecutar pipeline completo (modo demo con datos calibrados)
python main.py --demo

# 4. Ejecutar scraping real (requiere conexión a internet)
python main.py
```

## Modos de Ejecución

| Comando | Descripción |
|:--------|:------------|
| `python main.py` | Pipeline completo: scraping real + análisis + reporte |
| `python main.py --demo` | Datos demo calibrados con precios reales + análisis |
| `python main.py --scrapers-only` | Solo scraping (sin análisis) |
| `python main.py --analysis-only` | Solo análisis sobre datos existentes en `data/processed/` |

## Estructura del Proyecto

```
rappi-competitive-intel/
├── main.py                          # Entry point — orquesta el pipeline
├── config.py                        # 10 direcciones CDMX, 5 productos, constantes
├── scrapers/
│   ├── base.py                      # BaseScraper (ABC) + ScrapedItem (dataclass)
│   ├── rappi_scraper.py             # Rappi: API + Playwright
│   ├── ubereats_scraper.py          # Uber Eats: Playwright + cookie handling
│   └── didifood_scraper.py          # DiDi Food: detección de cierre
├── pipeline/
│   ├── normalizer.py                # List[ScrapedItem] → pd.DataFrame
│   └── exporter.py                  # DataFrame → CSV/JSON
├── analysis/
│   ├── comparator.py                # Análisis comparativo entre plataformas
│   └── report_generator.py          # Markdown + gráficos Plotly (PNG)
├── data/
│   ├── raw/                         # Screenshots de evidencia
│   └── processed/                   # CSV/JSON normalizado
├── reports/                         # Informe Markdown + gráficos PNG
├── test_real_scraping.py            # Tests de scraping HTTP (Fetcher)
├── test_real_scraping_v2.py         # Tests con Playwright Chromium
├── test_deep_scrape.py              # Navegación profunda al menú
├── test_final_extraction.py         # Extracción final de precios
├── test_stealthy.py                 # Tests con StealthyFetcher (Camoufox)
├── SCRAPING_LOG.md                  # Log detallado de cada intento de scraping
└── requirements.txt
```

## Dependencias

```
scrapling[all]>=0.3.0    # Web scraping (HTTP + stealth browser)
pandas>=2.0.0            # Procesamiento de datos
plotly>=5.18.0           # Gráficos interactivos
kaleido>=0.2.1           # Exportación de gráficos a PNG
python-dotenv>=1.0.0     # Variables de entorno
```

Adicionalmente se requiere **Playwright** (instalado con scrapling) y **Chromium**.

## Cobertura Geográfica

10 direcciones en CDMX, organizadas por nivel socioeconómico:

| Tipo | Zonas |
|:-----|:------|
| **Premium** | Polanco, Condesa, Roma Norte |
| **Media** | Del Valle, Coyoacán, Santa Fe, Tlalpan |
| **Popular** | Iztapalapa, Naucalpan, Ecatepec |

## Productos de Referencia

5 productos de McDonald's como benchmark estandarizado:

| Producto | Precio Real UE (MXN) |
|:---------|:--------------------:|
| Big Mac | $145.00 |
| McCombo Mediano Big Mac | $169.00 |
| McNuggets 10 pzas | $155.00 |
| Coca-Cola 600ml | $65.00 |
| Agua 1L | $39.00 |

*Precios reales extraídos de Uber Eats McDonald's Polanco el 2026-03-27.*

## Métricas Recolectadas

- Precio del producto
- Fee de envío (delivery fee)
- Fee de servicio (service fee)
- Precio total (producto + fees)
- Tiempo estimado de entrega (min/max)
- Disponibilidad del producto
- Descuentos activos

## Resultados de Scraping Real

| Plataforma | Método | Resultado | Blocker |
|:-----------|:-------|:----------|:--------|
| **Uber Eats** | Playwright Chromium | **155 precios reales extraídos** | Cookie consent (resuelto) |
| **Rappi** | Playwright + API | Página carga, APIs descubiertas | Login obligatorio para ver menú |
| **DiDi Food** | HTTP Fetcher | Dominio en venta | Servicio cerrado en México (2023) |

Ver `SCRAPING_LOG.md` para documentación detallada de cada intento.

## Outputs

| Archivo | Descripción |
|:--------|:------------|
| `data/processed/competitive_intel.csv` | Dataset normalizado (150 filas) |
| `data/processed/competitive_intel.json` | Mismo dataset en JSON |
| `reports/competitive_report_*.md` | Informe con 5 insights accionables |
| `reports/chart_cost_breakdown_*.png` | Desglose de costos por plataforma |
| `reports/chart_zone_heatmap_*.png` | Heatmap de precios por zona |
| `reports/chart_fees_by_zone_*.png` | Fees por tipo de zona |
| `data/raw/screenshot_*.png` | Screenshots de evidencia del scraping |

## Arquitectura

```
                    ┌──────────────┐
                    │   main.py    │
                    │  (orquesta)  │
                    └──────┬───────┘
                           │
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼
    ┌──────────────┐ ┌───────────┐ ┌────────────┐
    │ RappiScraper │ │ UberEats  │ │  DiDiFood  │
    │  (Playwright │ │ Scraper   │ │  Scraper   │
    │   + API)     │ │(Playwright│ │ (detección │
    │              │ │+ cookies) │ │  cierre)   │
    └──────┬───────┘ └─────┬─────┘ └─────┬──────┘
           │               │             │
           └───────┬───────┘─────────────┘
                   ▼
           List[ScrapedItem]
                   │
            ┌──────▼───────┐
            │  Normalizer  │──→ pd.DataFrame
            └──────┬───────┘
                   │
            ┌──────▼───────┐
            │   Exporter   │──→ CSV / JSON
            └──────┬───────┘
                   │
            ┌──────▼───────┐
            │  Comparator  │──→ Análisis comparativo
            └──────┬───────┘
                   │
            ┌──────▼───────┐
            │   Report     │──→ Markdown + Plotly PNGs
            │  Generator   │
            └──────────────┘
```

## Decisiones Técnicas

- **Scrapling + Playwright** en vez de Selenium: más rápido, mejor anti-detección, API moderna.
- **Playwright Chromium** como método principal (probado exitosamente en scraping real).
- **Camoufox (StealthyFetcher)** como fallback para anti-bot más agresivo.
- **Datos demo calibrados**: los precios base del modo `--demo` están calibrados con datos reales extraídos de Uber Eats, no son inventados.
- **Fallback automático**: si el scraping real falla, el pipeline genera datos demo para completar el análisis.

## Rate Limiting y Ética

- 3 segundos entre requests
- Máximo 3 reintentos por producto
- Timeout de 30 segundos
- User-Agent transparente (Chrome 131.0)
- Sin saturación de servidores
- Uso exclusivo para fines de reclutamiento

## Limitaciones Conocidas

1. **Rappi** requiere cuenta/login para ver precios del menú. Las APIs internas retornan 403 sin token de sesión autenticado.
2. **DiDi Food** cerró operaciones en México en 2023. El dominio `didifood.com` está en venta.
3. **Scraping a escala** (10 zonas x 5 productos x 3 plataformas = 150 requests con Playwright) toma ~30-60 min. El modo `--demo` existe para desarrollo rápido.
4. Los precios pueden variar por hora del día, día de la semana y demanda en tiempo real.

## Next Steps (con más tiempo)

- [ ] Autenticación en Rappi para extraer precios reales
- [ ] Dashboard interactivo con Streamlit
- [ ] Scraping multi-vertical (retail, farmacia)
- [ ] Scheduling con cron/GitHub Actions para monitoreo continuo
- [ ] Análisis de tendencias temporales
- [ ] Proxy rotation para escala
