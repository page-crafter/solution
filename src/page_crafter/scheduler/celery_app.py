from celery import Celery
from celery.schedules import crontab

from page_crafter.shared.settings.app import get_settings


def parse_cron(value: str) -> crontab:
    """Convert a five-field cron expression into a Celery crontab schedule."""
    minute, hour, day_of_month, month_of_year, day_of_week = value.split()
    return crontab(
        minute=minute,
        hour=hour,
        day_of_month=day_of_month,
        month_of_year=month_of_year,
        day_of_week=day_of_week,
    )


def create_celery_app() -> Celery:
    """Create the Celery Beat app with scheduled full-space sync configured."""
    settings = get_settings()
    app = Celery("page_crafter.scheduler", broker=settings.redis_url, backend=settings.redis_url)
    app.conf.beat_schedule = {
        "scheduled-confluence-sync": {
            "task": "page_crafter.scheduled_sync",
            "schedule": parse_cron(settings.sync_cron),
        }
    }
    return app


celery_app = create_celery_app()
