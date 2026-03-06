"""
Seed data for the product service.
Loaded once on startup – skipped if data already exists (idempotent).
"""

import time

from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from .database import client, families_collection, subfamilies_collection, campaigns_collection, products_collection


def _wait_for_mongo(retries: int = 10, delay: float = 2.0) -> None:
    """Block until MongoDB is reachable or raise after *retries* attempts."""
    for attempt in range(1, retries + 1):
        try:
            client.admin.command("ping")
            return
        except (ConnectionFailure, ServerSelectionTimeoutError) as exc:
            print(f"[seed] MongoDB not ready (attempt {attempt}/{retries}): {exc}")
            if attempt == retries:
                raise
            time.sleep(delay)


# ---------------------------------------------------------------------------
# 10 Families
# ---------------------------------------------------------------------------
FAMILIES = [
    {"id": "a1f6e2d0-1c3b-4e8a-9f7d-000000000001", "name": "Iluminación",  "family_code": 1},
    {"id": "a1f6e2d0-1c3b-4e8a-9f7d-000000000002", "name": "Textil",       "family_code": 2},
    {"id": "a1f6e2d0-1c3b-4e8a-9f7d-000000000003", "name": "Vidrio",       "family_code": 3},
    {"id": "a1f6e2d0-1c3b-4e8a-9f7d-000000000004", "name": "Mobiliario",   "family_code": 4},
    {"id": "a1f6e2d0-1c3b-4e8a-9f7d-000000000005", "name": "Electrónica",  "family_code": 5},
    {"id": "a1f6e2d0-1c3b-4e8a-9f7d-000000000006", "name": "Decoración",   "family_code": 6},
    {"id": "a1f6e2d0-1c3b-4e8a-9f7d-000000000007", "name": "Ferretería",   "family_code": 7},
    {"id": "a1f6e2d0-1c3b-4e8a-9f7d-000000000008", "name": "Alimentación", "family_code": 8},
    {"id": "a1f6e2d0-1c3b-4e8a-9f7d-000000000009", "name": "Papelería",    "family_code": 9},
    {"id": "a1f6e2d0-1c3b-4e8a-9f7d-000000000010", "name": "Juguetería",   "family_code": 10},
]

