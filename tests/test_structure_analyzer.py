"""Tests for the structure analyzer and reporter."""

from __future__ import annotations

from pathlib import Path

import pytest

from pyast_check.analyzers.structure import StructureAnalyzer
from pyast_check.reporters.structure import StructureReporter


@pytest.fixture
def analyzer() -> StructureAnalyzer:
    return StructureAnalyzer()


@pytest.fixture
def reporter() -> StructureReporter:
    return StructureReporter()


# ------------------------------------------------------------------
# Analyzer: directory analysis
# ------------------------------------------------------------------


class TestAnalyzeDirectory:
    """Tests for analyzing a directory of modules."""

    def test_all_modules_discovered(
        self, analyzer: StructureAnalyzer, fixtures_dir: Path
    ) -> None:
        report = analyzer.analyze(str(fixtures_dir / "refactored"))
        module_names = {m.module for m in report.modules}
        assert "__init__.py" in module_names
        assert "constants.py" in module_names
        assert "greetings.py" in module_names
        assert "helpers.py" in module_names
        assert "validation.py" in module_names

    def test_total_modules_count(
        self, analyzer: StructureAnalyzer, fixtures_dir: Path
    ) -> None:
        report = analyzer.analyze(str(fixtures_dir / "refactored"))
        assert report.total_modules == 5

    def test_target_label_is_directory(
        self, analyzer: StructureAnalyzer, fixtures_dir: Path
    ) -> None:
        report = analyzer.analyze(str(fixtures_dir / "refactored"))
        assert report.target_label == "refactored/"

    def test_greetings_symbols(
        self, analyzer: StructureAnalyzer, fixtures_dir: Path
    ) -> None:
        report = analyzer.analyze(str(fixtures_dir / "refactored"))
        greetings = next(m for m in report.modules if m.module == "greetings.py")
        assert greetings.functions == 2
        assert greetings.classes == 0
        assert greetings.constants == 0
        assert greetings.total == 2

    def test_constants_symbols(
        self, analyzer: StructureAnalyzer, fixtures_dir: Path
    ) -> None:
        report = analyzer.analyze(str(fixtures_dir / "refactored"))
        constants = next(m for m in report.modules if m.module == "constants.py")
        assert constants.functions == 0
        assert constants.classes == 0
        assert constants.constants == 2
        assert constants.total == 2

    def test_helpers_symbols(
        self, analyzer: StructureAnalyzer, fixtures_dir: Path
    ) -> None:
        report = analyzer.analyze(str(fixtures_dir / "refactored"))
        helpers = next(m for m in report.modules if m.module == "helpers.py")
        assert helpers.functions == 0
        assert helpers.classes == 1
        assert helpers.constants == 0
        assert helpers.total == 1

    def test_validation_symbols(
        self, analyzer: StructureAnalyzer, fixtures_dir: Path
    ) -> None:
        report = analyzer.analyze(str(fixtures_dir / "refactored"))
        validation = next(m for m in report.modules if m.module == "validation.py")
        assert validation.functions == 1
        assert validation.classes == 0
        assert validation.constants == 0
        assert validation.total == 1

    def test_init_symbols(
        self, analyzer: StructureAnalyzer, fixtures_dir: Path
    ) -> None:
        """__init__.py has no top-level function/class/constant definitions,
        only imports and __all__ (both skipped by the extractor)."""
        report = analyzer.analyze(str(fixtures_dir / "refactored"))
        init = next(m for m in report.modules if m.module == "__init__.py")
        assert init.total == 0

    def test_all_line_counts_positive(
        self, analyzer: StructureAnalyzer, fixtures_dir: Path
    ) -> None:
        report = analyzer.analyze(str(fixtures_dir / "refactored"))
        for m in report.modules:
            assert m.lines > 0, f"{m.module} should have positive line count"

    def test_total_lines_is_sum(
        self, analyzer: StructureAnalyzer, fixtures_dir: Path
    ) -> None:
        report = analyzer.analyze(str(fixtures_dir / "refactored"))
        assert report.total_lines == sum(m.lines for m in report.modules)

    def test_total_symbols_is_sum(
        self, analyzer: StructureAnalyzer, fixtures_dir: Path
    ) -> None:
        report = analyzer.analyze(str(fixtures_dir / "refactored"))
        assert report.total_symbols == sum(m.total for m in report.modules)


# ------------------------------------------------------------------
# Analyzer: single file analysis
# ------------------------------------------------------------------


