from pymongo import MongoClient
from .config import MONGO_URL, DATABASE_NAME

client = MongoClient(MONGO_URL)
db = client[DATABASE_NAME]

proposals_collection = db["proposals"]
