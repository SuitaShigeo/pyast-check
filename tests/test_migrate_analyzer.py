"""Tests for the migration analyzer."""

from __future__ import annotations

from pathlib import Path

from pyast_check.analyzers.migrate import MigrationAnalyzer
from pyast_check.models import MigrationStatus


class TestMigrationAnalyzer:
    def test_full_analysis(self, fixtures_dir: Path) -> None:
        analyzer = MigrationAnalyzer()
        source = str(fixtures_dir / "original.py")
        target = str(fixtures_dir / "refactored")
        report = analyzer.analyze(source, target)

        names = {r.symbol.name: r for r in report.results}

        # greet and farewell should be identical
        assert names["greet"].status is MigrationStatus.IDENTICAL
        assert names["farewell"].status is MigrationStatus.IDENTICAL
        assert names["greet"].destination == "greetings.py"

        # Helper should be identical
        assert names["Helper"].status is MigrationStatus.IDENTICAL
        assert names["Helper"].destination == "helpers.py"

        # Constants should be found
        assert names["MAX_RETRIES"].status is MigrationStatus.IDENTICAL
        assert names["TIMEOUT"].status is MigrationStatus.IDENTICAL

    def test_missing_symbol_detected(self, fixtures_dir: Path, tmp_path: Path) -> None:
        """Symbol not present in target should be MISSING."""
        # Create a source with a symbol that won't be in the target
        source_file = tmp_path / "source.py"
        source_file.write_text("def unique_func():\n    return 42\n")

        target_dir = tmp_path / "target"
        target_dir.mkdir()
        (target_dir / "__init__.py").write_text("")
        (target_dir / "other.py").write_text("def other():\n    pass\n")

        analyzer = MigrationAnalyzer()
        report = analyzer.analyze(str(source_file), str(target_dir))

        assert report.missing_count == 1
        assert report.results[0].symbol.name == "unique_func"
        assert report.results[0].status is MigrationStatus.MISSING

    def test_modified_symbol_detected(self, tmp_path: Path) -> None:
        """Changed function body should be flagged as MODIFIED."""
        source_file = tmp_path / "source.py"
        source_file.write_text("def compute(x: int) -> int:\n    return x + 1\n")

        target_dir = tmp_path / "target"
        target_dir.mkdir()
        (target_dir / "__init__.py").write_text("")
        (target_dir / "math.py").write_text(
            "def compute(x: int) -> int:\n    return x + 2\n"
        )

        analyzer = MigrationAnalyzer()
        report = analyzer.analyze(str(source_file), str(target_dir))

        assert report.modified_count == 1
        assert report.results[0].status is MigrationStatus.MODIFIED

    def test_ignore_option(self, fixtures_dir: Path) -> None:
        analyzer = MigrationAnalyzer(ignore={"greet", "farewell"})
        source = str(fixtures_dir / "original.py")
        target = str(fixtures_dir / "refactored")
        report = analyzer.analyze(source, target)

        names = {r.symbol.name for r in report.results}
        assert "greet" not in names
        assert "farewell" not in names

    def test_verbose_includes_diff(self, tmp_path: Path) -> None:
        source_file = tmp_path / "source.py"
        source_file.write_text("def f():\n    return 1\n")

        target_dir = tmp_path / "target"
        target_dir.mkdir()
        (target_dir / "__init__.py").write_text("")
        (target_dir / "mod.py").write_text("def f():\n    return 2\n")

        analyzer = MigrationAnalyzer(verbose=True)
        report = analyzer.analyze(str(source_file), str(target_dir))

        assert report.results[0].diff != ""

    def test_init_all_warning(self, fixtures_dir: Path) -> None:
        """validate is missing from __init__.py __all__."""
        analyzer = MigrationAnalyzer()
        source = str(fixtures_dir / "original.py")
        target = str(fixtures_dir / "refactored")
        report = analyzer.analyze(source, target)

        validate_result = next(
            r for r in report.results if r.symbol.name == "validate"
        )
        assert "MISSING from __all__" in validate_result.warnings
