# pyast-check

Python AST 分析ツールキット。コードの構造を AST レベルで解析し、リファクタリング検証・破壊的変更検出・エクスポート監査・構造可視化を行う。

## Installation

```bash
pip install pyast-check
```

## サブコマンド一覧

| サブコマンド | 説明 | 入力 |
|---|---|---|
| `migrate` | リファクタリング移行検証 | `[source] target` |
| `breaking` | API 破壊的変更の検出 | `old new` |
| `audit` | パッケージエクスポート監査 | `target` |
| `structure` | モジュール構造の可視化 | `target` |

```bash
pyast-check migrate source target
pyast-check breaking old_version.py new_version.py
pyast-check audit src/mypackage/
pyast-check structure src/mypackage/

# 後方互換: サブコマンド省略時は migrate
pyast-check source target
```

### 共通オプション

```bash
-o FILE    # Markdown ファイルに出力
-C DIR     # Git リポジトリディレクトリを指定
--strict   # 問題があれば終了コード 1
```

## migrate — リファクタリング移行検証

1ファイルをパッケージに分割したとき、**全シンボルが正しく移動されたか** を検証する。

```bash
# source を git 履歴から自動検出
pyast-check migrate src/mypackage/module/

# source と target を明示
pyast-check migrate 'main:src/pkg/module.py' src/pkg/module/

# git ref を指定
pyast-check migrate 'upstream/main:src/pkg/module.py' src/pkg/module/
```

**固有オプション:**

```bash
--verbose, -v    # Modified シンボルの diff 詳細を表示
--ignore NAME    # 特定のシンボルを無視
```

**出力例:**

```markdown
## Refactoring Migration Report

**Source:** `0501c9d4~1:parser.py`
**Target:** `upstream/main:parser`
**Summary:** 26/31 identical, 4 modified, 1 missing

| Symbol | Kind | Destination | Status | Warnings |
|--------|------|-------------|--------|----------|
| `FOLD` | constant | - | **MISSING** |  |
| `escape_char` | function | `string.py` | Body changed |  |
| `Contentline` | class | `content_line.py` | OK |  |
| `NAME` | constant | `string.py` | OK | MISSING from __all__ |
```

| Status | 意味 |
|--------|------|
| OK | AST 構造が完全一致 |
| Type hints changed | 型ヒントのみ変更、ロジック同一 |
| Body changed | 関数/メソッドの実装が変更 |
| Methods added: ... | クラスにメソッドが追加 |
| **MISSING** | ターゲットにシンボルが見つからない |

## breaking — API 破壊的変更の検出

旧バージョンと新バージョンを比較し、破壊的な API 変更を検出する。

```bash
pyast-check breaking old_api.py new_api.py
pyast-check breaking 'v1.0:src/lib/api.py' src/lib/api.py
pyast-check breaking old_package/ new_package/
```

**検出ルール:**

| 変更 | 深刻度 |
|------|--------|
| パブリックシンボルの削除 | ERROR |
| 必須パラメータの追加 | ERROR |
| パラメータの削除 | ERROR |
| パブリックメソッドの削除 | ERROR |
| 戻り値の型変更 | WARNING |
| 基底クラスの変更 | WARNING |
| 定数の型変更 | WARNING |

**出力例:**

```markdown
## Breaking Change Report

**Old:** `v1.0:api.py`
**New:** `api.py`
**Summary:** 3 errors, 2 warnings

| Symbol | Kind | Description | Severity |
|--------|------|-------------|----------|
| `process` | function | Removed | ERROR |
| `greet` | function | Required parameter added: `formal` | ERROR |
| `Service.stop` | method | Removed | ERROR |
| `validate` | function | Return type changed: bool → int | WARNING |
| `MAX_RETRIES` | constant | Type changed: int → str | WARNING |
```

## audit — パッケージエクスポート監査

パッケージの `__all__`、re-import、シンボル定義の整合性をチェックする。

```bash
pyast-check audit src/mypackage/
```

**チェック項目:**

| Issue | 意味 |
|-------|------|
| Not in `__all__` | 定義済みだが `__all__` に未登録 |
| Not defined | `__all__` にあるが定義が見つからない |
| Not imported in `__init__` | `__all__` にあるが `__init__.py` で re-import されていない |
| Shadowed | 複数ファイルで同名シンボルが定義されている |

**出力例:**

```markdown
## Export Audit Report

**Target:** `src/mypackage/`
**Summary:** 15 symbols, 12 exported, 3 issues

| Symbol | Issue | File | Description |
|--------|-------|------|-------------|
| `helper` | Not in __all__ | `utils.py` | Defined but not exported |
| `phantom` | Not defined | `__init__.py` | Listed in __all__ but not found |
| `parse` | Shadowed | `a.py`, `b.py` | Defined in multiple modules |
```

## structure — モジュール構造の可視化

ファイルまたはパッケージのシンボル構成を一覧表示する。

```bash
pyast-check structure src/mypackage/
pyast-check structure single_module.py
```

**出力例:**

```markdown
## Structure Report

**Target:** `src/mypackage/`
**Summary:** 5 modules, 45 symbols, 1,230 lines

| Module | Lines | Functions | Classes | Constants | Total |
|--------|-------|-----------|---------|-----------|-------|
| `__init__.py` | 50 | 0 | 0 | 2 | 2 |
| `core.py` | 450 | 12 | 3 | 5 | 20 |
| `utils.py` | 300 | 8 | 1 | 3 | 12 |
| `helpers.py` | 230 | 6 | 0 | 2 | 8 |
| `types.py` | 200 | 0 | 2 | 1 | 3 |
```

## How It Works

全サブコマンドは Python 標準ライブラリの `ast` モジュールでソースコードを解析する。

```
ソースコード  ──→  ast.parse  ──→  シンボル抽出  ──→  分析  ──→  Markdown レポート
```

**入力の解決:** ローカルファイルパスと git ref（`main:src/pkg/module.py`）の両方に対応。`-C` オプションでリポジトリ外からも実行可能。

**AST 比較:** `ast.dump(node, include_attributes=False)` で行番号を除いた構造のみを比較するため、移動やフォーマット変更を正確に検出できる。

## Requirements

- Python >= 3.10
- Git（git ref を使う場合）
- 外部依存なし（標準ライブラリのみ）

## License

MIT
