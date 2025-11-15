"""Tests for the audit analyzer and reporter."""

from __future__ import annotations

from pathlib import Path

import pytest

from pyast_check.analyzers.audit import AuditAnalyzer
from pyast_check.models import AuditIssueKind, AuditReport
from pyast_check.reporters.audit import AuditReporter


AUDIT_FIXTURES = Path(__file__).parent / "fixtures" / "audit"


class TestAuditAnalyzer:
    """Verify the AuditAnalyzer detects the expected issues."""

    @pytest.fixture()
    def report(self) -> AuditReport:
        analyzer = AuditAnalyzer()
        return analyzer.analyze(str(AUDIT_FIXTURES))

    def _issues_by_kind(
        self, report: AuditReport, kind: AuditIssueKind
    ) -> list[str]:
        """Return symbol names for issues of the given kind."""
        return [i.symbol_name for i in report.issues if i.kind is kind]

    # -- NOT_DEFINED -------------------------------------------------------

    def test_phantom_flagged_as_not_defined(self, report: AuditReport) -> None:
        """``phantom`` is listed in __all__ but never defined anywhere."""
        not_defined = self._issues_by_kind(report, AuditIssueKind.NOT_DEFINED)
        assert "phantom" in not_defined

    # -- SHADOWED ----------------------------------------------------------

    def test_shared_flagged_as_shadowed(self, report: AuditReport) -> None:
        """``shared`` is defined in both utils.py and extra.py."""
        shadowed = self._issues_by_kind(report, AuditIssueKind.SHADOWED)
        assert "shared" in shadowed

    def test_shadowed_issue_lists_both_files(self, report: AuditReport) -> None:
        """The file field for shadowed symbols should list all defining files."""
        shadowed_issues = [
            i for i in report.issues
            if i.kind is AuditIssueKind.SHADOWED and i.symbol_name == "shared"
        ]
        assert len(shadowed_issues) == 1
        assert "extra.py" in shadowed_issues[0].file
        assert "utils.py" in shadowed_issues[0].file

    # -- NOT_IN_ALL --------------------------------------------------------

    def test_shared_flagged_as_not_in_all(self, report: AuditReport) -> None:
        """``shared`` is defined but not listed in __all__."""
        not_in_all = self._issues_by_kind(report, AuditIssueKind.NOT_IN_ALL)
        assert "shared" in not_in_all

    # -- NOT_IMPORTED ------------------------------------------------------

    def test_helper_flagged_as_not_imported(self, report: AuditReport) -> None:
        """``helper`` is in __all__ but not imported in __init__.py."""
        not_imported = self._issues_by_kind(report, AuditIssueKind.NOT_IMPORTED)
        assert "helper" in not_imported

    # -- Summary counts ----------------------------------------------------

    def test_total_symbols(self, report: AuditReport) -> None:
        """Total symbols = unique names defined across non-init modules."""
        # greet, helper, shared = 3
        assert report.total_symbols == 3

    def test_exported_symbols(self, report: AuditReport) -> None:
        """Exported symbols = length of __all__."""
        # __all__ = ["greet", "helper", "phantom"]
        assert report.exported_symbols == 3

    def test_issue_count(self, report: AuditReport) -> None:
        """There should be at least 4 issues from the fixture."""
        assert report.issue_count >= 4


class TestAuditAnalyzerCleanPackage:
    """A package with no issues should produce a clean report."""

    def test_no_issues_for_clean_package(self, tmp_path: Path) -> None:
        pkg = tmp_path / "clean_pkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text(
            '__all__ = ["greet"]\nfrom clean_pkg.greetings import greet\n'
        )
        (pkg / "greetings.py").write_text(
            'def greet(name):\n    return f"Hello, {name}"\n'
        )

        analyzer = AuditAnalyzer()
        report = analyzer.analyze(str(pkg))

        assert report.issue_count == 0
        assert report.total_symbols == 1
        assert report.exported_symbols == 1

    def test_no_init_all(self, tmp_path: Path) -> None:
        """A package without __all__ should not flag NOT_IN_ALL."""
        pkg = tmp_path / "no_all_pkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "mod.py").write_text("def func():\n    pass\n")

        analyzer = AuditAnalyzer()
        report = analyzer.analyze(str(pkg))

        not_in_all = [
            i for i in report.issues if i.kind is AuditIssueKind.NOT_IN_ALL
        ]
        assert len(not_in_all) == 0
        assert report.exported_symbols == 0


class TestAuditReporter:
    """Verify Markdown report rendering."""

    def test_render_with_issues(self) -> None:
        analyzer = AuditAnalyzer()
        report = analyzer.analyze(str(AUDIT_FIXTURES))
        reporter = AuditReporter()
        md = reporter.render(report)

        assert "## Export Audit Report" in md
        assert "**Target:**" in md
        assert "**Summary:**" in md
        assert "| Symbol | Issue | File | Description |" in md
        assert "`phantom`" in md
        assert "`shared`" in md

    def test_render_no_issues(self, tmp_path: Path) -> None:
        pkg = tmp_path / "clean"
        pkg.mkdir()
        (pkg / "__init__.py").write_text(
            '__all__ = ["greet"]\nfrom clean.greetings import greet\n'
        )
        (pkg / "greetings.py").write_text(
            'def greet(name):\n    return f"Hello, {name}"\n'
        )

        analyzer = AuditAnalyzer()
        report = analyzer.analyze(str(pkg))
        reporter = AuditReporter()
        md = reporter.render(report)

        assert "No issues found." in md
        assert "| Symbol |" not in md
