# semgrep-agent

CLI agent that scans a codebase via the [Semgrep MCP server](https://github.com/semgrep/mcp) and creates GitHub issues for findings.

## How it works

1. Launches `semgrep mcp -t stdio` as an MCP server subprocess
2. Connects as an MCP client and calls `semgrep_scan_local` with file paths
3. Groups findings by rule ID
4. Checks existing open issues (by label) to avoid duplicates
5. Creates one GitHub issue per rule with all occurrences listed

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
# Dry-run first
semgrep-agent /path/to/repo --repo owner/repo-name --dry-run

# Create issues for real
semgrep-agent /path/to/repo --repo owner/repo-name

# Only high-severity findings
semgrep-agent /path/to/repo --repo owner/repo-name --severity ERROR

# Custom semgrep config
semgrep-agent /path/to/repo --repo owner/repo-name --config p/security-audit

# Exclude directories
semgrep-agent /path/to/repo --repo owner/repo-name --exclude "vendor/*" --exclude "test/*"

# Limit issues created per run
semgrep-agent /path/to/repo --repo owner/repo-name --max-issues 10
```

## Architecture

```
semgrep-agent (MCP client)
    │
    ├── Launches: semgrep mcp -t stdio (MCP server)
    │     └── calls semgrep_scan_local tool
    │
    ├── Deduplicates via: gh issue list --label semgrep
    │
    └── Creates via: gh issue create
```

## Labels

Issues are tagged with:
- `semgrep` — all agent-created issues
- `severity:high` / `severity:medium` / `severity:low`
- `semgrep:{rule_id}` — for deduplication

## License

MIT
