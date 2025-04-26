"""Data models for module structure visualization."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ModuleStats:
    """Statistics for a single module."""

    module: str
    lines: int
    functions: int
    classes: int
    constants: int

    @property
    def total(self) -> int:
        return self.functions + self.classes + self.constants


@dataclass
class StructureReport:
    """Full report of module structure analysis."""

    target_label: str
    modules: list[ModuleStats] = field(default_factory=list)

    @property
    def total_modules(self) -> int:
        return len(self.modules)

    @property
    def total_symbols(self) -> int:
        return sum(m.total for m in self.modules)

    @property
    def total_lines(self) -> int:
        return sum(m.lines for m in self.modules)
