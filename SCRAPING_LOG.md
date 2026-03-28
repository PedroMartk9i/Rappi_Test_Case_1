# Log de Scraping Real — Competitive Intelligence

## Fechas: 2026-03-27 (Rappi, Uber Eats) / 2026-03-28 (DiDi Food corregido, login Rappi y DiDi)
## Ubicación de prueba: Polanco, CDMX (19.4326, -99.1942)

---

## Resumen de Resultados

| Plataforma | HTTP (Fetcher) | Browser (Playwright) | Datos Extraídos | Blocker |
|:-----------|:--------------:|:-------------------:|:---------------:|:--------|
| **Rappi** | 200 (SPA vacía, 4 bytes) | Login automatizado (SMS+Email 2FA) | Parcial — 2FA completo | Doble verificación (SMS + email) |
| **Uber Eats** | 200 (SPA vacía, 4 bytes) | Menú completo cargado | **Precios reales extraídos** | Cookie consent (resuelto) |
| **DiDi Food** | 200 (SPA vacía, 4 bytes) | Login automatizado (Vue.js form) | Parcial — rate limited | Login funciona, rate limited temporalmente |

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

**Estrategias intentadas (2026-03-28 — login con credenciales):**
6. Login automatizado con Playwright:
   - URL `/login` → Página muestra opciones: "Continuar con tu celular", Facebook, Apple
   - Click "Continuar con tu celular" → Input de teléfono con selector de país
   - Selector de país: Click en "+52" → Dropdown → Seleccionar "Colombia" → +57 ✅
   - Ingreso de teléfono: [REDACTED] ✅
   - Botones: "Recibir código por SMS" (verde) y "Recibir código por WhatsApp"
   - Click "Recibir código por SMS" → Redirige a `/login/verify`
   - **Verificación paso 1 (SMS)**: 4 inputs tipo OTP, código de 4 dígitos → ✅ Verificado exitosamente
   - **Verificación paso 2 (Email)**: "Confirmación de seguridad — Hemos enviado un código de 6 dígitos al correo ********ai@outlook.com"
   - Rappi usa **doble factor de autenticación** (SMS + Email) para login desde dispositivo nuevo
   - El flujo funciona técnicamente, pero la sincronización de ambos códigos en tiempo real requiere interacción manual rápida

**Hallazgos clave:**
- Rappi usa `services.mxgrability.rappi.com` como backend de APIs
- La API `/api/pns-global-search-api/v1/unified-search` responde (405 = necesita POST, no GET)
- La API de passport/guest genera tokens temporales: `services.mxgrability.rappi.com/api/rocket/v2/guest/passport/`
- Login requiere **2FA completo**: SMS (4 dígitos) + Email (6 dígitos)
- El selector de país funciona correctamente (México → Colombia)
- Playwright puede automatizar todo el flujo excepto la lectura de los códigos OTP
- **Blocker**: Los códigos OTP expiran rápidamente y la doble verificación requiere sincronización manual
- **Solución potencial**: Usar API de email (IMAP/Graph API) para leer códigos automáticamente, o persistir cookies post-login

**Evidencia:** `data/raw/screenshot_rappi.png`, `screenshot_rappi_mcdonalds.png`, `screenshot_rappi_after_address.png`, `screenshot_rappi_v2_phone.png` (formulario con Colombia +57), `screenshot_rappi_v2_after_sms.png` (página de verificación SMS), `screenshot_rappi_direct_after_sms.png` (después de SMS code exitoso, muestra verificación email)

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

