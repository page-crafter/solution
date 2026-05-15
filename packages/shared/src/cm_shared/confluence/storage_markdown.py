from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable

from bs4 import BeautifulSoup
from bs4.element import NavigableString, PageElement, Tag

BLOCK_TAGS = {
    "address",
    "article",
    "aside",
    "blockquote",
    "div",
    "dl",
    "fieldset",
    "figcaption",
    "figure",
    "footer",
    "form",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "hr",
    "li",
    "main",
    "nav",
    "ol",
    "p",
    "pre",
    "section",
    "table",
    "ul",
}
SKIPPED_TAGS = {"script", "style", "ac:parameter"}
PRESERVED_MARKER_ATTR = "_cm_preserved_storage_marker"
PRESERVED_STORAGE_MARKER_RE = re.compile(r"\{\{confluence-storage:[0-9]{4}-[a-f0-9]{12}\}\}")
INLINE_CONFLUENCE_TAGS = {
    "ac:link",
    "ac:link-body",
    "ac:parameter",
    "ac:plain-text-body",
    "ac:plain-text-link-body",
    "ac:rich-text-body",
}


def storage_xhtml_to_markdown(storage_xhtml: str) -> str:
    """Convert Confluence Storage XHTML into clean editable Markdown."""
    soup = BeautifulSoup(storage_xhtml or "", "html.parser")
    annotate_preserved_storage_nodes(soup)
    root = soup.body.contents if soup.body else soup.contents
    return tidy_markdown(render_blocks(root))


def build_preserved_storage_map(storage_xhtml: str) -> dict[str, str]:
    """Return opaque Confluence Storage fragments keyed by their Markdown markers."""
    soup = BeautifulSoup(storage_xhtml or "", "html.parser")
    return annotate_preserved_storage_nodes(soup)


def annotate_preserved_storage_nodes(soup: BeautifulSoup) -> dict[str, str]:
    """Attach stable preservation markers to opaque Confluence Storage nodes."""
    preserved: dict[str, str] = {}
    for index, tag in enumerate(preserved_storage_tags(soup), start=1):
        storage = storage_fragment(tag)
        marker = preserved_storage_marker(index, storage)
        tag.attrs[PRESERVED_MARKER_ATTR] = marker
        preserved[marker] = storage
    return preserved


def preserved_storage_tags(soup: BeautifulSoup) -> list[Tag]:
    """Return top-level Confluence tags that must survive Markdown round-tripping."""
    tags: list[Tag] = []
    for tag in soup.find_all(is_preserved_storage_tag):
        if any(
            isinstance(parent, Tag) and is_preserved_storage_tag(parent)
            for parent in tag.parents
        ):
            continue
        tags.append(tag)
    return tags


def is_preserved_storage_tag(tag: Tag) -> bool:
    """Return whether a Storage tag should be represented as an opaque marker."""
    name = tag_name(tag)
    if name in INLINE_CONFLUENCE_TAGS:
        return False
    if name == "ac:structured-macro" and macro_name(tag) in {"code", "noformat"}:
        return False
    return name == "ac:image" or name == "ac:structured-macro" or name.startswith("ac:")


def storage_fragment(tag: Tag) -> str:
    """Serialize one Confluence Storage fragment without preservation metadata."""
    return tag.decode(formatter="minimal")


def preserved_storage_marker(index: int, storage: str) -> str:
    """Build a stable marker for one preserved Storage fragment."""
    digest = hashlib.sha256(storage.encode("utf-8")).hexdigest()[:12]
    return f"{{{{confluence-storage:{index:04d}-{digest}}}}}"


def tag_name(tag: Tag) -> str:
    """Return a normalized tag name for regular and namespaced Storage XHTML tags."""
    return (tag.name or "").lower()


def render_blocks(nodes: Iterable[PageElement]) -> str:
    """Render page elements as Markdown blocks separated by blank lines."""
    blocks = []
    for node in nodes:
        rendered = render_block(node).strip("\n")
        if rendered.strip():
            blocks.append(rendered)
    return "\n\n".join(blocks)


def render_block(node: PageElement) -> str:
    """Render one page element as a Markdown block."""
    if isinstance(node, NavigableString):
        return clean_inline(str(node))
    if not isinstance(node, Tag):
        return ""

    name = tag_name(node)
    if marker := node.attrs.get(PRESERVED_MARKER_ATTR):
        return str(marker)
    if name in SKIPPED_TAGS:
        return ""
    if name in {"[document]", "body", "html"}:
        return render_blocks(node.contents)
    if name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
        level = int(name[1])
        text = clean_inline(render_inline_children(node))
        return f"{'#' * level} {text}" if text else ""
    if name == "p":
        return clean_inline(render_inline_children(node))
    if name == "br":
        return "\n"
    if name in {"ul", "ol"}:
        return render_list(node, ordered=name == "ol")
    if name == "blockquote":
        return render_blockquote(node)
    if name == "pre":
        return render_preformatted(node)
    if name == "table":
        return render_table(node)
    if name == "hr":
        return "---"
    if name == "ac:structured-macro":
        return render_macro(node)
    if has_direct_block_children(node):
        return render_blocks(node.contents)
    return clean_inline(render_inline(node))


