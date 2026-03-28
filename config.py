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


# 10 zonas representativas de CDMX (3 premium, 4 media, 3 popular)
ADDRESSES: list[Address] = [
    Address(
        id="polanco",
        name="Polanco",
        zone_type="premium",
        lat=19.4326,
        lon=-99.1942,
        street="Av. Presidente Masaryk 360, Polanco, CDMX",
    ),
    Address(
        id="condesa",
        name="Condesa",
        zone_type="premium",
        lat=19.4111,
        lon=-99.1734,
        street="Av. Tamaulipas 100, Condesa, CDMX",
    ),
    Address(
        id="roma_norte",
        name="Roma Norte",
        zone_type="premium",
        lat=19.4195,
        lon=-99.1617,
        street="Calle Orizaba 150, Roma Norte, CDMX",
    ),
    Address(
        id="del_valle",
        name="Del Valle",
        zone_type="media",
        lat=19.3856,
        lon=-99.1632,
        street="Av. Universidad 1000, Del Valle, CDMX",
    ),
    Address(
        id="coyoacan",
        name="Coyoacán",
        zone_type="media",
        lat=19.3467,
        lon=-99.1617,
        street="Av. Universidad 3000, Coyoacán, CDMX",
    ),
    Address(
        id="santa_fe",
        name="Santa Fe",
        zone_type="media",
        lat=19.3659,
        lon=-99.2614,
        street="Av. Vasco de Quiroga 3800, Santa Fe, CDMX",
    ),
    Address(
        id="tlalpan",
        name="Tlalpan",
        zone_type="media",
        lat=19.2870,
        lon=-99.1680,
        street="Calzada de Tlalpan 4000, Tlalpan, CDMX",
    ),
    Address(
        id="iztapalapa",
        name="Iztapalapa",
        zone_type="popular",
        lat=19.3558,
        lon=-99.0742,
        street="Calzada Ermita Iztapalapa 3000, Iztapalapa, CDMX",
    ),
    Address(
        id="naucalpan",
        name="Naucalpan",
        zone_type="popular",
        lat=19.4784,
        lon=-99.2398,
        street="Av. Lomas Verdes 750, Naucalpan, Edo. Méx.",
    ),
    Address(
        id="ecatepec",
        name="Ecatepec",
        zone_type="popular",
        lat=19.6014,
        lon=-99.0530,
        street="Av. Central 500, Ecatepec, Edo. Méx.",
    ),
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
