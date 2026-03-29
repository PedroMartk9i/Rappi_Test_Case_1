"""
Configuración central del proyecto: direcciones de entrega en CDMX,
productos objetivo y constantes de scraping.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Address:
    id: str
    name: str
    zone_type: str  # "premium", "media", "popular"
    lat: float
    lon: float
    street: str  # dirección legible para input en plataformas


# 25 zonas representativas de CDMX (8 premium, 9 media, 8 popular)
ADDRESSES: list[Address] = [
    # === PREMIUM ===
    Address(id="polanco", name="Polanco", zone_type="premium",
            lat=19.4326, lon=-99.1942,
            street="Av. Presidente Masaryk 360, Polanco, CDMX"),
    Address(id="condesa", name="Condesa", zone_type="premium",
            lat=19.4111, lon=-99.1734,
            street="Av. Tamaulipas 100, Condesa, CDMX"),
    Address(id="roma_norte", name="Roma Norte", zone_type="premium",
            lat=19.4195, lon=-99.1617,
            street="Calle Orizaba 150, Roma Norte, CDMX"),
    Address(id="lomas", name="Lomas de Chapultepec", zone_type="premium",
            lat=19.4230, lon=-99.2170,
            street="Paseo de la Reforma 1000, Lomas de Chapultepec, CDMX"),
    Address(id="interlomas", name="Interlomas", zone_type="premium",
            lat=19.3960, lon=-99.2890,
            street="Av. Jesús del Monte 200, Interlomas, Huixquilucan"),
    Address(id="pedregal", name="Pedregal", zone_type="premium",
            lat=19.3120, lon=-99.2050,
            street="Av. de las Fuentes 200, Pedregal de San Ángel, CDMX"),
    Address(id="santa_fe", name="Santa Fe", zone_type="premium",
            lat=19.3659, lon=-99.2614,
            street="Av. Vasco de Quiroga 3800, Santa Fe, CDMX"),
    Address(id="satelite", name="Ciudad Satélite", zone_type="premium",
            lat=19.5090, lon=-99.2340,
            street="Circuito Centro Comercial 100, Ciudad Satélite, Naucalpan"),
    # === MEDIA ===
    Address(id="del_valle", name="Del Valle", zone_type="media",
            lat=19.3856, lon=-99.1632,
            street="Av. Universidad 1000, Del Valle, CDMX"),
    Address(id="coyoacan", name="Coyoacán", zone_type="media",
            lat=19.3467, lon=-99.1617,
            street="Av. Universidad 3000, Coyoacán, CDMX"),
    Address(id="tlalpan", name="Tlalpan", zone_type="media",
            lat=19.2870, lon=-99.1680,
            street="Calzada de Tlalpan 4000, Tlalpan, CDMX"),
    Address(id="narvarte", name="Narvarte", zone_type="media",
            lat=19.3990, lon=-99.1540,
            street="Av. Diagonal de San Antonio 1000, Narvarte, CDMX"),
    Address(id="napoles", name="Nápoles", zone_type="media",
            lat=19.3930, lon=-99.1730,
            street="Av. Insurgentes Sur 1400, Nápoles, CDMX"),
    Address(id="mixcoac", name="Mixcoac", zone_type="media",
            lat=19.3750, lon=-99.1870,
            street="Av. Revolución 1200, Mixcoac, CDMX"),
    Address(id="azcapotzalco", name="Azcapotzalco", zone_type="media",
            lat=19.4870, lon=-99.1860,
            street="Av. Azcapotzalco 500, Azcapotzalco, CDMX"),
    Address(id="lindavista", name="Lindavista", zone_type="media",
            lat=19.4930, lon=-99.1280,
            street="Av. Montevideo 400, Lindavista, CDMX"),
    Address(id="san_pedro_pinos", name="San Pedro de los Pinos", zone_type="media",
            lat=19.3963, lon=-99.1806,
            street="Av. Patriotismo 229, San Pedro de los Pinos, CDMX"),
    # === POPULAR ===
    Address(id="iztapalapa", name="Iztapalapa", zone_type="popular",
            lat=19.3558, lon=-99.0742,
            street="Calzada Ermita Iztapalapa 3000, Iztapalapa, CDMX"),
    Address(id="naucalpan", name="Naucalpan", zone_type="popular",
            lat=19.4784, lon=-99.2398,
            street="Av. Lomas Verdes 750, Naucalpan, Edo. Méx."),
    Address(id="ecatepec", name="Ecatepec", zone_type="popular",
            lat=19.6014, lon=-99.0530,
            street="Av. Central 500, Ecatepec, Edo. Méx."),
    Address(id="gustavo_madero", name="Gustavo A. Madero", zone_type="popular",
            lat=19.4840, lon=-99.1120,
            street="Av. Insurgentes Norte 1500, Gustavo A. Madero, CDMX"),
    Address(id="tlahuac", name="Tláhuac", zone_type="popular",
            lat=19.2860, lon=-99.0050,
            street="Calzada Tláhuac 3500, Tláhuac, CDMX"),
    Address(id="xochimilco", name="Xochimilco", zone_type="popular",
            lat=19.2610, lon=-99.1040,
            street="Av. Guadalupe Ramírez 200, Xochimilco, CDMX"),
    Address(id="iztacalco", name="Iztacalco", zone_type="popular",
            lat=19.3950, lon=-99.0970,
            street="Calzada de la Viga 1000, Iztacalco, CDMX"),
    Address(id="nezahualcoyotl", name="Nezahualcóyotl", zone_type="popular",
            lat=19.4000, lon=-99.0180,
            street="Av. Chimalhuacán 200, Nezahualcóyotl, Edo. Méx."),
]

# Productos McDonald's objetivo
@dataclass(frozen=True)
class Product:
    id: str
    name: str
    keywords: list[str]  # términos de búsqueda alternativos


PRODUCTS: list[Product] = [
    Product(id="big_mac", name="Big Mac", keywords=["big mac", "bigmac"]),
    Product(
        id="combo_mediano",
        name="McCombo Mediano Big Mac",
        keywords=["combo mediano", "mccombo mediano", "combo big mac"],
    ),
    Product(
        id="nuggets_10",
        name="McNuggets 10 piezas",
        keywords=["nuggets 10", "mcnuggets 10", "chicken mcnuggets 10"],
    ),
    Product(
        id="coca_600",
        name="Coca-Cola 600ml",
        keywords=["coca-cola 600", "coca cola 600", "refresco coca"],
    ),
    Product(
        id="agua_1l",
        name="Agua 1L",
        keywords=["agua 1l", "agua 1 litro", "agua natural"],
    ),
]

# Constantes de scraping
SCRAPING_CONFIG = {
    "rate_limit_seconds": 3,
    "max_retries": 3,
    "timeout_seconds": 30,
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
}

# Plataformas
PLATFORMS = {
    "rappi": {
        "name": "Rappi",
        "base_url": "https://www.rappi.com.mx",
        "restaurant_query": "mcdonalds",
    },
    "ubereats": {
        "name": "Uber Eats",
        "base_url": "https://www.ubereats.com/mx",
        "restaurant_query": "mcdonalds",
    },
    "didifood": {
        "name": "DiDi Food",
        "base_url": "https://www.didi-food.com/es-MX",
        "restaurant_query": "mcdonalds",
    },
}
