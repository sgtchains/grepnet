# `sc-conductor init` Command Design

**Purpose**: Bootstrap a new project with test orchestration framework  
**Scope**: One-time setup that creates config, hooks, and initial structure  
**Version**: 1.0 | October 7, 2026

---

## Overview

The `sc-conductor init` command is an interactive wizard that:
1. Detects project type (Python, Go, Rust, TypeScript, etc.)
2. Discovers existing tests
3. Configures appropriate plugins
4. Sets up git hooks (optional)
5. Creates `.conductor.yml` configuration
6. Initializes secrets management

---

## Command Invocation

```bash
# Standard init (interactive)
sc-conductor init

# Minimal init (use defaults)
sc-conductor init --defaults

# With custom options
sc-conductor init --language python --vcs git --secrets vault

# Dry-run (show what would be created)
sc-conductor init --dry-run

# Rerun after changes (preserve existing config)
sc-conductor init --update
```

---

## Interactive Flow

### Step 1: Welcome & Detection

```
╔════════════════════════════════════════════════════════════╗
║       sc-conductor Initialization Wizard                   ║
║                                                            ║
║  This will set up test orchestration for your project.    ║
║                                                            ║
║  Project root: /home/user/my-project                      ║
║  Detected Python project (setup.py found)                 ║
╚════════════════════════════════════════════════════════════╝

Press Enter to continue...
```

### Step 2: Language Detection & Confirmation

```
? Detected project language(s):
  ◉ Python (src/grepnet/**/*.py, tests/**/*.py)
  ◯ Go (cmd/**/*.go)
  ◯ Rust (src/**/*.rs)
  ◯ TypeScript (src/**/*.ts)

? Which languages does your project use?
  • Python
  (Use arrow keys to select, Space to toggle, Enter to confirm)
```

**Auto-detected by**:
- `setup.py`, `pyproject.toml` → Python
- `go.mod` → Go
- `Cargo.toml` → Rust
- `package.json`, `tsconfig.json` → TypeScript/Node
- `pom.xml`, `build.gradle` → Java/Kotlin

### Step 3: VCS Detection

```
? Which version control system does your project use?
  ◉ Git (latest: main branch, .git found)
  ◯ Mercurial (hg found)
  ◯ Perforce (p4 found)
  ◯ None / File timestamps only

? For git, which branch is primary?
  ◉ main
  ◯ master
  ◯ develop
  ◯ Custom: _______________
```

### Step 4: Test Discovery

```
? Scanning for test files...
  ✓ Found 50 shell scripts in tests/sub-tests/
  ✓ Found 12 Python tests in tests/
  ✓ Found 8 Go tests in cmd/tests/

? Create test catalogs?
  ◉ Yes, auto-detect (recommended)
  ◯ Manual configuration

? Which tests should be included?
  ◯ All found tests
  ◉ Interactive selection
  ◯ Filter by pattern: _______________
```

**Test discovery patterns** (per language):
- Python: `test_*.py`, `*_test.py`, `tests.py`
- Go: `*_test.go`
- Rust: `*_test.rs`
- TypeScript: `*.test.ts`, `*.spec.ts`
- Shell: `*.sh` in `tests/` directories

### Step 5: Test Approval Workflow

```
? Initialize test approval workflow?
  ◉ Yes (recommended for teams)
  ◯ No (automated mode only)

? Approval settings:
  ✓ State machine: DRAFT → APPROVED → AUTOMATED
  ✓ Approval required before automation
  ✓ Audit trail: Who approved, when

? Bootstrap approve all existing tests?
  ◉ Yes, mark all as APPROVED (first-time setup)
  ◯ No, keep as DRAFT (manual review)

? Who should be listed as approver?
  (Your name): alice@company.com
  (or) [skip]
```

### Step 6: Output Plugins (Optional)

