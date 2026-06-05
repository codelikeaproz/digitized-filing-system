import os
from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parent.parent
# Django loads environment variables from backend/.env only.
load_dotenv(BACKEND_DIR / ".env")


if os.getenv("DB_ENGINE", "sqlite").strip().lower() == "mysql":
    try:
        import MySQLdb  # noqa: F401
    except ImportError:
        import pymysql

        pymysql.version_info = (2, 2, 1, "final", 0)
        pymysql.install_as_MySQLdb()
