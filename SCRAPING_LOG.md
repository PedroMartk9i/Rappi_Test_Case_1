# Log de Scraping Real — Competitive Intelligence

## Fechas: 2026-03-27 (Rappi, Uber Eats) / 2026-03-28 (DiDi Food corregido)
## Ubicación de prueba: Polanco, CDMX (19.4326, -99.1942)

---

## Resumen de Resultados

| Plataforma | HTTP (Fetcher) | Browser (Playwright) | Datos Extraídos | Blocker |
|:-----------|:--------------:|:-------------------:|:---------------:|:--------|
| **Rappi** | 200 (SPA vacía, 4 bytes) | Carga página, 3 menciones McD | Parcial — requiere login | Login/signup obligatorio para ver menú |
| **Uber Eats** | 200 (SPA vacía, 4 bytes) | Menú completo cargado | **Precios reales extraídos** | Cookie consent (resuelto) |
| **DiDi Food** | 200 (SPA vacía, 4 bytes) | Carga landing, detecta dirección | Parcial — requiere login | Login obligatorio para ver feed |

> **CORRECCIÓN (2026-03-28):** El dominio correcto de DiDi Food es `didi-food.com` (con guión).
> El dominio `didifood.com` (sin guión) es un dominio en venta que NO pertenece a DiDi.
> DiDi Food opera activamente en México con 30M+ usuarios y 52K+ restaurantes.

---

## Detalle por Plataforma

### Rappi

**Estrategias intentadas:**
1. `Fetcher.get()` a `/restaurantes` → HTTP 200, body: "None" (4 bytes). Rappi es SPA pura.
2. APIs internas:
   - `/api/web-gateway/web/stores-router/search` → HTTP 403 (Forbidden)
   - `/api/pns-global-search-api/v1/unified-search` → HTTP 405 (Method Not Allowed, retorna JSON `{"message": "..."}`)
   - `/api/dynamic-mkt-gateway-api/...` → HTTP 404
   - `/api/web-gateway/web/dynamic/context/content/restaurants` → HTTP 403
3. Playwright Chromium → Página carga correctamente (609KB HTML). Se detectaron 3 menciones de McDonald's. Se interceptaron 8 API responses internas (Google Maps, `services.mxgrability.rappi.com`).
4. Navegación a McDonald's → Click en link `/ciudad-de-mexico/restaurantes/delivery/706-mcdonald-s` exitoso. Página de store listing carga pero requiere dirección.
5. Ingreso de dirección → Muestra sugerencias correctamente (Masaryk 360, Polanco) **pero redirige a `/login/signup` para ver menú y precios**.

**Hallazgos clave:**
- Rappi usa `services.mxgrability.rappi.com` como backend de APIs
- La API `/api/pns-global-search-api/v1/unified-search` responde (405 = necesita POST, no GET)
- La API de passport/guest genera tokens temporales: `services.mxgrability.rappi.com/api/rocket/v2/guest/passport/`
- **Blocker principal**: Rappi requiere cuenta/login para mostrar menú con precios
- **Solución potencial**: Usar guest token de la API passport para autenticarse en las APIs internas

**Evidencia:** `data/raw/screenshot_rappi.png`, `screenshot_rappi_mcdonalds.png`, `screenshot_rappi_after_address.png`

---

### Uber Eats

**Estrategias intentadas:**
1. `Fetcher.get()` → HTTP 307 redirect, body: "None" (4 bytes). Uber Eats es SPA con Cloudflare.
2. Playwright Chromium con cookie handling:
   - Aceptar cookies automáticamente → ✅
   - Ingresar dirección (Masaryk 360, Polanco) → ✅ Selección de sugerencia exitosa
   - Feed de restaurantes cargado → ✅ Precios visibles, 11 menciones de McDonald's
3. Navegación directa a McDonald's Polanco (`/mx/store/mcdonalds-polanco/GMcH3w_vX4CtLxBPRICeWA`) → ✅ Menú completo

