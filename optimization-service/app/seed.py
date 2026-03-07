"""
Seed data for the optimization service.
Loaded once on startup -- skipped if data already exists (idempotent).

Containers use max_side/med_side/min_side ranges (not length/width/height)
because orientation is determined dynamically by the algorithm.
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
            "max_side": {"min": 20.0, "max": 35.0},
            "med_side": {"min": 15.0, "max": 30.0},
            "min_side": {"min": 10.0, "max": 25.0},
        },
        "wall_thickness_mm": 3.0,
        "inner_margin_cm": {"max_side": 0.5, "med_side": 0.5, "min_side": 0.5},
        "max_weight_kg": 10.0,
        "priority": 1,
        "active": True,
        "local_rules": [],
    },
    {
        "id": "c0000000-0000-0000-0000-000000000002",
        "name": "Caja-M",
        "description": "Caja media -- uso general",
        "dims_cm": {
            "max_side": {"min": 30.0, "max": 50.0},
            "med_side": {"min": 25.0, "max": 40.0},
            "min_side": {"min": 20.0, "max": 35.0},
        },
        "wall_thickness_mm": 3.0,
        "inner_margin_cm": {"max_side": 0.5, "med_side": 0.5, "min_side": 0.5},
        "max_weight_kg": 20.0,
        "priority": 2,
        "active": True,
        "local_rules": [],
    },
    {
        "id": "c0000000-0000-0000-0000-000000000003",
        "name": "Caja-L",
        "description": "Caja grande -- productos voluminosos o lotes grandes",
        "dims_cm": {
            "max_side": {"min": 45.0, "max": 70.0},
            "med_side": {"min": 35.0, "max": 55.0},
            "min_side": {"min": 30.0, "max": 50.0},
        },
        "wall_thickness_mm": 4.0,
        "inner_margin_cm": {"max_side": 0.8, "med_side": 0.8, "min_side": 0.8},
        "max_weight_kg": 35.0,
        "priority": 3,
        "active": True,
        "local_rules": [],
    },
]

# -- Seed global rules ---------------------------------------------------------
# Catalog of available constraint types. No filters here -- filters go in
# rule_assignments. Admin-only write access.

SEED_RULES = [
    {
        "id": "r0000000-0000-0000-0000-000000000001",
        "name": "Max 2 capas",
        "description": "El inner no puede apilarse mas de 2 capas dentro del contenedor",
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
        "description": "El inner debe ir en posicion vertical: lado mayor hacia arriba",
        "constraint": {
            "orientation_locked": True,
            "locked_axis": "max_side",
            "max_stack_layers": None,
        },
        "active": True,
    },
    {
        "id": "r0000000-0000-0000-0000-000000000003",
        "name": "Siempre horizontal",
        "description": "El inner debe ir tumbado: lado menor hacia arriba (posicion plana)",
        "constraint": {
            "orientation_locked": True,
            "locked_axis": "min_side",
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
        # Vasos (Vidrio) -- siempre vertical
        "id": "a0000000-0000-0000-0000-000000000001",
        "rule_id": "r0000000-0000-0000-0000-000000000002",
        "filter": {
            "family_ids": [],
            "subfamily_ids": ["b2c7f3e1-2d4c-5f9b-a08e-100000000007"],
        },
        "active": True,
    },
    {
        # Botellas (Vidrio) -- siempre vertical
        "id": "a0000000-0000-0000-0000-000000000002",
        "rule_id": "r0000000-0000-0000-0000-000000000002",
        "filter": {
            "family_ids": [],
            "subfamily_ids": ["b2c7f3e1-2d4c-5f9b-a08e-100000000008"],
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