```
? Configure output plugins?
  ◉ Yes (recommended)
  ◯ No (skip for now)

? Which integrations do you need?
  ◯ Slack notifications
  ◯ Jira ticketing
  ◯ GitHub PR comments
  ◯ Email reports
  ◯ Database storage (Postgres)
  
? Configure Slack?
  Webhook URL (or [skip]): https://hooks.slack.com/...
  Channel: #test-results
  Notify on: test_failure

? Configure GitHub PR Comments?
  ◉ Yes, post impact analysis on PRs
  ◯ No
```

### Step 7: Compliance Plugins (Optional)

```
? Configure compliance reporting?
  ◉ Yes
  ◯ No

? Which reports do you need?
  ◯ SBOM (Software Bill of Materials)
  ◯ Security compliance (SOC2/ISO27001)
  ◯ Test coverage report
  ◯ Audit trail report

? SBOM format?
  ◉ CycloneDX (JSON)
  ◯ SPDX
  ◯ None
```

### Step 8: Secrets Management

```
? Configure secrets management?
  ◉ Yes (required for integrations)
  ◯ No

? Which secrets backend?
  ◯ Environment variables only
  ◉ Local encrypted file (~/.sc-conductor/secrets.enc)
  ◯ HashiCorp Vault
  ◯ AWS Secrets Manager
  ◯ Azure Key Vault

? Fallback strategy?
  ◉ Try env vars if backend unavailable
  ◯ Fail hard (security-first)

? Caching?
  ◉ Yes (5 minute TTL)
  ◯ No (always fresh)

? Access level for developers?
  ◉ Read-only
  ◯ Read-write
  ◯ Admin

? Required secrets to configure:
  ✓ jira_token (if using Jira)
  ✓ slack_webhook (if using Slack)
  ✓ github_token (if using GitHub)

? Add secrets now or later?
  ◯ Now (interactive)
  ◉ Later (via 'sc-conductor secrets set')
```

### Step 9: Git Hooks (Optional)

```
? Install git hooks?
  ◉ Yes (recommended)
  ◯ No

? Which hooks?
  ◯ pre-commit: Run impact analysis before committing
  ◯ pre-push: Require tests to pass before push
  ◯ post-merge: Update test cache after merge

? Pre-commit behavior?
  ◉ Warn only (allow commit anyway)
  ◯ Block if tests fail (strict)
```

### Step 10: CI/CD Integration (Optional)

```
? Configure CI/CD integration?
  ◉ Yes
  ◯ No

? Which CI/CD platform?
  ◯ GitHub Actions (detected: .github/workflows/)
  ◯ GitLab CI (detected: .gitlab-ci.yml)
  ◯ Jenkins (detected: Jenkinsfile)
  ◯ None

? GitHub Actions workflow?
  ◉ Create .github/workflows/test-conductor.yml
  ◯ Use existing workflow
  ◯ Skip

? Workflow behavior?
  ◉ Post impact analysis as PR comment
  ◯ Gate PR merge on test results
```

### Step 11: IDE Integration (Optional)

```
? Configure IDE integration?
  ◉ Yes
  ◯ No

? Detected IDE:
  ✓ VSCode (found .vscode/)
  ◯ PyCharm
  ◯ GoLand

? VSCode tasks?
  ◯ Create .vscode/tasks.json with test commands
  ◉ Yes, auto-configure
```

### Step 12: Summary & Create

```
╔════════════════════════════════════════════════════════════╗
║                    Configuration Summary                   ║
╠════════════════════════════════════════════════════════════╣
║                                                            ║
║  Language(s):        Python, Go                           ║
║  VCS:                Git (main branch)                     ║
║  Tests found:        50 shell + 12 Python + 8 Go          ║
║  Approval workflow:  ENABLED (bootstrap approve all)      ║
║  Output plugins:     Slack, GitHub PR comment             ║
║  Secrets backend:    Local encrypted file                 ║
║  Git hooks:          pre-commit, pre-push                 ║
║  CI/CD:              GitHub Actions                       ║
║                                                            ║
║  Files to create:                                         ║
║    • .conductor.yml (main config)                       ║
║    • .conductor.local.yml (secrets template)            ║
║    • .git/hooks/pre-commit                                ║
║    • .git/hooks/pre-push                                  ║
║    • .github/workflows/sc-conductor.yml                    ║
║    • .vscode/tasks.json                                   ║
║    • catalogs/ (test definitions)                         ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝

? Proceed with initialization?
  ◉ Yes
  ◯ Review config first
  ◯ Dry-run (show what would be created)
  ◯ Cancel
```