**Datos extraídos (precios reales MXN, McDonald's Polanco, Uber Eats):**

| Producto | Precio Individual | Precio McTrío Mediano |
|:---------|:-----------------:|:--------------------:|
| Big Mac | $145.00 | $169.00 |
| Big Mac Tocino | $165.00 | $189.00 |
| McNuggets 10 pzas | $155.00 | $179.00 |
| McNuggets 20 pzas | $209.00 | $229.00 |
| Coca-Cola mediana (21oz) | $65.00 | — |
| Coca-Cola Zero mediana | $65.00 | — |
| Agua Ciel 600ml | $39.00 | — |

**Otros precios detectados:**
- McNuggets 4 pzas: $59.00
- McNuggets 6 pzas: $109.00
- McTrío mediano Mario Galaxy Big Mac: $169.00
- McTrío mediano Mario Galaxy McNuggets: $179.00
- Cajita Feliz McNuggets: $159.00
- Combo familiar (4 Hamburguesas + 10 McNuggets + 2 Papas + 2 Refrescos): $679.00

**Info de store:**
- Store ID: `GMcH3w_vX4CtLxBPRICeWA`
- Rating: 4.5
- Dirección: Blvd Manuel Ávila Camacho No. 137
- 65 API responses interceptadas durante la navegación

**Evidencia:** `data/raw/screenshot_ubereats_mcdonalds_menu.png`, `ubereats_mcdonalds_menu.html`

---

### DiDi Food

> **CORRECCIÓN:** El dominio correcto es `didi-food.com` (con guión), NO `didifood.com`.

**Estrategias intentadas (2026-03-27 — dominio incorrecto):**
1. `Fetcher.get()` a `didifood.com/es-MX` → HTTP 302 redirect a `forsale.dynadot.com` — dominio en venta, NO es de DiDi

**Estrategias intentadas (2026-03-28 — dominio correcto):**
1. `Fetcher.get()` a `didi-food.com/es-MX` → HTTP 200, body: "None" (4 bytes). SPA pura, igual que Rappi y UE.
2. Playwright Chromium → Landing page carga correctamente:
   - Texto visible: "Entrega de comida hasta tu puerta"
   - Input detectado: "Ingresar dirección de entrega"
   - Geolocalización resolvió la dirección correctamente (Eugenio Sue 116, Polanco)
3. Ingreso de dirección + click "Buscar comida" → **Redirige a login** (page.didiglobal.com)
   - Formulario de login con teléfono (+52 México)
   - Acepta inicio con contraseña o código de verificación

**Hallazgo:** DiDi Food opera activamente en México (30M+ usuarios, 52K+ restaurantes, 60+ ciudades). Igual que Rappi, requiere cuenta para acceder al feed de restaurantes y precios.

**Blocker:** Login obligatorio. Mismo patrón que Rappi.

**Evidencia:** `data/raw/screenshot_didifood.png` (landing), `screenshot_didifood_feed.png` (login redirect)

---

## Hallazgos Técnicos

1. **Las 3 plataformas son SPAs** — HTTP simple retorna body vacío (4 bytes "None"). Se requiere browser rendering.
2. **Scrapling's Fetcher** funciona para requests HTTP pero no puede renderizar SPAs. StealthyFetcher (Camoufox) requiere instalación correcta del browser.
3. **Playwright Chromium** fue la herramienta más efectiva para las 3 plataformas.
4. **Uber Eats** fue la plataforma más accesible — menú completo con precios extraíbles después de aceptar cookies e ingresar dirección.
5. **Rappi** es restrictiva — requiere login/signup para ver precios del menú. Las APIs internas devuelven 403/405.
6. **DiDi Food** está activa en México (dominio correcto: `didi-food.com`). También requiere login para ver feed y precios.
7. **2 de 3 plataformas requieren autenticación** — solo Uber Eats permite acceso anónimo completo al menú.

## Archivos de Evidencia

```
data/raw/
├── screenshot_rappi.png                    # Landing page
├── screenshot_rappi_mcdonalds.png          # Store listing McDonald's
├── screenshot_rappi_after_address.png      # Después de ingresar dirección
├── screenshot_ubereats_step1.png           # Feed con dirección Polanco
├── screenshot_ubereats_mcdonalds_menu.png  # Menú completo McDonald's
├── sample_rappi_playwright.html            # HTML renderizado
├── ubereats_mcdonalds_menu.html            # HTML menú UE
├── scraping_test_results_v2.json           # Resultados HTTP tests
├── final_extraction_results.json           # Datos extraídos finales
└── scraping_test_log.txt                   # Log completo
```