# ---------------------------------------------------------------------------
# 30 Subfamilies – 3 per family (family_id = UUID of parent family)
# ---------------------------------------------------------------------------
SUBFAMILIES = [
    # Iluminación (family_code 1)
    {"id": "b2c7f3e1-2d4c-5f9b-a08e-100000000001", "name": "Bombillas",             "subfamily_code": 1,  "family_id": "a1f6e2d0-1c3b-4e8a-9f7d-000000000001"},
    {"id": "b2c7f3e1-2d4c-5f9b-a08e-100000000002", "name": "Lámparas de pie",       "subfamily_code": 2,  "family_id": "a1f6e2d0-1c3b-4e8a-9f7d-000000000001"},
    {"id": "b2c7f3e1-2d4c-5f9b-a08e-100000000003", "name": "Focos empotrables",     "subfamily_code": 3,  "family_id": "a1f6e2d0-1c3b-4e8a-9f7d-000000000001"},
    # Textil (family_code 2)
    {"id": "b2c7f3e1-2d4c-5f9b-a08e-100000000004", "name": "Camisetas",             "subfamily_code": 4,  "family_id": "a1f6e2d0-1c3b-4e8a-9f7d-000000000002"},
    {"id": "b2c7f3e1-2d4c-5f9b-a08e-100000000005", "name": "Pantalones",            "subfamily_code": 5,  "family_id": "a1f6e2d0-1c3b-4e8a-9f7d-000000000002"},
    {"id": "b2c7f3e1-2d4c-5f9b-a08e-100000000006", "name": "Ropa de cama",          "subfamily_code": 6,  "family_id": "a1f6e2d0-1c3b-4e8a-9f7d-000000000002"},
    # Vidrio (family_code 3)
    {"id": "b2c7f3e1-2d4c-5f9b-a08e-100000000007", "name": "Vasos",                 "subfamily_code": 7,  "family_id": "a1f6e2d0-1c3b-4e8a-9f7d-000000000003"},
    {"id": "b2c7f3e1-2d4c-5f9b-a08e-100000000008", "name": "Botellas",              "subfamily_code": 8,  "family_id": "a1f6e2d0-1c3b-4e8a-9f7d-000000000003"},
    {"id": "b2c7f3e1-2d4c-5f9b-a08e-100000000009", "name": "Espejos decorativos",   "subfamily_code": 9,  "family_id": "a1f6e2d0-1c3b-4e8a-9f7d-000000000003"},
    # Mobiliario (family_code 4)
    {"id": "b2c7f3e1-2d4c-5f9b-a08e-100000000010", "name": "Sillas",                "subfamily_code": 10, "family_id": "a1f6e2d0-1c3b-4e8a-9f7d-000000000004"},
    {"id": "b2c7f3e1-2d4c-5f9b-a08e-100000000011", "name": "Mesas",                 "subfamily_code": 11, "family_id": "a1f6e2d0-1c3b-4e8a-9f7d-000000000004"},
    {"id": "b2c7f3e1-2d4c-5f9b-a08e-100000000012", "name": "Armarios",              "subfamily_code": 12, "family_id": "a1f6e2d0-1c3b-4e8a-9f7d-000000000004"},
    # Electrónica (family_code 5)
    {"id": "b2c7f3e1-2d4c-5f9b-a08e-100000000013", "name": "Smartphones",           "subfamily_code": 13, "family_id": "a1f6e2d0-1c3b-4e8a-9f7d-000000000005"},
    {"id": "b2c7f3e1-2d4c-5f9b-a08e-100000000014", "name": "Tablets",               "subfamily_code": 14, "family_id": "a1f6e2d0-1c3b-4e8a-9f7d-000000000005"},
    {"id": "b2c7f3e1-2d4c-5f9b-a08e-100000000015", "name": "Portátiles",            "subfamily_code": 15, "family_id": "a1f6e2d0-1c3b-4e8a-9f7d-000000000005"},
    # Decoración (family_code 6)
    {"id": "b2c7f3e1-2d4c-5f9b-a08e-100000000016", "name": "Cuadros",               "subfamily_code": 16, "family_id": "a1f6e2d0-1c3b-4e8a-9f7d-000000000006"},
    {"id": "b2c7f3e1-2d4c-5f9b-a08e-100000000017", "name": "Plantas artificiales",  "subfamily_code": 17, "family_id": "a1f6e2d0-1c3b-4e8a-9f7d-000000000006"},
    {"id": "b2c7f3e1-2d4c-5f9b-a08e-100000000018", "name": "Velas y aromas",        "subfamily_code": 18, "family_id": "a1f6e2d0-1c3b-4e8a-9f7d-000000000006"},
    # Ferretería (family_code 7)
    {"id": "b2c7f3e1-2d4c-5f9b-a08e-100000000019", "name": "Tornillería",           "subfamily_code": 19, "family_id": "a1f6e2d0-1c3b-4e8a-9f7d-000000000007"},
    {"id": "b2c7f3e1-2d4c-5f9b-a08e-100000000020", "name": "Pinturas",              "subfamily_code": 20, "family_id": "a1f6e2d0-1c3b-4e8a-9f7d-000000000007"},
    {"id": "b2c7f3e1-2d4c-5f9b-a08e-100000000021", "name": "Herramientas manuales", "subfamily_code": 21, "family_id": "a1f6e2d0-1c3b-4e8a-9f7d-000000000007"},
    # Alimentación (family_code 8)
    {"id": "b2c7f3e1-2d4c-5f9b-a08e-100000000022", "name": "Conservas",             "subfamily_code": 22, "family_id": "a1f6e2d0-1c3b-4e8a-9f7d-000000000008"},
    {"id": "b2c7f3e1-2d4c-5f9b-a08e-100000000023", "name": "Bebidas",               "subfamily_code": 23, "family_id": "a1f6e2d0-1c3b-4e8a-9f7d-000000000008"},
    {"id": "b2c7f3e1-2d4c-5f9b-a08e-100000000024", "name": "Snacks",                "subfamily_code": 24, "family_id": "a1f6e2d0-1c3b-4e8a-9f7d-000000000008"},
    # Papelería (family_code 9)
    {"id": "b2c7f3e1-2d4c-5f9b-a08e-100000000025", "name": "Bolígrafos",            "subfamily_code": 25, "family_id": "a1f6e2d0-1c3b-4e8a-9f7d-000000000009"},
    {"id": "b2c7f3e1-2d4c-5f9b-a08e-100000000026", "name": "Cuadernos",             "subfamily_code": 26, "family_id": "a1f6e2d0-1c3b-4e8a-9f7d-000000000009"},
    {"id": "b2c7f3e1-2d4c-5f9b-a08e-100000000027", "name": "Archivadores",          "subfamily_code": 27, "family_id": "a1f6e2d0-1c3b-4e8a-9f7d-000000000009"},
    # Juguetería (family_code 10)
    {"id": "b2c7f3e1-2d4c-5f9b-a08e-100000000028", "name": "Puzzles",               "subfamily_code": 28, "family_id": "a1f6e2d0-1c3b-4e8a-9f7d-000000000010"},
    {"id": "b2c7f3e1-2d4c-5f9b-a08e-100000000029", "name": "Sets de construcción",  "subfamily_code": 29, "family_id": "a1f6e2d0-1c3b-4e8a-9f7d-000000000010"},
    {"id": "b2c7f3e1-2d4c-5f9b-a08e-100000000030", "name": "Muñecos y figuras",     "subfamily_code": 30, "family_id": "a1f6e2d0-1c3b-4e8a-9f7d-000000000010"},
]

