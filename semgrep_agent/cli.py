"""CLI entry point for semgrep-agent."""

import sys
from pathlib import Path

import click

from .scanner import run_semgrep, group_findings
from .issues import get_existing_issues, create_issue


@click.command()
@click.argument("target", type=click.Path(exists=True, path_type=Path))
@click.option("--repo", required=True, help="GitHub repo (owner/name)")
@click.option("--config", default="auto", help="Semgrep config (default: auto)")
@click.option(
    "--severity",
    multiple=True,
    type=click.Choice(["ERROR", "WARNING", "INFO"], case_sensitive=False),
    help="Filter by severity (repeatable). Default: all.",
)
@click.option(
    "--exclude",
    multiple=True,
    help="Glob patterns to exclude (repeatable).",
)
@click.option("--dry-run", is_flag=True, help="Show what would be created without creating issues.")
@click.option("--max-issues", default=50, help="Max issues to create per run (default: 50).")
def main(
    target: Path,
    repo: str,
    config: str,
    severity: tuple[str, ...],
    exclude: tuple[str, ...],
    dry_run: bool,
    max_issues: int,
) -> None:
    """Scan a codebase with Semgrep and create GitHub issues for findings.

    TARGET is the path to the codebase to scan.
    """
    click.echo(f"Scanning {target} with config '{config}'...")

    findings = run_semgrep(
        target,
        config=config,
        exclude=list(exclude) or None,
        severity=list(severity) or None,
    )

    if not findings:
        click.echo("No findings. Clean!")
        return

    groups = group_findings(findings)
    click.echo(f"Found {len(findings)} findings across {len(groups)} rules.")

    # Deduplicate against existing issues
    if not dry_run:
        click.echo(f"Checking existing issues in {repo}...")
        existing = get_existing_issues(repo)
        new_rules = {r: f for r, f in groups.items() if r not in existing}
        skipped = len(groups) - len(new_rules)
        if skipped:
            click.echo(f"Skipping {skipped} rules that already have open issues.")
    else:
        new_rules = groups

    if not new_rules:
        click.echo("All findings already have open issues. Nothing to do.")
        return

    # Sort by severity (ERROR first) then by count
    severity_order = {"ERROR": 0, "WARNING": 1, "INFO": 2}
    sorted_rules = sorted(
        new_rules.items(),
        key=lambda kv: (severity_order.get(kv[1][0].severity, 9), -len(kv[1])),
    )

    created = 0
    for rule_id, rule_findings in sorted_rules:
        if created >= max_issues:
            remaining = len(sorted_rules) - created
            click.echo(f"Hit max-issues limit ({max_issues}). {remaining} rules skipped.")
            break

        click.echo(f"[{rule_findings[0].severity}] {rule_id} ({len(rule_findings)} hits)")
        create_issue(repo, rule_id, rule_findings, dry_run=dry_run)
        created += 1

    click.echo(f"\nDone. {'Would create' if dry_run else 'Created'} {created} issues.")


if __name__ == "__main__":
    main()
