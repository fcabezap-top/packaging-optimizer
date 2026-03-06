"""
Seed data for the users service.
Loaded once on startup – skipped if data already exists (idempotent).
"""

import time
from uuid import uuid4

from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from .database import client, users_collection
from .security import hash_password

SEED_USERS = [
    {
        "id": "d4e5f6a7-b8c9-4d0e-a1f2-000000000001",
        "username": "manufacturer01",
        "email": "manufacturer01@packopt.com",
        "first_name": "Ana",
        "last_name": "García",
        "role": "manufacturer",
        "password": hash_password("Manufacturer1!"),
    },
    {
        "id": "d4e5f6a7-b8c9-4d0e-a1f2-000000000002",
        "username": "manufacturer02",
        "email": "manufacturer02@packopt.com",
        "first_name": "Miguel",
        "last_name": "Torres",
        "role": "manufacturer",
        "password": hash_password("Manufacturer2!"),
    },
    {
        "id": "d4e5f6a7-b8c9-4d0e-a1f2-000000000003",
        "username": "reviewer01",
        "email": "reviewer01@packopt.com",
        "first_name": "Carlos",
        "last_name": "López",
        "role": "reviewer",
        "password": hash_password("Reviewer1!"),
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
    if users_collection.count_documents({}) == 0:
        users_collection.insert_many(SEED_USERS)
        print(f"[seed] Inserted {len(SEED_USERS)} users.")
    else:
        print("[seed] Users already exist – skipping.")
