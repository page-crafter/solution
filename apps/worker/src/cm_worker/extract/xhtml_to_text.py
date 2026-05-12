from bs4 import BeautifulSoup


def extract_text_from_storage(storage_xhtml: str) -> str:
    """Extract clean searchable text from Confluence Storage XHTML."""
    soup = BeautifulSoup(storage_xhtml or "", "html.parser")
    for macro in soup.find_all(["ac:structured-macro", "ri:attachment"]):
        macro_name = macro.get("ac:name") or macro.name
        macro.insert_before(f" [Confluence macro: {macro_name}] ")
    return " ".join(soup.get_text(" ").split())
