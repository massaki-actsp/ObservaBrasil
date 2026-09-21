import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def env_value(name, default=None):
    value = os.getenv(name)
    return value if value not in (None, "") else default


class Config:
    SECRET_KEY = env_value("SECRET_KEY", "dev-change-me")
    SQLALCHEMY_DATABASE_URI = env_value(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'instance' / 'observa_brasil.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_SORT_KEYS = False
    PORT = int(env_value("PORT", "5000"))
    INPE_QUEIMADAS_URL = env_value(
        "INPE_QUEIMADAS_URL",
        "https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/diario/Brasil/",
    )
    BDC_STAC_URL = env_value("BDC_STAC_URL", "https://data.inpe.br/bdc/stac/v1/")
    BDC_COLLECTION = env_value("BDC_COLLECTION", "S2-16D-2")
    REQUEST_TIMEOUT = float(env_value("REQUEST_TIMEOUT", "20"))
    CACHE_DIR = Path(env_value("CACHE_DIR", BASE_DIR / "instance" / "cache"))
    GEOJSON_MAX_BYTES = int(env_value("GEOJSON_MAX_BYTES", str(2 * 1024 * 1024)))
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = env_value("SESSION_COOKIE_SECURE", "0") == "1"
    WTF_CSRF_ENABLED = env_value("WTF_CSRF_ENABLED", "1") == "1"
    SMTP_HOST = env_value("SMTP_HOST")
    SMTP_PORT = int(env_value("SMTP_PORT", "587"))
    SMTP_TLS = env_value("SMTP_TLS", "1") == "1"
    SMTP_USER = env_value("SMTP_USER")
    SMTP_PASSWORD = env_value("SMTP_PASSWORD")
    SMTP_FROM = env_value("SMTP_FROM")
    TELEGRAM_BOT_TOKEN = env_value("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = env_value("TELEGRAM_CHAT_ID")
    ALERTA_WEBHOOK_URL = env_value("ALERTA_WEBHOOK_URL")


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


class ProductionConfig(Config):
    DEBUG = False


def get_config():
    env = os.getenv("FLASK_ENV", "development").lower()
    if env == "production":
        return ProductionConfig
    if env == "testing":
        return TestingConfig
    return DevelopmentConfig
