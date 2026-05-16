from celery import Celery

from page_crafter.shared.settings.app import get_settings


def create_queue_app() -> Celery:
    """Create the API-side Celery app used only to publish and revoke tasks."""
    settings = get_settings()
    return Celery("page_crafter.api.queue", broker=settings.redis_url, backend=settings.redis_url)


queue_app = create_queue_app()
