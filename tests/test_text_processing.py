from types import SimpleNamespace

import pytest

from page_crafter.shared.confluence.move_validation import (
    PageMoveOutsideSpaceError,
    ensure_move_stays_in_space,
)
from page_crafter.shared.confluence.storage_markdown import (
    PRESERVED_STORAGE_MARKER_RE,
    build_preserved_storage_map,
    storage_xhtml_to_markdown,
)
from page_crafter.shared.settings.app import get_settings
from page_crafter.worker.confluence.client import ConfluenceClient
from page_crafter.worker.confluence.preview import preview_has_rendered_content, storage_for_preview
from page_crafter.worker.extract.xhtml_to_text import extract_text_from_storage
from page_crafter.worker.page_editor.convert_markdown import convert_markdown_to_storage
from page_crafter.worker.page_editor.diffing import (
    build_storage_diff,
    format_storage_xhtml_for_diff,
)
from page_crafter.worker.sync.fetch_pages import page_parent_id, page_sort_order


def test_extract_text_from_storage_keeps_macro_hint() -> None:
    """Storage XHTML extraction keeps useful macro context for RAG."""
    text = extract_text_from_storage('<p>Hello</p><ac:structured-macro ac:name="toc" />')

    assert "Hello" in text
    assert "Confluence macro: toc" in text


def test_storage_xhtml_to_markdown_converts_common_blocks() -> None:
    """Storage XHTML is converted into editable Markdown instead of flat text."""
    markdown = storage_xhtml_to_markdown(
        '<h1>Install</h1>'
        '<p>Hello <strong>world</strong> and <em>team</em>.</p>'
        '<ul><li>One</li><li>Two <a href="https://example.com">link</a></li></ul>'
        '<blockquote><p>Note</p></blockquote>'
        '<hr />'
    )

    assert markdown == (
        "# Install\n\n"
        "Hello **world** and *team*.\n\n"
        "- One\n"
        "- Two [link](https://example.com)\n\n"
        "> Note\n\n"
        "---"
    )


def test_storage_xhtml_to_markdown_converts_tables() -> None:
    """Storage XHTML tables become GitHub-flavored Markdown tables."""
    markdown = storage_xhtml_to_markdown(
        "<table><tbody>"
        "<tr><th>A</th><th>B</th></tr>"
        "<tr><td>1</td><td>2</td></tr>"
        "</tbody></table>"
    )

    assert markdown == "| A | B |\n| --- | --- |\n| 1 | 2 |"


def test_storage_xhtml_to_markdown_preserves_images_as_markers() -> None:
    """Confluence images become opaque markers instead of lossy filenames."""
    storage = (
        '<p>Diagram</p><ac:image><ri:attachment ri:filename="diagram.png">'
        "</ri:attachment></ac:image>"
    )

    markdown = storage_xhtml_to_markdown(storage)
    marker = PRESERVED_STORAGE_MARKER_RE.search(markdown)
    preserved = build_preserved_storage_map(storage)

    assert marker
    assert markdown == f"Diagram\n\n{marker.group(0)}"
    assert preserved[marker.group(0)] == (
        '<ac:image><ri:attachment ri:filename="diagram.png"></ri:attachment></ac:image>'
    )
    assert "diagram.png" not in markdown


def test_storage_xhtml_to_markdown_preserves_custom_macro_with_body() -> None:
    """Custom macros keep their original Storage XHTML behind a stable marker."""
    storage = (
        '<ac:structured-macro ac:name="panel">'
        '<ac:parameter ac:name="title">Internal title</ac:parameter>'
        "<ac:rich-text-body><p>Keep <strong>this</strong></p></ac:rich-text-body>"
        "</ac:structured-macro>"
    )

    markdown = storage_xhtml_to_markdown(storage)
    preserved = build_preserved_storage_map(storage)

    assert PRESERVED_STORAGE_MARKER_RE.fullmatch(markdown)
    assert preserved[markdown] == storage
    assert "Keep **this**" not in markdown


