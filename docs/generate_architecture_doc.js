const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
  ShadingType, PageNumber, PageBreak, LevelFormat, ImageRun,
  TableOfContents,
} = require("docx");

// ─── Colors ───
const C = {
  primary: "1B3A5C",
  accent: "FF6B35",
  green: "1A936F",
  bg: "F5F7FA",
  bgCode: "1E1E2E",
  textCode: "CDD6F4",
  border: "D0D5DD",
  headerBg: "1B3A5C",
  headerText: "FFFFFF",
  lightBlue: "D5E8F0",
};

const border = { style: BorderStyle.SINGLE, size: 1, color: C.border };
const borders = { top: border, bottom: border, left: border, right: border };
const cellMargins = { top: 80, bottom: 80, left: 120, right: 120 };

// ─── Helper: code block ───
function codeBlock(code) {
  const lines = code.split("\n");
  return lines.map(
    (line) =>
      new Paragraph({
        spacing: { before: 0, after: 0, line: 260 },
        shading: { fill: C.bgCode, type: ShadingType.CLEAR },
        indent: { left: 360, right: 360 },
        children: [
          new TextRun({
            text: line || " ",
            font: "Consolas",
            size: 17,
            color: C.textCode,
          }),
        ],
      })
  );
}

// ─── Helper: bullet list ───
function bulletItem(text, level = 0) {
  return new Paragraph({
    numbering: { reference: "bullets", level },
    spacing: { before: 40, after: 40 },
    children: [new TextRun({ text, font: "Arial", size: 22 })],
  });
}

// ─── Helper: section header ───
function sectionHeader(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 360, after: 200 },
    children: [new TextRun({ text, bold: true, font: "Arial", size: 32, color: C.primary })],
  });
}

function subHeader(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 280, after: 160 },
    children: [new TextRun({ text, bold: true, font: "Arial", size: 26, color: C.primary })],
  });
}

function subSubHeader(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    spacing: { before: 200, after: 120 },
    children: [new TextRun({ text, bold: true, font: "Arial", size: 23, color: C.accent })],
  });
}

function para(text, opts = {}) {
  return new Paragraph({
    spacing: { before: 80, after: 80 },
    children: [new TextRun({ text, font: "Arial", size: 22, ...opts })],
  });
}

function boldPara(label, text) {
  return new Paragraph({
    spacing: { before: 80, after: 80 },
    children: [
      new TextRun({ text: label, font: "Arial", size: 22, bold: true }),
      new TextRun({ text, font: "Arial", size: 22 }),
    ],
  });
}

// ─── Helper: info table (key-value) ───
function infoTable(rows) {
  const W = 9360;
  const C1 = 2800;
  const C2 = W - C1;
  return new Table({
    width: { size: W, type: WidthType.DXA },
    columnWidths: [C1, C2],
    rows: rows.map(
      ([k, v]) =>
        new TableRow({
          children: [
            new TableCell({
              borders,
              width: { size: C1, type: WidthType.DXA },
              shading: { fill: C.lightBlue, type: ShadingType.CLEAR },
              margins: cellMargins,
              children: [new Paragraph({ children: [new TextRun({ text: k, bold: true, font: "Arial", size: 20 })] })],
            }),
            new TableCell({
              borders,
              width: { size: C2, type: WidthType.DXA },
              margins: cellMargins,
              children: [new Paragraph({ children: [new TextRun({ text: v, font: "Arial", size: 20 })] })],
            }),
          ],
        })
    ),
  });
}

// ─── Helper: multi-col table ───
function dataTable(headers, rows, colWidths) {
  const W = 9360;
  const widths = colWidths || headers.map(() => Math.floor(W / headers.length));
  return new Table({
    width: { size: W, type: WidthType.DXA },
    columnWidths: widths,
    rows: [
      new TableRow({
        children: headers.map(
          (h, i) =>
            new TableCell({
              borders,
              width: { size: widths[i], type: WidthType.DXA },
              shading: { fill: C.headerBg, type: ShadingType.CLEAR },
              margins: cellMargins,
              children: [
                new Paragraph({
                  alignment: AlignmentType.CENTER,
                  children: [new TextRun({ text: h, bold: true, font: "Arial", size: 20, color: C.headerText })],
                }),
              ],
            })
        ),
      }),
      ...rows.map(
        (row, ri) =>
          new TableRow({
            children: row.map(
              (cell, ci) =>
                new TableCell({
                  borders,
                  width: { size: widths[ci], type: WidthType.DXA },
                  shading: { fill: ri % 2 === 0 ? "FFFFFF" : C.bg, type: ShadingType.CLEAR },
                  margins: cellMargins,
                  children: [new Paragraph({ children: [new TextRun({ text: cell, font: "Arial", size: 19 })] })],
                })
            ),
          })
      ),
    ],
  });
}

