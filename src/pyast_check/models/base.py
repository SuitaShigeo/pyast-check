"""Base data models shared across all analyzers."""

from __future__ import annotations

import enum
from dataclasses import dataclass


class SymbolKind(enum.Enum):
    """Kind of a top-level symbol."""

    FUNCTION = "function"
    CLASS = "class"
    CONSTANT = "constant"
    TYPE_ALIAS = "type_alias"
    IMPORT = "import"


@dataclass
class SymbolInfo:
    """A single top-level symbol extracted from source code."""

    name: str
    kind: SymbolKind
    ast_dump: str
    """``ast.dump(node, include_attributes=False)`` serialisation."""
    source_lines: tuple[int, int] = (0, 0)
    """(start_line, end_line) in the original source — informational only."""
