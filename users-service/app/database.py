from pymongo import MongoClient
from .config import MONGO_URL, DATABASE_NAME

client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=3000)
db = client[DATABASE_NAME]

users_collection = db["users"]
