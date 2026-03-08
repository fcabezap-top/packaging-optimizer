from pymongo import MongoClient
from .config import MONGO_URL, DATABASE_NAME

client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=3000)
db = client[DATABASE_NAME]

users_collection = db["users"]
reset_tokens_collection = db["password_reset_tokens"]


def ensure_indexes() -> None:
    """Create indexes. Called from lifespan, not at import time."""
    # TTL index: MongoDB eliminates expired tokens automatically
    reset_tokens_collection.create_index("expires_at", expireAfterSeconds=0)