def test_storage_xhtml_to_markdown_preserves_self_closing_custom_macro() -> None:
    """Self-closing custom macros are preserved as opaque markers."""
    storage = '<ac:structured-macro ac:name="toc"></ac:structured-macro>'

    markdown = storage_xhtml_to_markdown(storage)
    preserved = build_preserved_storage_map(storage)

    assert PRESERVED_STORAGE_MARKER_RE.fullmatch(markdown)
    assert preserved[markdown] == storage


def test_storage_xhtml_to_markdown_renders_code_macro_as_markdown() -> None:
    """Confluence code macros become editable fenced Markdown blocks."""
    storage = (
        '<ac:structured-macro ac:name="code">'
        '<ac:parameter ac:name="language">bash</ac:parameter>'
        "<ac:plain-text-body>kubectl get pods</ac:plain-text-body>"
        "</ac:structured-macro>"
    )

    markdown = storage_xhtml_to_markdown(storage)
    preserved = build_preserved_storage_map(storage)

    assert markdown == "```bash\nkubectl get pods\n```"
    assert preserved == {}


def test_convert_markdown_to_storage_uses_md2conf(monkeypatch) -> None:
    """Markdown conversion emits Confluence Storage XHTML, not escaped Markdown."""
    monkeypatch.setenv("CONFLUENCE_BASE_URL", "http://confluence:8090")
    monkeypatch.setenv("CONFLUENCE_SPACE_KEY", "DEV")
    get_settings.cache_clear()
    try:
        storage = convert_markdown_to_storage(
            "# Title\n\nHello **world**\n\n- one\n- two\n\n| A | B |\n|---|---|\n| 1 | 2 |\n"
        )
    finally:
        get_settings.cache_clear()

    assert "<h1>Title</h1>" in storage
    assert "<strong>world</strong>" in storage
    assert "<ul>" in storage
    assert "<table" in storage
    assert "# Title" not in storage


def test_convert_markdown_to_storage_normalizes_tasklists(monkeypatch) -> None:
    """Task lists stay renderable by Confluence's preview action."""
    monkeypatch.setenv("CONFLUENCE_BASE_URL", "http://confluence:8090")
    monkeypatch.setenv("CONFLUENCE_SPACE_KEY", "DEV")
    get_settings.cache_clear()
    try:
        storage = convert_markdown_to_storage("- [ ] write docs\n- [x] ship fix\n")
    finally:
        get_settings.cache_clear()

    assert "<ac:task-list>" not in storage
    assert "<ul>" in storage
    assert "[ ] write docs" in storage
    assert "[x] ship fix" in storage


def test_convert_markdown_to_storage_restores_preserved_image(monkeypatch) -> None:
    """Known preservation markers restore their original Storage XHTML without wrapper tags."""
    marker = "{{confluence-storage:0001-abc123abc123}}"
    image_storage = '<ac:image><ri:attachment ri:filename="diagram.png"></ri:attachment></ac:image>'
    monkeypatch.setenv("CONFLUENCE_BASE_URL", "http://confluence:8090")
    monkeypatch.setenv("CONFLUENCE_SPACE_KEY", "DEV")
    get_settings.cache_clear()
    try:
        storage = convert_markdown_to_storage(
            f"# Title\n\n{marker}\n",
            {marker: image_storage},
        )
    finally:
        get_settings.cache_clear()

    assert image_storage in storage
    assert f"<p>{image_storage}</p>" not in storage


def test_convert_markdown_to_storage_restores_preserved_custom_macro(monkeypatch) -> None:
    """Known custom macro markers restore their original Storage XHTML."""
    marker = "{{confluence-storage:0002-def456def456}}"
    macro_storage = (
        '<ac:structured-macro ac:name="custom">'
        '<ac:parameter ac:name="id">42</ac:parameter>'
        "</ac:structured-macro>"
    )
    monkeypatch.setenv("CONFLUENCE_BASE_URL", "http://confluence:8090")
    monkeypatch.setenv("CONFLUENCE_SPACE_KEY", "DEV")
    get_settings.cache_clear()
    try:
        storage = convert_markdown_to_storage(
            f"{marker}\n\n{marker}\n",
            {marker: macro_storage},
        )
    finally:
        get_settings.cache_clear()

    assert storage.count(macro_storage) == 2


