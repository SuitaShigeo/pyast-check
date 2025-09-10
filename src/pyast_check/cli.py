"""Command-line interface for pyast-check."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pyast_check import __version__

_KNOWN_COMMANDS = {"migrate", "breaking", "audit", "structure"}


def _add_common_options(parser: argparse.ArgumentParser) -> None:
    """Add options shared by all subcommands."""
    parser.add_argument(
        "-o", "--output",
        metavar="FILE",
        help="Write report to a file instead of stdout",
    )
    parser.add_argument(
        "-C", "--repo",
        metavar="DIR",
        help="Git repository directory (like git -C)",
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        dest="format",
        help="Output format (default: markdown)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with non-zero status if issues are found",
    )


def _build_migrate_parser(
    subparsers: argparse._SubParsersAction,
) -> None:
    p = subparsers.add_parser(
        "migrate",
        help="Verify refactoring migration",
        description="Verify that all symbols migrated correctly during a Python refactoring.",
    )
    p.add_argument(
        "source",
        nargs="?",
        default=None,
        help=(
            "Original source (file path or git ref, e.g. main:src/pkg/module.py). "
            "If omitted, auto-detected from git history of the target directory."
        ),
    )
    p.add_argument(
        "target",
        help="Refactored target (directory path or git ref, e.g. src/pkg/module/)",
    )
    p.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show unified diffs for modified symbols",
    )
    p.add_argument(
        "--ignore",
        nargs="*",
        default=[],
        metavar="NAME",
        help="Symbol names to ignore",
    )
    _add_common_options(p)


def _build_breaking_parser(
    subparsers: argparse._SubParsersAction,
) -> None:
    p = subparsers.add_parser(
        "breaking",
        help="Detect API breaking changes",
        description="Compare old and new versions to detect API breaking changes.",
    )
    p.add_argument("old", help="Old version (file/directory path or git ref)")
    p.add_argument("new", help="New version (file/directory path or git ref)")
    _add_common_options(p)


def _build_audit_parser(
    subparsers: argparse._SubParsersAction,
) -> None:
    p = subparsers.add_parser(
        "audit",
        help="Audit package exports",
        description="Check __all__, re-exports, and symbol shadowing in a package.",
    )
    p.add_argument("target", help="Package directory (local path or git ref)")
    _add_common_options(p)


def _build_structure_parser(
    subparsers: argparse._SubParsersAction,
) -> None:
    p = subparsers.add_parser(
        "structure",
        help="Visualize module structure",
        description="Show module statistics: symbols, lines, and composition.",
    )
    p.add_argument("target", help="File or package directory (local path or git ref)")
    _add_common_options(p)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pyast-check",
        description="Python AST analysis toolkit.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command")
    _build_migrate_parser(subparsers)
    _build_breaking_parser(subparsers)
    _build_audit_parser(subparsers)
    _build_structure_parser(subparsers)

    return parser


def _write_or_print(output: str, path: str | None) -> None:
    """Write output to file or stdout."""
    if path:
        out_path = Path(path)
        out_path.write_text(output, encoding="utf-8")
        print(f"Report written to {out_path}", file=sys.stderr)
    else:
        print(output)


def run_migrate(args: argparse.Namespace) -> None:
    from pyast_check.analyzers.migrate import MigrationAnalyzer
    from pyast_check.reporters.migrate import MigrationReporter
    from pyast_check.source import SourceResolver

    repo_dir = Path(args.repo).resolve() if args.repo else None
    resolver = SourceResolver(repo_dir=repo_dir)

    source_spec = args.source
    if source_spec is None:
        try:
            source_spec = resolver.detect_source(args.target)
        except Exception as exc:
            print(f"Auto-detection failed: {exc}", file=sys.stderr)
            sys.exit(2)
        print(f"Auto-detected source: `{source_spec}`\n", file=sys.stderr)

    analyzer = MigrationAnalyzer(
        ignore=set(args.ignore),
        verbose=args.verbose,
        resolver=resolver,
    )

    try:
        report = analyzer.analyze(source_spec, args.target)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(2)

    if args.format == "json":
        from pyast_check.reporters.json_reporter import JsonReporter
        output = JsonReporter().render_migration(report, verbose=args.verbose)
    else:
        reporter = MigrationReporter()
        output = reporter.render(report, verbose=args.verbose)
    _write_or_print(output, args.output)

    if args.strict and (report.missing_count or report.modified_count):
        sys.exit(1)


def run_breaking(args: argparse.Namespace) -> None:
    from pyast_check.analyzers.breaking import BreakingAnalyzer
    from pyast_check.reporters.breaking import BreakingReporter
    from pyast_check.source import SourceResolver

    repo_dir = Path(args.repo).resolve() if args.repo else None
    resolver = SourceResolver(repo_dir=repo_dir)

    try:
        analyzer = BreakingAnalyzer(resolver=resolver)
        report = analyzer.analyze(args.old, args.new)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(2)

    if args.format == "json":
        from pyast_check.reporters.json_reporter import JsonReporter
        output = JsonReporter().render_breaking(report)
    else:
        reporter = BreakingReporter()
        output = reporter.render(report)
    _write_or_print(output, args.output)

    if args.strict and report.error_count:
        sys.exit(1)


def run_audit(args: argparse.Namespace) -> None:
    from pyast_check.analyzers.audit import AuditAnalyzer
    from pyast_check.reporters.audit import AuditReporter
    from pyast_check.source import SourceResolver

    repo_dir = Path(args.repo).resolve() if args.repo else None
    resolver = SourceResolver(repo_dir=repo_dir)

    try:
        analyzer = AuditAnalyzer(resolver=resolver)
        report = analyzer.analyze(args.target)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(2)

    if args.format == "json":
        from pyast_check.reporters.json_reporter import JsonReporter
        output = JsonReporter().render_audit(report)
    else:
        reporter = AuditReporter()
        output = reporter.render(report)
    _write_or_print(output, args.output)

    if args.strict and report.issue_count:
        sys.exit(1)


def run_structure(args: argparse.Namespace) -> None:
    from pyast_check.analyzers.structure import StructureAnalyzer
    from pyast_check.reporters.structure import StructureReporter
    from pyast_check.source import SourceResolver

    repo_dir = Path(args.repo).resolve() if args.repo else None
    resolver = SourceResolver(repo_dir=repo_dir)

    try:
        analyzer = StructureAnalyzer(resolver=resolver)
        report = analyzer.analyze(args.target)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(2)

    if args.format == "json":
        from pyast_check.reporters.json_reporter import JsonReporter
        output = JsonReporter().render_structure(report)
    else:
        reporter = StructureReporter()
        output = reporter.render(report)
    _write_or_print(output, args.output)


def main(argv: list[str] | None = None) -> None:
    argv = argv if argv is not None else sys.argv[1:]

    # Backward compat: if first arg is not a known command, insert "migrate"
    if argv and argv[0] not in _KNOWN_COMMANDS and not argv[0].startswith("-"):
        argv = ["migrate"] + argv

    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        sys.exit(2)

    dispatch = {
        "migrate": run_migrate,
        "breaking": run_breaking,
        "audit": run_audit,
        "structure": run_structure,
    }
    dispatch[args.command](args)
