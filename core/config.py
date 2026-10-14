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

try:
    TOKEN_BOT: str = os.environ["BOT_TOKEN"]
except KeyError:
    raise RuntimeError("BOT_TOKEN is not set in environment variables")


try:
    DATABASE_URL_DOCKER: str = os.environ["DATABASE_URL_DOCKER"]
except KeyError:
    raise RuntimeError("DATABASE_URL_DOCKER is not set in environment variables")


try:
    REDIS_URL: str = os.environ["ANALYSIS_CACHE_REDIS"]
except KeyError:
    raise RuntimeError(" REDIS_URL is not set in environment variables")


try:
    ADMIN_ID: int = int(os.environ["ADMIN_ID"])
except KeyError:
    raise RuntimeError(" ADMIN_ID is not set in environment variables")


try:
    PROXI_API_KEY = os.environ["OPENAI_API_KEY"]
except KeyError:
    raise ValueError(
        "Critical error: OPENAI_API_KEY must be set in the environment variables."
    )

try:
    PROXI_BASE_URL = os.environ["OPENAI_BASE_URL"]
except KeyError:
    raise ValueError(
        "Critical error: OPENAI_API_KEY must be set in the environment variables."
    )

ENGINE_KWARGS = dict(echo=False, pool_pre_ping=True, pool_recycle=1800, pool_timeout=10)
