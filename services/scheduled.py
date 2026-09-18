from apscheduler.schedulers.asyncio import AsyncIOScheduler

from financial_bot.tasks.vehicle_reports import send_weekly_stats_task, send_monthly_stats_task


def setup_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")

    scheduler.add_job(
        send_weekly_stats_task.delay,
        "cron", day_of_week=6, hour=16, minute=1,
    )
    scheduler.add_job(
        send_monthly_stats_task.delay,
        "cron", day=1, hour=11, minute=1,
    )
    return scheduler


