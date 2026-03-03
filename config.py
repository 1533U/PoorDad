"""App config from environment. Load .env so SECRET_KEY, DATABASE_URL, SQL_ECHO can be set there."""
import os

from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "change-me-before-deploying")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///poordad.db")
SQL_ECHO = os.getenv("SQL_ECHO", "false").lower() in ("1", "true", "yes")
