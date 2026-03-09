"""
Seed data for the optimization service.
Loaded once on startup -- skipped if data already exists (idempotent).

Container dimensions use length/height/width (L, H, W) ranges.
Global rules are fixed by design; only admin can create/modify them.
"""

import time
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from .database import client, containers_collection, rules_collection, rule_assignments_collection

# -- Seed containers -----------------------------------------------------------
# Three containers ordered by priority (try smallest first to minimise air).
# Dimensions are interior ranges in cm. wall_thickness_mm is cardboard wall.

SEED_CONTAINERS = [
    {
        "id": "c0000000-0000-0000-0000-000000000001",
        "name": "Caja-S",
        "description": "Caja pequena -- alta densidad, menor volumen de aire",
        "dims_cm": {
            "length": {"min": 20.0, "max": 35.0},
            "height": {"min": 15.0, "max": 30.0},
            "width":  {"min": 10.0, "max": 25.0},
        },
        "wall_thickness_mm": 3.0,
        "inner_margin_cm": {"length": 0.5, "height": 0.5, "width": 0.5},
        "max_weight_kg": 10.0,
        "max_air_pct": 5.0,
        "priority": 3,
        "active": True,
        "local_rules": [
            {"name": "air_max", "value": 5.0},
        ],
    },
    {
        "id": "c0000000-0000-0000-0000-000000000002",
        "name": "Caja-M",
        "description": "Caja media -- uso general",
        "dims_cm": {
            "length": {"min": 30.0, "max": 50.0},
            "height": {"min": 32.0, "max": 32.0},
            "width":  {"min": 20.0, "max": 35.0},
        },
        "wall_thickness_mm": 3.0,
        "inner_margin_cm": {"length": 0.5, "height": 0.5, "width": 0.5},
        "max_weight_kg": 20.0,
        "max_air_pct": 10.0,
        "priority": 2,
        "active": True,
        "local_rules": [
            {"name": "air_max", "value": 10.0},
        ],
    },
    {
        "id": "c0000000-0000-0000-0000-000000000003",
        "name": "Caja-L",
        "description": "Caja grande -- productos voluminosos o lotes grandes",
        "dims_cm": {
            "length": {"min": 45.0, "max": 70.0},
            "height": {"min": 35.0, "max": 55.0},
            "width":  {"min": 30.0, "max": 50.0},
        },
        "wall_thickness_mm": 4.0,
        "inner_margin_cm": {"length": 0.8, "height": 0.8, "width": 0.8},
        "max_weight_kg": 35.0,
        "max_air_pct": 5.0,
        "priority": 1,
        "active": True,
        "local_rules": [
            {"name": "air_max", "value": 5.0},
        ],
    },
    {
        "id": "c0000000-0000-0000-0000-000000000004",
        "name": "Caja-XL",
        "description": "Caja extra grande -- dimensiones fijas, sin rango",
        "dims_cm": {
            "length": {"min": 80.0, "max": 80.0},
            "height": {"min": 60.0, "max": 60.0},
            "width":  {"min": 55.0, "max": 55.0},
        },
        "wall_thickness_mm": 5.0,
        "inner_margin_cm": {"length": 1.0, "height": 1.0, "width": 1.0},
        "max_weight_kg": 50.0,
        "max_air_pct": 5.0,
        "priority": 4,
        "active": True,
        "local_rules": [
            {"name": "air_max", "value": 5.0},
        ],
    },
]

# -- Seed global rules ---------------------------------------------------------
# Catalog of available constraint types. No filters here -- filters go in
# rule_assignments. Admin-only write access.