def render_inline_children(tag: Tag) -> str:
    """Render a tag's children as Markdown inline content."""
    return "".join(render_inline(child) for child in tag.contents)


def render_inline(node: PageElement) -> str:
    """Render one page element as Markdown inline content."""
    if isinstance(node, NavigableString):
        return str(node)
    if not isinstance(node, Tag):
        return ""

    name = tag_name(node)
    if marker := node.attrs.get(PRESERVED_MARKER_ATTR):
        return str(marker)
    if name in SKIPPED_TAGS:
        return ""
    if name == "br":
        return "\n"
    if name in {"strong", "b"}:
        return wrap_inline("**", render_inline_children(node), "**")
    if name in {"em", "i"}:
        return wrap_inline("*", render_inline_children(node), "*")
    if name in {"s", "strike", "del"}:
        return wrap_inline("~~", render_inline_children(node), "~~")
    if name == "code":
        return inline_code(node.get_text())
    if name == "a":
        return render_html_link(node)
    if name == "ac:link":
        return render_confluence_link(node)
    if name == "ri:attachment":
        return node.get("ri:filename", "") or ""
    if name == "ac:structured-macro":
        return render_macro(node)
    if name in BLOCK_TAGS:
        return render_block(node)
    return render_inline_children(node)


def wrap_inline(prefix: str, text: str, suffix: str) -> str:
    """Wrap non-empty inline content in Markdown delimiters."""
    cleaned = clean_inline(text)
    return f"{prefix}{cleaned}{suffix}" if cleaned else ""


def render_html_link(tag: Tag) -> str:
    """Render a normal HTML anchor as Markdown."""
    text = clean_inline(render_inline_children(tag))
    href = tag.get("href")
    if text and href:
        return f"[{text}]({href})"
    return text


def render_confluence_link(tag: Tag) -> str:
    """Render Confluence Storage links without leaking Storage XHTML."""
    plain_body = tag.find("ac:plain-text-link-body")
    rich_body = tag.find("ac:link-body")
    page = tag.find("ri:page")
    url = tag.find("ri:url")

    text = ""
    if plain_body:
        text = plain_body.get_text()
    elif rich_body:
        text = clean_inline(render_inline_children(rich_body))
    elif page:
        text = page.get("ri:content-title", "") or ""
    elif url:
        text = url.get("ri:value", "") or ""
    else:
        text = clean_inline(render_inline_children(tag))

    href = url.get("ri:value") if url else None
    text = clean_inline(text)
    if text and href:
        return f"[{text}]({href})"
    return text


def inline_code(text: str) -> str:
    """Render inline code with a fence that can contain backticks."""
    code = clean_inline(text)
    if not code:
        return ""
    longest_run = max((len(match.group(0)) for match in re.finditer(r"`+", code)), default=0)
    fence = "`" * (longest_run + 1)
    padding = " " if code.startswith("`") or code.endswith("`") else ""
    return f"{fence}{padding}{code}{padding}{fence}"


def render_preformatted(tag: Tag) -> str:
    """Render preformatted content as a fenced Markdown code block."""
    code = tag.find("code")
    return fenced_code((code or tag).get_text())


def render_macro(tag: Tag) -> str:
    """Render supported Confluence macros and drop unsupported macro wrappers."""
    name = macro_name(tag)
    if name in {"code", "noformat"}:
        body = tag.find("ac:plain-text-body") or tag.find("ac:rich-text-body")
        language = macro_parameter(tag, "language") if name == "code" else ""
        return fenced_code(body.get_text() if body else "", language)

    rich_body = tag.find("ac:rich-text-body")
    if rich_body:
        return render_blocks(rich_body.contents)

    plain_body = tag.find("ac:plain-text-body")
    if plain_body:
        return clean_block_text(plain_body.get_text("\n"))

    return ""


def macro_name(tag: Tag) -> str:
    """Return a normalized Confluence macro name."""
    return (tag.get("ac:name") or "").lower()


