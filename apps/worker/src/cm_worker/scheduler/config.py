from cm_worker.celery_app import parse_cron
from cm_shared.settings.app import get_settings


def configured_sync_schedule():
    """Return the Celery schedule for the configured Confluence sync cron."""
    return parse_cron(get_settings().sync_cron)

