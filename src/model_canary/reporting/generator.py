from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from model_canary.core.interfaces import Reporter
from model_canary.core.models import CanaryRunResult, DriftSeverity


class ReportGenerator(Reporter):
    @property
    def name(self) -> str:
        return "html"

    async def generate_report(
        self,
        run_result: CanaryRunResult,
        format: str = "html",
        **kwargs: Any,
    ) -> str:
        if format == "html":
            return self._generate_html(run_result)
        if format == "md" or format == "markdown":
            return self._generate_markdown(run_result)
        if format == "json":
            return self._generate_json(run_result)
        if format == "csv":
            return self._generate_csv(run_result)
        return self._generate_html(run_result)

    def _generate_html(self, result: CanaryRunResult) -> str:
        status_color = "green" if result.status == "completed" else "red"
        severity_colors = {
            DriftSeverity.LOW: "#238636",
            DriftSeverity.MEDIUM: "#d29922",
            DriftSeverity.HIGH: "#f85149",
            DriftSeverity.CRITICAL: "#da3633",
        }

        drifts_rows = ""
        for r in result.drift_reports:
            color = severity_colors.get(r.severity, "#8b949e")
            drifts_rows += f"""
            <tr>
                <td>{r.drift_type.value}</td>
                <td><span class="badge" style="background:{color}">{r.severity.value}</span></td>
                <td>{r.prompt_name}</td>
                <td>{r.model}</td>
                <td>{r.provider}</td>
                <td>{r.drift_score:.4f}</td>
                <td>{r.timestamp.strftime('%Y-%m-%d %H:%M:%S') if r.timestamp else ''}</td>
                <td>{r.message}</td>
            </tr>"""

        prompts_rows = ""
        for p in result.prompt_results:
            status_icon = "✅" if p.success else "❌"
            prompts_rows += f"""
            <tr>
                <td>{status_icon}</td>
                <td>{p.prompt_name}</td>
                <td>{p.model}</td>
                <td>{p.provider}</td>
                <td>{p.token_usage.total_tokens}</td>
                <td>{p.latency.total_time_ms:.1f}ms</td>
                <td>${p.cost.total_cost:.6f}</td>
                <td>{'Yes' if p.refusal else 'No'}</td>
                <td>{p.response[:100]}...</td>
            </tr>"""

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Model Canary Report - {result.suite_name}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0d1117; color: #c9d1d9; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ color: #58a6ff; border-bottom: 2px solid #30363d; padding-bottom: 10px; margin-bottom: 20px; }}
        h2 {{ color: #58a6ff; margin: 20px 0 10px; }}
        .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; margin: 15px 0; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; }}
        .status {{ padding: 4px 12px; border-radius: 12px; font-weight: bold; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin: 15px 0; }}
        .stat {{ text-align: center; padding: 15px; background: #0d1117; border-radius: 6px; border: 1px solid #30363d; }}
        .stat-value {{ font-size: 1.8em; font-weight: bold; color: #58a6ff; }}
        .stat-label {{ color: #8b949e; font-size: 0.85em; margin-top: 5px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
        th, td {{ padding: 8px 12px; text-align: left; border-bottom: 1px solid #30363d; font-size: 0.9em; }}
        th {{ color: #8b949e; font-weight: 600; text-transform: uppercase; font-size: 0.8em; letter-spacing: 0.05em; }}
        .badge {{ display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 0.8em; font-weight: 600; color: white; }}
        pre {{ background: #0d1117; padding: 10px; border-radius: 4px; overflow-x: auto; font-size: 0.85em; }}
        .footer {{ text-align: center; color: #8b949e; font-size: 0.8em; margin-top: 30px; padding-top: 20px; border-top: 1px solid #30363d; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Model Canary Report</h1>
            <span class="status" style="background:{status_color};color:white;">{result.status.upper()}</span>
        </div>
        <p style="color:#8b949e;margin-bottom:20px;">{result.suite_name} &middot; {result.start_time.strftime('%Y-%m-%d %H:%M:%S') if result.start_time else 'N/A'}</p>

        <div class="summary">
            <div class="stat"><div class="stat-value">{result.total_prompts}</div><div class="stat-label">Total Prompts</div></div>
            <div class="stat"><div class="stat-value" style="color:#3fb950;">{result.successful_prompts}</div><div class="stat-label">Successful</div></div>
            <div class="stat"><div class="stat-value" style="color:#f85149;">{result.failed_prompts}</div><div class="stat-label">Failed</div></div>
            <div class="stat"><div class="stat-value">{result.duration_ms:.1f}ms</div><div class="stat-label">Duration</div></div>
            <div class="stat"><div class="stat-value">${result.total_cost:.6f}</div><div class="stat-label">Total Cost</div></div>
            <div class="stat"><div class="stat-value">{result.drift_count}</div><div class="stat-label">Drifts</div></div>
        </div>

        <div class="card">
            <h2>Drift Reports ({result.drift_count})</h2>
            <table>
                <thead><tr><th>Type</th><th>Severity</th><th>Prompt</th><th>Model</th><th>Provider</th><th>Score</th><th>Timestamp</th><th>Message</th></tr></thead>
                <tbody>{drifts_rows if drifts_rows else '<tr><td colspan="8" style="text-align:center;color:#8b949e;">No drifts detected</td></tr>'}</tbody>
            </table>
        </div>

        <div class="card">
            <h2>Prompt Results ({len(result.prompt_results)})</h2>
            <table>
                <thead><tr><th>Status</th><th>Name</th><th>Model</th><th>Provider</th><th>Tokens</th><th>Latency</th><th>Cost</th><th>Refusal</th><th>Response Preview</th></tr></thead>
                <tbody>{prompts_rows}</tbody>
            </table>
        </div>

        {f'<div class="card"><h2>Error</h2><pre>{result.error}</pre></div>' if result.error else ''}

        <div class="footer">
            Generated by Model Canary on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} &middot; Run ID: {result.id}
        </div>
    </div>
</body>
</html>"""

    def _generate_markdown(self, result: CanaryRunResult) -> str:
        lines = [
            f"# Model Canary Report: {result.suite_name}",
            "",
            f"- **Status:** {result.status.upper()}",
            f"- **Time:** {result.start_time.strftime('%Y-%m-%d %H:%M:%S') if result.start_time else 'N/A'}",
            f"- **Duration:** {result.duration_ms:.1f}ms",
            f"- **Run ID:** {result.id}",
            "",
            "## Summary",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Total Prompts | {result.total_prompts} |",
            f"| Successful | {result.successful_prompts} |",
            f"| Failed | {result.failed_prompts} |",
            f"| Total Cost | ${result.total_cost:.6f} |",
            f"| Drifts Detected | {result.drift_count} |",
            f"| Alerts Sent | {result.alerts_sent} |",
        ]

        if result.drift_reports:
            lines.extend([
                "",
                "## Drift Reports",
                "",
                "| Type | Severity | Prompt | Score | Message |",
                "|------|----------|--------|-------|---------|",
            ])
            for r in result.drift_reports:
                lines.append(
                    f"| {r.drift_type.value} | {r.severity.value} | {r.prompt_name} | {r.drift_score:.4f} | {r.message} |"
                )

        if result.error:
            lines.extend([
                "",
                "## Error",
                "",
                "```",
                f"{result.error}",
                "```",
            ])

        lines.extend([
            "",
            "---",
            f"*Generated by Model Canary on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
        ])

        return "\n".join(lines)

    def _generate_json(self, result: CanaryRunResult) -> str:
        return json.dumps(result.model_dump(mode='json'), indent=2, default=str)

    def _generate_csv(self, result: CanaryRunResult) -> str:
        lines = ["type,severity,prompt_name,model,provider,drift_score,message,timestamp"]
        for r in result.drift_reports:
            ts = r.timestamp.strftime('%Y-%m-%d %H:%M:%S') if r.timestamp else ""
            msg = r.message.replace('"', '""')
            lines.append(
                f'"{r.drift_type.value}","{r.severity.value}","{r.prompt_name}","{r.model}","{r.provider}",{r.drift_score:.4f},"{msg}","{ts}"'
            )
        return "\n".join(lines)
