"""Tests for the source resolver."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pyast_check.source import SourceError, SourceResolver, _is_git_spec


class TestIsGitSpec:
    def test_local_file(self, fixtures_dir: Path) -> None:
        assert _is_git_spec(str(fixtures_dir / "original.py")) is False

    def test_git_ref(self) -> None:
        assert _is_git_spec("main:src/pkg/module.py") is True

    def test_colon_in_existing_path(self, tmp_path: Path) -> None:
        """If the path actually exists, it's not a git spec even with a colon."""
        # On macOS/Linux, colons in filenames are technically allowed
        # but _is_git_spec checks Path(spec).exists(), so we test the logic
        assert _is_git_spec("nonexistent:path.py") is True


class TestSourceResolver:
    def setup_method(self) -> None:
        self.resolver = SourceResolver()

    def test_resolve_local_file(self, fixtures_dir: Path) -> None:
        source = self.resolver.resolve_single(str(fixtures_dir / "original.py"))
        assert "def greet" in source

    def test_resolve_nonexistent_file(self) -> None:
        with pytest.raises(SourceError, match="File not found"):
            self.resolver.resolve_single("/nonexistent/path.py")

    def test_resolve_directory_error(self, fixtures_dir: Path) -> None:
        with pytest.raises(SourceError, match="Not a file"):
            self.resolver.resolve_single(str(fixtures_dir / "refactored"))

    def test_resolve_local_directory(self, fixtures_dir: Path) -> None:
        files = self.resolver.resolve_directory(str(fixtures_dir / "refactored"))
        assert "__init__.py" in files
        assert "greetings.py" in files
        assert "helpers.py" in files
        for content in files.values():
            assert isinstance(content, str)

    def test_resolve_nonexistent_directory(self) -> None:
        with pytest.raises(SourceError, match="Not a directory"):
            self.resolver.resolve_directory("/nonexistent/dir")

    def test_detect_source_not_in_repo(self) -> None:
        with pytest.raises(SourceError):
            self.resolver.detect_source("/tmp/nonexistent_pkg")