SEED_RULES = [
    {
        "id": "r0000000-0000-0000-0000-000000000001",
        "name": "Max 2 capas",
        "description": "La caja interior no puede apilarse mas de 2 capas dentro del contenedor",
        "constraint": {
            "orientation_locked": False,
            "locked_axis": None,
            "max_stack_layers": 2,
        },
        "active": True,
    },
    {
        "id": "r0000000-0000-0000-0000-000000000002",
        "name": "Siempre vertical",
        "description": "La caja interior debe ir en posicion vertical: lado mayor hacia arriba",
        "constraint": {
            "orientation_locked": True,
            "locked_axis": "height",
            "max_stack_layers": None,
        },
        "active": True,
    },
    {
        "id": "r0000000-0000-0000-0000-000000000003",
        "name": "Siempre horizontal",
        "description": "La caja interior debe ir tumbada: lado menor hacia arriba (posicion plana)",
        "constraint": {
            "orientation_locked": True,
            "locked_axis": "width",
            "max_stack_layers": None,
        },
        "active": True,
    },
]
# -- Seed rule assignments ---------------------------------------------------------
# Concrete assignments: which rule applies to which subfamily.
# IDs reference products seeded in product-service.
#   Vidrio / Vasos    -> b2c7f3e1-2d4c-5f9b-a08e-100000000007
#   Vidrio / Botellas -> b2c7f3e1-2d4c-5f9b-a08e-100000000008

SEED_RULE_ASSIGNMENTS = [
    {
        # Vidrio / Vasos + Botellas -- siempre vertical
        # subfamily_ids non-empty: rule applies only to these subfamilies within Vidrio
        "id": "a0000000-0000-0000-0000-000000000001",
        "rule_id": "r0000000-0000-0000-0000-000000000002",
        "filter": {
            "family_id": "a1f6e2d0-1c3b-4e8a-9f7d-000000000003",  # Vidrio
            "subfamily_ids": [
                "b2c7f3e1-2d4c-5f9b-a08e-100000000007",  # Vasos
                "b2c7f3e1-2d4c-5f9b-a08e-100000000008",  # Botellas
            ],
        },
        "active": True,
    },
    {
        # Vidrio (toda la familia) -- max 2 capas
        # subfamily_ids empty: rule applies to the whole Vidrio family
        "id": "a0000000-0000-0000-0000-000000000002",
        "rule_id": "r0000000-0000-0000-0000-000000000001",
        "filter": {
            "family_id": "a1f6e2d0-1c3b-4e8a-9f7d-000000000003",  # Vidrio
            "subfamily_ids": [],
        },
        "active": True,
    },
    {
        # Electrónica / Tablets -- siempre horizontal (se empacan planas)
        "id": "a0000000-0000-0000-0000-000000000003",
        "rule_id": "r0000000-0000-0000-0000-000000000003",
        "filter": {
            "family_id": "a1f6e2d0-1c3b-4e8a-9f7d-000000000005",  # Electrónica
            "subfamily_ids": [
                "b2c7f3e1-2d4c-5f9b-a08e-100000000014",  # Tablets
            ],
        },
        "active": True,
    },
]

def _wait_for_mongo(retries: int = 10, delay: float = 2.0) -> None:
    for attempt in range(1, retries + 1):
        try:
            client.admin.command("ping")
            return
        except (ConnectionFailure, ServerSelectionTimeoutError) as exc:
            print(f"[seed] MongoDB not ready (attempt {attempt}/{retries}): {exc}")
            if attempt == retries:
                raise
            time.sleep(delay)


def run_seed() -> None:
    _wait_for_mongo()

    if containers_collection.count_documents({}) == 0:
        containers_collection.insert_many(SEED_CONTAINERS)
        print(f"[seed] Inserted {len(SEED_CONTAINERS)} containers.")
    else:
        print("[seed] Containers already exist -- skipping.")

    if rules_collection.count_documents({}) == 0:
        rules_collection.insert_many(SEED_RULES)
        print(f"[seed] Inserted {len(SEED_RULES)} global rules.")
    else:
        print("[seed] Rules already exist -- skipping.")

    if rule_assignments_collection.count_documents({}) == 0:
        rule_assignments_collection.insert_many(SEED_RULE_ASSIGNMENTS)
        print(f"[seed] Inserted {len(SEED_RULE_ASSIGNMENTS)} rule assignments.")
    else:
        print("[seed] Rule assignments already exist -- skipping.")
