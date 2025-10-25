"""Tests for the shared utility module."""

from __future__ import annotations

import ast

from pyast_check.utils import parse_ast_dump, short_label


class TestParseAstDump:
    def test_roundtrip_function(self) -> None:
        source = "def foo(x: int) -> str:\n    return str(x)\n"
        tree = ast.parse(source)
        node = tree.body[0]
        dump = ast.dump(node, include_attributes=False)
        recovered = parse_ast_dump(dump)
        assert recovered is not None
        assert isinstance(recovered, ast.FunctionDef)
        assert recovered.name == "foo"

    def test_roundtrip_class(self) -> None:
        source = "class Bar:\n    pass\n"
        tree = ast.parse(source)
        node = tree.body[0]
        dump = ast.dump(node, include_attributes=False)
        recovered = parse_ast_dump(dump)
        assert recovered is not None
        assert isinstance(recovered, ast.ClassDef)
        assert recovered.name == "Bar"

    def test_invalid_dump_returns_none(self) -> None:
        assert parse_ast_dump("not valid python ast") is None

    def test_empty_string_returns_none(self) -> None:
        assert parse_ast_dump("") is None


class TestShortLabel:
    def test_directory(self, tmp_path) -> None:
        label = short_label(str(tmp_path))
        assert label == tmp_path.name + "/"

    def test_file(self, tmp_path) -> None:
        f = tmp_path / "module.py"
        f.write_text("")
        label = short_label(str(f))
        assert label == "module.py"

    def test_git_ref(self) -> None:
        label = short_label("main:src/pkg/module.py")
        assert label == "main:module.py"

    def test_long_sha_shortened(self) -> None:
        # SHA starting with a digit triggers shortening heuristic
        sha = "1a2b3c4d" + "0" * 32
        label = short_label(f"{sha}:src/pkg/module.py")
        assert label == "1a2b3c4d:module.py"

    def test_sha_with_tilde_suffix(self) -> None:
        sha = "1a2b3c4d" + "0" * 32 + "~1"
        label = short_label(f"{sha}:src/pkg/module.py")
        assert label == "1a2b3c4d~1:module.py"

    def test_alpha_starting_sha_not_shortened(self) -> None:
        # SHA starting with a letter is not shortened (could be branch name)
        sha = "a" * 40
        label = short_label(f"{sha}:src/pkg/module.py")
        assert label == f"{sha}:module.py"
