"""Generate Markdown reports for migration analysis."""

from __future__ import annotations

import io

from pyast_check.models import MigrationReport, MigrationResult, MigrationStatus


class MigrationReporter:
    """Render a :class:`MigrationReport` as a GitHub-flavoured Markdown table."""

    def render(self, report: MigrationReport, *, verbose: bool = False) -> str:
        buf = io.StringIO()
        buf.write("## Refactoring Migration Report\n\n")
        buf.write(f"**Source:** `{report.source_label}`\n")
        buf.write(f"**Target:** `{report.target_label}`\n")
        buf.write(
            f"**Summary:** {report.identical_count}/{report.total_count} identical"
        )
        if report.modified_count:
            buf.write(f", {report.modified_count} modified")
        if report.missing_count:
            buf.write(f", {report.missing_count} missing")
        buf.write("\n\n")

        has_warnings = any(r.warnings for r in report.results)

        # Table header
        header = "| Symbol | Kind | Destination | Status |"
        separator = "|--------|------|-------------|--------|"
        if has_warnings:
            header += " Warnings |"
            separator += "----------|"
        buf.write(header + "\n")
        buf.write(separator + "\n")

        for r in report.results:
            buf.write(_row(r, has_warnings))
            buf.write("\n")

        if verbose:
            modified = [
                r for r in report.results if r.status is MigrationStatus.MODIFIED and r.diff
            ]
            if modified:
                buf.write("\n---\n\n### Diffs\n\n")
                for r in modified:
                    buf.write(f"#### `{r.symbol.name}`\n\n")
                    buf.write("```diff\n")
                    buf.write(r.diff)
                    buf.write("\n```\n\n")

        return buf.getvalue()


def _row(r: MigrationResult, show_warnings: bool) -> str:
    name = f"`{r.symbol.name}`"
    kind = r.symbol.kind.value
    dest = f"`{r.destination}`" if r.destination else "-"
    status = _status_cell(r)
    row = f"| {name} | {kind} | {dest} | {status} |"
    if show_warnings:
        warnings = "; ".join(r.warnings) if r.warnings else ""
        row += f" {warnings} |"
    return row


def _status_cell(r: MigrationResult) -> str:
    if r.status is MigrationStatus.IDENTICAL:
        return "OK"
    if r.status is MigrationStatus.MODIFIED:
        detail = r.notes or "Modified"
        return detail
    return "**MISSING**"
