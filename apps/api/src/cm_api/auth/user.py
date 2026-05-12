from dataclasses import dataclass, field


@dataclass(frozen=True)
class CurrentUser:
    """Represent the authenticated user extracted from a bearer token."""

    subject: str
    email: str
    display_name: str
    roles: frozenset[str] = field(default_factory=frozenset)

    def has_role(self, *roles: str) -> bool:
        return bool(self.roles & set(roles))

