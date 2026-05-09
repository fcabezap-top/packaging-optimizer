import os

MONGO_URL = os.getenv(
    "MONGO_URL",
    "mongodb://admin:admin123@mongo:27017"
)

DATABASE_NAME = "optimization_db"

SECRET_KEY = os.getenv("SECRET_KEY", "changeme-use-a-long-random-secret-in-production")
ALGORITHM = "HS256"

PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://product:8000")

# SMTP — notificaciones de rechazo de propuesta
SMTP_HOST     = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER     = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM     = os.getenv("SMTP_FROM", SMTP_USER)
NOTIFY_EMAIL  = os.getenv("NOTIFY_EMAIL", "optimizacionpackaging@gmail.com")
