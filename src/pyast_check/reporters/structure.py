"""Generate Markdown reports for structure analysis."""

from __future__ import annotations

import io

from pyast_check.models import StructureReport


class StructureReporter:
    """Render a StructureReport as a GitHub-flavoured Markdown table."""

    def render(self, report: StructureReport) -> str:
        buf = io.StringIO()
        buf.write("## Structure Report\n\n")
        buf.write(f"**Target:** `{report.target_label}`\n")
        buf.write(
            f"**Summary:** {report.total_modules} modules, "
            f"{report.total_symbols} symbols, "
            f"{report.total_lines:,} lines\n\n"
        )
        buf.write("| Module | Lines | Functions | Classes | Constants | Total |\n")
        buf.write("|--------|-------|-----------|---------|-----------|-------|\n")
        for m in report.modules:
            buf.write(
                f"| `{m.module}` | {m.lines} | {m.functions} | {m.classes} "
                f"| {m.constants} | {m.total} |\n"
            )
        return buf.getvalue()