### Step 13: Completion

```
✓ Created .conductor.yml
✓ Created catalogs/
  • catalogs/001-010.yml (shell tests)
  • catalogs/python.yml (Python tests)
  • catalogs/go.yml (Go tests)
✓ Created .git/hooks/pre-commit
✓ Created .git/hooks/pre-push
✓ Created .github/workflows/test-conductor.yml
✓ Created .vscode/tasks.json
✓ Bootstrap approved 70 tests
✓ Created .conductor.local.yml template

╔════════════════════════════════════════════════════════════╗
║                  Next Steps                                ║
╠════════════════════════════════════════════════════════════╣
║                                                            ║
║  1. Add secrets:                                          ║
║     sc-conductor secrets set jira_token "..."          ║
║     sc-conductor secrets set slack_webhook "..."       ║
║                                                            ║
║  2. Test impact analysis:                                 ║
║     git diff HEAD~1                                       ║
║     sc-conductor impact --analyze                                 ║
║                                                            ║
║  3. Run affected tests:                                   ║
║     sc-conductor run --affected --verbose                ║
║                                                            ║
║  4. Approve tests interactively:                          ║
║     sc-conductor approve --interactive                            ║
║                                                            ║
║  5. Documentation:                                        ║
║     See README.md for complete usage guide                ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝

✓ Initialization complete!
```

---

## Generated Artifacts

### `.conductor.yml` (Main Config)

```yaml
# Auto-generated by: sc-conductor init
# Last updated: 2026-10-07

framework_version: "1.0"
project_name: "my-project"

# Languages
language: auto
language_plugins:
  - python: src/**/*.py
  - go: cmd/**/*.go

# VCS
vcs_type: git
vcs_options: "--staged"

# Test approval workflow
approval_workflow:
  enabled: true
  state_machine: ["DRAFT", "APPROVED", "AUTOMATED"]
  require_approval: true
  bootstrap_approved: true
  bootstrap_approver: "alice@company.com"
  bootstrap_reason: "Initial import from test discovery"

# Output plugins
output_plugins:
  - type: slack
    webhook_url: ${SLACK_WEBHOOK}
    on_event: test_failure
    channel: "#test-results"
  
  - type: github_pr_comment
    on_event: impact_analysis

# Compliance plugins
compliance_plugins:
  - type: audit_trail
    retention_days: 90

# Secrets
secrets_plugin:
  type: local_file
  fallback_strategy: "env"
  cache_enabled: true
  cache_ttl_seconds: 300

# Test discovery
test_discovery:
  auto_detect: true
  patterns:
    - "tests/sub-tests/*.sh"
    - "tests/*_test.py"
    - "cmd/**/*_test.go"

# Git hooks
git_hooks:
  pre_commit: true
  pre_push: true
  post_merge: false
```

### `.conductor.local.yml` (User Overrides - Gitignored)

```yaml
# DO NOT COMMIT - User-specific overrides and secrets
# Add to .gitignore: .conductor.local.yml

secrets_plugin:
  type: local_file
  # Secrets configured via: sc-conductor secrets set

# Developer-specific overrides
output_plugins:
  - type: slack
    # Using env var SLACK_WEBHOOK instead

# Local development: skip compliance checks
compliance_plugins: []
```

### `catalogs/001-010.yml` (Test Catalog)

```yaml
# Auto-generated by: sc-conductor init --discover
# Contains: Shell scripts from tests/sub-tests/

tests:
  001:
    name: "Basic CIDR pattern matching"
    category: core
    file: "sub-tests/001_basic_matching.sh"
    status: APPROVED  # Bootstrap approved
    approved_by: alice@company.com
    approved_at: "2026-10-07T10:30:00Z"
    
  002:
    name: "Netmask format validation"
    category: core
    file: "sub-tests/002_netmask.sh"
    status: APPROVED
    # ... more tests
```

