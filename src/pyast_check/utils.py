"""Shared utility functions."""

from __future__ import annotations

import ast
from pathlib import Path


def short_label(spec: str) -> str:
    """Shorten a source/target spec for display.

    ``abc123~1:src/mypackage/cal.py`` -> ``abc123~1:cal.py``
    ``/Users/win/dev/mypackage/src/mypackage/cal/`` -> ``cal/``
    """
    if ":" in spec and not Path(spec).exists():
        # Git ref spec — shorten hash and path
        ref, _, path = spec.partition(":")
        # Shorten hash (keep first 8 chars + suffix like ~1)
        if len(ref) > 12 and not ref[0].isalpha():
            # Looks like a full SHA
            base = ref[:8]
            # Preserve ~N suffix
            for i, c in enumerate(ref):
                if c == "~":
                    base = ref[:8] + ref[i:]
                    break
            ref = base
        short_path = Path(path).name
        return f"{ref}:{short_path}"

    # Local path — show just the last component(s)
    path_obj = Path(spec)
    if path_obj.is_dir():
        return path_obj.name + "/"
    return path_obj.name


def _build_ast_namespace() -> dict:
    """Build a namespace mapping AST class names to their constructors."""
    ns: dict = {}
    for name in dir(ast):
        obj = getattr(ast, name)
        if isinstance(obj, type) and issubclass(obj, ast.AST):
            ns[name] = obj
    return ns


_AST_NS: dict = _build_ast_namespace()


def parse_ast_dump(dump: str) -> ast.AST | None:
    """Reconstruct an AST node from its ``ast.dump()`` string.

    Returns ``None`` if the dump cannot be parsed.
    """
    try:
        return eval(dump, {"__builtins__": {}}, _AST_NS)  # noqa: S307
    except Exception:
        return None
