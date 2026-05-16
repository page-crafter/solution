from celery import Celery

from page_crafter.shared.settings.app import get_settings


def create_celery_app() -> Celery:
    """Create the Celery worker and register executable task modules."""
    settings = get_settings()
    app = Celery("page_crafter.worker", broker=settings.redis_url, backend=settings.redis_url)
    app.conf.imports = (
        "page_crafter.worker.tasks.sync_tasks",
        "page_crafter.worker.tasks.page_editor_tasks",
        "page_crafter.worker.tasks.chat_tasks",
    )
    return app


celery_app = create_celery_app()
celery_app.loader.import_default_modules()