# ---------------------------------------------------------------------------
# Product helpers – aliases for readability in PRODUCTS list
# ---------------------------------------------------------------------------
_FAM_IL = "a1f6e2d0-1c3b-4e8a-9f7d-000000000001"  # Iluminación
_FAM_TX = "a1f6e2d0-1c3b-4e8a-9f7d-000000000002"  # Textil
_FAM_VI = "a1f6e2d0-1c3b-4e8a-9f7d-000000000003"  # Vidrio
_FAM_MO = "a1f6e2d0-1c3b-4e8a-9f7d-000000000004"  # Mobiliario
_FAM_EL = "a1f6e2d0-1c3b-4e8a-9f7d-000000000005"  # Electrónica
_FAM_DE = "a1f6e2d0-1c3b-4e8a-9f7d-000000000006"  # Decoración
_FAM_JU = "a1f6e2d0-1c3b-4e8a-9f7d-000000000010"  # Juguetería

_SUB_BOMBILLAS   = "b2c7f3e1-2d4c-5f9b-a08e-100000000001"  # Iluminación
_SUB_LAMPARAS    = "b2c7f3e1-2d4c-5f9b-a08e-100000000002"  # Iluminación
_SUB_FOCOS       = "b2c7f3e1-2d4c-5f9b-a08e-100000000003"  # Iluminación
_SUB_CAMISETAS   = "b2c7f3e1-2d4c-5f9b-a08e-100000000004"  # Textil
_SUB_PANTALONES  = "b2c7f3e1-2d4c-5f9b-a08e-100000000005"  # Textil
_SUB_ROPA_CAMA   = "b2c7f3e1-2d4c-5f9b-a08e-100000000006"  # Textil
_SUB_VASOS       = "b2c7f3e1-2d4c-5f9b-a08e-100000000007"  # Vidrio
_SUB_BOTELLAS    = "b2c7f3e1-2d4c-5f9b-a08e-100000000008"  # Vidrio
_SUB_SILLAS      = "b2c7f3e1-2d4c-5f9b-a08e-100000000010"  # Mobiliario
_SUB_MESAS       = "b2c7f3e1-2d4c-5f9b-a08e-100000000011"  # Mobiliario
_SUB_SMARTPHONES = "b2c7f3e1-2d4c-5f9b-a08e-100000000013"  # Electrónica
_SUB_TABLETS     = "b2c7f3e1-2d4c-5f9b-a08e-100000000014"  # Electrónica
_SUB_PORTATILES  = "b2c7f3e1-2d4c-5f9b-a08e-100000000015"  # Electrónica
_SUB_CUADROS     = "b2c7f3e1-2d4c-5f9b-a08e-100000000016"  # Decoración
_SUB_PLANTAS     = "b2c7f3e1-2d4c-5f9b-a08e-100000000017"  # Decoración
_SUB_VELAS       = "b2c7f3e1-2d4c-5f9b-a08e-100000000018"  # Decoración
_SUB_PUZZLES     = "b2c7f3e1-2d4c-5f9b-a08e-100000000028"  # Juguetería
_SUB_CONSTRUC    = "b2c7f3e1-2d4c-5f9b-a08e-100000000029"  # Juguetería

