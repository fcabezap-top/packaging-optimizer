import os

MONGO_URL = os.getenv(
    "MONGO_URL",
    "mongodb://admin:admin123@mongo:27017"
)

DATABASE_NAME = "users_db"

SECRET_KEY = os.getenv("SECRET_KEY", "changeme-use-a-long-random-secret-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 30  # 30 días — sesión permanente hasta logout explícito

# SMTP — configurar con variables de entorno en producción
SMTP_HOST     = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER     = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM     = os.getenv("SMTP_FROM", SMTP_USER)

# URL base del frontend — para componer el enlace de reset
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# Expiración del token de reset (minutos)
RESET_TOKEN_EXPIRE_MINUTES = 60
