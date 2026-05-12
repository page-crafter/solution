from typing import Protocol


class PageLike(Protocol):
    space_key: str


class PageMoveOutsideSpaceError(ValueError):
    """Raised when a page move would leave the synced Confluence space."""


def ensure_move_stays_in_space(page: PageLike, target: PageLike | None) -> None:
    """Reject page moves whose target is missing or belongs to another space."""
    if target is None:
        raise PageMoveOutsideSpaceError(
            "Move target page must belong to the synced Confluence space."
        )
    if page.space_key != target.space_key:
        raise PageMoveOutsideSpaceError("Cannot move a page outside its Confluence space.")
