from cm_worker.celery_app import celery_app


def test_page_editor_proposal_task_is_registered_on_app_import() -> None:
    """The worker must know the task name emitted by the API page editor router."""
    assert "cm_worker.propose_markdown_update" in celery_app.tasks
