from services.scheduled_reports import send_weekly_stats, send_monthly_stats
from services.worker_loop import run_in_worker_loop
from services.celery_app import app
from loguru import logger

celery_app = app

@celery_app.task(name="financial_bot.vehicle_reports.send_weekly_stats_task", bind=True, max_retries=2)
def send_weekly_stats_task(self):
    try:
        run_in_worker_loop(
            send_weekly_stats()
        )
        logger.info("Weekly stats mailing completed successfully.")
    except Exception:
        logger.exception("Critical error during weekly stats mailing.")
        raise


@celery_app.task(name="financial_bot.vehicle_reports.send_monthly_stats_task", bind=True, max_retries=2)
def send_monthly_stats_task(self):
    try:
        run_in_worker_loop(
            send_monthly_stats()
        )
        logger.info("Monthly stats mailing completed successfully.")
    except Exception:
        logger.exception("Critical error during monthly stats mailing.")
        raise