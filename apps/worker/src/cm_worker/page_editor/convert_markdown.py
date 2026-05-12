import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup, NavigableString

from cm_shared.settings.app import get_settings


def confluence_web_options() -> list[str]:
    """Build the Confluence identity options required by md2conf local mode."""
    settings = get_settings()
    parsed = urlparse(settings.confluence_base_url)
    if not parsed.netloc:
        parsed = urlparse(f"http://{settings.confluence_base_url}")

    domain = parsed.netloc
    path = parsed.path or "/"
    if not domain:
        raise ValueError("Confluence base URL must include a host")

    return [
        "--domain",
        domain,
        "--path",
        path,
        "--api-version",
        "v1",
        "--space",
        settings.confluence_space_key,
    ]


def normalize_storage_for_preview(storage_xhtml: str) -> str:
    """Normalize md2conf output that the Confluence preview action cannot render."""
    soup = BeautifulSoup(storage_xhtml, "html.parser")
    for task_list in soup.find_all("ac:task-list"):
        replacement = soup.new_tag("ul")
        for task in task_list.find_all("ac:task", recursive=False):
            status = task.find("ac:task-status")
            body = task.find("ac:task-body")
            item = soup.new_tag("li")
            marker = "[x] " if status and status.get_text(strip=True) == "complete" else "[ ] "
            item.append(NavigableString(marker))
            if body:
                for index, child in enumerate(list(body.contents)):
                    extracted = child.extract()
                    if index == 0 and isinstance(extracted, NavigableString):
                        item.append(NavigableString(str(extracted).lstrip()))
                    else:
                        item.append(extracted)
            replacement.append(item)
        task_list.replace_with(replacement)
    return str(soup)


def convert_markdown_to_storage(markdown: str) -> str:
    """Convert Markdown to Confluence Storage XHTML with markdown-to-confluence."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        source = Path(tmp_dir) / "draft.md"
        source.write_text(markdown, encoding="utf-8")
        command = [
            sys.executable,
            "-m",
            "md2conf",
            "--local",
            "--no-generated-by",
            "--skip-update",
            *confluence_web_options(),
            str(source),
        ]
        try:
            completed = subprocess.run(
                command,
                check=True,
                cwd=tmp_dir,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            details = (exc.stderr or exc.stdout or str(exc)).strip()
            raise RuntimeError(f"markdown-to-confluence failed: {details}") from exc

        output = source.with_suffix(".csf")
        if output.exists():
            return normalize_storage_for_preview(output.read_text(encoding="utf-8"))
        details = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(f"markdown-to-confluence did not write Storage XHTML: {details}")