class TestAnalyzeSingleFile:
    """Tests for analyzing a single Python file."""

    def test_single_file_one_module(
        self, analyzer: StructureAnalyzer, fixtures_dir: Path
    ) -> None:
        report = analyzer.analyze(str(fixtures_dir / "original.py"))
        assert report.total_modules == 1

    def test_single_file_module_name(
        self, analyzer: StructureAnalyzer, fixtures_dir: Path
    ) -> None:
        report = analyzer.analyze(str(fixtures_dir / "original.py"))
        assert report.modules[0].module == "original.py"

    def test_single_file_target_label(
        self, analyzer: StructureAnalyzer, fixtures_dir: Path
    ) -> None:
        report = analyzer.analyze(str(fixtures_dir / "original.py"))
        assert report.target_label == "original.py"

    def test_single_file_line_count_positive(
        self, analyzer: StructureAnalyzer, fixtures_dir: Path
    ) -> None:
        report = analyzer.analyze(str(fixtures_dir / "original.py"))
        assert report.modules[0].lines > 0

    def test_single_file_functions(
        self, analyzer: StructureAnalyzer, fixtures_dir: Path
    ) -> None:
        """original.py has greet, farewell, validate (public); _internal_helper is private."""
        report = analyzer.analyze(str(fixtures_dir / "original.py"))
        assert report.modules[0].functions == 3

    def test_single_file_classes(
        self, analyzer: StructureAnalyzer, fixtures_dir: Path
    ) -> None:
        """original.py has Helper class."""
        report = analyzer.analyze(str(fixtures_dir / "original.py"))
        assert report.modules[0].classes == 1

    def test_single_file_constants(
        self, analyzer: StructureAnalyzer, fixtures_dir: Path
    ) -> None:
        """original.py has MAX_RETRIES and TIMEOUT constants."""
        report = analyzer.analyze(str(fixtures_dir / "original.py"))
        assert report.modules[0].constants == 2

    def test_single_file_total_symbols(
        self, analyzer: StructureAnalyzer, fixtures_dir: Path
    ) -> None:
        report = analyzer.analyze(str(fixtures_dir / "original.py"))
        # 3 functions + 1 class + 2 constants = 6
        assert report.modules[0].total == 6


# ------------------------------------------------------------------
# Reporter
# ------------------------------------------------------------------


class TestStructureReporter:
    """Tests for the Markdown reporter."""

    def test_render_contains_heading(
        self, analyzer: StructureAnalyzer, reporter: StructureReporter, fixtures_dir: Path
    ) -> None:
        report = analyzer.analyze(str(fixtures_dir / "refactored"))
        output = reporter.render(report)
        assert "## Structure Report" in output

    def test_render_contains_target(
        self, analyzer: StructureAnalyzer, reporter: StructureReporter, fixtures_dir: Path
    ) -> None:
        report = analyzer.analyze(str(fixtures_dir / "refactored"))
        output = reporter.render(report)
        assert "**Target:**" in output
        assert "`refactored/`" in output

    def test_render_contains_summary(
        self, analyzer: StructureAnalyzer, reporter: StructureReporter, fixtures_dir: Path
    ) -> None:
        report = analyzer.analyze(str(fixtures_dir / "refactored"))
        output = reporter.render(report)
        assert "**Summary:**" in output
        assert "5 modules" in output

    def test_render_contains_table_header(
        self, analyzer: StructureAnalyzer, reporter: StructureReporter, fixtures_dir: Path
    ) -> None:
        report = analyzer.analyze(str(fixtures_dir / "refactored"))
        output = reporter.render(report)
        assert "| Module | Lines | Functions | Classes | Constants | Total |" in output

    def test_render_contains_module_rows(
        self, analyzer: StructureAnalyzer, reporter: StructureReporter, fixtures_dir: Path
    ) -> None:
        report = analyzer.analyze(str(fixtures_dir / "refactored"))
        output = reporter.render(report)
        assert "`greetings.py`" in output
        assert "`constants.py`" in output
        assert "`helpers.py`" in output
        assert "`validation.py`" in output
        assert "`__init__.py`" in output

    def test_render_is_valid_markdown(
        self, analyzer: StructureAnalyzer, reporter: StructureReporter, fixtures_dir: Path
    ) -> None:
        """Basic validation that the output looks like valid Markdown."""
        report = analyzer.analyze(str(fixtures_dir / "refactored"))
        output = reporter.render(report)
        lines = output.strip().splitlines()
        # Must start with heading
        assert lines[0].startswith("## ")
        # Table separator line must exist
        separator_lines = [line for line in lines if line.startswith("|---")]
        assert len(separator_lines) == 1

    def test_render_single_file(
        self, analyzer: StructureAnalyzer, reporter: StructureReporter, fixtures_dir: Path
    ) -> None:
        report = analyzer.analyze(str(fixtures_dir / "original.py"))
        output = reporter.render(report)
        assert "1 modules" in output or "1 module" in output
        assert "`original.py`" in output
