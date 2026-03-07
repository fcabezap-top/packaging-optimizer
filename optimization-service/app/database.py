from pymongo import MongoClient
from .config import MONGO_URL, DATABASE_NAME

client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=3000)
db = client[DATABASE_NAME]

proposals_collection = db["proposals"]
containers_collection = db["containers"]
rules_collection = db["rules"]
rule_assignments_collection = db["rule_assignments"]
