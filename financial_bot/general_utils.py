from datetime import datetime, time, timezone as dt_timezone
from zoneinfo import ZoneInfo
from loguru import logger

def get_today_boundaries_utc(user_timezone: str = "UTC") -> tuple[datetime, datetime]:
    """Возвращает начало и конец 'сегодня' в UTC, вычисленные относительно
    часового пояса пользователя. Если пояс некорректен — fallback на UTC."""
    try:
        tz = ZoneInfo(user_timezone)
    except Exception:
        logger.warning("Invalid timezone '{tz}', falling back to UTC", tz=user_timezone)
        tz = dt_timezone.utc

    now_local = datetime.now(tz)
    today_start_local = datetime.combine(now_local.date(), time.min, tzinfo=tz)
    today_end_local = datetime.combine(now_local.date(), time.max, tzinfo=tz)

    return today_start_local.astimezone(dt_timezone.utc), today_end_local.astimezone(dt_timezone.utc)



POPULAR_TIMEZONES = [
    ("Europe/Moscow", "🇷🇺 Москва (UTC+3)"),
    ("Europe/Kaliningrad", "🇷🇺 Калининград (UTC+2)"),
    ("Asia/Yekaterinburg", "🇷🇺 Екатеринбург (UTC+5)"),
    ("Asia/Novosibirsk", "🇷🇺 Новосибирск (UTC+7)"),
    ("Asia/Vladivostok", "🇷🇺 Владивосток (UTC+10)"),
    ("Europe/London", "🇬🇧 London (UTC+0/+1)"),
    ("Europe/Berlin", "🇩🇪 Berlin (UTC+1/+2)"),
    ("America/New_York", "🇺🇸 New York (UTC-5/-4)"),
    ("America/Los_Angeles", "🇺🇸 Los Angeles (UTC-8/-7)"),
    ("Asia/Dubai", "🇦🇪 Dubai (UTC+4)"),
    ("Asia/Almaty", "🇰🇿 Алматы (UTC+5)"),
]