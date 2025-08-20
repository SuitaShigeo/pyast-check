"""Analyze module structure and produce statistics."""

from __future__ import annotations

from pathlib import Path

from pyast_check.extractor import SymbolExtractor
from pyast_check.models import ModuleStats, StructureReport, SymbolKind
from pyast_check.source import SourceResolver, _is_git_spec
from pyast_check.utils import short_label


class StructureAnalyzer:
    """Produce per-module statistics: line counts, symbol counts by kind."""

    def __init__(self, *, resolver: SourceResolver | None = None) -> None:
        self._resolver = resolver or SourceResolver()
        self._extractor = SymbolExtractor()

    def analyze(self, target_spec: str) -> StructureReport:
        files = self._resolve_target(target_spec)
        modules: list[ModuleStats] = []
        for rel_path, code in sorted(files.items()):
            symbols = self._extractor.extract(code)
            lines = code.count("\n") + (1 if code and not code.endswith("\n") else 0)
            stats = ModuleStats(
                module=rel_path,
                lines=lines,
                functions=sum(1 for s in symbols if s.kind is SymbolKind.FUNCTION),
                classes=sum(1 for s in symbols if s.kind is SymbolKind.CLASS),
                constants=sum(
                    1 for s in symbols if s.kind in (SymbolKind.CONSTANT, SymbolKind.TYPE_ALIAS)
                ),
            )
            modules.append(stats)
        return StructureReport(
            target_label=short_label(target_spec),
            modules=modules,
        )

    def _resolve_target(self, spec: str) -> dict[str, str]:
        """Resolve target as directory or single file."""
        # Try directory first
        try:
            return self._resolver.resolve_directory(spec)
        except Exception:
            pass
        # Fall back to single file
        code = self._resolver.resolve_single(spec)
        if _is_git_spec(spec):
            name = spec.partition(":")[2].split("/")[-1]
        else:
            name = Path(spec).name
        return {name: code}
