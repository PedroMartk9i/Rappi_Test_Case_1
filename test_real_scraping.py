"""
Script de prueba de scraping real contra las 3 plataformas.

Ejecuta intentos reales con Fetcher (HTTP) y StealthyFetcher (browser)
para cada plataforma y documenta resultados, bloqueos y hallazgos.

Uso: python test_real_scraping.py
"""

import json
import logging
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("data/raw/scraping_test_log.txt", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# Coordenadas de prueba: Polanco, CDMX
TEST_LAT = 19.4326
TEST_LON = -99.1942
TEST_ADDRESS = "Av. Presidente Masaryk 360, Polanco, CDMX"

RESULTS_DIR = Path("data/raw")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

results = {
    "test_timestamp": datetime.now(timezone.utc).isoformat(),
    "test_location": {"lat": TEST_LAT, "lon": TEST_LON, "address": TEST_ADDRESS},
    "platforms": {},
}


def save_page_sample(name: str, content: str, max_chars: int = 5000):
    """Guardar muestra del contenido para análisis."""
    filepath = RESULTS_DIR / f"sample_{name}.txt"
    filepath.write_text(content[:max_chars], encoding="utf-8")
    logger.info(f"  Muestra guardada: {filepath} ({min(len(content), max_chars)} chars)")


# ═══════════════════════════════════════════════════════════
# TEST 1: RAPPI
# ═══════════════════════════════════════════════════════════
def test_rappi():
    logger.info("=" * 60)
    logger.info("TEST: RAPPI")
    logger.info("=" * 60)

    platform_results = {
        "fetcher_attempts": [],
        "stealthy_attempts": [],
        "findings": [],
        "data_extracted": [],
    }

    # --- Intento 1: Fetcher HTTP directo a la web ---
    logger.info("\n[Rappi] Intento 1: Fetcher HTTP - página principal McDonald's")
    try:
        from scrapling.fetchers import Fetcher

        url = f"https://www.rappi.com.mx/restaurantes/mcdonalds?lat={TEST_LAT}&lng={TEST_LON}"
        logger.info(f"  URL: {url}")

        response = Fetcher.get(url, stealthy_headers=True, follow_redirects=True, timeout=30)
        status = response.status if response else "No response"
        content_len = len(response.text) if response and response.text else 0

        logger.info(f"  Status: {status}")
        logger.info(f"  Content length: {content_len}")

        result = {"method": "Fetcher.get", "url": url, "status": status, "content_length": content_len}

        if response and response.text:
            save_page_sample("rappi_fetcher", response.text)

            # Analizar contenido
            text = response.text.lower()
            if "mcdonald" in text:
                logger.info("  ✓ Contiene referencia a McDonald's")
                result["contains_mcdonalds"] = True
            else:
                logger.info("  ✗ No contiene referencia a McDonald's (probablemente SPA)")
                result["contains_mcdonalds"] = False

            if any(w in text for w in ["captcha", "challenge", "blocked", "access denied"]):
                logger.info("  ⚠ Posible bloqueo/captcha detectado")
                result["blocked"] = True
            else:
                result["blocked"] = False

            # Buscar JSON embebido (Next.js / React)
            if "__NEXT_DATA__" in response.text:
                logger.info("  ✓ Encontrado __NEXT_DATA__ (Next.js SSR)")
                result["has_next_data"] = True
            if "window.__INITIAL_STATE__" in response.text or "window.__APP_STATE__" in response.text:
                logger.info("  ✓ Encontrado estado inicial de la app")
                result["has_app_state"] = True

        platform_results["fetcher_attempts"].append(result)

    except Exception as e:
        logger.error(f"  Error: {e}")
        platform_results["fetcher_attempts"].append({"method": "Fetcher.get", "error": str(e)})

    time.sleep(3)

    # --- Intento 2: Fetcher HTTP a posibles APIs internas ---
    logger.info("\n[Rappi] Intento 2: Fetcher HTTP - APIs internas")
    api_urls = [
        f"https://www.rappi.com.mx/api/web-gateway/web/stores-router/search?lat={TEST_LAT}&lng={TEST_LON}&query=mcdonalds",
        f"https://services.rappi.com.mx/api/web-gateway/web/stores-router/search?lat={TEST_LAT}&lng={TEST_LON}&query=mcdonalds",
        f"https://www.rappi.com.mx/api/restaurants/search?lat={TEST_LAT}&lng={TEST_LON}&term=mcdonalds",
    ]

    for api_url in api_urls:
        try:
            logger.info(f"  URL: {api_url}")
            from scrapling.fetchers import Fetcher

            response = Fetcher.get(api_url, stealthy_headers=True, follow_redirects=True, timeout=30)
            status = response.status if response else "No response"
            logger.info(f"  Status: {status}")

            result = {"method": "Fetcher.get (API)", "url": api_url, "status": status}

            if response and response.text:
                content = response.text[:500]
                logger.info(f"  Preview: {content[:200]}")
                result["content_preview"] = content[:200]

                # ¿Es JSON?
                try:
                    data = json.loads(response.text)
                    logger.info("  ✓ Respuesta es JSON válido")
                    result["is_json"] = True
                    result["json_keys"] = list(data.keys()) if isinstance(data, dict) else "array"
                    save_page_sample(f"rappi_api_{api_urls.index(api_url)}", json.dumps(data, indent=2, ensure_ascii=False))
                except json.JSONDecodeError:
                    result["is_json"] = False

            platform_results["fetcher_attempts"].append(result)
            time.sleep(3)

        except Exception as e:
            logger.error(f"  Error: {e}")
            platform_results["fetcher_attempts"].append({"method": "Fetcher.get (API)", "url": api_url, "error": str(e)})
            time.sleep(3)

    # --- Intento 3: StealthyFetcher (browser headless) ---
    logger.info("\n[Rappi] Intento 3: StealthyFetcher (browser stealth)")
    try:
        from scrapling.fetchers import StealthyFetcher

        url = f"https://www.rappi.com.mx/restaurantes/mcdonalds?lat={TEST_LAT}&lng={TEST_LON}"
        logger.info(f"  URL: {url}")
        logger.info("  Lanzando browser stealth (puede tardar 15-30s)...")

        page = StealthyFetcher.fetch(url, headless=True, network_idle=True, timeout=45000)

        result = {"method": "StealthyFetcher.fetch", "url": url}

        if page:
            page_text = page.text if hasattr(page, 'text') else str(page)
            content_len = len(page_text) if page_text else 0
            logger.info(f"  Content length: {content_len}")
            result["content_length"] = content_len

            if page_text:
                save_page_sample("rappi_stealthy", page_text)

            # Buscar elementos de precio
            try:
                prices = page.css("[class*='price'], [class*='Price'], [data-qa*='price']")
                logger.info(f"  Elementos de precio encontrados: {len(prices)}")
                result["price_elements"] = len(prices)

                for i, p in enumerate(prices[:5]):
                    p_text = p.text if hasattr(p, 'text') else str(p)
                    logger.info(f"    Precio {i}: {p_text}")
                    if "data_extracted" not in result:
                        result["data_extracted"] = []
                    result["data_extracted"] = result.get("data_extracted", [])
                    result["data_extracted"].append({"element": i, "text": p_text})
            except Exception as e:
                logger.debug(f"  Error buscando precios: {e}")

            # Buscar productos
            try:
                products = page.css("[class*='product'], [class*='Product'], [data-qa*='product']")
                logger.info(f"  Elementos de producto encontrados: {len(products)}")
                result["product_elements"] = len(products)

                for i, p in enumerate(products[:5]):
                    p_text = p.text[:200] if hasattr(p, 'text') and p.text else str(p)[:200]
                    logger.info(f"    Producto {i}: {p_text}")
            except Exception as e:
                logger.debug(f"  Error buscando productos: {e}")

            result["success"] = True
        else:
            logger.warning("  ✗ StealthyFetcher retornó None")
            result["success"] = False

        platform_results["stealthy_attempts"].append(result)

    except Exception as e:
        logger.error(f"  Error: {e}")
        logger.error(f"  Traceback: {traceback.format_exc()}")
        platform_results["stealthy_attempts"].append({"method": "StealthyFetcher.fetch", "error": str(e)})

    results["platforms"]["rappi"] = platform_results
    return platform_results


# ═══════════════════════════════════════════════════════════
# TEST 2: UBER EATS
# ═══════════════════════════════════════════════════════════
def test_ubereats():
    logger.info("\n" + "=" * 60)
    logger.info("TEST: UBER EATS")
    logger.info("=" * 60)

    platform_results = {
        "fetcher_attempts": [],
        "stealthy_attempts": [],
        "findings": [],
        "data_extracted": [],
    }

    # --- Intento 1: Fetcher HTTP ---
    logger.info("\n[UberEats] Intento 1: Fetcher HTTP - búsqueda")
    try:
        from scrapling.fetchers import Fetcher

        url = f"https://www.ubereats.com/mx/search?q=McDonald%27s&pl={TEST_LAT}%2C{TEST_LON}"
        logger.info(f"  URL: {url}")

        response = Fetcher.get(url, stealthy_headers=True, follow_redirects=True, timeout=30)
        status = response.status if response else "No response"
        content_len = len(response.text) if response and response.text else 0

        logger.info(f"  Status: {status}")
        logger.info(f"  Content length: {content_len}")

        result = {"method": "Fetcher.get", "url": url, "status": status, "content_length": content_len}

        if response and response.text:
            save_page_sample("ubereats_fetcher", response.text)
            text = response.text.lower()

            if any(w in text for w in ["captcha", "challenge", "blocked", "access denied", "cloudflare"]):
                logger.info("  ⚠ Posible bloqueo Cloudflare/captcha")
                result["blocked"] = True
            else:
                result["blocked"] = False

            if "mcdonald" in text:
                logger.info("  ✓ Contiene referencia a McDonald's")
                result["contains_mcdonalds"] = True

        platform_results["fetcher_attempts"].append(result)

    except Exception as e:
        logger.error(f"  Error: {e}")
        platform_results["fetcher_attempts"].append({"method": "Fetcher.get", "error": str(e)})

    time.sleep(3)

    # --- Intento 2: StealthyFetcher ---
    logger.info("\n[UberEats] Intento 2: StealthyFetcher (browser stealth)")
    try:
        from scrapling.fetchers import StealthyFetcher

        url = f"https://www.ubereats.com/mx/search?q=McDonald%27s&pl={TEST_LAT}%2C{TEST_LON}"
        logger.info(f"  URL: {url}")
        logger.info("  Lanzando browser stealth...")

        page = StealthyFetcher.fetch(url, headless=True, network_idle=True, timeout=45000)

        result = {"method": "StealthyFetcher.fetch", "url": url}

        if page:
            page_text = page.text if hasattr(page, 'text') else str(page)
            content_len = len(page_text) if page_text else 0
            logger.info(f"  Content length: {content_len}")
            result["content_length"] = content_len

            if page_text:
                save_page_sample("ubereats_stealthy", page_text)

            # Buscar store cards
            try:
                cards = page.css("[data-testid='store-card'], a[href*='store'], [class*='StoreCard']")
                logger.info(f"  Store cards encontrados: {len(cards)}")
                result["store_cards"] = len(cards)

                for i, card in enumerate(cards[:5]):
                    card_text = card.text[:200] if hasattr(card, 'text') and card.text else ""
                    logger.info(f"    Card {i}: {card_text}")
            except Exception as e:
                logger.debug(f"  Error buscando cards: {e}")

            # Buscar precios y fees
            try:
                fees = page.css("[class*='fee'], [class*='Fee'], [class*='delivery']")
                logger.info(f"  Elementos de fee encontrados: {len(fees)}")
                result["fee_elements"] = len(fees)
            except Exception:
                pass

            result["success"] = True
        else:
            result["success"] = False

        platform_results["stealthy_attempts"].append(result)

    except Exception as e:
        logger.error(f"  Error: {e}")
        platform_results["stealthy_attempts"].append({"method": "StealthyFetcher.fetch", "error": str(e)})

    results["platforms"]["ubereats"] = platform_results
    return platform_results


# ═══════════════════════════════════════════════════════════
# TEST 3: DIDI FOOD
# ═══════════════════════════════════════════════════════════
def test_didifood():
    logger.info("\n" + "=" * 60)
    logger.info("TEST: DIDI FOOD")
    logger.info("=" * 60)

    platform_results = {
        "fetcher_attempts": [],
        "stealthy_attempts": [],
        "findings": [],
        "data_extracted": [],
    }

    # --- Intento 1: Fetcher HTTP ---
    logger.info("\n[DiDiFood] Intento 1: Fetcher HTTP")
    try:
        from scrapling.fetchers import Fetcher

        url = "https://www.didifood.com/es-MX"
        logger.info(f"  URL: {url}")

        response = Fetcher.get(url, stealthy_headers=True, follow_redirects=True, timeout=30)
        status = response.status if response else "No response"
        content_len = len(response.text) if response and response.text else 0

        logger.info(f"  Status: {status}")
        logger.info(f"  Content length: {content_len}")

        result = {"method": "Fetcher.get", "url": url, "status": status, "content_length": content_len}

        if response and response.text:
            save_page_sample("didifood_fetcher", response.text)
            text = response.text.lower()

            # DiDi Food cerró en México en 2023
            if any(w in text for w in ["no disponible", "cerrado", "not available", "closed", "ya no opera"]):
                logger.info("  ⚠ Plataforma indica servicio no disponible/cerrado")
                result["service_closed"] = True
                platform_results["findings"].append("DiDi Food aparenta estar cerrado en México")

            if any(w in text for w in ["redirect", "301", "302"]):
                result["redirected"] = True

        platform_results["fetcher_attempts"].append(result)

    except Exception as e:
        logger.error(f"  Error: {e}")
        platform_results["fetcher_attempts"].append({"method": "Fetcher.get", "error": str(e)})

    time.sleep(3)

    # --- Intento 2: StealthyFetcher ---
    logger.info("\n[DiDiFood] Intento 2: StealthyFetcher (browser stealth)")
    try:
        from scrapling.fetchers import StealthyFetcher

        url = "https://www.didifood.com/es-MX"
        logger.info(f"  URL: {url}")
        logger.info("  Lanzando browser stealth...")

        page = StealthyFetcher.fetch(url, headless=True, network_idle=True, timeout=45000)

        result = {"method": "StealthyFetcher.fetch", "url": url}

        if page:
            page_text = page.text if hasattr(page, 'text') else str(page)
            content_len = len(page_text) if page_text else 0
            logger.info(f"  Content length: {content_len}")
            result["content_length"] = content_len

            if page_text:
                save_page_sample("didifood_stealthy", page_text)

                # Verificar si redirige o muestra cierre
                if any(w in page_text.lower() for w in ["didi", "food"]):
                    logger.info("  ✓ Página de DiDi Food cargó")
                    result["page_loaded"] = True
                else:
                    logger.info("  ✗ No parece ser DiDi Food (posible redirect)")
                    result["page_loaded"] = False

            result["success"] = True
        else:
            result["success"] = False

        platform_results["stealthy_attempts"].append(result)

    except Exception as e:
        logger.error(f"  Error: {e}")
        platform_results["stealthy_attempts"].append({"method": "StealthyFetcher.fetch", "error": str(e)})

    results["platforms"]["didifood"] = platform_results
    return platform_results


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    logger.info("╔══════════════════════════════════════════════════════════╗")
    logger.info("║  TEST DE SCRAPING REAL — Competitive Intelligence      ║")
    logger.info("╚══════════════════════════════════════════════════════════╝")
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    logger.info(f"Ubicación de prueba: {TEST_ADDRESS}")
    logger.info(f"Coordenadas: {TEST_LAT}, {TEST_LON}\n")

    test_rappi()
    time.sleep(5)

    test_ubereats()
    time.sleep(5)

    test_didifood()

    # Guardar resultados consolidados
    results_path = RESULTS_DIR / "scraping_test_results.json"
    results_path.write_text(json.dumps(results, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    logger.info(f"\n{'=' * 60}")
    logger.info(f"Resultados guardados en: {results_path}")
    logger.info(f"Log guardado en: data/raw/scraping_test_log.txt")
    logger.info(f"{'=' * 60}")

    # Resumen
    logger.info("\n📊 RESUMEN DE RESULTADOS:")
    for platform, data in results["platforms"].items():
        fetcher_ok = any(a.get("status") == 200 for a in data.get("fetcher_attempts", []))
        stealthy_ok = any(a.get("success") for a in data.get("stealthy_attempts", []))
        logger.info(f"  {platform}: Fetcher={'OK' if fetcher_ok else 'FAIL'} | StealthyFetcher={'OK' if stealthy_ok else 'FAIL'}")
        if data.get("findings"):
            for f in data["findings"]:
                logger.info(f"    → {f}")