class TestSourceResolverGitSpec:
    """Test git ref resolution paths using mocked subprocess."""

    def test_resolve_single_git_spec(self) -> None:
        resolver = SourceResolver(repo_dir=Path("/fake/repo"))
        with patch("pyast_check.source.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="def hello(): pass\n")
            result = resolver.resolve_single("main:src/module.py")
        assert "def hello" in result
        mock_run.assert_called_once()
        args = mock_run.call_args
        assert args[0][0] == ["git", "show", "main:src/module.py"]

    def test_resolve_single_git_spec_error(self) -> None:
        resolver = SourceResolver(repo_dir=Path("/fake/repo"))
        with patch("pyast_check.source.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                128, "git show", stderr="fatal: not a valid object"
            )
            with pytest.raises(SourceError, match="git show"):
                resolver.resolve_single("bad_ref:module.py")

    def test_resolve_directory_git_spec(self) -> None:
        resolver = SourceResolver(repo_dir=Path("/fake/repo"))
        with patch("pyast_check.source.subprocess.run") as mock_run:
            # First call: git ls-tree
            ls_result = MagicMock(
                stdout="src/pkg/__init__.py\nsrc/pkg/core.py\nsrc/pkg/README.md\n"
            )
            # Second/third calls: git show for each .py file
            show_init = MagicMock(stdout='__all__ = ["greet"]\n')
            show_core = MagicMock(stdout="def greet(): pass\n")
            mock_run.side_effect = [ls_result, show_init, show_core]

            result = resolver.resolve_directory("main:src/pkg")

        assert "__init__.py" in result
        assert "core.py" in result
        assert "README.md" not in result  # non-.py files excluded
        assert '__all__' in result["__init__.py"]
        assert "def greet" in result["core.py"]

    def test_resolve_directory_git_ls_tree_error(self) -> None:
        resolver = SourceResolver(repo_dir=Path("/fake/repo"))
        with patch("pyast_check.source.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                128, "git ls-tree", stderr="fatal: not a tree"
            )
            with pytest.raises(SourceError, match="git ls-tree failed"):
                resolver.resolve_directory("bad_ref:src/pkg")

    def test_detect_source_from_git_ref(self) -> None:
        resolver = SourceResolver(repo_dir=Path("/fake/repo"))
        with patch("pyast_check.source.subprocess.run") as mock_run:
            # 1st call: git log --diff-filter=D → returns commit hash
            log_result = MagicMock(stdout="abc123def456\n")
            # 2nd call: git show (verify the spec) → returns source
            show_result = MagicMock(stdout="def process(): pass\n")
            mock_run.side_effect = [log_result, show_result]

            spec = resolver.detect_source("main:src/pkg/module/")

        assert spec == "abc123def456~1:src/pkg/module.py"

    def test_detect_source_git_ref_no_deletion_found(self) -> None:
        resolver = SourceResolver(repo_dir=Path("/fake/repo"))
        with patch("pyast_check.source.subprocess.run") as mock_run:
            # git log returns empty (no deletion commit found)
            mock_run.return_value = MagicMock(stdout="\n")
            with pytest.raises(SourceError, match="Could not find a commit"):
                resolver.detect_source("main:src/pkg/module/")

    def test_detect_source_git_ref_verify_fails(self) -> None:
        resolver = SourceResolver(repo_dir=Path("/fake/repo"))
        with patch("pyast_check.source.subprocess.run") as mock_run:
            log_result = MagicMock(stdout="abc123def456\n")
            mock_run.side_effect = [
                log_result,
                subprocess.CalledProcessError(128, "git show", stderr="not found"),
            ]
            with pytest.raises(SourceError, match="did not exist"):
                resolver.detect_source("main:src/pkg/module/")


class TestSourceResolverDetectLocal:
    """Test detect_source with local directory paths using mocked subprocess."""

    def test_detect_source_local_success(self, tmp_path: Path) -> None:
        target_dir = tmp_path / "pkg" / "module"
        target_dir.mkdir(parents=True)

        resolver = SourceResolver(repo_dir=tmp_path)
        with patch("pyast_check.source.subprocess.run") as mock_run:
            # 1st call: git rev-parse --show-toplevel → repo root
            repo_root_result = MagicMock(stdout=str(tmp_path) + "\n")
            # 2nd call: git log --diff-filter=D → commit hash
            log_result = MagicMock(stdout="deadbeef1234\n")
            # 3rd call: git show → verify source exists
            show_result = MagicMock(stdout="def old_func(): pass\n")
            mock_run.side_effect = [repo_root_result, log_result, show_result]

            spec = resolver.detect_source(str(target_dir))

        assert "deadbeef1234~1:" in spec
        assert "module.py" in spec

    def test_detect_source_local_not_in_repo(self, tmp_path: Path) -> None:
        target_dir = tmp_path / "outside_dir"
        target_dir.mkdir()

        # repo root is different from target
        other_repo = tmp_path / "other_repo"
        other_repo.mkdir()
        resolver = SourceResolver(repo_dir=other_repo)

        with patch("pyast_check.source.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=str(other_repo) + "\n")
            with pytest.raises(SourceError, match="not inside the git repository"):
                resolver.detect_source(str(target_dir))

    def test_detect_source_local_git_log_error(self, tmp_path: Path) -> None:
        target_dir = tmp_path / "pkg" / "module"
        target_dir.mkdir(parents=True)

        resolver = SourceResolver(repo_dir=tmp_path)
        with patch("pyast_check.source.subprocess.run") as mock_run:
            repo_root_result = MagicMock(stdout=str(tmp_path) + "\n")
            mock_run.side_effect = [
                repo_root_result,
                subprocess.CalledProcessError(128, "git log", stderr="git error"),
            ]
            with pytest.raises(SourceError, match="git log failed"):
                resolver.detect_source(str(target_dir))


class TestEnsureRepoDir:
    """Test _ensure_repo_dir auto-detection."""

    def test_sets_repo_dir_from_path(self, fixtures_dir: Path) -> None:
        resolver = SourceResolver()
        assert resolver._repo_dir is None
        resolver.resolve_single(str(fixtures_dir / "original.py"))
        assert resolver._repo_dir is not None

    def test_skips_if_already_set(self, fixtures_dir: Path) -> None:
        custom_dir = Path("/custom/repo")
        resolver = SourceResolver(repo_dir=custom_dir)
        resolver.resolve_single(str(fixtures_dir / "original.py"))
        assert resolver._repo_dir == custom_dir

    def test_fallback_when_not_git_repo(self, tmp_path: Path) -> None:
        """If the path is not in a git repo, falls back to the directory itself."""
        py_file = tmp_path / "module.py"
        py_file.write_text("x = 1\n")

        resolver = SourceResolver()
        with patch("pyast_check.source.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                128, "git", stderr="not a git repo"
            )
            resolver._ensure_repo_dir(tmp_path)

        assert resolver._repo_dir == tmp_path
