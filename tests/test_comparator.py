"""Tests for the AST body comparator."""

from __future__ import annotations

import ast

from pyast_check.comparator import BodyComparator
from pyast_check.models import MigrationStatus


def _dump(code: str) -> str:
    """Parse code and dump the first statement's AST."""
    return ast.dump(ast.parse(code).body[0], include_attributes=False)


class TestBodyComparator:
    def setup_method(self) -> None:
        self.comparator = BodyComparator()

    def test_identical(self) -> None:
        dump = _dump("def foo(): return 1")
        status, diff = self.comparator.compare(dump, dump)
        assert status is MigrationStatus.IDENTICAL
        assert diff == ""

    def test_modified(self) -> None:
        src = _dump("def foo(): return 1")
        tgt = _dump("def foo(): return 2")
        status, diff = self.comparator.compare(src, tgt)
        assert status is MigrationStatus.MODIFIED
        assert diff != ""

    def test_whitespace_irrelevant(self) -> None:
        """Line numbers / whitespace should not affect AST dumps."""
        src_a = "def foo():\n    return 1\n"
        src_b = "\ndef foo():\n    return 1\n"
        dump_a = ast.dump(ast.parse(src_a).body[0], include_attributes=False)
        dump_b = ast.dump(ast.parse(src_b).body[0], include_attributes=False)
        status, _ = self.comparator.compare(dump_a, dump_b)
        assert status is MigrationStatus.IDENTICAL


class TestSummarizeDiffFunction:
    """Test summarize_diff with function-level changes."""

    def test_return_type_changed(self) -> None:
        src = _dump("def foo() -> int: return 1")
        tgt = _dump("def foo() -> str: return 1")
        summary = BodyComparator.summarize_diff(src, tgt)
        assert "Return type changed" in summary

    def test_type_hints_changed(self) -> None:
        src = _dump("def foo(x: int): return x")
        tgt = _dump("def foo(x: str): return x")
        summary = BodyComparator.summarize_diff(src, tgt)
        assert "Type hints changed" in summary

    def test_parameters_changed(self) -> None:
        src = _dump("def foo(x=1): return x")
        tgt = _dump("def foo(x=2): return x")
        summary = BodyComparator.summarize_diff(src, tgt)
        assert "Parameters changed" in summary

    def test_decorators_changed(self) -> None:
        src = _dump("def foo(): pass")
        tgt = _dump("@staticmethod\ndef foo(): pass")
        summary = BodyComparator.summarize_diff(src, tgt)
        assert "Decorators changed" in summary

    def test_body_changed_fallback(self) -> None:
        src = _dump("def foo(): return 1")
        tgt = _dump("def foo(): return 2")
        summary = BodyComparator.summarize_diff(src, tgt)
        assert "Body changed" in summary

    def test_invalid_dump_returns_structure_changed(self) -> None:
        summary = BodyComparator.summarize_diff("not_valid_ast", "also_not_valid")
        assert "Structure changed" in summary


class TestSummarizeDiffClass:
    """Test summarize_diff with class-level changes."""

    def test_base_classes_changed(self) -> None:
        src = _dump("class Foo: pass")
        tgt = _dump("class Foo(Base): pass")
        summary = BodyComparator.summarize_diff(src, tgt)
        assert "Base classes changed" in summary

    def test_decorators_changed(self) -> None:
        src = _dump("class Foo: pass")
        tgt = _dump("@dataclass\nclass Foo: pass")
        summary = BodyComparator.summarize_diff(src, tgt)
        assert "Decorators changed" in summary

    def test_method_added(self) -> None:
        src = _dump("class Foo:\n    def run(self): pass")
        tgt = _dump("class Foo:\n    def run(self): pass\n    def stop(self): pass")
        summary = BodyComparator.summarize_diff(src, tgt)
        assert "Methods added" in summary
        assert "stop" in summary

    def test_method_removed(self) -> None:
        src = _dump("class Foo:\n    def run(self): pass\n    def stop(self): pass")
        tgt = _dump("class Foo:\n    def run(self): pass")
        summary = BodyComparator.summarize_diff(src, tgt)
        assert "Methods removed" in summary
        assert "stop" in summary

    def test_method_modified(self) -> None:
        src = _dump("class Foo:\n    def run(self): return 1")
        tgt = _dump("class Foo:\n    def run(self): return 2")
        summary = BodyComparator.summarize_diff(src, tgt)
        assert "Methods modified" in summary
        assert "run" in summary

    def test_method_type_hints_only(self) -> None:
        src = _dump("class Foo:\n    def run(self, x: int): return x")
        tgt = _dump("class Foo:\n    def run(self, x: str): return x")
        summary = BodyComparator.summarize_diff(src, tgt)
        assert "Type hints changed" in summary

    def test_method_return_type_only(self) -> None:
        src = _dump("class Foo:\n    def run(self) -> int: return 1")
        tgt = _dump("class Foo:\n    def run(self) -> str: return 1")
        summary = BodyComparator.summarize_diff(src, tgt)
        assert "Type hints changed" in summary

    def test_method_both_hints_and_return_type(self) -> None:
        """When both hints and return type change, order matters for detection."""
        src = _dump("class Foo:\n    def run(self, x: int) -> int: return x")
        tgt = _dump("class Foo:\n    def run(self, x: str) -> str: return x")
        summary = BodyComparator.summarize_diff(src, tgt)
        # _compare_function produces ["Return type changed", "Type hints changed"]
        # which doesn't match the exact list checks in _compare_class,
        # so it falls through to "Methods modified"
        assert "Methods modified" in summary
        assert "run" in summary

    def test_method_hints_and_modified(self) -> None:
        src = _dump(
            "class Foo:\n"
            "    def run(self, x: int): return x\n"
            "    def stop(self): return 1"
        )
        tgt = _dump(
            "class Foo:\n"
            "    def run(self, x: str): return x\n"
            "    def stop(self): return 2"
        )
        summary = BodyComparator.summarize_diff(src, tgt)
        assert "Type hints changed" in summary
        assert "Methods modified" in summary
        assert "stop" in summary

    def test_class_attributes_changed(self) -> None:
        src = _dump("class Foo:\n    x = 1")
        tgt = _dump("class Foo:\n    x = 2")
        summary = BodyComparator.summarize_diff(src, tgt)
        assert "Class attributes changed" in summary


class TestSummarizeDiffKindChanged:
    """Test summarize_diff when the AST node type itself changes."""

    def test_function_to_class(self) -> None:
        src = _dump("def foo(): pass")
        tgt = _dump("class foo: pass")
        summary = BodyComparator.summarize_diff(src, tgt)
        assert "Kind changed" in summary
        assert "FunctionDef" in summary
        assert "ClassDef" in summary