def test_convert_markdown_to_storage_drops_removed_preserved_marker(monkeypatch) -> None:
    """If a marker is removed from the Markdown, its macro is not reinserted."""
    marker = "{{confluence-storage:0001-abc123abc123}}"
    image_storage = '<ac:image><ri:attachment ri:filename="diagram.png"></ri:attachment></ac:image>'
    monkeypatch.setenv("CONFLUENCE_BASE_URL", "http://confluence:8090")
    monkeypatch.setenv("CONFLUENCE_SPACE_KEY", "DEV")
    get_settings.cache_clear()
    try:
        storage = convert_markdown_to_storage("# Title\n\nNo image\n", {marker: image_storage})
    finally:
        get_settings.cache_clear()

    assert image_storage not in storage


def test_convert_markdown_to_storage_leaves_unknown_marker_as_text(monkeypatch) -> None:
    """Unknown preservation markers stay as text instead of restoring arbitrary storage."""
    marker = "{{confluence-storage:9999-deadbeefcafe}}"
    monkeypatch.setenv("CONFLUENCE_BASE_URL", "http://confluence:8090")
    monkeypatch.setenv("CONFLUENCE_SPACE_KEY", "DEV")
    get_settings.cache_clear()
    try:
        storage = convert_markdown_to_storage(marker)
    finally:
        get_settings.cache_clear()

    assert marker in storage


def test_format_storage_xhtml_for_diff_splits_storage_tags() -> None:
    """Storage XHTML is expanded into stable line units before diffing."""
    formatted = format_storage_xhtml_for_diff('<p>Hello</p><ac:structured-macro ac:name="toc" />')

    assert formatted == (
        '<p>\n Hello\n</p>\n<ac:structured-macro ac:name="toc">\n</ac:structured-macro>\n'
    )


def test_build_storage_diff_compares_current_and_generated_xhtml() -> None:
    """Review diffs compare Confluence Storage XHTML instead of text versus Markdown."""
    diff = build_storage_diff(
        "<p>Hello</p><p>World</p>",
        "<p>Hello</p><p>World</p><p>Added line</p>",
    )

    assert "--- current-storage.xhtml" in diff
    assert "+++ generated-storage.xhtml" in diff
    assert "+<p>" in diff
    assert "+ Added line" in diff
    assert "current-documentation.txt" not in diff
    assert "generated-draft.md" not in diff


def test_preview_has_rendered_content_rejects_empty_wiki_content() -> None:
    """Confluence can return a non-empty page shell with an empty rendered body."""
    assert preview_has_rendered_content('<div class="wiki-content"><p>Hello</p></div>')
    assert not preview_has_rendered_content('<div class="wiki-content"> </div>')


def test_storage_for_preview_adds_confluence_namespaces() -> None:
    """Confluence preview parsing needs namespace declarations for ac/ri macros."""
    storage = '<ac:structured-macro ac:name="code" />'

    preview_storage = storage_for_preview(storage)

    assert preview_storage.startswith('<div xmlns:ac="http://atlassian.com/content"')
    assert 'xmlns:ri="http://atlassian.com/resource/identifier"' in preview_storage
    assert storage in preview_storage


def test_page_tree_metadata_uses_immediate_parent_and_position() -> None:
    """Synced page metadata keeps the hierarchy information needed by the tree view."""
    payload = {
        "ancestors": [{"id": "100"}, {"id": 200}],
        "extensions": {"position": "7"},
    }

    assert page_parent_id(payload) == "200"
    assert page_sort_order(payload, fallback=3) == 7
    assert page_sort_order({"extensions": {"position": "bad"}}, fallback=3) == 3


