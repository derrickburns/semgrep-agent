"""Create and deduplicate GitHub issues."""

import json
import subprocess
import sys

from .scanner import Finding


SEVERITY_LABELS = {
    "ERROR": "severity:high",
    "WARNING": "severity:medium",
    "INFO": "severity:low",
}

LABEL_PREFIX = "semgrep"


def get_existing_issues(repo: str) -> set[str]:
    """Get rule_ids that already have open issues (by label)."""
    cmd = [
        "gh", "issue", "list",
        "--repo", repo,
        "--label", LABEL_PREFIX,
        "--state", "open",
        "--json", "title,labels",
        "--limit", "500",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Warning: could not list issues: {result.stderr}", file=sys.stderr)
        return set()

    existing = set()
    for issue in json.loads(result.stdout):
        for label in issue.get("labels", []):
            name = label.get("name", "")
            if name.startswith(f"{LABEL_PREFIX}:"):
                existing.add(name.removeprefix(f"{LABEL_PREFIX}:"))
    return existing


def ensure_labels_exist(repo: str, labels: set[str]) -> None:
    """Create labels if they don't exist."""
    colors = {
        "semgrep": "5319E7",
        "severity:high": "D93F0B",
        "severity:medium": "FBCA04",
        "severity:low": "0E8A16",
    }
    for label in labels:
        color = colors.get(label, "EDEDED")
        subprocess.run(
            ["gh", "label", "create", label, "--repo", repo,
             "--color", color, "--force"],
            capture_output=True, text=True,
        )


def format_issue_body(rule_id: str, findings: list[Finding]) -> str:
    """Format the issue body with all locations for a given rule."""
    f0 = findings[0]
    lines = [
        f"## Semgrep: `{rule_id}`",
        "",
        f"**Severity:** {f0.severity}",
        f"**Category:** {f0.category or 'general'}" if f0.category else "",
        "",
        f"### Description",
        "",
        f0.message,
        "",
        f"### Locations ({len(findings)} occurrence{'s' if len(findings) > 1 else ''})",
        "",
    ]

    for f in findings[:20]:  # cap at 20 to avoid huge issues
        lines.append(f"- `{f.location}`")
        if f.snippet:
            lines.append(f"  ```")
            for snippet_line in f.snippet.strip().splitlines()[:5]:
                lines.append(f"  {snippet_line}")
            lines.append(f"  ```")

    if len(findings) > 20:
        lines.append(f"- ... and {len(findings) - 20} more")

    ref = f0.metadata.get("references") or f0.metadata.get("source")
    if ref:
        lines.extend(["", f"### References", ""])
        if isinstance(ref, list):
            for r in ref[:5]:
                lines.append(f"- {r}")
        else:
            lines.append(f"- {ref}")

    lines.extend(["", "---", f"*Created by semgrep-agent*"])
    return "\n".join(lines)


def create_issue(
    repo: str,
    rule_id: str,
    findings: list[Finding],
    dry_run: bool = False,
) -> str | None:
    """Create a GitHub issue for a group of findings. Returns the issue URL."""
    f0 = findings[0]
    severity_label = SEVERITY_LABELS.get(f0.severity, "severity:medium")
    rule_label = f"{LABEL_PREFIX}:{rule_id}"

    title = f"[semgrep] {rule_id} ({len(findings)} occurrence{'s' if len(findings) > 1 else ''})"
    if len(title) > 120:
        short_rule = rule_id.split(".")[-1]
        title = f"[semgrep] {short_rule} ({len(findings)} occurrences)"

    body = format_issue_body(rule_id, findings)
    labels = [LABEL_PREFIX, severity_label, rule_label]

    if dry_run:
        print(f"  [dry-run] Would create: {title}")
        print(f"  Labels: {', '.join(labels)}")
        return None

    ensure_labels_exist(repo, set(labels))

    cmd = [
        "gh", "issue", "create",
        "--repo", repo,
        "--title", title,
        "--body", body,
    ]
    for label in labels:
        cmd.extend(["--label", label])

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  Failed to create issue: {result.stderr}", file=sys.stderr)
        return None

    url = result.stdout.strip()
    print(f"  Created: {url}")
    return url
