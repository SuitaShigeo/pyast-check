"""Data models for migration analysis."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field

from pyast_check.models.base import SymbolInfo


class MigrationStatus(enum.Enum):
    """Result of a single symbol migration check."""

    IDENTICAL = "Identical"
    MODIFIED = "Modified"
    MISSING = "Missing"


@dataclass
class MigrationResult:
    """Outcome of checking one symbol's migration."""

    symbol: SymbolInfo
    status: MigrationStatus
    destination: str | None = None
    """Relative path of the target file where the symbol was found."""
    notes: str = ""
    """What changed (e.g. "Type hints changed"). Empty for IDENTICAL."""
    warnings: list[str] = field(default_factory=list)
    """Export warnings (e.g. "MISSING from __all__")."""
    diff: str = ""
    """Human-readable unified diff (populated when status is MODIFIED)."""


@dataclass
class MigrationReport:
    """Full report of a refactoring migration analysis."""

    source_label: str
    target_label: str
    results: list[MigrationResult] = field(default_factory=list)

    @property
    def identical_count(self) -> int:
        return sum(1 for r in self.results if r.status is MigrationStatus.IDENTICAL)

    @property
    def modified_count(self) -> int:
        return sum(1 for r in self.results if r.status is MigrationStatus.MODIFIED)

    @property
    def missing_count(self) -> int:
        return sum(1 for r in self.results if r.status is MigrationStatus.MISSING)

    @property
    def total_count(self) -> int:
        return len(self.results)
