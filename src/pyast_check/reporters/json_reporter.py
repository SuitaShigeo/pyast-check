"""Generate JSON reports for all analysis types."""

from __future__ import annotations

import enum
import json
from dataclasses import asdict

from pyast_check.models import (
    AuditReport,
    BreakingReport,
    MigrationReport,
    StructureReport,
)


def _serialize(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, default=_json_default)


def _json_default(obj: object) -> object:
    if isinstance(obj, enum.Enum):
        return obj.value
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


class JsonReporter:
    """Render any report dataclass as a JSON string."""

    def render_migration(self, report: MigrationReport, *, verbose: bool = False) -> str:
        data = asdict(report)
        data["summary"] = {
            "total": report.total_count,
            "identical": report.identical_count,
            "modified": report.modified_count,
            "missing": report.missing_count,
        }
        if not verbose:
            for r in data["results"]:
                r.pop("diff", None)
        return _serialize(data)

    def render_breaking(self, report: BreakingReport) -> str:
        data = asdict(report)
        data["summary"] = {
            "total": report.total_count,
            "errors": report.error_count,
            "warnings": report.warning_count,
        }
        return _serialize(data)

    def render_audit(self, report: AuditReport) -> str:
        data = asdict(report)
        data["summary"] = {
            "total_symbols": report.total_symbols,
            "exported_symbols": report.exported_symbols,
            "issues": report.issue_count,
        }
        return _serialize(data)

    def render_structure(self, report: StructureReport) -> str:
        data = asdict(report)
        data["summary"] = {
            "total_modules": report.total_modules,
            "total_symbols": report.total_symbols,
            "total_lines": report.total_lines,
        }
        return _serialize(data)
