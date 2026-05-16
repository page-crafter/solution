from cm_beat.celery_app import celery_app


def test_scheduled_sync_is_configured_for_worker_task() -> None:
    schedule = celery_app.conf.beat_schedule["scheduled-confluence-sync"]

    assert schedule["task"] == "cm_worker.scheduled_sync"
    assert "schedule" in schedule