def test_move_page_uses_data_center_legacy_action() -> None:
    """Data Center moves use the relative page move action directly."""
    client = ConfluenceClient.__new__(ConfluenceClient)
    client.settings = SimpleNamespace(confluence_space_key="DOC")
    legacy_calls: list[dict] = []

    def request(method: str, path: str) -> dict:
        pytest.fail(f"Unexpected non-legacy move call: {method} {path}")

    def get_page_space_key(confluence_id: str) -> str:
        return "DOC"

    def request_text(method: str, path: str, **kwargs) -> str:
        legacy_calls.append({"method": method, "path": path, **kwargs})
        return (
            '{"valid": true, "authorized": true, "progressMeter": {"completedSuccessfully": true}}'
        )

    client.request = request
    client.get_page_space_key = get_page_space_key
    client.request_text = request_text

    assert client.move_page("123", "456", "before")["valid"] is True
    assert legacy_calls == [
        {
            "method": "POST",
            "path": "/pages/movepage.action",
            "headers": {
                "Accept": "application/json, text/plain, */*",
                "X-Atlassian-Token": "no-check",
            },
            "params": {
                "pageId": "123",
                "targetId": "456",
                "position": "above",
                "mode": "LEGACY",
            },
        }
    ]


def test_move_page_rejects_remote_target_outside_configured_space() -> None:
    """The Confluence action is not called when remote page spaces do not match."""
    client = ConfluenceClient.__new__(ConfluenceClient)
    client.settings = SimpleNamespace(confluence_space_key="DOC")
    spaces = {"123": "DOC", "456": "OPS"}

    def get_page_space_key(confluence_id: str) -> str:
        return spaces[confluence_id]

    def request_text(method: str, path: str, **kwargs) -> str:
        pytest.fail(f"Unexpected legacy move call: {method} {path}")

    client.get_page_space_key = get_page_space_key
    client.request_text = request_text

    with pytest.raises(RuntimeError, match="configured Confluence space"):
        client.move_page("123", "456", "append")


def test_move_page_legacy_action_reports_rejected_moves() -> None:
    """A legacy move action that rejects the request must fail the worker job."""
    client = ConfluenceClient.__new__(ConfluenceClient)
    client.settings = SimpleNamespace(confluence_space_key="DOC")

    def get_page_space_key(confluence_id: str) -> str:
        return "DOC"

    def request_text(method: str, path: str, **kwargs) -> str:
        return '{"valid": false, "authorized": true}'

    client.get_page_space_key = get_page_space_key
    client.request_text = request_text

    with pytest.raises(RuntimeError, match="rejected"):
        client.move_page("123", "456", "append")


def test_move_validation_rejects_targets_outside_synced_space() -> None:
    """Move targets must exist in the same synced Confluence space."""
    page = SimpleNamespace(space_key="DOC")
    same_space_target = SimpleNamespace(space_key="DOC")
    other_space_target = SimpleNamespace(space_key="OPS")

    ensure_move_stays_in_space(page, same_space_target)
    with pytest.raises(PageMoveOutsideSpaceError, match="synced Confluence space"):
        ensure_move_stays_in_space(page, None)
    with pytest.raises(PageMoveOutsideSpaceError, match="outside"):
        ensure_move_stays_in_space(page, other_space_target)


def test_page_tree_metadata_prefers_child_endpoint_parent() -> None:
    """Child endpoint metadata overrides missing or stale ancestor metadata."""
    payload = {
        "ancestors": [{"id": "old-parent"}],
        "extensions": {"position": "1"},
        "_tree_parent_id": "real-parent",
        "_tree_sort_order": 4,
    }

    assert page_parent_id(payload) == "real-parent"
    assert page_sort_order(payload, fallback=0) == 4


def test_page_tree_metadata_keeps_space_root_pages_without_parent() -> None:
    """A tree-discovered root page must not fall back to stale ancestors."""
    payload = {
        "ancestors": [{"id": "old-parent"}],
        "_tree_parent_id": None,
        "_tree_sort_order": 0,
    }

    assert page_parent_id(payload) is None
    assert page_sort_order(payload, fallback=8) == 0
