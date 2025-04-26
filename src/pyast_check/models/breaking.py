"""Data models for breaking change detection."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class BreakingChangeKind(enum.Enum):
    """Kind of breaking change detected."""

    REMOVED = "Removed"
    PARAMETER_ADDED = "Required parameter added"
    PARAMETER_REMOVED = "Parameter removed"
    RETURN_TYPE_CHANGED = "Return type changed"
    BASE_CLASSES_CHANGED = "Base classes changed"
    METHOD_REMOVED = "Public method removed"
    TYPE_CHANGED = "Type changed"


class Severity(enum.Enum):
    """Severity level of a breaking change."""

    ERROR = "ERROR"
    WARNING = "WARNING"


@dataclass
class BreakingChange:
    """A single breaking change detected between versions."""

    symbol_name: str
    kind: BreakingChangeKind
    severity: Severity
    description: str


@dataclass
class BreakingReport:
    """Full report of breaking change analysis."""

    old_label: str
    new_label: str
    changes: list[BreakingChange] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(1 for c in self.changes if c.severity is Severity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for c in self.changes if c.severity is Severity.WARNING)

    @property
    def total_count(self) -> int:
        return len(self.changes)
