"""Tests for the JSON reporter."""

from __future__ import annotations

import json
from pathlib import Path

from pyast_check.analyzers.audit import AuditAnalyzer
from pyast_check.analyzers.breaking import BreakingAnalyzer
from pyast_check.analyzers.structure import StructureAnalyzer
from pyast_check.reporters.json_reporter import JsonReporter

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestJsonReporterStructure:
    def test_valid_json(self) -> None:
        analyzer = StructureAnalyzer()
        report = analyzer.analyze(str(FIXTURES_DIR / "refactored"))
        output = JsonReporter().render_structure(report)
        data = json.loads(output)
        assert isinstance(data, dict)

    def test_contains_summary(self) -> None:
        analyzer = StructureAnalyzer()
        report = analyzer.analyze(str(FIXTURES_DIR / "refactored"))
        data = json.loads(JsonReporter().render_structure(report))
        assert "summary" in data
        assert "total_modules" in data["summary"]
        assert "total_symbols" in data["summary"]
        assert "total_lines" in data["summary"]

    def test_contains_modules(self) -> None:
        analyzer = StructureAnalyzer()
        report = analyzer.analyze(str(FIXTURES_DIR / "refactored"))
        data = json.loads(JsonReporter().render_structure(report))
        assert "modules" in data
        assert len(data["modules"]) > 0
        module = data["modules"][0]
        assert "module" in module
        assert "lines" in module
        assert "functions" in module


class TestJsonReporterAudit:
    def test_valid_json(self) -> None:
        analyzer = AuditAnalyzer()
        report = analyzer.analyze(str(FIXTURES_DIR / "audit"))
        output = JsonReporter().render_audit(report)
        data = json.loads(output)
        assert isinstance(data, dict)

    def test_enum_serialized_as_value(self) -> None:
        analyzer = AuditAnalyzer()
        report = analyzer.analyze(str(FIXTURES_DIR / "audit"))
        data = json.loads(JsonReporter().render_audit(report))
        for issue in data["issues"]:
            assert isinstance(issue["kind"], str)


class TestJsonReporterBreaking:
    def test_valid_json(self) -> None:
        old = str(FIXTURES_DIR / "breaking" / "old_version.py")
        new = str(FIXTURES_DIR / "breaking" / "new_version.py")
        analyzer = BreakingAnalyzer()
        report = analyzer.analyze(old, new)
        output = JsonReporter().render_breaking(report)
        data = json.loads(output)
        assert isinstance(data, dict)
        assert "summary" in data
        assert data["summary"]["errors"] > 0

    def test_enum_serialized_as_value(self) -> None:
        old = str(FIXTURES_DIR / "breaking" / "old_version.py")
        new = str(FIXTURES_DIR / "breaking" / "new_version.py")
        analyzer = BreakingAnalyzer()
        report = analyzer.analyze(old, new)
        data = json.loads(JsonReporter().render_breaking(report))
        for change in data["changes"]:
            assert isinstance(change["kind"], str)
            assert isinstance(change["severity"], str)