_CAMP_S26 = "c3d8a4f2-3e5d-6f0c-b19f-200000000003"  # Summer 2026
_CAMP_W26 = "c3d8a4f2-3e5d-6f0c-b19f-200000000004"  # Winter 2026
_CAMP_S25 = "c3d8a4f2-3e5d-6f0c-b19f-200000000001"  # Summer 2025

# Manufacturer UUIDs – must match users-service seed
_MFR01 = "d4e5f6a7-b8c9-4d0e-a1f2-000000000001"  # Ana García    → 5 products  (1–5)
_MFR02 = "d4e5f6a7-b8c9-4d0e-a1f2-000000000002"  # Miguel Torres → 15 products (6–20)


def _sz(order: int, name: str, product_num: int) -> dict:
    return {"id": f"e6a1d7f5-6b8c-4c3f-d42c-5{product_num:02d}0000{order:02d}0000", "name": name, "order": order}


# ---------------------------------------------------------------------------
# 20 Products  (MFR01 = products 1-5 · MFR02 = products 6-20)
# ---------------------------------------------------------------------------
PRODUCTS = [
    # 1 – Bombilla LED E27 9W (Iluminación / Bombillas) – Summer 2026
    {
        "id": "f7b2e8a6-7c9d-4d4a-e53d-600000000001",
        "name": "Bombilla LED E27 9W",
        "description": "Bombilla LED de bajo consumo con casquillo E27, 9W y 806 lúmenes. Luz cálida 2700K. Vida útil 15.000h.",
        "ean_code": "8400000100001",
        "manufacturer_id": _MFR01,
        "family_id": _FAM_IL, "subfamily_id": _SUB_BOMBILLAS, "campaign_id": _CAMP_S26,
        "sizes": [_sz(0, "9W", 1), _sz(1, "12W", 1)],
    },
    # 2 – Bombilla LED E14 regulable (Iluminación / Bombillas) – Winter 2026
    {
        "id": "f7b2e8a6-7c9d-4d4a-e53d-600000000002",
        "name": "Bombilla LED E14 regulable",
        "description": "Bombilla LED regulable con casquillo E14, acabado ámbar vintage. Compatible con reguladores estándar.",
        "ean_code": "8400000100002",
        "manufacturer_id": _MFR01,
        "family_id": _FAM_IL, "subfamily_id": _SUB_BOMBILLAS, "campaign_id": _CAMP_W26,
        "sizes": [_sz(0, "4W", 2), _sz(1, "6W", 2)],
    },
    # 3 – Lámpara de pie trípode nogal (Iluminación / Lámparas de pie) – Summer 2026
    {
        "id": "f7b2e8a6-7c9d-4d4a-e53d-600000000003",
        "name": "Lámpara de pie trípode nogal",
        "description": "Lámpara de pie con estructura de madera de nogal y pantalla de lino natural. Altura 150 cm.",
        "ean_code": "8400000100003",
        "manufacturer_id": _MFR01,
        "family_id": _FAM_IL, "subfamily_id": _SUB_LAMPARAS, "campaign_id": _CAMP_S26,
        "sizes": [_sz(0, "150cm", 3)],
    },
    # 4 – Foco empotrable LED redondo (Iluminación / Focos empotrables) – Winter 2026
    {
        "id": "f7b2e8a6-7c9d-4d4a-e53d-600000000004",
        "name": "Foco empotrable LED redondo",
        "description": "Foco empotrable LED IP44 apto para baños. Acabado blanco, luz neutra 4000K.",
        "ean_code": "8400000100004",
        "manufacturer_id": _MFR01,
        "family_id": _FAM_IL, "subfamily_id": _SUB_FOCOS, "campaign_id": _CAMP_W26,
        "sizes": [_sz(0, "7W", 4), _sz(1, "12W", 4)],
    },
    # 5 – Camiseta básica cuello redondo (Textil / Camisetas) – Summer 2026
    {
        "id": "f7b2e8a6-7c9d-4d4a-e53d-600000000005",
        "name": "Camiseta básica cuello redondo",
        "description": "Camiseta unisex 100% algodón orgánico, cuello redondo. Disponible en varios colores.",
        "ean_code": "8400000100005",
        "manufacturer_id": _MFR01,
        "family_id": _FAM_TX, "subfamily_id": _SUB_CAMISETAS, "campaign_id": _CAMP_S26,
        "sizes": [_sz(0, "S", 5), _sz(1, "M", 5), _sz(2, "L", 5), _sz(3, "XL", 5)],
    },
    # 6 – Camiseta manga larga estampada (Textil / Camisetas) – Winter 2026
    {
        "id": "f7b2e8a6-7c9d-4d4a-e53d-600000000006",
        "name": "Camiseta manga larga estampada",
        "description": "Camiseta de manga larga con estampado geométrico. Tejido suave 95% algodón 5% elastano.",
        "ean_code": "8400000100006",
        "manufacturer_id": _MFR02,
        "family_id": _FAM_TX, "subfamily_id": _SUB_CAMISETAS, "campaign_id": _CAMP_W26,
        "sizes": [_sz(0, "S", 6), _sz(1, "M", 6), _sz(2, "L", 6), _sz(3, "XL", 6)],
    },
    # 7 – Pantalón chino slim fit (Textil / Pantalones) – Summer 2026
    {
        "id": "f7b2e8a6-7c9d-4d4a-e53d-600000000007",
        "name": "Pantalón chino slim fit",
        "description": "Pantalón chino de corte slim en sarga de algodón. Cintura ajustable. Colores neutros.",
        "ean_code": "8400000100007",
        "manufacturer_id": _MFR02,
        "family_id": _FAM_TX, "subfamily_id": _SUB_PANTALONES, "campaign_id": _CAMP_S26,
        "sizes": [_sz(0, "38", 7), _sz(1, "40", 7), _sz(2, "42", 7)],
    },
    # 8 – Juego de sábanas percal 200 hilos (Textil / Ropa de cama) – Winter 2026
    {
        "id": "f7b2e8a6-7c9d-4d4a-e53d-600000000008",
        "name": "Juego de sábanas percal 200 hilos",
        "description": "Juego de sábanas encimera + bajera ajustable + funda almohada en percal 200 hilos. Tacto suave y duradero.",
        "ean_code": "8400000100008",
        "manufacturer_id": _MFR02,
        "family_id": _FAM_TX, "subfamily_id": _SUB_ROPA_CAMA, "campaign_id": _CAMP_W26,
        "sizes": [_sz(0, "150cm", 8), _sz(1, "180cm", 8)],
    },
    # 9 – Vaso agua cristal borosilicato (Vidrio / Vasos) – Summer 2026
    {
        "id": "f7b2e8a6-7c9d-4d4a-e53d-600000000009",
        "name": "Vaso agua cristal borosilicato",
        "description": "Vaso de agua fabricado en cristal borosilicato resistente a cambios de temperatura. Apto lavavajillas.",
        "ean_code": "8400000100009",
        "manufacturer_id": _MFR02,
        "family_id": _FAM_VI, "subfamily_id": _SUB_VASOS, "campaign_id": _CAMP_S26,
        "sizes": [_sz(0, "25cl", 9), _sz(1, "40cl", 9)],
    },
    # 10 – Botella agua vidrio hermética (Vidrio / Botellas) – Summer 2026
    {
        "id": "f7b2e8a6-7c9d-4d4a-e53d-600000000010",
        "name": "Botella agua vidrio hermética",
        "description": "Botella reutilizable de vidrio con tapa hermética de bambú. Sin BPA. Ideal para uso diario.",
        "ean_code": "8400000100010",
        "manufacturer_id": _MFR02,
        "family_id": _FAM_VI, "subfamily_id": _SUB_BOTELLAS, "campaign_id": _CAMP_S26,
        "sizes": [_sz(0, "500ml", 10), _sz(1, "1L", 10)],
    },
    # 11 – Silla oficina ergonómica (Mobiliario / Sillas) – Winter 2026
    {
        "id": "f7b2e8a6-7c9d-4d4a-e53d-600000000011",
        "name": "Silla oficina ergonómica",
        "description": "Silla de oficina con soporte lumbar ajustable, reposabrazos 3D y base giratoria de aluminio. Carga máx. 120kg.",
        "ean_code": "8400000100011",
        "manufacturer_id": _MFR02,
        "family_id": _FAM_MO, "subfamily_id": _SUB_SILLAS, "campaign_id": _CAMP_W26,
        "sizes": [_sz(0, "Estándar", 11)],
    },
    # 12 – Mesa escritorio minimalista (Mobiliario / Mesas) – Summer 2026
    {
        "id": "f7b2e8a6-7c9d-4d4a-e53d-600000000012",
        "name": "Mesa escritorio minimalista",
        "description": "Mesa de escritorio de tablero MDF con acabado roble y patas de acero negro. Gestión de cables integrada.",
        "ean_code": "8400000100012",
        "manufacturer_id": _MFR02,
        "family_id": _FAM_MO, "subfamily_id": _SUB_MESAS, "campaign_id": _CAMP_S26,
        "sizes": [_sz(0, "120cm", 12), _sz(1, "160cm", 12)],
    },
    # 13 – Smartphone Android 6.5" (Electrónica / Smartphones) – Summer 2026
    {
        "id": "f7b2e8a6-7c9d-4d4a-e53d-600000000013",
        "name": "Smartphone Android 6.5\"",
        "description": "Smartphone con pantalla AMOLED 6.5\", cámara triple 64MP, batería 5000mAh y carga rápida 33W.",
        "ean_code": "8400000100013",
        "manufacturer_id": _MFR02,
        "family_id": _FAM_EL, "subfamily_id": _SUB_SMARTPHONES, "campaign_id": _CAMP_S26,
        "sizes": [_sz(0, "64GB", 13), _sz(1, "128GB", 13)],
    },
    # 14 – Tablet Android 10" (Electrónica / Tablets) – Summer 2026
    {
        "id": "f7b2e8a6-7c9d-4d4a-e53d-600000000014",
        "name": "Tablet Android 10\"",
        "description": "Tablet con pantalla IPS 10\", procesador octa-core, 4GB RAM y batería 6000mAh. Incluye funda protectora.",
        "ean_code": "8400000100014",
        "manufacturer_id": _MFR02,
        "family_id": _FAM_EL, "subfamily_id": _SUB_TABLETS, "campaign_id": _CAMP_S26,
        "sizes": [_sz(0, "32GB", 14), _sz(1, "64GB", 14)],
    },
    # 15 – Portátil ultrabook 15.6" (Electrónica / Portátiles) – Winter 2026
    {
        "id": "f7b2e8a6-7c9d-4d4a-e53d-600000000015",
        "name": "Portátil ultrabook 15.6\"",
        "description": "Ultrabook con pantalla Full HD 15.6\", procesador Intel Core i5, SSD 512GB y batería 12h. Peso 1,4kg.",
        "ean_code": "8400000100015",
        "manufacturer_id": _MFR02,
        "family_id": _FAM_EL, "subfamily_id": _SUB_PORTATILES, "campaign_id": _CAMP_W26,
        "sizes": [_sz(0, "8GB RAM", 15), _sz(1, "16GB RAM", 15)],
    },
    # 16 – Cuadro abstracto moderno (Decoración / Cuadros) – Summer 2026
    {
        "id": "f7b2e8a6-7c9d-4d4a-e53d-600000000016",
        "name": "Cuadro abstracto moderno",
        "description": "Cuadro impreso sobre lienzo canvas con bastidor de madera. Motivo abstracto geométrico en tonos tierra.",
        "ean_code": "8400000100016",
        "manufacturer_id": _MFR02,
        "family_id": _FAM_DE, "subfamily_id": _SUB_CUADROS, "campaign_id": _CAMP_S26,
        "sizes": [_sz(0, "30x40cm", 16), _sz(1, "50x70cm", 16), _sz(2, "70x100cm", 16)],
    },
    # 17 – Planta artificial bambú (Decoración / Plantas artificiales) – Summer 2026
    {
        "id": "f7b2e8a6-7c9d-4d4a-e53d-600000000017",
        "name": "Planta artificial bambú decorativo",
        "description": "Planta artificial de bambú con maceta cerámica blanca. Aspecto ultra-realista. Sin mantenimiento.",
        "ean_code": "8400000100017",
        "manufacturer_id": _MFR02,
        "family_id": _FAM_DE, "subfamily_id": _SUB_PLANTAS, "campaign_id": _CAMP_S26,
        "sizes": [_sz(0, "60cm", 17), _sz(1, "120cm", 17)],
    },
    # 18 – Vela aromática lavanda (Decoración / Velas y aromas) – Winter 2026
    {
        "id": "f7b2e8a6-7c9d-4d4a-e53d-600000000018",
        "name": "Vela aromática lavanda",
        "description": "Vela de soja 100% natural con aroma de lavanda y aceites esenciales. Mecha de algodón. Quema limpia.",
        "ean_code": "8400000100018",
        "manufacturer_id": _MFR02,
        "family_id": _FAM_DE, "subfamily_id": _SUB_VELAS, "campaign_id": _CAMP_W26,
        "sizes": [_sz(0, "150g", 18), _sz(1, "300g", 18)],
    },
    # 19 – Puzzle 1000 piezas ciudad (Juguetería / Puzzles) – Summer 2026
    {
        "id": "f7b2e8a6-7c9d-4d4a-e53d-600000000019",
        "name": "Puzzle 1000 piezas ciudad",
        "description": "Puzzle 1000 piezas con ilustración panorámica de ciudad europea. Cartón reciclado de alta calidad.",
        "ean_code": "8400000100019",
        "manufacturer_id": _MFR02,
        "family_id": _FAM_JU, "subfamily_id": _SUB_PUZZLES, "campaign_id": _CAMP_S26,
        "sizes": [_sz(0, "1000 piezas", 19)],
    },
    # 20 – Set de construcción bloques (Juguetería / Sets de construcción) – Winter 2026
    {
        "id": "f7b2e8a6-7c9d-4d4a-e53d-600000000020",
        "name": "Set de construcción bloques",
        "description": "Set de bloques de construcción compatibles con sistemas estándar. Plástico ABS libre de BPA. +6 años.",
        "ean_code": "8400000100020",
        "manufacturer_id": _MFR02,
        "family_id": _FAM_JU, "subfamily_id": _SUB_CONSTRUC, "campaign_id": _CAMP_W26,
        "sizes": [_sz(0, "100 pzs", 20), _sz(1, "250 pzs", 20), _sz(2, "500 pzs", 20)],
    },
]

