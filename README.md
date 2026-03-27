# semgrep-agent

CLI tool that scans a codebase with [Semgrep](https://semgrep.dev) and creates GitHub issues for findings.

## Features

- Runs Semgrep locally against any codebase
- Groups findings by rule (one issue per rule, listing all occurrences)
- Deduplicates against existing open issues to avoid duplicates on re-runs
- Labels issues by severity (`severity:high`, `severity:medium`, `severity:low`)
- Supports dry-run mode to preview before creating issues
- Configurable severity filter, exclusion patterns, and issue limits

## Prerequisites

- Python 3.10+
- [Semgrep](https://semgrep.dev/docs/getting-started/) (`pip install semgrep` or `brew install semgrep`)
- [GitHub CLI](https://cli.github.com/) (`gh`) authenticated with `gh auth login`

## Install

```bash
pip install -e .
```

## Usage

```bash
# Scan a repo and create issues (dry-run first)
semgrep-agent /path/to/repo --repo owner/repo-name --dry-run

# Create issues for real
semgrep-agent /path/to/repo --repo owner/repo-name

# Only high-severity findings
semgrep-agent /path/to/repo --repo owner/repo-name --severity ERROR

# Custom semgrep config
semgrep-agent /path/to/repo --repo owner/repo-name --config p/security-audit

# Exclude directories
semgrep-agent /path/to/repo --repo owner/repo-name --exclude "vendor/*" --exclude "test/*"

# Limit number of issues created
semgrep-agent /path/to/repo --repo owner/repo-name --max-issues 10
```

## How it works

1. Runs `semgrep --json` on the target directory
2. Groups findings by rule ID
3. Checks existing open issues (by label) to avoid duplicates
4. Creates one GitHub issue per rule with all occurrences listed
5. Applies labels: `semgrep`, `severity:{level}`, `semgrep:{rule_id}`

## License

MIT
