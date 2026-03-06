import os
from pymongo import MongoClient

MONGO_URL = os.getenv("MONGO_URL", "mongodb://admin:admin123@mongo:27017/?authSource=admin")

client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=3000)
db = client["products_db"]

families_collection = db["families"]
subfamilies_collection = db["subfamilies"]
campaigns_collection = db["campaigns"]
products_collection = db["products"]
