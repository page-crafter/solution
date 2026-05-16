from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from page_crafter.api.main import create_app
from page_crafter.api.routers.page_editor import (
    apply_proposal,
    create_manual_draft,
    proposal_base,
    restore_draft_version,
    update_draft,
)
from page_crafter.shared.models.confluence import ConfluencePage
from page_crafter.shared.models.page_editor import DraftVersion, PageEditRun, PageProposal
from page_crafter.shared.schemas.page_editor import CreateProposalRequest, UpdateDraftRequest


def test_page_editor_routes_are_canonical_without_legacy_paths() -> None:
    paths = {route.path for route in create_app().routes}

    assert "/api/editor/pages/{page_id}/proposals" in paths
    assert "/api/editor/proposals/{proposal_id}/apply" in paths
    assert all(not path.startswith("/api/pipeline") for path in paths)
    assert all("edit-proposals" not in path for path in paths)


class FakeSession:
    def __init__(self, proposal=None, run=None, active_run=None, versions=None) -> None:
        self.proposal = proposal
        self.run = run
        self.active_run = active_run
        self.versions = versions or []

    def get(self, _model, item_id):
        if _model is DraftVersion:
            return next((version for version in self.versions if version.id == item_id), None)
        if self.proposal and self.proposal.id == item_id:
            return self.proposal
        if self.run and self.run.id == item_id:
            return self.run
        return None

    def scalar(self, _statement):
        if "draft_versions" in str(_statement):
            return max(self.versions, key=lambda version: version.version_number, default=None)
        return self.active_run


class ManualDraftSession:
    def __init__(self, page) -> None:
        self.page = page
        self.added = []
        self.versions = []

    def get(self, _model, item_id):
        return self.page if item_id == self.page.id else None

    def add(self, item) -> None:
        if isinstance(item, PageEditRun) and not item.id:
            item.id = "run-manual"
        if isinstance(item, DraftVersion) and item.id is None:
            item.id = len(self.versions) + 1
            self.versions.append(item)
        self.added.append(item)

    def scalar(self, _statement):
        if "draft_versions" in str(_statement):
            return max(self.versions, key=lambda version: version.version_number, default=None)
        return None

    def execute(self, _statement) -> None:
        pass

    def flush(self) -> None:
        pass

    def refresh(self, _item) -> None:
        pass


class PageEditorRouteSession:
    def __init__(self, *, page, run, proposal=None, versions=None) -> None:
        self.page = page
        self.run = run
        self.proposal = proposal
        self.versions = versions or []
        self.added = []
        self.commits = 0

    def get(self, model, item_id):
        if model is ConfluencePage:
            return self.page if item_id == self.page.id else None
        if model is PageEditRun:
            return self.run if item_id == self.run.id else None
        if model is PageProposal:
            return self.proposal if self.proposal and item_id == self.proposal.id else None
        if model is DraftVersion:
            return next((version for version in self.versions if version.id == item_id), None)
        return None

    def add(self, item) -> None:
        if isinstance(item, DraftVersion):
            if item.id is None:
                item.id = len(self.versions) + 1
            self.versions.append(item)
        if isinstance(item, PageEditRun) and not item.id:
            item.id = "run-created"
            self.run = item
        self.added.append(item)

    def scalar(self, statement):
        if "draft_versions" in str(statement):
            run_versions = [version for version in self.versions if version.run_id == self.run.id]
            return max(run_versions, key=lambda version: version.version_number, default=None)
        return None

    def execute(self, _statement) -> None:
        pass

    def flush(self) -> None:
        pass

    def commit(self) -> None:
        self.commits += 1

    def refresh(self, _item) -> None:
        pass


