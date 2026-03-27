"""Run semgrep and parse results."""

import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


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


def run_semgrep(
    target: Path,
    config: str = "auto",
    exclude: list[str] | None = None,
    severity: list[str] | None = None,
) -> list[Finding]:
    """Run semgrep on a target directory and return parsed findings."""
    cmd = [
        "semgrep",
        "--json",
        "--config",
        config,
        "--no-git-ignore",  # scan everything
        str(target),
    ]
    if exclude:
        for pattern in exclude:
            cmd.extend(["--exclude", pattern])
    if severity:
        for s in severity:
            cmd.extend(["--severity", s.upper()])

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode not in (0, 1):
        # returncode 1 means findings were found, which is expected
        print(f"semgrep failed (exit {result.returncode}):", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        raise SystemExit(1)

    data = json.loads(result.stdout)
    findings = []

    for r in data.get("results", []):
        extra = r.get("extra", {})
        findings.append(
            Finding(
                rule_id=r.get("check_id", "unknown"),
                message=extra.get("message", ""),
                severity=extra.get("severity", "WARNING"),
                path=r.get("path", ""),
                start_line=r.get("start", {}).get("line", 0),
                end_line=r.get("end", {}).get("line", 0),
                snippet=extra.get("lines", ""),
                category=extra.get("metadata", {}).get("category", ""),
                metadata=extra.get("metadata", {}),
            )
        )

    return findings


def group_findings(findings: list[Finding]) -> dict[str, list[Finding]]:
    """Group findings by rule_id so each issue covers one rule."""
    groups: dict[str, list[Finding]] = {}
    for f in findings:
        groups.setdefault(f.rule_id, []).append(f)
    return groups
