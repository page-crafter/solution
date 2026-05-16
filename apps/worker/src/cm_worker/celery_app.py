from celery import Celery
from cm_shared.settings.app import get_settings


def create_celery_app() -> Celery:
    """Create the Celery worker and register executable task modules."""
    settings = get_settings()
    app = Celery("cm_worker", broker=settings.redis_url, backend=settings.redis_url)
    app.conf.imports = (
        "cm_worker.tasks.sync_tasks",
        "cm_worker.tasks.page_editor_tasks",
        "cm_worker.tasks.chat_tasks",
    )
    return app


celery_app = create_celery_app()
celery_app.loader.import_default_modules()
