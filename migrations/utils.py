from alembic.config import Config
from loguru import logger
from sqlalchemy.exc import SQLAlchemyError

from alembic import command
from core.config import ALEMBIC_INI, ALEMBIC_SCRIPTS, SYNC_URL_FOR_ALEMBIC


def run_upgrade():
    alembic_cfg = Config(str(ALEMBIC_INI))
    alembic_cfg.set_main_option("sqlalchemy.url", str(SYNC_URL_FOR_ALEMBIC))  # new
    alembic_cfg.set_main_option("script_location", str(ALEMBIC_SCRIPTS))
    try:
        command.upgrade(alembic_cfg, "head")
        logger.info("Migrations applied successfully")
    except SQLAlchemyError as e:
        logger.error("Error running migrations: {}", e)
