"""Data models for package export audit."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class AuditIssueKind(enum.Enum):
    """Kind of export audit issue."""

    NOT_IN_ALL = "Not in __all__"
    NOT_DEFINED = "Not defined"
    NOT_IMPORTED = "Not imported in __init__"
    SHADOWED = "Shadowed"


@dataclass
class AuditIssue:
    """A single issue found during export audit."""

    symbol_name: str
    kind: AuditIssueKind
    file: str
    description: str


@dataclass
class AuditReport:
    """Full report of a package export audit."""

    target_label: str
    total_symbols: int
    exported_symbols: int
    issues: list[AuditIssue] = field(default_factory=list)

    @property
    def issue_count(self) -> int:
        return len(self.issues)
