import os

MONGO_URL = os.getenv(
    "MONGO_URL",
    "mongodb://admin:admin123@mongo:27017"
)

DATABASE_NAME = "users_db"

SECRET_KEY = os.getenv("SECRET_KEY", "changeme-use-a-long-random-secret-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
