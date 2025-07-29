"""Analyze package exports for consistency issues."""

from __future__ import annotations

from pyast_check.extractor import SymbolExtractor
from pyast_check.models import AuditIssue, AuditIssueKind, AuditReport
from pyast_check.source import SourceResolver
from pyast_check.utils import short_label


class AuditAnalyzer:
    """Audit package exports: __all__, re-imports, shadowing."""

    def __init__(self, *, resolver: SourceResolver | None = None) -> None:
        self._resolver = resolver or SourceResolver()
        self._extractor = SymbolExtractor()

    def analyze(self, target_spec: str) -> AuditReport:
        files = self._resolver.resolve_directory(target_spec)
        issues: list[AuditIssue] = []

        # Collect all defined symbols across all modules (excluding __init__.py)
        all_defined: dict[str, list[str]] = {}  # name -> [files defining it]
        for rel_path, code in files.items():
            if rel_path == "__init__.py":
                continue
            for sym in self._extractor.extract(code):
                all_defined.setdefault(sym.name, []).append(rel_path)

        # Parse __init__.py
        init_source = files.get("__init__.py", "")
        init_all = self._extractor.extract_all_names(init_source) if init_source else []
        init_imports = self._extractor.extract_imports(init_source) if init_source else []

        # Total unique symbols across the package
        total_symbols = len(all_defined)
        exported_symbols = len(init_all) if init_all else 0

        # Check 1: Defined but not in __all__
        if init_all:
            for name, defining_files in sorted(all_defined.items()):
                if name not in init_all:
                    issues.append(AuditIssue(
                        symbol_name=name,
                        kind=AuditIssueKind.NOT_IN_ALL,
                        file=defining_files[0],
                        description="Defined but not exported",
                    ))

        # Check 2: In __all__ but not defined anywhere
        init_symbols = {s.name for s in self._extractor.extract(init_source)} if init_source else set()
        for name in init_all:
            if name not in all_defined and name not in init_symbols:
                issues.append(AuditIssue(
                    symbol_name=name,
                    kind=AuditIssueKind.NOT_DEFINED,
                    file="__init__.py",
                    description="Listed in __all__ but not found",
                ))

        # Check 3: Not re-imported in __init__.py
        if init_imports:
            for name in init_all:
                if name not in init_imports and name in all_defined:
                    issues.append(AuditIssue(
                        symbol_name=name,
                        kind=AuditIssueKind.NOT_IMPORTED,
                        file="__init__.py",
                        description="In __all__ but not imported in __init__.py",
                    ))

        # Check 4: Shadowed symbols (defined in multiple files)
        for name, defining_files in sorted(all_defined.items()):
            if len(defining_files) > 1:
                issues.append(AuditIssue(
                    symbol_name=name,
                    kind=AuditIssueKind.SHADOWED,
                    file=", ".join(sorted(defining_files)),
                    description="Defined in multiple modules",
                ))

        label = short_label(target_spec)
        return AuditReport(
            target_label=label,
            total_symbols=total_symbols,
            exported_symbols=exported_symbols,
            issues=issues,
        )
