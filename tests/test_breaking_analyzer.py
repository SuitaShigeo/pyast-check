"""Tests for the breaking change analyzer and reporter."""

from __future__ import annotations

from pathlib import Path

import pytest

from pyast_check.analyzers.breaking import BreakingAnalyzer
from pyast_check.models import (
    BreakingChangeKind,
    BreakingReport,
    Severity,
)
from pyast_check.reporters.breaking import BreakingReporter

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "breaking"


@pytest.fixture
def analyzer() -> BreakingAnalyzer:
    return BreakingAnalyzer()


@pytest.fixture
def report(analyzer: BreakingAnalyzer) -> BreakingReport:
    old = str(FIXTURES_DIR / "old_version.py")
    new = str(FIXTURES_DIR / "new_version.py")
    return analyzer.analyze(old, new)


class TestBreakingAnalyzer:
    """Tests for individual breaking change detection rules."""

    def test_removed_function_detected(self, report: BreakingReport) -> None:
        """Removed function (process) should be detected as ERROR."""
        removed = [
            c for c in report.changes
            if c.kind is BreakingChangeKind.REMOVED and c.symbol_name == "process"
        ]
        assert len(removed) == 1
        assert removed[0].severity is Severity.ERROR

    def test_required_parameter_added(self, report: BreakingReport) -> None:
        """Required parameter added to greet should be detected as ERROR."""
        added = [
            c for c in report.changes
            if c.kind is BreakingChangeKind.PARAMETER_ADDED
            and c.symbol_name == "greet"
        ]
        assert len(added) == 1
        assert added[0].severity is Severity.ERROR
        assert "formal" in added[0].description

    def test_return_type_changed(self, report: BreakingReport) -> None:
        """Return type change on validate (bool -> int) should be WARNING."""
        ret_changes = [
            c for c in report.changes
            if c.kind is BreakingChangeKind.RETURN_TYPE_CHANGED
            and c.symbol_name == "validate"
        ]
        assert len(ret_changes) == 1
        assert ret_changes[0].severity is Severity.WARNING

    def test_removed_public_method(self, report: BreakingReport) -> None:
        """Removed public method (Service.stop) should be detected as ERROR."""
        method_removed = [
            c for c in report.changes
            if c.kind is BreakingChangeKind.METHOD_REMOVED
            and c.symbol_name == "Service.stop"
        ]
        assert len(method_removed) == 1
        assert method_removed[0].severity is Severity.ERROR

    def test_constant_type_changed(self, report: BreakingReport) -> None:
        """Constant type change (MAX_RETRIES int -> str) should be WARNING."""
        type_changes = [
            c for c in report.changes
            if c.kind is BreakingChangeKind.TYPE_CHANGED
            and c.symbol_name == "MAX_RETRIES"
        ]
        assert len(type_changes) == 1
        assert type_changes[0].severity is Severity.WARNING
        assert "int" in type_changes[0].description
        assert "str" in type_changes[0].description

    def test_error_count(self, report: BreakingReport) -> None:
        """Report should have the correct number of errors."""
        # Errors: process removed, greet parameter added, Service.stop removed
        assert report.error_count == 3

    def test_warning_count(self, report: BreakingReport) -> None:
        """Report should have the correct number of warnings."""
        # Warnings: validate return type, MAX_RETRIES type changed
        assert report.warning_count == 2

    def test_total_count(self, report: BreakingReport) -> None:
        """Total count should equal errors + warnings."""
        assert report.total_count == report.error_count + report.warning_count

    def test_identical_files_no_changes(
        self, analyzer: BreakingAnalyzer,
    ) -> None:
        """Comparing a file with itself should produce no changes."""
        old = str(FIXTURES_DIR / "old_version.py")
        report = analyzer.analyze(old, old)
        assert report.total_count == 0
        assert report.changes == []

    def test_optional_parameter_not_flagged(
        self, analyzer: BreakingAnalyzer, tmp_path: Path,
    ) -> None:
        """Adding an optional parameter (with default) should NOT be flagged."""
        old_file = tmp_path / "old.py"
        old_file.write_text(
            "def connect(host: str, port: int) -> None:\n    pass\n"
        )
        new_file = tmp_path / "new.py"
        new_file.write_text(
            "def connect(host: str, port: int, timeout: int = 30) -> None:\n"
            "    pass\n"
        )
        report = analyzer.analyze(str(old_file), str(new_file))
        param_added = [
            c for c in report.changes
            if c.kind is BreakingChangeKind.PARAMETER_ADDED
        ]
        assert param_added == []

    def test_adding_kwargs_not_flagged(
        self, analyzer: BreakingAnalyzer, tmp_path: Path,
    ) -> None:
        """Adding **kwargs should NOT be flagged as a required param."""
        old_file = tmp_path / "old.py"
        old_file.write_text("def fetch(url: str) -> None:\n    pass\n")
        new_file = tmp_path / "new.py"
        new_file.write_text(
            "def fetch(url: str, **kwargs) -> None:\n    pass\n"
        )
        report = analyzer.analyze(str(old_file), str(new_file))
        param_added = [
            c for c in report.changes
            if c.kind is BreakingChangeKind.PARAMETER_ADDED
        ]
        assert param_added == []

    def test_adding_varargs_not_flagged(
        self, analyzer: BreakingAnalyzer, tmp_path: Path,
    ) -> None:
        """Adding *args should NOT be flagged as a required param."""
        old_file = tmp_path / "old.py"
        old_file.write_text("def log(msg: str) -> None:\n    pass\n")
        new_file = tmp_path / "new.py"
        new_file.write_text(
            "def log(msg: str, *args) -> None:\n    pass\n"
        )
        report = analyzer.analyze(str(old_file), str(new_file))
        param_added = [
            c for c in report.changes
            if c.kind is BreakingChangeKind.PARAMETER_ADDED
        ]
        assert param_added == []

    def test_optional_kwonly_not_flagged(
        self, analyzer: BreakingAnalyzer, tmp_path: Path,
    ) -> None:
        """Adding keyword-only param with default should NOT be flagged."""
        old_file = tmp_path / "old.py"
        old_file.write_text("def send(data: bytes) -> None:\n    pass\n")
        new_file = tmp_path / "new.py"
        new_file.write_text(
            "def send(data: bytes, *, timeout: int = 30) -> None:\n    pass\n"
        )
        report = analyzer.analyze(str(old_file), str(new_file))
        param_added = [
            c for c in report.changes
            if c.kind is BreakingChangeKind.PARAMETER_ADDED
        ]
        assert param_added == []

    def test_required_kwonly_flagged(
        self, analyzer: BreakingAnalyzer, tmp_path: Path,
    ) -> None:
        """Adding keyword-only param WITHOUT default SHOULD be flagged."""
        old_file = tmp_path / "old.py"
        old_file.write_text("def send(data: bytes) -> None:\n    pass\n")
        new_file = tmp_path / "new.py"
        new_file.write_text(
            "def send(data: bytes, *, encoding: str) -> None:\n    pass\n"
        )
        report = analyzer.analyze(str(old_file), str(new_file))
        param_added = [
            c for c in report.changes
            if c.kind is BreakingChangeKind.PARAMETER_ADDED
        ]
        assert len(param_added) == 1
        assert "encoding" in param_added[0].description

    def test_removed_kwargs_flagged(
        self, analyzer: BreakingAnalyzer, tmp_path: Path,
    ) -> None:
        """Removing **kwargs IS a breaking change."""
        old_file = tmp_path / "old.py"
        old_file.write_text(
            "def fetch(url: str, **kwargs) -> None:\n    pass\n"
        )
        new_file = tmp_path / "new.py"
        new_file.write_text("def fetch(url: str) -> None:\n    pass\n")
        report = analyzer.analyze(str(old_file), str(new_file))
        param_removed = [
            c for c in report.changes
            if c.kind is BreakingChangeKind.PARAMETER_REMOVED
        ]
        assert len(param_removed) == 1
        assert "kwargs" in param_removed[0].description

    def test_posonly_param_detected(
        self, analyzer: BreakingAnalyzer, tmp_path: Path,
    ) -> None:
        """Removing a positional-only parameter is a breaking change."""
        old_file = tmp_path / "old.py"
        old_file.write_text(
            "def compute(x: int, y: int, /) -> int:\n    return x + y\n"
        )
        new_file = tmp_path / "new.py"
        new_file.write_text(
            "def compute(x: int, /) -> int:\n    return x\n"
        )
        report = analyzer.analyze(str(old_file), str(new_file))
        param_removed = [
            c for c in report.changes
            if c.kind is BreakingChangeKind.PARAMETER_REMOVED
        ]
        assert len(param_removed) == 1
        assert "y" in param_removed[0].description

    def test_camelcase_constant_type_change_detected(
        self, analyzer: BreakingAnalyzer, tmp_path: Path,
    ) -> None:
        """CamelCase constant (TYPE_ALIAS kind) type change should be detected."""
        old_file = tmp_path / "old.py"
        old_file.write_text("DefaultTimeout = 30\n")
        new_file = tmp_path / "new.py"
        new_file.write_text("DefaultTimeout = 'thirty'\n")
        report = analyzer.analyze(str(old_file), str(new_file))
        type_changes = [
            c for c in report.changes
            if c.kind is BreakingChangeKind.TYPE_CHANGED
        ]
        assert len(type_changes) == 1
        assert "int" in type_changes[0].description
        assert "str" in type_changes[0].description


class TestBreakingReporter:
    """Tests for the Markdown report generator."""

    def test_render_with_changes(self, report: BreakingReport) -> None:
        """Reporter should generate valid Markdown with a table."""
        reporter = BreakingReporter()
        output = reporter.render(report)

        assert "## Breaking Change Report" in output
        assert "| Symbol | Kind | Description | Severity |" in output
        assert "`process`" in output
        assert "**ERROR**" in output
        assert "WARNING" in output

    def test_render_no_changes(self, analyzer: BreakingAnalyzer) -> None:
        """Reporter should indicate no breaking changes when none exist."""
        old = str(FIXTURES_DIR / "old_version.py")
        report = analyzer.analyze(old, old)
        reporter = BreakingReporter()
        output = reporter.render(report)

        assert "No breaking changes detected." in output

    def test_render_summary_counts(self, report: BreakingReport) -> None:
        """Reporter should include error and warning counts in summary."""
        reporter = BreakingReporter()
        output = reporter.render(report)

        assert f"{report.error_count} errors" in output
        assert f"{report.warning_count} warnings" in output