// ═══════════════════════════════════════════
// DOCUMENT
// ═══════════════════════════════════════════

const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      {
        id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: "Arial", color: C.primary },
        paragraph: { spacing: { before: 360, after: 200 }, outlineLevel: 0 },
      },
      {
        id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, font: "Arial", color: C.primary },
        paragraph: { spacing: { before: 280, after: 160 }, outlineLevel: 1 },
      },
      {
        id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 23, bold: true, font: "Arial", color: C.accent },
        paragraph: { spacing: { before: 200, after: 120 }, outlineLevel: 2 },
      },
    ],
  },
  numbering: {
    config: [
      {
        reference: "bullets",
        levels: [
          { level: 0, format: LevelFormat.BULLET, text: "-", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
          { level: 1, format: LevelFormat.BULLET, text: "-", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 1440, hanging: 360 } } } },
        ],
      },
      {
        reference: "numbers",
        levels: [
          { level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
        ],
      },
    ],
  },
  sections: [
    // ═══ COVER PAGE ═══
    {
      properties: {
        page: {
          size: { width: 12240, height: 15840 },
          margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
        },
      },
      children: [
        new Paragraph({ spacing: { before: 3000 } }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 200 },
          children: [new TextRun({ text: "Rappi Competitive Intelligence", font: "Arial", size: 52, bold: true, color: C.primary })],
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 100 },
          children: [new TextRun({ text: "Arquitectura del Sistema", font: "Arial", size: 36, color: C.accent })],
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 600 },
          border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: C.accent, space: 8 } },
          children: [new TextRun({ text: "De lo general a lo especifico: flujo de datos, modulos y codigo", font: "Arial", size: 24, color: "667085", italics: true })],
        }),
        new Paragraph({ spacing: { before: 400 } }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: "Caso Tecnico - Sistema de Competitive Intelligence", font: "Arial", size: 22, color: "667085" })],
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 200 },
          children: [new TextRun({ text: "Marzo 2026", font: "Arial", size: 22, color: "667085" })],
        }),
        new Paragraph({ spacing: { before: 200 } }),
        infoTable([
          ["Stack", "Python 3.11 + Scrapling + Playwright + Pandas + Plotly"],
          ["Plataformas", "Rappi, Uber Eats, DiDi Food"],
          ["Cobertura", "10 zonas CDMX (premium, media, popular)"],
          ["Productos", "5 items McDonald's como benchmark"],
          ["Output", "CSV normalizado + reporte Markdown + 3 graficos"],
        ]),
      ],
    },
    // ═══ TOC ═══
    {
      properties: {
        page: {
          size: { width: 12240, height: 15840 },
          margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
        },
      },
      headers: {
        default: new Header({
          children: [
            new Paragraph({
              border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: C.primary, space: 4 } },
              children: [new TextRun({ text: "Rappi Competitive Intelligence - Arquitectura del Sistema", font: "Arial", size: 18, color: C.primary, italics: true })],
            }),
          ],
        }),
      },
      footers: {
        default: new Footer({
          children: [
            new Paragraph({
              alignment: AlignmentType.CENTER,
              border: { top: { style: BorderStyle.SINGLE, size: 2, color: C.border, space: 4 } },
              children: [
                new TextRun({ text: "Pagina ", font: "Arial", size: 18, color: "667085" }),
                new TextRun({ children: [PageNumber.CURRENT], font: "Arial", size: 18, color: "667085" }),
              ],
            }),
          ],
        }),
      },
      children: [
        sectionHeader("Tabla de Contenidos"),
        new TableOfContents("Tabla de Contenidos", { hyperlink: true, headingStyleRange: "1-3" }),
        new Paragraph({ children: [new PageBreak()] }),

        // ═══ 1. VISION GENERAL ═══
        sectionHeader("1. Vision General del Sistema"),
        para("El sistema de Competitive Intelligence es un pipeline automatizado que recolecta, normaliza, analiza y reporta precios de delivery de McDonald's en CDMX a traves de 3 plataformas competidoras."),

        subHeader("1.1 Objetivo"),
        para("Responder la pregunta: \"En que zonas de CDMX es Rappi mas caro, mas barato o igual que la competencia, y por que?\""),

        subHeader("1.2 Flujo de Datos (Pipeline)"),
        para("El sistema sigue un flujo lineal de 5 etapas:"),

        dataTable(
          ["Etapa", "Input", "Output", "Modulo"],
          [
            ["1. Configuracion", "Constantes hardcoded", "Addresses, Products", "config.py"],
            ["2. Scraping", "URLs + direcciones", "List[ScrapedItem]", "scrapers/*.py"],
            ["3. Normalizacion", "List[ScrapedItem]", "pd.DataFrame", "pipeline/normalizer.py"],
            ["4. Exportacion", "pd.DataFrame", "CSV + JSON", "pipeline/exporter.py"],
            ["5. Analisis", "pd.DataFrame", "Insights + graficos", "analysis/*.py"],
          ],
          [1800, 1800, 2000, 2760]
        ),

        para(""),
        boldPara("Orquestador: ", "main.py controla todo el flujo. Acepta flags --demo, --scrapers-only, --analysis-only."),

        subHeader("1.3 Estructura de Directorios"),
        ...codeBlock(
`rappi-competitive-intel/
|-- main.py                     # Entry point - orquesta el pipeline
|-- config.py                   # Direcciones, productos, constantes
|-- scrapers/
|   |-- __init__.py
|   |-- base.py                 # BaseScraper (ABC) + ScrapedItem (dataclass)
|   |-- rappi_scraper.py        # Scraper Rappi (API + Playwright)
|   |-- ubereats_scraper.py     # Scraper Uber Eats (Playwright)
|   |-- didifood_scraper.py     # Scraper DiDi Food (deteccion cierre)
|-- pipeline/
|   |-- normalizer.py           # List[ScrapedItem] -> pd.DataFrame
|   |-- exporter.py             # DataFrame -> CSV / JSON
|-- analysis/
|   |-- comparator.py           # Analisis comparativo entre plataformas
|   |-- report_generator.py     # Markdown + graficos Plotly
|-- data/raw/                   # Datos crudos y screenshots
|-- data/processed/             # CSV normalizado final
|-- reports/                    # Reportes e imagenes
|-- requirements.txt
|-- SCRAPING_LOG.md             # Log de intentos de scraping real`
        ),

        new Paragraph({ children: [new PageBreak()] }),

        // ═══ 2. FRAMEWORKS ═══
        sectionHeader("2. Frameworks y Tecnologias"),

        subHeader("2.1 Stack Tecnologico"),
        dataTable(
          ["Tecnologia", "Version", "Proposito"],
          [
            ["Python", "3.11+", "Lenguaje principal del sistema"],
            ["Scrapling", ">=0.3.0", "HTTP requests con stealth headers + parsing HTML"],
            ["Playwright", "Built-in", "Browser automation headless (Chromium)"],
            ["Camoufox", "Via Scrapling", "Firefox stealth anti-deteccion (StealthyFetcher)"],
            ["Pandas", ">=2.0.0", "Normalizacion y analisis tabular de datos"],
            ["Plotly", ">=5.18.0", "Graficos interactivos exportados como PNG"],
            ["Kaleido", ">=0.2.1", "Engine de renderizado para exportar Plotly a imagen"],
          ],
          [2000, 1500, 5860]
        ),

        subHeader("2.2 Por que Scrapling y no Selenium/BeautifulSoup?"),
        bulletItem("Scrapling combina HTTP client (Fetcher) y browser stealth (StealthyFetcher) en una sola libreria"),
        bulletItem("Fetcher genera headers realistas automaticamente (user-agent rotation, TLS fingerprint)"),
        bulletItem("StealthyFetcher usa Camoufox (Firefox anti-deteccion) para evadir Cloudflare"),
        bulletItem("API de selectors compatible con CSS (page.css('.price::text'))"),
        para(""),
        boldPara("Hallazgo real: ", "En la practica, Playwright Chromium resulto mas confiable que StealthyFetcher para estas plataformas especificas, por lo que se usa como metodo principal."),

        new Paragraph({ children: [new PageBreak()] }),

        // ═══ 3. CONFIG.PY ═══
        sectionHeader("3. Modulo: config.py"),
        para("Define todas las constantes del sistema: direcciones de entrega, productos objetivo y parametros de scraping. Usa dataclasses inmutables (frozen=True) para garantizar integridad."),

        subHeader("3.1 Dataclass Address"),
        para("Representa una ubicacion de entrega en CDMX con clasificacion socioeconomica:"),
        ...codeBlock(
`@dataclass(frozen=True)
class Address:
    id: str           # Identificador unico (ej: "polanco")
    name: str         # Nombre legible (ej: "Polanco")
    zone_type: str    # "premium", "media", "popular"
    lat: float        # Latitud para geolocalizacion
    lon: float        # Longitud para geolocalizacion
    street: str       # Direccion completa para input en plataformas`
        ),

        para("Se definen 10 direcciones representativas agrupadas en 3 tipos de zona:"),
        dataTable(
          ["Zona", "Tipo", "Lat", "Lon"],
          [
            ["Polanco", "premium", "19.4326", "-99.1942"],
            ["Condesa", "premium", "19.4111", "-99.1734"],
            ["Roma Norte", "premium", "19.4195", "-99.1617"],
            ["Del Valle", "media", "19.3856", "-99.1632"],
            ["Coyoacan", "media", "19.3467", "-99.1617"],
            ["Santa Fe", "media", "19.3659", "-99.2614"],
            ["Tlalpan", "media", "19.2870", "-99.1680"],
            ["Iztapalapa", "popular", "19.3558", "-99.0742"],
            ["Naucalpan", "popular", "19.4784", "-99.2398"],
            ["Ecatepec", "popular", "19.6014", "-99.0530"],
          ],
          [2500, 1800, 2530, 2530]
        ),

        subHeader("3.2 Dataclass Product"),
        para("Cada producto tiene un ID unico y keywords para buscarlo en distintas plataformas:"),
        ...codeBlock(
`@dataclass(frozen=True)
class Product:
    id: str              # "big_mac", "combo_mediano", etc.
    name: str            # Nombre display
    keywords: list[str]  # Terminos de busqueda alternativos`
        ),

        subHeader("3.3 Constantes de Scraping"),
        ...codeBlock(
`SCRAPING_CONFIG = {
    "rate_limit_seconds": 3,    # Pausa entre requests
    "max_retries": 3,           # Reintentos por request
    "timeout_seconds": 30,      # Timeout por request
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)..."
}`
        ),
        boldPara("Etica: ", "Rate limiting de 3 segundos, User-Agent transparente, sin saturacion de servidores. Solo para fines de reclutamiento."),

        new Paragraph({ children: [new PageBreak()] }),

        // ═══ 4. SCRAPERS ═══
        sectionHeader("4. Modulo: scrapers/"),

        subHeader("4.1 base.py - ScrapedItem y BaseScraper"),
        para("Define el contrato que todos los scrapers deben cumplir y la estructura de datos de salida."),

        subSubHeader("ScrapedItem (dataclass)"),
        para("Cada item scraped contiene 16 campos que capturan precio, fees, tiempo y metadata:"),
        ...codeBlock(
`@dataclass
class ScrapedItem:
    platform: str              # "rappi", "ubereats", "didifood"
    address_id: str            # ID de la zona
    address_name: str          # Nombre de la zona
    address_type: str          # premium / media / popular
    product_id: str            # ID del producto
    product_name: str          # Nombre del producto
    restaurant: str = "McDonald's"
    product_price: float | None = None
    delivery_fee: float | None = None
    service_fee: float | None = None
    total_price: float | None = None
    delivery_time_min: int | None = None
    delivery_time_max: int | None = None
    discount_text: str | None = None
    available: bool = True
    scrape_timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )`
        ),
        para("El metodo to_dict() convierte el item a diccionario para facilitar la conversion a DataFrame."),

        subSubHeader("BaseScraper (ABC)"),
        para("Clase abstracta con 3 metodos clave:"),
        dataTable(
          ["Metodo", "Tipo", "Descripcion"],
          [
            ["set_location(address)", "Abstracto", "Configura la direccion de entrega en la plataforma"],
            ["scrape_product(address, product)", "Abstracto", "Obtiene datos de 1 producto en 1 direccion"],
            ["scrape_all(addresses, products)", "Concreto", "Itera todas las combinaciones address x product"],
          ],
          [3000, 1500, 4860]
        ),

        para(""),
        boldPara("Rate Limiting: ", "_rate_limit_wait() mide el tiempo transcurrido desde el ultimo request y espera si es menor a 3 segundos."),
        ...codeBlock(
`def _rate_limit_wait(self) -> None:
    elapsed = time.time() - self._last_request_time
    if elapsed < self.rate_limit:
        wait = self.rate_limit - elapsed
        time.sleep(wait)
    self._last_request_time = time.time()`
        ),

        boldPara("Retry con Backoff: ", "_retry() ejecuta una funcion hasta 3 veces con backoff multiplicativo:"),
        ...codeBlock(
`def _retry(self, func, *args, **kwargs):
    for attempt in range(1, self.max_retries + 1):
        try:
            self._rate_limit_wait()
            return func(*args, **kwargs)
        except Exception as e:
            if attempt == self.max_retries:
                return None
            time.sleep(self.rate_limit * attempt)  # backoff`
        ),

        new Paragraph({ children: [new PageBreak()] }),

        subHeader("4.2 rappi_scraper.py"),
        para("Scraper para Rappi Mexico con 2 estrategias de extraccion."),

        subSubHeader("Hallazgos del scraping real"),
        bulletItem("HTTP Fetcher retorna SPA vacia (4 bytes) - Rappi es 100% client-side rendering"),
        bulletItem("APIs internas (/api/web-gateway/...) retornan 403 sin token de autenticacion"),
        bulletItem("API de guest token descubierta: services.mxgrability.rappi.com/api/rocket/v2/guest/passport/"),
        bulletItem("BLOCKER: Rappi requiere login/signup para ver menu con precios"),

        subSubHeader("Estrategia 1: API con Guest Token"),
        ...codeBlock(
`def _obtain_guest_token(self) -> str | None:
    response = Fetcher.get(
        "https://services.mxgrability.rappi.com/api/rocket/v2/guest/passport/",
        stealthy_headers=True,
        timeout=15,
    )
    if response and response.status == 200:
        data = json.loads(response.text)
        token = data.get("token") or data.get("access_token")
        self._guest_token = token
        return token`
        ),

        subSubHeader("Estrategia 2: Playwright Chromium"),
        ...codeBlock(
`def _try_playwright_scrape(self, address, product):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            locale="es-MX",
            geolocation={"latitude": address.lat, "longitude": address.lon},
        )
        page = context.new_page()
        page.goto("https://www.rappi.com.mx" + MCDONALDS_STORE_PATH)

        # Ingresar direccion manualmente
        addr_input = page.query_selector("input[placeholder*='quieres']")
        addr_input.fill(address.street)

        # Detectar redirect a login
        if "/login" in page.url:
            self._login_required = True
            return None  # Rappi requiere cuenta`
        ),

        boldPara("Deteccion de login: ", "Si Rappi redirige a /login/signup, el scraper marca _login_required = True y salta los demas intentos para esa sesion, evitando requests innecesarios."),

        new Paragraph({ children: [new PageBreak()] }),

        subHeader("4.3 ubereats_scraper.py"),
        para("Scraper para Uber Eats Mexico - la plataforma donde se logro la extraccion mas completa."),

        subSubHeader("Hallazgos del scraping real"),
        bulletItem("HTTP retorna SPA vacia (4 bytes) al igual que Rappi"),
        bulletItem("Playwright con cookie handling funciona perfectamente"),
        bulletItem("Se descubrio store URL: /mx/store/mcdonalds-polanco/GMcH3w_vX4CtLxBPRICeWA"),
        bulletItem("EXITO: Menu completo con 155 precios reales extraidos"),

        subSubHeader("Flujo del scraper"),
        para("El scraper ejecuta 4 pasos secuenciales:"),
        ...codeBlock(
`# Paso 1: Landing + aceptar cookies
page.goto("https://www.ubereats.com/mx")
accept = page.query_selector("button:has-text('Aceptar')")
accept.click()

# Paso 2: Ingresar direccion
addr_input.fill(address.street)
suggestion = page.wait_for_selector("li[role='option']")
suggestion.click()

# Paso 3: Buscar McDonald's
page.goto(search_url)
store_links = page.query_selector_all("a[href*='mcdonalds']")

# Paso 4: Navegar al store y extraer precios
page.goto(store_url)
body_text = page.inner_text("body")`
        ),

        subSubHeader("Extraccion de precios"),
        para("Los precios se extraen con regex del texto renderizado, usando contexto de lineas adyacentes:"),
        ...codeBlock(
`def _extract_product_from_text(self, text, address, product):
    lines = text.split("\\n")
    for i, line in enumerate(lines):
        if product.id == "big_mac" and "big mac" in line.lower():
            # Buscar precio en contexto cercano (+/- 2 lineas)
            context = " ".join(lines[max(0,i-1):i+3])
            prices = re.findall(r"\\$\\s*(\\d{1,4}(?:\\.\\d{2})?)", context)
            if prices:
                return ScrapedItem(
                    product_price=float(prices[0]),
                    ...
                )`
        ),

        subSubHeader("Precios reales extraidos (McDonald's Polanco, Uber Eats)"),
        dataTable(
          ["Producto", "Precio Individual", "Precio McTrio"],
          [
            ["Big Mac", "$145.00", "$169.00"],
            ["Big Mac Tocino", "$165.00", "$189.00"],
            ["McNuggets 10 pzas", "$155.00", "$179.00"],
            ["McNuggets 20 pzas", "$209.00", "$229.00"],
            ["Coca-Cola mediana", "$65.00", "-"],
            ["Agua Ciel 600ml", "$39.00", "-"],
          ],
          [3500, 2930, 2930]
        ),

        new Paragraph({ children: [new PageBreak()] }),

        subHeader("4.4 didifood_scraper.py"),
        para("Scraper para DiDi Food con deteccion automatica de plataforma cerrada."),

        subSubHeader("Hallazgo critico"),
        boldPara("DiDi Food cerro operaciones en Mexico en 2023. ", "El dominio didifood.com redirige a forsale.dynadot.com (pagina de venta de dominios)."),

        subSubHeader("Deteccion automatica"),
        ...codeBlock(
`def _check_platform_status(self) -> bool:
    response = Fetcher.get(DIDI_CONFIG["base_url"], ...)
    final_url = str(response.url)

    # Detectar dominio en venta
    if any(x in final_url.lower() for x in [
        "forsale", "dynadot", "sedo", "afternic"
    ]):
        self._platform_available = False
        return False`
        ),
        para("El scraper esta implementado con la arquitectura correcta como ejercicio de diseno, pero falla gracefully al detectar que la plataforma no esta operativa."),

        new Paragraph({ children: [new PageBreak()] }),

        // ═══ 5. PIPELINE ═══
        sectionHeader("5. Modulo: pipeline/"),

        subHeader("5.1 normalizer.py"),
        para("Convierte la lista de ScrapedItems a un DataFrame de Pandas con columnas calculadas."),

        subSubHeader("Transformaciones"),
        ...codeBlock(
`def normalize(items: list[ScrapedItem]) -> pd.DataFrame:
    records = [item.to_dict() for item in items]
    df = pd.DataFrame(records)

    # Calcular total_price donde no exista
    mask = df["total_price"].isna()
    df.loc[mask, "total_price"] = (
        df.loc[mask, "product_price"].fillna(0)
        + df.loc[mask, "delivery_fee"].fillna(0)
        + df.loc[mask, "service_fee"].fillna(0)
    )

    # Calcular delivery_time_avg
    df["delivery_time_avg"] = (
        df[["delivery_time_min", "delivery_time_max"]]
        .mean(axis=1).round(1)
    )`
        ),

        subSubHeader("Columnas del DataFrame final (17 columnas)"),
        dataTable(
          ["Columna", "Tipo", "Descripcion"],
          [
            ["platform", "str", "Nombre de la plataforma"],
            ["address_id", "str", "ID de la zona"],
            ["address_name", "str", "Nombre legible de la zona"],
            ["address_type", "str", "premium / media / popular"],
            ["product_id", "str", "ID del producto"],
            ["product_name", "str", "Nombre del producto"],
            ["restaurant", "str", "Nombre del restaurante"],
            ["product_price", "float", "Precio del producto (MXN)"],
            ["delivery_fee", "float", "Costo de envio"],
            ["service_fee", "float", "Fee de servicio de la plataforma"],
            ["total_price", "float", "Calculado: product + delivery + service"],
            ["delivery_time_min", "int", "Tiempo minimo de entrega (min)"],
            ["delivery_time_max", "int", "Tiempo maximo de entrega (min)"],
            ["delivery_time_avg", "float", "Calculado: promedio min/max"],
            ["discount_text", "str", "Texto de promocion (si aplica)"],
            ["available", "bool", "Producto disponible en esa zona"],
            ["scrape_timestamp", "str", "Fecha/hora UTC del scraping"],
          ],
          [2800, 1200, 5360]
        ),

        subHeader("5.2 exporter.py"),
        para("Exporta el DataFrame normalizado a dos formatos:"),
        ...codeBlock(
`def to_csv(df, filename="competitive_intel.csv",
           output_dir=Path("data/processed")) -> Path:
    df.to_csv(filepath, index=False, encoding="utf-8-sig")

def to_json(df, filename="competitive_intel.json",
            output_dir=Path("data/processed")) -> Path:
    df.to_json(filepath, orient="records",
               force_ascii=False, indent=2)`
        ),
        boldPara("Nota: ", "Se usa utf-8-sig en CSV para compatibilidad con Excel en espanol (BOM header)."),

        new Paragraph({ children: [new PageBreak()] }),

        // ═══ 6. ANALYSIS ═══
        sectionHeader("6. Modulo: analysis/"),

        subHeader("6.1 comparator.py"),
        para("Genera 5 analisis comparativos usando agrupaciones de Pandas:"),

        dataTable(
          ["Analisis", "GroupBy", "Metricas"],
          [
            ["platform_summary", "platform", "avg price, fees, delivery time, count"],
            ["zone_comparison", "address_type, address_name, platform", "avg product price, total price, delivery fee"],
            ["product_comparison", "product_name, platform", "avg, min, max price, zones available"],
            ["fee_analysis", "platform, address_type", "avg delivery fee, service fee, total fees"],
            ["availability", "platform, address_name", "total, available, availability rate"],
          ],
          [2500, 3500, 3360]
        ),

        subSubHeader("Ejemplo: platform_summary"),
        ...codeBlock(
`def _platform_summary(df):
    return df.groupby("platform").agg(
        avg_product_price=("product_price", "mean"),
        avg_delivery_fee=("delivery_fee", "mean"),
        avg_service_fee=("service_fee", "mean"),
        avg_total_price=("total_price", "mean"),
        avg_delivery_time=("delivery_time_avg", "mean"),
        product_count=("product_id", "count"),
    ).round(2).reset_index()`
        ),

        subHeader("6.2 report_generator.py"),
        para("Genera el reporte final con 3 componentes:"),

        subSubHeader("3 Graficos Plotly"),
        dataTable(
          ["Grafico", "Tipo", "Funcion Plotly"],
          [
            ["Desglose de costos por plataforma", "Barras apiladas", "px.bar(barmode='stack')"],
            ["Heatmap precios por zona", "Mapa de calor", "px.imshow(color_continuous_scale='RdYlGn_r')"],
            ["Fees de envio por tipo de zona", "Barras agrupadas", "px.bar(barmode='group')"],
          ],
          [3200, 2000, 4160]
        ),

        subSubHeader("5 Insights (Finding / Impact / Recommendation)"),
        para("Cada insight se genera automaticamente a partir de los datos:"),
        ...codeBlock(
`# Insight 1: Plataforma mas economica
cheapest = platform_summary.loc[
    platform_summary["avg_total_price"].idxmin()
]
diff_pct = (most_expensive - cheapest) / cheapest * 100
# -> "ubereats es 12.3% mas barata que rappi"

# Insight 2: Peso de fees sobre precio total
fee_share = (delivery_fee + service_fee) / total_price * 100
# -> "En rappi, los fees representan ~25% del costo total"

# Insight 3: Variacion por zona socioeconomica
# Insight 4: Tiempos de entrega como diferenciador
# Insight 5: Cobertura geografica`
        ),

        new Paragraph({ children: [new PageBreak()] }),

        // ═══ 7. MAIN.PY ═══
        sectionHeader("7. Orquestador: main.py"),
        para("Entry point del sistema. Coordina el flujo completo con 4 modos de ejecucion:"),

        dataTable(
          ["Comando", "Descripcion"],
          [
            ["python main.py", "Pipeline completo: scraping + normalizacion + analisis"],
            ["python main.py --demo", "Datos demo calibrados + analisis (sin scraping real)"],
            ["python main.py --scrapers-only", "Solo ejecutar scrapers, exportar datos crudos"],
            ["python main.py --analysis-only", "Solo analisis sobre datos existentes (CSV)"],
          ],
          [3500, 5860]
        ),

        subHeader("7.1 Generacion de datos demo"),
        para("Cuando el scraping real falla (bloqueos, login required), el sistema genera datos demo calibrados con precios reales:"),
        ...codeBlock(
`# Precios calibrados con datos REALES de Uber Eats (2026-03-27):
# Big Mac: $145, McTrio Big Mac: $169, McNuggets 10: $155,
# Coca-Cola mediana: $65, Agua Ciel 600ml: $39
base_prices = {
    "big_mac": (139, 149),
    "combo_mediano": (165, 179),
    "nuggets_10": (149, 159),
    "coca_600": (59, 69),
    "agua_1l": (35, 45),
}

# Factores por plataforma
platform_factors = {
    "rappi":    {"price_mult": 1.05, "delivery_base": (29, 49)},
    "ubereats": {"price_mult": 1.0,  "delivery_base": (0, 29)},
    "didifood": {"price_mult": 0.95, "delivery_base": (15, 35)},
}`
        ),

        subHeader("7.2 Fallback automatico"),
        ...codeBlock(
`# Si scraping real no obtiene datos -> fallback a demo
items = run_scrapers()
available = sum(1 for i in items if i.available)
if available == 0:
    logger.warning("No se obtuvieron datos reales. Modo demo...")
    items = generate_demo_data()`
        ),

        new Paragraph({ children: [new PageBreak()] }),

        // ═══ 8. SCRAPING REAL ═══
        sectionHeader("8. Resultados del Scraping Real"),
        para("Se ejecutaron pruebas reales contra las 3 plataformas el 2026-03-27 desde Polanco, CDMX."),

        subHeader("8.1 Resumen de resultados"),
        dataTable(
          ["Plataforma", "HTTP", "Browser", "Datos", "Blocker"],
          [
            ["Rappi", "200 (SPA vacia)", "Carga OK", "Parcial", "Login obligatorio"],
            ["Uber Eats", "200 (SPA vacia)", "Menu completo", "155 precios", "Cookie consent (resuelto)"],
            ["DiDi Food", "302 redirect", "N/A", "Ninguno", "Dominio en venta"],
          ],
          [1500, 1700, 1700, 1500, 2960]
        ),

        subHeader("8.2 Evidencia visual"),
        para("Se capturaron screenshots en cada paso del scraping como evidencia documental:"),
        bulletItem("screenshot_rappi.png - Landing page con 'Los 10 mas elegidos'"),
        bulletItem("screenshot_rappi_mcdonalds.png - Pagina de McDonald's pidiendo direccion"),
        bulletItem("screenshot_ubereats_step1.png - Feed de restaurantes en Polanco"),
        bulletItem("screenshot_ubereats_mcdonalds_menu.png - Menu completo con precios"),

        subHeader("8.3 Hallazgos tecnicos"),
        bulletItem("Ambas plataformas activas son SPAs puras - HTTP simple retorna 4 bytes"),
        bulletItem("Scrapling Fetcher funciona para requests pero no renderiza JavaScript"),
        bulletItem("Playwright Chromium fue la herramienta mas efectiva"),
        bulletItem("Uber Eats fue la plataforma mas accesible (menu completo sin login)"),
        bulletItem("Rappi es mas restrictiva (requiere cuenta para ver precios)"),
        bulletItem("DiDi Food no existe en Mexico desde 2023"),

        new Paragraph({ children: [new PageBreak()] }),

        // ═══ 9. COMO CORRER ═══
        sectionHeader("9. Como ejecutar el sistema"),

        subHeader("9.1 Instalacion"),
        ...codeBlock(
`# 1. Clonar repositorio
git clone https://github.com/PedroMartk9i/Rappi_Test_Case_1.git
cd Rappi_Test_Case_1

# 2. Instalar dependencias Python
pip install -r requirements.txt

# 3. Instalar browser para Playwright
python -m playwright install chromium

# 4. (Opcional) Instalar Camoufox para StealthyFetcher
scrapling install`
        ),

        subHeader("9.2 Ejecucion"),
        ...codeBlock(
`# Modo demo (recomendado para primera ejecucion)
python main.py --demo

# Scraping real (puede tomar varios minutos)
python main.py

# Solo analisis sobre datos existentes
python main.py --analysis-only`
        ),

        subHeader("9.3 Outputs generados"),
        dataTable(
          ["Archivo", "Ubicacion", "Descripcion"],
          [
            ["competitive_intel.csv", "data/processed/", "Dataset normalizado con 150 filas"],
            ["competitive_intel.json", "data/processed/", "Mismo dataset en formato JSON"],
            ["competitive_report_*.md", "reports/", "Reporte Markdown con 5 insights"],
            ["chart_cost_breakdown_*.png", "reports/", "Barras apiladas de costos"],
            ["chart_zone_heatmap_*.png", "reports/", "Heatmap de precios por zona"],
            ["chart_fees_by_zone_*.png", "reports/", "Fees de envio por tipo de zona"],
          ],
          [3200, 2200, 3960]
        ),
      ],
    },
  ],
});

// ─── Generate ───
const outPath = process.argv[2] || "docs/Arquitectura_Sistema_Rappi_CI.docx";
Packer.toBuffer(doc).then((buffer) => {
  fs.mkdirSync("docs", { recursive: true });
  fs.writeFileSync(outPath, buffer);
  console.log(`Document generated: ${outPath}`);
});