def macro_parameter(tag: Tag, name: str) -> str:
    """Return a direct Confluence macro parameter value."""
    for parameter in tag.find_all("ac:parameter", recursive=False):
        if parameter.get("ac:name") == name:
            return clean_inline(parameter.get_text())
    return ""


def fenced_code(text: str, language: str = "") -> str:
    """Render a fenced Markdown code block."""
    code = text.strip("\n")
    if not code:
        return ""
    longest_fence = max((len(match.group(0)) for match in re.finditer(r"`{3,}", code)), default=2)
    fence = "`" * max(3, longest_fence + 1)
    lang = clean_code_language(language)
    return f"{fence}{lang}\n{code}\n{fence}"


def clean_code_language(language: str) -> str:
    """Keep only Markdown-friendly code fence language tokens."""
    cleaned = clean_inline(language)
    return cleaned if re.fullmatch(r"[\w.+#-]+", cleaned) else ""


def render_list(tag: Tag, *, ordered: bool, indent: int = 0) -> str:
    """Render ordered and unordered lists, including nested lists."""
    lines: list[str] = []
    items = [child for child in tag.children if isinstance(child, Tag) and tag_name(child) == "li"]
    for index, item in enumerate(items, start=1):
        marker = f"{index}. " if ordered else "- "
        lines.extend(render_list_item(item, marker, indent))
    return "\n".join(lines)


def render_list_item(item: Tag, marker: str, indent: int) -> list[str]:
    """Render one list item with continuation indentation."""
    content_children: list[PageElement] = []
    nested_lists: list[str] = []
    for child in item.contents:
        if isinstance(child, Tag) and tag_name(child) in {"ul", "ol"}:
            nested_lists.append(
                render_list(child, ordered=tag_name(child) == "ol", indent=indent + 2)
            )
        else:
            content_children.append(child)

    if any(isinstance(child, Tag) and tag_name(child) in BLOCK_TAGS for child in content_children):
        content = render_blocks(content_children)
    else:
        content = clean_inline("".join(render_inline(child) for child in content_children))

    prefix = f"{' ' * indent}{marker}"
    continuation = " " * len(prefix)
    item_lines = content.splitlines() or [""]
    lines = [f"{prefix}{item_lines[0]}"]
    lines.extend(f"{continuation}{line}" if line else "" for line in item_lines[1:])
    lines.extend(nested for nested in nested_lists if nested.strip())
    return lines


def render_blockquote(tag: Tag) -> str:
    """Render blockquote children with Markdown quote prefixes."""
    inner = render_blocks(tag.contents)
    return "\n".join(f"> {line}" if line else ">" for line in inner.splitlines())


def render_table(tag: Tag) -> str:
    """Render an HTML table using GitHub-flavored Markdown table syntax."""
    rows: list[list[str]] = []
    for row in tag.find_all("tr"):
        cells = row.find_all(["th", "td"], recursive=False)
        if not cells:
            continue
        rows.append([table_cell_text(cell) for cell in cells])

    if not rows:
        return ""

    width = max(len(row) for row in rows)
    padded_rows = [row + [""] * (width - len(row)) for row in rows]
    header = padded_rows[0]
    separator = ["---"] * width
    body = padded_rows[1:]
    return "\n".join(
        [
            markdown_table_row(header),
            markdown_table_row(separator),
            *(markdown_table_row(row) for row in body),
        ]
    )


def table_cell_text(cell: Tag) -> str:
    """Render a table cell as one escaped Markdown table cell."""
    text = clean_inline(render_inline_children(cell)).replace("\n", "<br>")
    return text.replace("|", r"\|")


def markdown_table_row(values: list[str]) -> str:
    """Render one Markdown table row."""
    return f"| {' | '.join(values)} |"


def has_direct_block_children(tag: Tag) -> bool:
    """Return whether a tag contains direct children that should start Markdown blocks."""
    return any(isinstance(child, Tag) and tag_name(child) in BLOCK_TAGS for child in tag.contents)


def clean_inline(text: str) -> str:
    """Normalize inline whitespace while preserving explicit line breaks."""
    cleaned = text.replace("\xa0", " ")
    cleaned = re.sub(r"[ \t\r\f\v]+", " ", cleaned)
    cleaned = re.sub(r" *\n *", "\n", cleaned)
    return cleaned.strip()


def clean_block_text(text: str) -> str:
    """Normalize standalone plain text blocks."""
    lines = [clean_inline(line) for line in text.splitlines()]
    return "\n".join(line for line in lines if line).strip()


def tidy_markdown(markdown: str) -> str:
    """Trim trailing whitespace and collapse excessive blank lines."""
    lines = [line.rstrip() for line in markdown.replace("\xa0", " ").splitlines()]
    cleaned = "\n".join(lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()
