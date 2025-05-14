"""Compare AST bodies of two symbols."""

from __future__ import annotations

import ast
import difflib

from pyast_check.models import MigrationStatus
from pyast_check.utils import parse_ast_dump


class BodyComparator:
    """Compare two symbol AST dumps and produce a human-readable diff."""

    def compare(
        self, source_dump: str, target_dump: str
    ) -> tuple[MigrationStatus, str]:
        """Compare two ``ast.dump`` strings.

        Returns ``(status, diff_text)``.
        *diff_text* is non-empty only when status is MODIFIED.
        """
        if source_dump == target_dump:
            return MigrationStatus.IDENTICAL, ""

        diff = self._unified_diff(source_dump, target_dump)
        return MigrationStatus.MODIFIED, diff

    @staticmethod
    def summarize_diff(source_dump: str, target_dump: str) -> str:
        """Return a short human-readable summary of what changed.

        Parses both AST dumps back into nodes and compares structural
        elements (arguments, decorators, body, etc.) to produce a
        meaningful description like "Type hints changed".
        """
        # Try to recover AST nodes for structural comparison
        src_node = parse_ast_dump(source_dump)
        tgt_node = parse_ast_dump(target_dump)

        if src_node is not None and tgt_node is not None:
            changes = _describe_changes(src_node, tgt_node)
            if changes:
                return "; ".join(changes)

        return "Structure changed"

    @staticmethod
    def _unified_diff(a: str, b: str) -> str:
        a_lines = a.splitlines(keepends=True)
        b_lines = b.splitlines(keepends=True)
        diff = difflib.unified_diff(
            a_lines, b_lines, fromfile="source", tofile="target", lineterm=""
        )
        return "".join(diff)


# ------------------------------------------------------------------
# Structural diff helpers
# ------------------------------------------------------------------


def _describe_changes(src: ast.AST, tgt: ast.AST) -> list[str]:
    """Compare two AST nodes and return human-readable change descriptions."""
    changes: list[str] = []

    if type(src) is not type(tgt):
        changes.append(f"Kind changed ({type(src).__name__} -> {type(tgt).__name__})")
        return changes

    # Function / method specific
    if isinstance(src, (ast.FunctionDef, ast.AsyncFunctionDef)):
        assert isinstance(tgt, (ast.FunctionDef, ast.AsyncFunctionDef))
        _compare_function(src, tgt, changes)
    elif isinstance(src, ast.ClassDef):
        assert isinstance(tgt, ast.ClassDef)
        _compare_class(src, tgt, changes)

    if not changes:
        changes.append("Body changed")

    return changes


def _dump(node: ast.AST | None) -> str:
    if node is None:
        return ""
    return ast.dump(node, include_attributes=False)


def _dump_list(nodes: list) -> str:
    return ",".join(ast.dump(n, include_attributes=False) for n in nodes)


def _compare_function(
    src: ast.FunctionDef | ast.AsyncFunctionDef,
    tgt: ast.FunctionDef | ast.AsyncFunctionDef,
    changes: list[str],
) -> None:
    # Return annotation
    if _dump(src.returns) != _dump(tgt.returns):
        changes.append("Return type changed")

    # Parameter annotations
    src_args = src.args
    tgt_args = tgt.args
    if _dump(src_args) != _dump(tgt_args):
        # Check if only annotations changed
        src_anno = _extract_annotations(src_args)
        tgt_anno = _extract_annotations(tgt_args)
        if src_anno != tgt_anno:
            changes.append("Type hints changed")
        else:
            changes.append("Parameters changed")

    # Decorators
    if _dump_list(src.decorator_list) != _dump_list(tgt.decorator_list):
        changes.append("Decorators changed")

    # Body
    if _dump_list(src.body) != _dump_list(tgt.body):
        if not changes:
            changes.append("Body changed")


def _compare_class(
    src: ast.ClassDef,
    tgt: ast.ClassDef,
    changes: list[str],
) -> None:
    # Bases
    if _dump_list(src.bases) != _dump_list(tgt.bases):
        changes.append("Base classes changed")

    # Decorators
    if _dump_list(src.decorator_list) != _dump_list(tgt.decorator_list):
        changes.append("Decorators changed")

    # Methods — compare individually
    src_methods = {n.name: n for n in src.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    tgt_methods = {n.name: n for n in tgt.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}

    added = set(tgt_methods) - set(src_methods)
    removed = set(src_methods) - set(tgt_methods)
    common = set(src_methods) & set(tgt_methods)

    if added:
        changes.append(f"Methods added: {', '.join(sorted(added))}")
    if removed:
        changes.append(f"Methods removed: {', '.join(sorted(removed))}")

    modified_methods: list[str] = []
    hint_changed = False
    for name in sorted(common):
        if _dump(src_methods[name]) != _dump(tgt_methods[name]):
            sub: list[str] = []
            _compare_function(src_methods[name], tgt_methods[name], sub)
            if sub == ["Type hints changed"] or sub == ["Return type changed"]:
                hint_changed = True
            elif sub == ["Type hints changed", "Return type changed"]:
                hint_changed = True
            else:
                modified_methods.append(name)

    if hint_changed and not modified_methods:
        changes.append("Type hints changed")
    elif hint_changed and modified_methods:
        changes.append("Type hints changed")
        changes.append(f"Methods modified: {', '.join(modified_methods)}")
    elif modified_methods:
        changes.append(f"Methods modified: {', '.join(modified_methods)}")

    # Class body (non-method attributes, class vars, etc.)
    src_other = [n for n in src.body if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    tgt_other = [n for n in tgt.body if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    if _dump_list(src_other) != _dump_list(tgt_other):
        changes.append("Class attributes changed")


def _extract_annotations(args: ast.arguments) -> list[str]:
    """Extract annotation dumps from an arguments node."""
    annos: list[str] = []
    for arg in args.args + args.posonlyargs + args.kwonlyargs:
        annos.append(_dump(arg.annotation))
    if args.vararg:
        annos.append(_dump(args.vararg.annotation))
    if args.kwarg:
        annos.append(_dump(args.kwarg.annotation))
    return annos
