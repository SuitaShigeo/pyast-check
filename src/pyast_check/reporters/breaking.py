"""Generate Markdown reports for breaking change detection."""

from __future__ import annotations

import io

from pyast_check.models import BreakingReport, Severity


class BreakingReporter:
    """Render a BreakingReport as a GitHub-flavoured Markdown table."""

    def render(self, report: BreakingReport) -> str:
        buf = io.StringIO()
        buf.write("## Breaking Change Report\n\n")
        buf.write(f"**Old:** `{report.old_label}`\n")
        buf.write(f"**New:** `{report.new_label}`\n")
        buf.write(
            f"**Summary:** {report.error_count} errors, "
            f"{report.warning_count} warnings\n\n"
        )
        if not report.changes:
            buf.write("No breaking changes detected.\n")
            return buf.getvalue()

        buf.write("| Symbol | Kind | Description | Severity |\n")
        buf.write("|--------|------|-------------|----------|\n")
        for c in report.changes:
            sev = "**ERROR**" if c.severity is Severity.ERROR else "WARNING"
            buf.write(
                f"| `{c.symbol_name}` | {c.kind.value} "
                f"| {c.description} | {sev} |\n"
            )
        return buf.getvalue()
