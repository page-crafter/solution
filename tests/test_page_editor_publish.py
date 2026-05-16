from types import SimpleNamespace

from page_crafter.worker.tasks import page_editor_tasks


class FakeSession:
    def __init__(self) -> None:
        self.commit_count = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def commit(self) -> None:
        self.commit_count += 1


def test_publish_page_submits_published_page_to_lightrag(monkeypatch) -> None:
    """A successful page editor publish refreshes the matching LightRAG document."""
    session = FakeSession()
    run = SimpleNamespace(
        id="run-1",
        status="preview_ready",
        draft_status="Preview ready",
        error_message=None,
        updated_at=None,
    )
    page = SimpleNamespace(
        id=7,
        confluence_id="42",
        space_key="DOC",
        title="Changed page",
        extracted_text="Old text",
        draft_state="Preview ready",
    )
    events: list[tuple[str, str]] = []
    finished_tasks: list[dict[str, str]] = []
    synced_pages = []
    clear_existing_values = []

    def fake_publish(_session, published_run, published_page) -> None:
        published_run.status = "published"
        published_run.draft_status = "Published"
        published_page.extracted_text = "New text for LightRAG"
        published_page.draft_state = "Published"

    def fake_sync(pages, *, clear_existing):
        synced_pages.extend(pages)
        clear_existing_values.append(clear_existing)
        return SimpleNamespace(submitted_count=1, skipped_count=0, track_ids=("track-1",))

    monkeypatch.setattr(page_editor_tasks, "SessionLocal", lambda: session)
    monkeypatch.setattr(
        page_editor_tasks,
        "get_run_and_page",
        lambda _session, _run_id: (run, page),
    )
    monkeypatch.setattr(page_editor_tasks, "publish_generated_page", fake_publish)
    monkeypatch.setattr(page_editor_tasks, "sync_pages_to_lightrag", fake_sync)
    monkeypatch.setattr(page_editor_tasks, "mark_task_running", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        page_editor_tasks,
        "add_event",
        lambda _session, _job_id, message, level="info": events.append((level, message)),
    )
    monkeypatch.setattr(
        page_editor_tasks,
        "mark_task_finished",
        lambda *args, **kwargs: finished_tasks.append(kwargs),
    )

    page_editor_tasks.publish_page.run("run-1")

    assert run.status == "published"
    assert run.error_message is None
    assert synced_pages == [page]
    assert clear_existing_values == [False]
    assert page.extracted_text == "New text for LightRAG"
    assert any(message == "Submitting published page to LightRAG" for _level, message in events)
    assert finished_tasks[-1]["status"] == "completed"
    assert "submitted 1 LightRAG document" in finished_tasks[-1]["message"]


def test_publish_page_keeps_published_status_when_lightrag_sync_fails(monkeypatch) -> None:
    """A post-publish LightRAG failure must not make the Confluence publish look blocked."""
    session = FakeSession()
    run = SimpleNamespace(
        id="run-2",
        status="preview_ready",
        draft_status="Preview ready",
        error_message=None,
        updated_at=None,
    )
    page = SimpleNamespace(
        id=8,
        confluence_id="84",
        space_key="DOC",
        title="Changed page",
        extracted_text="Old text",
        draft_state="Preview ready",
    )
    events: list[tuple[str, str]] = []
    finished_tasks: list[dict[str, str]] = []

    def fake_publish(_session, published_run, published_page) -> None:
        published_run.status = "published"
        published_run.draft_status = "Published"
        published_page.draft_state = "Published"

    def fake_sync(_pages, *, clear_existing) -> None:
        raise RuntimeError("pipeline is busy")

    monkeypatch.setattr(page_editor_tasks, "SessionLocal", lambda: session)
    monkeypatch.setattr(
        page_editor_tasks,
        "get_run_and_page",
        lambda _session, _run_id: (run, page),
    )
    monkeypatch.setattr(page_editor_tasks, "publish_generated_page", fake_publish)
    monkeypatch.setattr(page_editor_tasks, "sync_pages_to_lightrag", fake_sync)
    monkeypatch.setattr(page_editor_tasks, "mark_task_running", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        page_editor_tasks,
        "add_event",
        lambda _session, _job_id, message, level="info": events.append((level, message)),
    )
    monkeypatch.setattr(
        page_editor_tasks,
        "mark_task_finished",
        lambda *args, **kwargs: finished_tasks.append(kwargs),
    )

    page_editor_tasks.publish_page.run("run-2")

    assert run.status == "published"
    assert page.draft_state == "Published"
    assert run.error_message == "Published page, but LightRAG sync failed: pipeline is busy"
    assert ("error", run.error_message) in events
    assert finished_tasks[-1]["status"] == "failed"