# ---------------------------------------------------------------------------
# 4 Campaigns / Seasons
# ---------------------------------------------------------------------------
CAMPAIGNS = [
    {"id": "c3d8a4f2-3e5d-6f0c-b19f-200000000001", "name": "Summer 2025"},
    {"id": "c3d8a4f2-3e5d-6f0c-b19f-200000000002", "name": "Winter 2025"},
    {"id": "c3d8a4f2-3e5d-6f0c-b19f-200000000003", "name": "Summer 2026"},
    {"id": "c3d8a4f2-3e5d-6f0c-b19f-200000000004", "name": "Winter 2026"},
]


def run_seed() -> None:
    """Insert seed documents only if each collection is still empty."""
    _wait_for_mongo()
    if families_collection.count_documents({}) == 0:
        families_collection.insert_many(FAMILIES)
        print(f"[seed] Inserted {len(FAMILIES)} families.")
    else:
        print("[seed] Families already exist – skipping.")

    if subfamilies_collection.count_documents({}) == 0:
        subfamilies_collection.insert_many(SUBFAMILIES)
        print(f"[seed] Inserted {len(SUBFAMILIES)} subfamilies.")
    else:
        print("[seed] Subfamilies already exist – skipping.")

    if campaigns_collection.count_documents({}) == 0:
        campaigns_collection.insert_many(CAMPAIGNS)
        print(f"[seed] Inserted {len(CAMPAIGNS)} campaigns.")    
    else:
        print("[seed] Campaigns already exist \u2013 skipping.")

    if products_collection.count_documents({}) == 0:
        products_collection.insert_many(PRODUCTS)
        print(f"[seed] Inserted {len(PRODUCTS)} products.")
    else:
        print("[seed] Products already exist – skipping.")
