"""Resolve source code from local files or git refs."""

from __future__ import annotations

import subprocess
from pathlib import Path


class SourceError(Exception):
    """Raised when a source cannot be resolved."""


def _is_git_spec(spec: str) -> bool:
    """Return True if *spec* looks like ``ref:path`` rather than a local path."""
    return ":" in spec and not Path(spec).exists()


class SourceResolver:
    """Read Python sources from local paths or ``git show ref:path``.

    Parameters
    ----------
    repo_dir:
        Working directory for git commands.  When *None* it is inferred
        from the first path that is passed to any method.
    """

    def __init__(self, repo_dir: Path | None = None) -> None:
        self._repo_dir = repo_dir

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve_single(self, spec: str) -> str:
        """Return Python source code for *spec*.

        *spec* is either a local file path or ``ref:path`` for a git object.
        """
        if _is_git_spec(spec):
            return self._git_show(spec)
        path = Path(spec)
        if not path.exists():
            raise SourceError(f"File not found: {spec}")
        if not path.is_file():
            raise SourceError(f"Not a file: {spec}")
        self._ensure_repo_dir(path.parent)
        return path.read_text(encoding="utf-8")

    def resolve_directory(self, spec: str) -> dict[str, str]:
        """Return ``{relative_path: source}`` for every ``.py`` in *spec*.

        *spec* is either a local directory or ``ref:path/`` for a git tree.
        """
        if _is_git_spec(spec):
            return self._git_ls_tree(spec)
        path = Path(spec)
        if not path.is_dir():
            raise SourceError(f"Not a directory: {spec}")
        self._ensure_repo_dir(path)
        result: dict[str, str] = {}
        for py in sorted(path.rglob("*.py")):
            rel = str(py.relative_to(path))
            result[rel] = py.read_text(encoding="utf-8")
        return result

    def detect_source(self, target_spec: str) -> str:
        """Auto-detect the original ``.py`` file before a package split.

        Works with both local directories and git ref specs:
        - ``src/mypackage/parser/`` -> finds when ``src/mypackage/parser.py`` was deleted
        - ``upstream/main:src/mypackage/parser/`` -> finds the same, using the tree path
        """
        if _is_git_spec(target_spec):
            return self._detect_source_from_git_ref(target_spec)
        return self._detect_source_from_local(target_spec)

    # ------------------------------------------------------------------
    # Auto-detection implementations
    # ------------------------------------------------------------------

    def _detect_source_from_local(self, target_dir: str) -> str:
        """Auto-detect source from a local directory target."""
        path = Path(target_dir).resolve()
        self._ensure_repo_dir(path)

        repo_root = self._find_repo_root()
        candidate_py = str(path) + ".py"
        try:
            rel_path = Path(candidate_py).relative_to(repo_root)
        except ValueError:
            raise SourceError(
                f"Target {target_dir} is not inside the git repository at {repo_root}"
            )

        return self._find_deletion_source(str(rel_path))

    def _detect_source_from_git_ref(self, target_spec: str) -> str:
        """Auto-detect source from a git ref target like ``ref:path/``."""
        ref, _, tree_path = target_spec.partition(":")
        tree_path = tree_path.rstrip("/")
        # The original file would be tree_path + ".py"
        rel_path = tree_path + ".py"

        return self._find_deletion_source(rel_path)

    def _find_deletion_source(self, rel_path: str) -> str:
        """Find the commit that deleted *rel_path* and return a source spec."""
        try:
            log = subprocess.run(
                [
                    "git", "log", "--all", "--diff-filter=D",
                    "--format=%H", "-1", "--", rel_path,
                ],
                capture_output=True,
                text=True,
                check=True,
                cwd=self._repo_dir,
            )
        except subprocess.CalledProcessError as exc:
            raise SourceError(
                f"git log failed: {exc.stderr.strip()}"
            ) from exc

        commit = log.stdout.strip()
        if not commit:
            raise SourceError(
                f"Could not find a commit that deleted {rel_path}. "
                f"Specify the source explicitly (e.g. main:{rel_path})."
            )

        spec = f"{commit}~1:{rel_path}"
        # Verify it actually exists at that ref
        try:
            self._git_show(spec)
        except SourceError:
            raise SourceError(
                f"Found deletion commit {commit[:12]} but {rel_path} "
                f"did not exist at {commit}~1."
            )
        return spec

    # ------------------------------------------------------------------
    # Git helpers
    # ------------------------------------------------------------------

    def _find_repo_root(self) -> Path:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                check=True,
                cwd=self._repo_dir,
            )
        except subprocess.CalledProcessError as exc:
            raise SourceError("Not inside a git repository") from exc
        return Path(result.stdout.strip())

    def _git_show(self, spec: str) -> str:
        """Run ``git show <spec>`` and return its output."""
        try:
            result = subprocess.run(
                ["git", "show", spec],
                capture_output=True,
                text=True,
                check=True,
                cwd=self._repo_dir,
            )
        except subprocess.CalledProcessError as exc:
            raise SourceError(
                f"git show {spec} failed: {exc.stderr.strip()}"
            ) from exc
        return result.stdout

    def _git_ls_tree(self, spec: str) -> dict[str, str]:
        """List ``.py`` blobs under a git tree and read each one."""
        ref, _, tree_path = spec.partition(":")
        tree_path = tree_path.rstrip("/")
        try:
            ls = subprocess.run(
                ["git", "ls-tree", "-r", "--name-only", ref, f"{tree_path}/"],
                capture_output=True,
                text=True,
                check=True,
                cwd=self._repo_dir,
            )
        except subprocess.CalledProcessError as exc:
            raise SourceError(
                f"git ls-tree failed: {exc.stderr.strip()}"
            ) from exc

        result: dict[str, str] = {}
        for line in ls.stdout.splitlines():
            if not line.endswith(".py"):
                continue
            rel = line
            if rel.startswith(tree_path + "/"):
                rel = rel[len(tree_path) + 1:]
            blob_spec = f"{ref}:{line}"
            content = self._git_show(blob_spec)
            result[rel] = content
        return result

    def _ensure_repo_dir(self, path: Path) -> None:
        """Set ``_repo_dir`` to the git repo root inferred from *path*."""
        if self._repo_dir is not None:
            return
        candidate = path if path.is_dir() else path.parent
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                check=True,
                cwd=candidate,
            )
            self._repo_dir = Path(result.stdout.strip())
        except (subprocess.CalledProcessError, OSError):
            # Not a git repo — fall back to the directory itself
            self._repo_dir = candidate
