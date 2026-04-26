import os
from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR.parent / ".env")
load_dotenv(BACKEND_DIR / ".env", override=True)


if os.getenv("DB_ENGINE", "sqlite").strip().lower() == "mysql":
    try:
        import MySQLdb  # noqa: F401
    except ImportError:
        import pymysql

        pymysql.version_info = (2, 2, 1, "final", 0)
        pymysql.install_as_MySQLdb()
