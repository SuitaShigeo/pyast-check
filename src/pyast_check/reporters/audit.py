"""Generate Markdown reports for export audit."""

from __future__ import annotations

import io

from pyast_check.models import AuditReport


class AuditReporter:
    """Render an AuditReport as a GitHub-flavoured Markdown table."""

    def render(self, report: AuditReport) -> str:
        buf = io.StringIO()
        buf.write("## Export Audit Report\n\n")
        buf.write(f"**Target:** `{report.target_label}`\n")
        buf.write(
            f"**Summary:** {report.total_symbols} symbols, "
            f"{report.exported_symbols} exported, "
            f"{report.issue_count} issues\n\n"
        )
        if not report.issues:
            buf.write("No issues found.\n")
            return buf.getvalue()

        buf.write("| Symbol | Issue | File | Description |\n")
        buf.write("|--------|-------|------|-------------|\n")
        for issue in report.issues:
            buf.write(
                f"| `{issue.symbol_name}` | {issue.kind.value} "
                f"| `{issue.file}` | {issue.description} |\n"
            )
        return buf.getvalue()
