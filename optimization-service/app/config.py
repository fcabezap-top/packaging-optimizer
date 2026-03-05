import os

MONGO_URL = os.getenv(
    "MONGO_URL",
    "mongodb://admin:admin123@mongo:27017"
)

DATABASE_NAME = "optimization_db"

SECRET_KEY = os.getenv("SECRET_KEY", "changeme-use-a-long-random-secret-in-production")
ALGORITHM = "HS256"