def make_page_edit_run(markdown: str = "# Draft", **overrides) -> PageEditRun:
    values = {
        "id": "run-1",
        "page_id": 7,
        "instruction": "Update docs",
        "status": "preview_ready",
        "draft_status": "Preview ready",
        "preview_status": "ready",
        "source_version": 3,
        "markdown_draft": markdown,
        "generated_storage_xhtml": "<p>Draft</p>",
        "preview_html": "<p>Preview</p>",
        "diff_text": "diff",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    values.update(overrides)
    return PageEditRun(**values)


def make_proposal(markdown: str = "# Proposed draft", **overrides) -> PageProposal:
    values = {
        "id": "proposal-1",
        "page_id": 7,
        "run_id": "run-1",
        "instruction": "Update the setup",
        "base_markdown": "# Draft",
        "base_source": "draft",
        "status": "ready",
        "proposed_markdown": markdown,
        "diff_text": "diff",
        "summary": "Prepared an update.",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    values.update(overrides)
    return PageProposal(**values)


def make_version(markdown: str, **overrides) -> DraftVersion:
    values = {
        "id": 1,
        "run_id": "run-1",
        "version_number": 1,
        "markdown_draft": markdown,
        "change_source": "manual",
        "actor": "editor@example.com",
        "created_at": datetime.utcnow(),
    }
    values.update(overrides)
    return DraftVersion(**values)


def capture_enqueue(monkeypatch):
    queued = {}

    def fake_enqueue_task_for_job(_session, job, task_name, *task_args, **kwargs):
        queued["job_id"] = job.id
        queued["task_name"] = task_name
        queued["task_args"] = task_args
        queued["actor"] = kwargs["actor"]

    monkeypatch.setattr(
        "page_crafter.api.routers.page_editor.enqueue_task_for_job",
        fake_enqueue_task_for_job,
    )
    return queued


def test_proposal_can_chain_from_ready_proposal() -> None:
    page = SimpleNamespace(id=7, extracted_text="Original page", source_markdown="# Original page")
    base_proposal = SimpleNamespace(
        id="proposal-1",
        page_id=7,
        run_id="run-1",
        status="ready",
        proposed_markdown="# First chat edit",
    )

    run_id, base_markdown, base_source = proposal_base(
        FakeSession(base_proposal),
        page,
        CreateProposalRequest(
            message="Add another change",
            base_proposal_id="proposal-1",
        ),
    )

    assert run_id == "run-1"
    assert base_markdown == "# First chat edit"
    assert base_source == "proposal"


def test_proposal_rejects_unready_base_proposal() -> None:
    page = SimpleNamespace(id=7, extracted_text="Original page", source_markdown="# Original page")
    base_proposal = SimpleNamespace(
        id="proposal-1",
        page_id=7,
        run_id="run-1",
        status="generating",
        proposed_markdown=None,
    )

    with pytest.raises(HTTPException) as exc_info:
        proposal_base(
            FakeSession(base_proposal),
            page,
            CreateProposalRequest(
                message="Add another change",
                base_proposal_id="proposal-1",
            ),
        )

    assert exc_info.value.status_code == 409


def test_proposal_can_use_client_draft_as_base() -> None:
    page = SimpleNamespace(id=7, extracted_text="Original page", source_markdown="# Original page")
    run = SimpleNamespace(id="run-1", page_id=7, status="previewing")

    run_id, base_markdown, base_source = proposal_base(
        FakeSession(run=run),
        page,
        CreateProposalRequest(
            message="Add another change",
            base_run_id="run-1",
            base_markdown="# First applied edit",
        ),
    )

    assert run_id == "run-1"
    assert base_markdown == "# First applied edit"
    assert base_source == "draft"


def test_proposal_rejects_client_draft_for_another_page() -> None:
    page = SimpleNamespace(id=7, extracted_text="Original page", source_markdown="# Original page")
    run = SimpleNamespace(id="run-1", page_id=8, status="previewing")

    with pytest.raises(HTTPException) as exc_info:
        proposal_base(
            FakeSession(run=run),
            page,
            CreateProposalRequest(
                message="Add another change",
                base_run_id="run-1",
                base_markdown="# First applied edit",
            ),
        )

    assert exc_info.value.status_code == 409


def test_proposal_uses_source_markdown_for_page_base() -> None:
    page = SimpleNamespace(
        id=7,
        extracted_text="Original page text",
        source_markdown="# Original page",
    )

    run_id, base_markdown, base_source = proposal_base(
        FakeSession(),
        page,
        CreateProposalRequest(message="Add setup steps"),
    )

    assert run_id is None
    assert base_markdown == "# Original page"
    assert base_source == "page"


def test_create_manual_draft_queues_render_without_generation(monkeypatch) -> None:
    queued = capture_enqueue(monkeypatch)
    page = SimpleNamespace(id=7, version_number=3, deleted_at=None, draft_state="Published")
    session = ManualDraftSession(page)

    run = create_manual_draft(
        7,
        UpdateDraftRequest(markdown_draft="# Manual edit"),
        session,
        SimpleNamespace(email="editor@example.com"),
    )

    assert run.id == "run-manual"
    assert run.markdown_draft == "# Manual edit"
    assert run.status == "converting"
    assert run.preview_status == "rendering"
    assert page.draft_state == "Draft generated"
    assert [
        (version.version_number, version.change_source, version.markdown_draft)
        for version in session.versions
    ] == [(1, "manual", "# Manual edit")]
    assert queued == {
        "job_id": "run-manual",
        "task_name": "page_crafter.render_draft",
        "task_args": ("run-manual",),
        "actor": "editor@example.com",
    }


def test_update_draft_records_baseline_and_manual_versions(monkeypatch) -> None:
    queued = capture_enqueue(monkeypatch)
    page = SimpleNamespace(id=7, version_number=3, deleted_at=None, draft_state="Preview ready")
    run = make_page_edit_run("# Old draft")
    session = PageEditorRouteSession(page=page, run=run)

    updated = update_draft(
        "run-1",
        UpdateDraftRequest(markdown_draft="# New draft"),
        session,
        SimpleNamespace(email="editor@example.com"),
    )

    assert updated.markdown_draft == "# New draft"
    assert updated.generated_storage_xhtml is None
    assert updated.preview_html is None
    assert updated.diff_text is None
    assert page.draft_state == "Draft generated"
    assert [
        (version.version_number, version.change_source, version.markdown_draft)
        for version in session.versions
    ] == [
        (1, "baseline", "# Old draft"),
        (2, "manual", "# New draft"),
    ]
    assert queued["task_name"] == "page_crafter.render_draft"
    assert queued["task_args"] == ("run-1",)


def test_update_draft_skips_duplicate_latest_version(monkeypatch) -> None:
    capture_enqueue(monkeypatch)
    page = SimpleNamespace(id=7, version_number=3, deleted_at=None, draft_state="Preview ready")
    run = make_page_edit_run("# Draft")
    session = PageEditorRouteSession(
        page=page,
        run=run,
        versions=[make_version("# Draft")],
    )

    update_draft(
        "run-1",
        UpdateDraftRequest(markdown_draft="# Draft"),
        session,
        SimpleNamespace(email="editor@example.com"),
    )

    assert len(session.versions) == 1
    assert session.versions[0].markdown_draft == "# Draft"


def test_apply_proposal_records_proposal_version(monkeypatch) -> None:
    queued = capture_enqueue(monkeypatch)
    page = SimpleNamespace(id=7, version_number=3, deleted_at=None, draft_state="Preview ready")
    run = make_page_edit_run("# Old draft")
    proposal = make_proposal("# Proposed draft")
    session = PageEditorRouteSession(page=page, run=run, proposal=proposal)

    response = apply_proposal(
        "proposal-1",
        session,
        SimpleNamespace(email="editor@example.com"),
    )

    assert response.run.markdown_draft == "# Proposed draft"
    assert response.proposal.status == "applied"
    assert [
        (version.version_number, version.change_source, version.markdown_draft, version.proposal_id)
        for version in session.versions
    ] == [
        (1, "baseline", "# Old draft", None),
        (2, "proposal", "# Proposed draft", "proposal-1"),
    ]
    assert queued["task_name"] == "page_crafter.render_draft"


def test_restore_draft_version_records_restore_and_queues_render(monkeypatch) -> None:
    queued = capture_enqueue(monkeypatch)
    page = SimpleNamespace(id=7, version_number=3, deleted_at=None, draft_state="Preview ready")
    run = make_page_edit_run("# Current draft")
    restored_from = make_version("# Earlier draft")
    session = PageEditorRouteSession(page=page, run=run, versions=[restored_from])

    restored_run = restore_draft_version(
        "run-1",
        restored_from.id,
        session,
        SimpleNamespace(email="editor@example.com"),
    )

    assert restored_run.markdown_draft == "# Earlier draft"
    assert restored_run.status == "converting"
    assert page.draft_state == "Draft generated"
    assert session.versions[-1].change_source == "restore"
    assert session.versions[-1].restored_from_version_id == restored_from.id
    assert queued["task_name"] == "page_crafter.render_draft"


def test_restore_draft_version_rejects_version_from_another_run(monkeypatch) -> None:
    capture_enqueue(monkeypatch)
    page = SimpleNamespace(id=7, version_number=3, deleted_at=None, draft_state="Preview ready")
    run = make_page_edit_run("# Current draft")
    other_version = make_version("# Other draft", run_id="run-2")
    session = PageEditorRouteSession(page=page, run=run, versions=[other_version])

    with pytest.raises(HTTPException) as exc_info:
        restore_draft_version(
            "run-1",
            other_version.id,
            session,
            SimpleNamespace(email="editor@example.com"),
        )

    assert exc_info.value.status_code == 409