### `.git/hooks/pre-commit`

```bash
#!/bin/bash
# Auto-generated by: sc-conductor init

set -euo pipefail

echo "🧪 Running test impact analysis..."
if ! sc-conductor impact --analyze --staged; then
  echo "⚠️  Impact analysis failed"
  # Continue anyway (--warn-only mode)
fi

echo "✓ Pre-commit checks passed"
```

### `.github/workflows/sc-conductor.yml`

```yaml
# Auto-generated by: sc-conductor init

name: Test Impact Analysis

on: [pull_request]

jobs:
  impact:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0
      
      - name: Install sc-conductor
        run: pip install sc-conductor
      
      - name: Analyze test impact
        run: |
          sc-conductor impact --analyze --json > impact_report.json
      
      - name: Comment on PR
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const report = JSON.parse(fs.readFileSync('impact_report.json'));
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `🧪 Test Impact: ${report.affected_count} tests`
            });
```

---

## Flags & Options

| Flag | Type | Default | Purpose |
|------|------|---------|---------|
| `--defaults` | bool | false | Skip interactive, use all defaults |
| `--language` | string | (auto-detect) | Force language(s) |
| `--vcs` | string | (auto-detect) | Force VCS type |
| `--secrets` | string | local_file | Secrets backend |
| `--dry-run` | bool | false | Show what would be created, don't create |
| `--update` | bool | false | Rerun after project changes, preserve existing config |
| `--skip-hooks` | bool | false | Don't create git hooks |
| `--skip-secrets` | bool | false | Don't prompt for secrets setup |
| `--skip-ci` | bool | false | Don't configure CI/CD |
| `--approver` | string | (env USER) | Who approves bootstrap tests |
| `--no-bootstrap` | bool | false | Don't auto-approve existing tests |

---

## Error Handling

### Not in Project Root

```
✗ Not in a project root directory
  Looking for: pyproject.toml, setup.py, go.mod, Cargo.toml, package.json, .git

  Run from project root:
  cd /path/to/project
  sc-conductor init
```

### Already Initialized

```
✗ Project already initialized
  Found: .conductor.yml (created 2026-10-01)

  Options:
  • sc-conductor init --update (rerun, preserve config)
  • sc-conductor init --force (overwrite config)
  • rm .conductor.yml && sc-conductor init (start fresh)
```

### No Tests Found

```
? No tests detected automatically
  
  Searched for:
  • tests/test_*.py
  • tests/**/*.sh
  • cmd/**/*_test.go
  
  Options:
  • sc-conductor init --test-pattern "my_tests/**/*.py"
  • sc-conductor init --manual (skip auto-discovery)
```

---

## Success Metrics

After `sc-conductor init` completes:

✅ `.conductor.yml` exists and is valid YAML  
✅ All referenced test files are discoverable  
✅ Git hooks installed and executable  
✅ No secrets committed to git  
✅ `sc-conductor impact --analyze` runs successfully  
✅ `sc-conductor run --all` executes all tests  
✅ IDE configured and tasks available  
✅ CI/CD workflow created (if applicable)

---

## Examples

### Python Project (Simple)

```bash
cd my-python-project
sc-conductor init
# Detects: Python, Git, tests/test_*.py
# Auto-approves all tests
# Done in 2 minutes
```

### Multi-Language Monorepo (Complex)

```bash
cd company/monorepo
sc-conductor init
# Detects: Python (src/), Go (cmd/), TypeScript (ui/)
# Discovers: 100+ tests across languages
# Configures: Slack, Jira, GitHub Actions
# Done in 10 minutes
```

### CI/CD Integration Only

```bash
sc-conductor init --skip-secrets --skip-hooks
# Only: GitHub Actions workflow
# For: Automated PR commenting on test impact
```
