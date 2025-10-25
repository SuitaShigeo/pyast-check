"""Tests for the symbol extractor."""

from __future__ import annotations

from pyast_check.extractor import SymbolExtractor
from pyast_check.models import SymbolKind


class TestSymbolExtractor:
    def setup_method(self) -> None:
        self.extractor = SymbolExtractor()

    def test_extract_functions(self, original_source: str) -> None:
        symbols = self.extractor.extract(original_source)
        names = {s.name for s in symbols if s.kind is SymbolKind.FUNCTION}
        assert "greet" in names
        assert "farewell" in names
        assert "validate" in names

    def test_extract_classes(self, original_source: str) -> None:
        symbols = self.extractor.extract(original_source)
        names = {s.name for s in symbols if s.kind is SymbolKind.CLASS}
        assert "Helper" in names

    def test_extract_constants(self, original_source: str) -> None:
        symbols = self.extractor.extract(original_source)
        names = {s.name for s in symbols if s.kind is SymbolKind.CONSTANT}
        assert "MAX_RETRIES" in names
        assert "TIMEOUT" in names

    def test_skips_private_symbols(self, original_source: str) -> None:
        symbols = self.extractor.extract(original_source)
        names = {s.name for s in symbols}
        assert "_internal_helper" not in names

    def test_extract_all_names(self, original_source: str) -> None:
        names = self.extractor.extract_all_names(original_source)
        assert names == ["greet", "farewell", "Helper", "MAX_RETRIES", "validate"]

    def test_extract_all_names_missing(self) -> None:
        source = "x = 1\n"
        names = self.extractor.extract_all_names(source)
        assert names == []

    def test_extract_imports(self) -> None:
        source = "from foo import bar, baz\nimport os\n"
        names = self.extractor.extract_imports(source)
        assert "bar" in names
        assert "baz" in names
        assert "os" in names

    def test_extract_empty_source(self) -> None:
        symbols = self.extractor.extract("")
        assert symbols == []

    def test_ast_dump_excludes_line_numbers(self) -> None:
        """Same function at different lines should produce the same ast_dump."""
        src_a = "def foo():\n    return 1\n"
        src_b = "\n\n\ndef foo():\n    return 1\n"
        syms_a = self.extractor.extract(src_a)
        syms_b = self.extractor.extract(src_b)
        assert syms_a[0].ast_dump == syms_b[0].ast_dump


class TestInferKindFromName:
    """Tests for CamelCase → TYPE_ALIAS and UPPER_CASE → CONSTANT heuristic."""

    def setup_method(self) -> None:
        self.extractor = SymbolExtractor()

    def test_upper_case_is_constant(self) -> None:
        symbols = self.extractor.extract("MAX_RETRIES = 3\n")
        assert symbols[0].kind is SymbolKind.CONSTANT

    def test_dunder_is_constant(self) -> None:
        symbols = self.extractor.extract("__version__ = '1.0'\n")
        assert symbols[0].kind is SymbolKind.CONSTANT

    def test_camel_case_is_type_alias(self) -> None:
        symbols = self.extractor.extract("UserId = int\n")
        assert symbols[0].kind is SymbolKind.TYPE_ALIAS

    def test_camel_case_multi_word_is_type_alias(self) -> None:
        symbols = self.extractor.extract("DefaultTimeout = 30\n")
        assert symbols[0].kind is SymbolKind.TYPE_ALIAS

    def test_lower_case_is_constant(self) -> None:
        symbols = self.extractor.extract("config_path = '/etc/app'\n")
        assert symbols[0].kind is SymbolKind.CONSTANT

    def test_single_upper_char_not_all_upper(self) -> None:
        symbols = self.extractor.extract("Timeout = 30\n")
        assert symbols[0].kind is SymbolKind.TYPE_ALIAS
