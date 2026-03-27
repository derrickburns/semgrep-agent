"""Scan a codebase via the Semgrep MCP server."""

import asyncio
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@dataclass
class Finding:
    rule_id: str
    message: str
    severity: str
    path: str
    start_line: int
    end_line: int
    snippet: str = ""
    category: str = ""
    metadata: dict = field(default_factory=dict)

    @property
    def location(self) -> str:
        if self.start_line == self.end_line:
            return f"{self.path}:{self.start_line}"
        return f"{self.path}:{self.start_line}-{self.end_line}"


def _collect_files(target: Path, exclude: list[str] | None) -> list[dict]:
    """Collect files under target as CodePath dicts for semgrep_scan_local."""
    exclude = exclude or []
    code_paths = []
    for root, dirs, files in os.walk(target):
        rel_root = Path(root).relative_to(target)
        # Skip hidden dirs and common noise
        dirs[:] = [
            d for d in dirs
            if not d.startswith(".")
            and d not in {"node_modules", "__pycache__", ".venv", "venv", ".git"}
        ]
        for f in files:
            rel_path = str(rel_root / f)
            skip = any(
                Path(rel_path).match(pat) for pat in exclude
            )
            if skip:
                continue
            abs_path = str(Path(root) / f)
            code_paths.append({"path": abs_path})
    return code_paths


def _parse_findings(result_text: str) -> list[Finding]:
    """Parse the MCP tool result into Finding objects."""
    try:
        data = json.loads(result_text)
    except json.JSONDecodeError:
        # The result may be a text summary rather than JSON
        return _parse_text_findings(result_text)

    findings = []
    results = data if isinstance(data, list) else data.get("results", [])
    for r in results:
        extra = r.get("extra", {})
        findings.append(
            Finding(
                rule_id=r.get("check_id", "unknown"),
                message=extra.get("message", r.get("message", "")),
                severity=extra.get("severity", r.get("severity", "WARNING")),
                path=r.get("path", ""),
                start_line=r.get("start", {}).get("line", 0),
                end_line=r.get("end", {}).get("line", 0),
                snippet=extra.get("lines", ""),
                category=extra.get("metadata", {}).get("category", ""),
                metadata=extra.get("metadata", {}),
            )
        )
    return findings


def _parse_text_findings(text: str) -> list[Finding]:
    """Fallback parser for non-JSON MCP responses."""
    # If the MCP server returns plain text, try to extract what we can
    findings = []
    # This is a best-effort fallback
    return findings


async def _scan_via_mcp(
    target: Path,
    config: str | None,
    exclude: list[str] | None,
    severity: list[str] | None,
) -> list[Finding]:
    """Connect to the Semgrep MCP server and run a scan."""
    server_params = StdioServerParameters(
        command="semgrep",
        args=["mcp", "-t", "stdio"],
    )

    code_paths = _collect_files(target, exclude)
    if not code_paths:
        return []

    # Batch files to avoid overwhelming the server
    batch_size = 100
    all_findings: list[Finding] = []

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            for i in range(0, len(code_paths), batch_size):
                batch = code_paths[i : i + batch_size]
                args: dict = {"code_files": batch}

                result = await session.call_tool("semgrep_scan", args)

                # Extract text from MCP result
                for content in result.content:
                    if hasattr(content, "text"):
                        all_findings.extend(_parse_findings(content.text))

    # Filter by severity if requested
    if severity:
        sev_set = {s.upper() for s in severity}
        all_findings = [f for f in all_findings if f.severity in sev_set]

    return all_findings


def run_semgrep(
    target: Path,
    config: str | None = None,
    exclude: list[str] | None = None,
    severity: list[str] | None = None,
) -> list[Finding]:
    """Run semgrep via MCP and return parsed findings."""
    return asyncio.run(_scan_via_mcp(target, config, exclude, severity))


def group_findings(findings: list[Finding]) -> dict[str, list[Finding]]:
    """Group findings by rule_id so each issue covers one rule."""
    groups: dict[str, list[Finding]] = {}
    for f in findings:
        groups.setdefault(f.rule_id, []).append(f)
    return groups
