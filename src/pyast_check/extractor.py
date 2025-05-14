"""Extract top-level symbols from Python source using the AST."""

from __future__ import annotations

import ast

from pyast_check.models import SymbolInfo, SymbolKind


class SymbolExtractor:
    """Parse Python source and extract top-level symbols."""

    def extract(self, source: str) -> list[SymbolInfo]:
        """Return all top-level symbols found in *source*."""
        tree = ast.parse(source)
        symbols: list[SymbolInfo] = []
        for node in ast.iter_child_nodes(tree):
            info = self._classify(node, source)
            if info is not None:
                symbols.append(info)
        return symbols

    def extract_all_names(self, source: str) -> list[str]:
        """Return the contents of ``__all__`` if defined, else empty list."""
        tree = ast.parse(source)
        for node in ast.iter_child_nodes(tree):
            names = self._try_parse_all(node)
            if names is not None:
                return names
        return []

    def extract_imports(self, source: str) -> list[str]:
        """Return names re-exported via import statements at module level."""
        tree = ast.parse(source)
        names: list[str] = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    names.append(alias.asname if alias.asname else alias.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    names.append(alias.asname if alias.asname else alias.name)
        return names

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _classify(self, node: ast.AST, source: str) -> SymbolInfo | None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("_") and not node.name.startswith("__"):
                return None
            return self._make(node.name, SymbolKind.FUNCTION, node)
        if isinstance(node, ast.ClassDef):
            if node.name.startswith("_") and not node.name.startswith("__"):
                return None
            return self._make(node.name, SymbolKind.CLASS, node)
        if isinstance(node, ast.Assign):
            return self._handle_assign(node, source)
        if isinstance(node, ast.AnnAssign) and node.target and isinstance(
            node.target, ast.Name
        ):
            name = node.target.id
            if name == "__all__":
                return None
            kind = self._infer_kind_from_name(name)
            return self._make(name, kind, node)
        # Python 3.12+ type alias statement
        if isinstance(node, ast.AST) and type(node).__name__ == "TypeAlias":
            name_node = getattr(node, "name", None)
            if name_node and isinstance(name_node, ast.Name):
                return self._make(name_node.id, SymbolKind.TYPE_ALIAS, node)
        return None

    def _handle_assign(self, node: ast.Assign, source: str) -> SymbolInfo | None:
        if len(node.targets) != 1:
            return None
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            return None
        name = target.id
        if name.startswith("_") and not name.startswith("__"):
            return None
        if name == "__all__":
            return None
        kind = self._infer_kind_from_name(name)
        return self._make(name, kind, node)

    @staticmethod
    def _infer_kind_from_name(name: str) -> SymbolKind:
        if name.isupper() or (name.startswith("__") and name.endswith("__")):
            return SymbolKind.CONSTANT
        # TypeAlias convention: CamelCase name (e.g. ``UserId = int``)
        if name[0:1].isupper() and not name.isupper():
            return SymbolKind.TYPE_ALIAS
        return SymbolKind.CONSTANT

    @staticmethod
    def _make(name: str, kind: SymbolKind, node: ast.AST) -> SymbolInfo:
        dump = ast.dump(node, include_attributes=False)
        start = getattr(node, "lineno", 0)
        end = getattr(node, "end_lineno", start)
        return SymbolInfo(
            name=name,
            kind=kind,
            ast_dump=dump,
            source_lines=(start, end),
        )

    @staticmethod
    def _try_parse_all(node: ast.AST) -> list[str] | None:
        """Try to extract ``__all__ = [...]`` from an Assign node."""
        if not isinstance(node, ast.Assign):
            return None
        if len(node.targets) != 1:
            return None
        target = node.targets[0]
        if not isinstance(target, ast.Name) or target.id != "__all__":
            return None
        if not isinstance(node.value, (ast.List, ast.Tuple)):
            return None
        names: list[str] = []
        for elt in node.value.elts:
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                names.append(elt.value)
        return names
