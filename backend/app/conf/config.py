import os


def _as_bool(value, default=False):
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    WTF_CSRF_ENABLED = _as_bool(os.getenv("WTF_CSRF_ENABLED"), default=True)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'instance', 'app.db'))}",
    )

    DEBUG = _as_bool(os.getenv("FLASK_DEBUG"), default=False)
    SQL_KIT_ROOT = os.getenv(
        "SQL_KIT_ROOT",
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "sql_kit_data")),
    )

    REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
    REDIS_ENABLED = _as_bool(os.getenv("REDIS_ENABLED"), default=False)
    REDIS_DECODE_RESPONSES = False

    FPP_PLATFORM_DB_HOST = os.getenv("FPP_PLATFORM_DB_HOST", "8.134.37.199")
    FPP_PLATFORM_DB_PORT = int(os.getenv("FPP_PLATFORM_DB_PORT", "6033"))
    FPP_PLATFORM_DB_USER = os.getenv("FPP_PLATFORM_DB_USER", "root")
    FPP_PLATFORM_DB_PASSWORD = os.getenv("FPP_PLATFORM_DB_PASSWORD", "Xzpp_Mysql_2024_test!")
    FPP_PLATFORM_DB_NAME = os.getenv("FPP_PLATFORM_DB_NAME", "fpp_platform")
