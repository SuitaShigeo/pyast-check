"""Detect API breaking changes between versions."""

from __future__ import annotations

import ast

from pyast_check.extractor import SymbolExtractor
from pyast_check.models import (
    BreakingChange,
    BreakingChangeKind,
    BreakingReport,
    Severity,
    SymbolInfo,
    SymbolKind,
)
from pyast_check.source import SourceResolver
from pyast_check.utils import parse_ast_dump, short_label


class BreakingAnalyzer:
    def __init__(self, *, resolver: SourceResolver | None = None) -> None:
        self._resolver = resolver or SourceResolver()
        self._extractor = SymbolExtractor()

    def analyze(self, old_spec: str, new_spec: str) -> BreakingReport:
        old_symbols = self._extract_symbols(old_spec)
        new_symbols = self._extract_symbols(new_spec)

        old_index = {s.name: s for s in old_symbols}
        new_index = {s.name: s for s in new_symbols}

        changes: list[BreakingChange] = []

        for name, old_sym in sorted(old_index.items()):
            if name not in new_index:
                changes.append(BreakingChange(
                    symbol_name=name,
                    kind=BreakingChangeKind.REMOVED,
                    severity=Severity.ERROR,
                    description=f"{old_sym.kind.value} `{name}` removed",
                ))
                continue

            new_sym = new_index[name]
            if old_sym.ast_dump == new_sym.ast_dump:
                continue

            # Detailed comparison based on kind
            if old_sym.kind is SymbolKind.FUNCTION:
                changes.extend(self._compare_functions(name, old_sym, new_sym))
            elif old_sym.kind is SymbolKind.CLASS:
                changes.extend(self._compare_classes(name, old_sym, new_sym))
            elif old_sym.kind in (SymbolKind.CONSTANT, SymbolKind.TYPE_ALIAS):
                changes.extend(self._compare_constants(name, old_sym, new_sym))

        return BreakingReport(
            old_label=short_label(old_spec),
            new_label=short_label(new_spec),
            changes=changes,
        )

    def _extract_symbols(self, spec: str) -> list[SymbolInfo]:
        """Extract symbols from a file or directory spec."""
        try:
            code = self._resolver.resolve_single(spec)
            return self._extractor.extract(code)
        except Exception:
            pass
        files = self._resolver.resolve_directory(spec)
        symbols: list[SymbolInfo] = []
        for code in files.values():
            symbols.extend(self._extractor.extract(code))
        return symbols

    def _compare_functions(
        self, name: str, old: SymbolInfo, new: SymbolInfo,
    ) -> list[BreakingChange]:
        changes: list[BreakingChange] = []
        old_node = parse_ast_dump(old.ast_dump)
        new_node = parse_ast_dump(new.ast_dump)
        if old_node is None or new_node is None:
            return changes

        if isinstance(old_node, (ast.FunctionDef, ast.AsyncFunctionDef)) and \
           isinstance(new_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Compare parameters
            old_args = _get_param_names(old_node.args)
            new_args = _get_param_names(new_node.args)
            new_required = _get_required_param_names(new_node.args)

            # Check for removed parameters
            removed = set(old_args) - set(new_args)
            for p in sorted(removed):
                if p in ("self", "cls"):
                    continue
                changes.append(BreakingChange(
                    symbol_name=name,
                    kind=BreakingChangeKind.PARAMETER_REMOVED,
                    severity=Severity.ERROR,
                    description=f"Parameter `{p}` removed",
                ))

            # Check for new required parameters
            added_required = set(new_required) - set(old_args)
            for p in sorted(added_required):
                if p in ("self", "cls"):
                    continue
                changes.append(BreakingChange(
                    symbol_name=name,
                    kind=BreakingChangeKind.PARAMETER_ADDED,
                    severity=Severity.ERROR,
                    description=f"Required parameter `{p}` added",
                ))

            # Check return type change
            old_ret = (
                ast.dump(old_node.returns, include_attributes=False)
                if old_node.returns
                else ""
            )
            new_ret = (
                ast.dump(new_node.returns, include_attributes=False)
                if new_node.returns
                else ""
            )
            if old_ret != new_ret:
                old_label = _type_label(old_node.returns)
                new_label = _type_label(new_node.returns)
                changes.append(BreakingChange(
                    symbol_name=name,
                    kind=BreakingChangeKind.RETURN_TYPE_CHANGED,
                    severity=Severity.WARNING,
                    description=f"Return type changed: {old_label} -> {new_label}",
                ))

        return changes

    def _compare_classes(
        self, name: str, old: SymbolInfo, new: SymbolInfo,
    ) -> list[BreakingChange]:
        changes: list[BreakingChange] = []
        old_node = parse_ast_dump(old.ast_dump)
        new_node = parse_ast_dump(new.ast_dump)
        if not isinstance(old_node, ast.ClassDef) or \
           not isinstance(new_node, ast.ClassDef):
            return changes

        # Base classes changed
        old_bases = [ast.dump(b, include_attributes=False) for b in old_node.bases]
        new_bases = [ast.dump(b, include_attributes=False) for b in new_node.bases]
        if old_bases != new_bases:
            changes.append(BreakingChange(
                symbol_name=name,
                kind=BreakingChangeKind.BASE_CLASSES_CHANGED,
                severity=Severity.WARNING,
                description="Base classes changed",
            ))

        # Public methods removed
        old_methods = {
            n.name for n in old_node.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            and not n.name.startswith("_")
        }
        new_methods = {
            n.name for n in new_node.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            and not n.name.startswith("_")
        }
        # Also include dunder methods as public
        old_methods |= {
            n.name for n in old_node.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            and n.name.startswith("__") and n.name.endswith("__")
        }
        new_methods |= {
            n.name for n in new_node.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            and n.name.startswith("__") and n.name.endswith("__")
        }
        removed_methods = old_methods - new_methods
        for m in sorted(removed_methods):
            changes.append(BreakingChange(
                symbol_name=f"{name}.{m}",
                kind=BreakingChangeKind.METHOD_REMOVED,
                severity=Severity.ERROR,
                description=f"Public method `{m}` removed from `{name}`",
            ))

        return changes

    def _compare_constants(
        self, name: str, old: SymbolInfo, new: SymbolInfo,
    ) -> list[BreakingChange]:
        changes: list[BreakingChange] = []
        old_node = parse_ast_dump(old.ast_dump)
        new_node = parse_ast_dump(new.ast_dump)
        if old_node is None or new_node is None:
            return changes

        old_val = _get_assign_value(old_node)
        new_val = _get_assign_value(new_node)
        if old_val is not None and new_val is not None:
            if type(old_val) is not type(new_val):
                changes.append(BreakingChange(
                    symbol_name=name,
                    kind=BreakingChangeKind.TYPE_CHANGED,
                    severity=Severity.WARNING,
                    description=(
                        f"Type changed: {type(old_val).__name__} -> "
                        f"{type(new_val).__name__}"
                    ),
                ))
        return changes


def _get_param_names(args: ast.arguments) -> list[str]:
    """Get all parameter names from an arguments node."""
    names = [arg.arg for arg in args.posonlyargs + args.args + args.kwonlyargs]
    if args.vararg:
        names.append(args.vararg.arg)
    if args.kwarg:
        names.append(args.kwarg.arg)
    return names


def _get_required_param_names(args: ast.arguments) -> list[str]:
    """Get names of parameters that have no default value.

    - ``posonlyargs + args``: ``args.defaults`` covers the last N of these.
    - ``kwonlyargs``: ``args.kw_defaults`` is a parallel list (``None`` = no default).
    - ``vararg`` / ``kwarg``: collectors, never "required".
    """
    positional = [arg.arg for arg in args.posonlyargs + args.args]
    defaults_count = len(args.defaults)
    if defaults_count:
        required = positional[:len(positional) - defaults_count]
    else:
        required = list(positional)

    for arg, default in zip(args.kwonlyargs, args.kw_defaults):
        if default is None:
            required.append(arg.arg)

    return required


def _type_label(node: ast.AST | None) -> str:
    if node is None:
        return "None"
    if isinstance(node, ast.Constant):
        return repr(node.value)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return ast.dump(node, include_attributes=False)
    return ast.dump(node, include_attributes=False)


def _get_assign_value(node: ast.AST) -> object | None:
    """Extract the constant value from an Assign node."""
    if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
        return node.value.value
    if isinstance(node, ast.AnnAssign) and node.value and \
       isinstance(node.value, ast.Constant):
        return node.value.value
    return None