**Estrategias intentadas (2026-03-28 — login con credenciales):**
4. Login automatizado con Playwright:
   - URL con `country_id=170` → Colombia (+57) seleccionado correctamente
   - Tab "Ingresar con contraseña" → Activo
   - Phone: [REDACTED], Password: [REDACTED]
   - Checkbox "Acepto Términos": Clickeado correctamente
   - **Vue.js state confirmado**: `cellValid: true`, `passwordValid: true`, `agreementValid: true`
   - Login page usa Vue.js con componentes: formulario en `<DIV>` con `formData.cell`, `formData.country`
   - El botón "Iniciar sesión" es un `<DIV class="button actived">`, NO un `<button>` HTML
   - **Rate limited**: Después de múltiples intentos con país incorrecto (México +52), DiDi bloqueó temporalmente: "Demasiados intentos de inicio de sesión. Inténtalo de nuevo más tarde"

**Hallazgo:** DiDi Food opera activamente en México (30M+ usuarios, 52K+ restaurantes, 60+ ciudades). Requiere cuenta para acceder al feed de restaurantes y precios. El login automatizado funciona técnicamente — la forma se llena correctamente y Vue valida los campos — pero el rate limiting bloqueó el intento final.

**Blocker actual:** Rate limiting temporal. La automatización del login está lista para reintentar después del período de cooldown.

**Evidencia:** `data/raw/screenshot_didifood.png` (landing), `screenshot_didifood_feed.png` (login redirect), `screenshot_didifood_v7_ready.png` (formulario llenado), `screenshot_didifood_v7_final.png` (rate limit error)

---

## Hallazgos Técnicos

1. **Las 3 plataformas son SPAs** — HTTP simple retorna body vacío (4 bytes "None"). Se requiere browser rendering.
2. **Scrapling's Fetcher** funciona para requests HTTP pero no puede renderizar SPAs. StealthyFetcher (Camoufox) requiere instalación correcta del browser.
3. **Playwright Chromium** fue la herramienta más efectiva para las 3 plataformas.
4. **Uber Eats** fue la plataforma más accesible — menú completo con precios extraíbles después de aceptar cookies e ingresar dirección.
5. **Rappi** usa doble verificación (SMS + Email) para login desde dispositivos nuevos. El flujo automatizado funciona pero requiere sincronización manual de códigos OTP.
6. **DiDi Food** está activa en México (dominio correcto: `didi-food.com`). Login con Vue.js automatizado, form validation pasa, rate limited después de múltiples intentos.
7. **2 de 3 plataformas requieren autenticación** — solo Uber Eats permite acceso anónimo completo al menú.
8. **Rate limiting** es un riesgo real — DiDi Food bloqueó después de ~5 intentos. Rappi permite más intentos pero los códigos OTP expiran rápido (~60s).
9. **Estrategia recomendada para producción**: Persistir cookies/tokens post-login exitoso (`storage_state`) para reutilizar sesiones sin re-autenticar. Implementar lectura automática de OTP via IMAP/API para el email code.

## Archivos de Evidencia

```
data/raw/
├── screenshot_rappi.png                        # Landing page
├── screenshot_rappi_mcdonalds.png              # Store listing McDonald's
├── screenshot_rappi_after_address.png          # Redirect a login
├── screenshot_rappi_v2_phone.png               # Login: Colombia +57, teléfono ingresado
├── screenshot_rappi_v2_after_sms.png           # Verificación SMS enviado
├── screenshot_rappi_direct_after_sms.png       # SMS verificado, pide email code
├── screenshot_ubereats_step1.png               # Feed con dirección Polanco
├── screenshot_ubereats_mcdonalds_menu.png      # Menú completo McDonald's
├── screenshot_didifood_login.png               # Login page DiDi Food
├── screenshot_didifood_v7_ready.png            # Form llenado (Colombia +57, validado)
├── screenshot_didifood_v7_final.png            # Rate limit error
├── ubereats_mcdonalds_menu.html                # HTML menú Uber Eats
├── final_extraction_results.json               # Datos extraídos finales
└── scraping_test_log.txt                       # Log completo
```

```
data/processed/
├── competitive_intel.csv                       # Dataset completo (150 filas)
├── competitive_intel_v2.csv                    # Dataset actualizado
└── competitive_intel_v2.json                   # Dataset JSON
```
