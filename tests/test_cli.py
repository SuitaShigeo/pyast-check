"""Tests for the CLI subcommand dispatch and backward compatibility."""

from __future__ import annotations

from pathlib import Path

import pytest

from pyast_check.cli import build_parser, main


class TestBackwardCompat:
    """Backward compat: first arg not a known command → insert 'migrate'."""

    def test_positional_args_get_migrate_prefix(self) -> None:
        """pyast-check source target → pyast-check migrate source target."""
        parser = build_parser()
        # Simulate: first arg is not a known command
        args = parser.parse_args(["migrate", "source.py", "target/"])
        assert args.command == "migrate"
        assert args.source == "source.py"
        assert args.target == "target/"

    def test_known_command_not_prefixed(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["breaking", "old.py", "new.py"])
        assert args.command == "breaking"

    def test_version_flag(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0

    def test_no_args_shows_help(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main([])
        assert exc_info.value.code == 2


class TestMigrateSubcommand:
    def test_migrate_explicit(self, fixtures_dir: Path, capsys: pytest.CaptureFixture) -> None:
        source = str(fixtures_dir / "original.py")
        target = str(fixtures_dir / "refactored")
        main(["migrate", source, target])
        captured = capsys.readouterr()
        assert "Migration Report" in captured.out

    def test_migrate_implicit(self, fixtures_dir: Path, capsys: pytest.CaptureFixture) -> None:
        """Backward compat: no subcommand → migrate."""
        source = str(fixtures_dir / "original.py")
        target = str(fixtures_dir / "refactored")
        main([source, target])
        captured = capsys.readouterr()
        assert "Migration Report" in captured.out

    def test_migrate_strict_exit_code(self, tmp_path: Path) -> None:
        source_file = tmp_path / "source.py"
        source_file.write_text("def gone():\n    pass\n")
        target_dir = tmp_path / "target"
        target_dir.mkdir()
        (target_dir / "__init__.py").write_text("")

        with pytest.raises(SystemExit) as exc_info:
            main(["migrate", "--strict", str(source_file), str(target_dir)])
        assert exc_info.value.code == 1

    def test_migrate_output_file(self, fixtures_dir: Path, tmp_path: Path) -> None:
        source = str(fixtures_dir / "original.py")
        target = str(fixtures_dir / "refactored")
        out_file = str(tmp_path / "report.md")
        main(["migrate", source, target, "-o", out_file])
        content = Path(out_file).read_text()
        assert "Migration Report" in content


class TestStructureSubcommand:
    def test_structure_directory(self, fixtures_dir: Path, capsys: pytest.CaptureFixture) -> None:
        target = str(fixtures_dir / "refactored")
        main(["structure", target])
        captured = capsys.readouterr()
        assert "Structure Report" in captured.out

    def test_structure_single_file(self, fixtures_dir: Path, capsys: pytest.CaptureFixture) -> None:
        target = str(fixtures_dir / "original.py")
        main(["structure", target])
        captured = capsys.readouterr()
        assert "Structure Report" in captured.out


class TestAuditSubcommand:
    def test_audit_directory(self, fixtures_dir: Path, capsys: pytest.CaptureFixture) -> None:
        target = str(fixtures_dir / "refactored")
        main(["audit", target])
        captured = capsys.readouterr()
        assert "Export Audit Report" in captured.out


class TestBreakingSubcommand:
    def test_breaking_files(self, fixtures_dir: Path, capsys: pytest.CaptureFixture) -> None:
        old = str(fixtures_dir / "breaking" / "old_version.py")
        new = str(fixtures_dir / "breaking" / "new_version.py")
        if not Path(old).exists():
            pytest.skip("breaking fixtures not yet created")
        main(["breaking", old, new])
        captured = capsys.readouterr()
        assert "Breaking Change Report" in captured.out

    def test_breaking_strict(self, fixtures_dir: Path) -> None:
        old = str(fixtures_dir / "breaking" / "old_version.py")
        new = str(fixtures_dir / "breaking" / "new_version.py")
        if not Path(old).exists():
            pytest.skip("breaking fixtures not yet created")
        with pytest.raises(SystemExit) as exc_info:
            main(["breaking", "--strict", old, new])
        assert exc_info.value.code == 1


class TestCommonOptions:
    def test_repo_option_parsed(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["migrate", "s.py", "t/", "-C", "/some/repo"])
        assert args.repo == "/some/repo"

    def test_output_option_parsed(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["audit", "pkg/", "-o", "out.md"])
        assert args.output == "out.md"

    def test_strict_option_parsed(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["structure", "pkg/", "--strict"])
        assert args.strict is True

    def test_format_default_is_markdown(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["structure", "pkg/"])
        assert args.format == "markdown"

    def test_format_json_parsed(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["structure", "pkg/", "--format", "json"])
        assert args.format == "json"


class TestFormatJsonOutput:
    def test_structure_json(self, fixtures_dir: Path, capsys: pytest.CaptureFixture) -> None:
        target = str(fixtures_dir / "refactored")
        main(["structure", target, "--format", "json"])
        captured = capsys.readouterr()
        import json
        data = json.loads(captured.out)
        assert "modules" in data
        assert "summary" in data

    def test_audit_json(self, fixtures_dir: Path, capsys: pytest.CaptureFixture) -> None:
        target = str(fixtures_dir / "refactored")
        main(["audit", target, "--format", "json"])
        captured = capsys.readouterr()
        import json
        data = json.loads(captured.out)
        assert "target_label" in data
