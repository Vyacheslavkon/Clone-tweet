import os
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
BASE_DIR = CURRENT_FILE.parent.parent
ROOT_DIR = BASE_DIR.parent

STATIC_DIR = BASE_DIR / "static"
MEDIA_DIR = BASE_DIR / "media"
JS_DIR = STATIC_DIR / "js"
CSS_DIR = STATIC_DIR / "css"


ALEMBIC_INI = BASE_DIR / "alembic.ini"
db_url = os.getenv("DATABASE_URL_DOCKER")
if db_url:
    SYNC_URL_FOR_ALEMBIC = db_url.replace(
        "postgresql+asyncpg://", "postgresql://"
    )  # new
else:
    "".replace("postgresql+asyncpg://", "postgresql://")  # new

ALEMBIC_SCRIPTS = BASE_DIR / "migrations"

TOKEN_BOT = os.getenv("BOT_TOKEN")
