"""Orchestrate the migration analysis."""

from __future__ import annotations

from pyast_check.comparator import BodyComparator
from pyast_check.extractor import SymbolExtractor
from pyast_check.models import (
    MigrationReport,
    MigrationResult,
    MigrationStatus,
    SymbolInfo,
)
from pyast_check.source import SourceResolver
from pyast_check.utils import short_label


class MigrationAnalyzer:
    """Analyse migration from a single source file to a target package."""

    def __init__(
        self,
        *,
        ignore: set[str] | None = None,
        verbose: bool = False,
        resolver: SourceResolver | None = None,
    ) -> None:
        self._ignore = ignore or set()
        self._verbose = verbose
        self._resolver = resolver or SourceResolver()
        self._extractor = SymbolExtractor()
        self._comparator = BodyComparator()

    def analyze(self, source_spec: str, target_spec: str) -> MigrationReport:
        """Run the full analysis and return a report."""
        source_code = self._resolver.resolve_single(source_spec)
        source_symbols = self._extractor.extract(source_code)

        target_files = self._resolver.resolve_directory(target_spec)
        # Build lookup: symbol_name -> (relative_path, ast_dump)
        target_index = self._build_target_index(target_files)
        # Parse __init__.py for re-export / __all__ validation
        init_source = target_files.get("__init__.py", "")
        init_all = self._extractor.extract_all_names(init_source) if init_source else []
        init_imports = (
            self._extractor.extract_imports(init_source) if init_source else []
        )

        report = MigrationReport(
            source_label=short_label(source_spec),
            target_label=short_label(target_spec),
        )

        for sym in source_symbols:
            if sym.name in self._ignore:
                continue
            result = self._check_symbol(sym, target_index, init_all, init_imports)
            report.results.append(result)

        # Sort: MISSING first, then MODIFIED, then IDENTICAL
        status_order = {
            MigrationStatus.MISSING: 0,
            MigrationStatus.MODIFIED: 1,
            MigrationStatus.IDENTICAL: 2,
        }
        report.results.sort(key=lambda r: (status_order[r.status], r.symbol.name))
        return report

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_target_index(
        self, target_files: dict[str, str]
    ) -> dict[str, list[tuple[str, str]]]:
        """Map symbol name -> [(relative_path, ast_dump), ...]."""
        index: dict[str, list[tuple[str, str]]] = {}
        for rel_path, code in target_files.items():
            for sym in self._extractor.extract(code):
                index.setdefault(sym.name, []).append((rel_path, sym.ast_dump))
        return index

    def _check_symbol(
        self,
        sym: SymbolInfo,
        target_index: dict[str, list[tuple[str, str]]],
        init_all: list[str],
        init_imports: list[str],
    ) -> MigrationResult:
        entries = target_index.get(sym.name, [])
        if not entries:
            rename_candidate = self._find_rename_candidate(sym.name, target_index)
            if rename_candidate:
                rel_path, _ = target_index[rename_candidate][0]
                return MigrationResult(
                    symbol=sym,
                    status=MigrationStatus.MODIFIED,
                    destination=rel_path,
                    notes=f"Possibly renamed to `{rename_candidate}`",
                )
            return MigrationResult(
                symbol=sym,
                status=MigrationStatus.MISSING,
            )

        # Pick the best match (prefer identical)
        for rel_path, dump in entries:
            status, diff = self._comparator.compare(sym.ast_dump, dump)
            if status is MigrationStatus.IDENTICAL:
                return MigrationResult(
                    symbol=sym,
                    status=MigrationStatus.IDENTICAL,
                    destination=rel_path,
                    warnings=self._check_exports(sym.name, init_all, init_imports),
                )

        # No identical match — report the first modified one
        rel_path, dump = entries[0]
        status, diff = self._comparator.compare(sym.ast_dump, dump)
        summary = self._comparator.summarize_diff(sym.ast_dump, dump)
        return MigrationResult(
            symbol=sym,
            status=MigrationStatus.MODIFIED,
            destination=rel_path,
            notes=summary,
            warnings=self._check_exports(sym.name, init_all, init_imports),
            diff=diff if self._verbose else "",
        )

    @staticmethod
    def _check_exports(
        name: str, init_all: list[str], init_imports: list[str]
    ) -> list[str]:
        """Check whether *name* is re-exported from ``__init__.py``."""
        warnings: list[str] = []
        if init_all and name not in init_all:
            warnings.append("MISSING from __all__")
        if init_imports and name not in init_imports:
            warnings.append("Not imported in __init__.py")
        return warnings

    @staticmethod
    def _find_rename_candidate(
        name: str, target_index: dict[str, list[tuple[str, str]]]
    ) -> str | None:
        """Return the first matching rename candidate, or ``None``.

        Checks ``_foo`` <-> ``foo`` heuristic.
        """
        if name.startswith("_") and not name.startswith("__"):
            alt = name[1:]
        else:
            alt = f"_{name}"
        return alt if alt in target_index else None
