# Installation & Setup Documentation

**Purpose**: Complete guide for installing and setting up sc-conductor  
**Scope**: Individual dev, teams, enterprises, CI/CD integration  
**Version**: 1.0 | October 7, 2026

---

## Table of Contents

1. [Quick Start (5 minutes)](#quick-start)
2. [Installation Methods](#installation-methods)
3. [Project Initialization](#project-initialization)
4. [User Setup](#user-setup)
5. [Team Setup](#team-setup)
6. [Enterprise Deployment](#enterprise-deployment)
7. [CI/CD Integration](#cicd-integration)
8. [Troubleshooting](#troubleshooting)
9. [Verification Checklist](#verification-checklist)

---

## Quick Start

### For Solo Developer (5 minutes)

```bash
# 1. Install (one-time)
pip install sc-conductor

# 2. Initialize project
cd my-project
sc-conductor init --defaults

# 3. Run impact analysis
sc-conductor impact --analyze

# ✓ Done! You now have test impact analysis
```

**Output**:
```
✓ Created .conductor.yml
✓ Discovered 42 tests
✓ Impact Analysis: 3 tests affected by your changes
```

---

## Installation Methods

### Method 1: pip (Recommended)

**Pros**: Simple, automatic updates, no dependencies  
**Cons**: Global installation (affects all Python projects)

```bash
# Install latest version
pip install sc-conductor

# Install specific version
pip install sc-conductor==1.0.0

# Upgrade
pip upgrade sc-conductor

# Verify
sc-conductor --version
sc-conductor impact --help
sc-conductor run --help
```

**Uninstall**:
```bash
pip uninstall sc-conductor
```

---

### Method 2: Conda

**Pros**: Works with conda environments, isolates dependencies  
**Cons**: Requires conda setup

```bash
# Create environment
conda create -n sc-conductor python=3.10
conda activate sc-conductor

# Install
conda install -c conda-forge sc-conductor

# Use
sc-conductor init
```

---

### Method 3: Docker

**Pros**: Complete isolation, works on any machine  
**Cons**: Container overhead, slower for local development

```bash
# Pull image
docker pull ghcr.io/sc-conductor/sc-conductor:latest

# Run from project
cd my-project
docker run -v $(pwd):/project sc-conductor impact --analyze

# Or: Create alias
alias sc-conductor='docker run -v $(pwd):/project \
  -v ~/.sc-conductor:/home/user/.sc-conductor:ro \
  sc-conductor'
```

---

### Method 4: From Source (Development)

**Pros**: Latest changes, contribute back  
**Cons**: Requires git, Python 3.8+, more setup

```bash
# Clone repo
git clone https://github.com/sc-conductor/sc-conductor.git
cd sc-conductor

# Install in development mode
pip install -e .

# Verify
sc-conductor --version

# Contribute
# See CONTRIBUTING.md for guidelines
```

---

## Project Initialization

### Step 1: Navigate to Project Root

```bash
cd /path/to/my-project

# Verify you're in right place
ls -la | grep -E "(setup.py|pyproject.toml|go.mod|package.json|.git)"
# Should show at least one
```

### Step 2: Run Initialization

#### Interactive Setup (Recommended)

```bash
sc-conductor init

# Follow prompts:
# ✓ Detects Python project
# ✓ Found 42 tests
# ✓ Use Git? (yes)
# ✓ Approval workflow? (yes)
# ✓ Output plugins? (optional)
# ✓ Secrets management? (optional)
# ✓ Git hooks? (optional)
```

#### Quick Setup (Defaults)

```bash
sc-conductor init --defaults

# Creates:
# • .conductor.yml (default config)
# • catalogs/001-010.yml (tests)
# • .gitignore entry (secrets)
```

#### Dry Run (Preview)

```bash
sc-conductor init --dry-run

# Shows what would be created without modifying files
```

### Step 3: Verify Configuration

```bash
# Review generated config
cat .conductor.yml

# Check test discovery
sc-conductor catalog --list
# Should show all your tests

# Test impact analysis
git diff HEAD~1 | sc-conductor impact --analyze
# Should detect affected tests
```

### Step 4: Approve Existing Tests (First Time)

```bash
# One-time bootstrap approval
sc-conductor validate --bootstrap-approve-all --approver "your@email.com"

# Verify
sc-conductor validate --list --status APPROVED
# Should show all tests as APPROVED
```

### Step 5: Configure Secrets (If Using Integrations)

```bash
# If Jira plugin enabled
sc-conductor secrets set jira_token "abc123xyz"

# If Slack enabled
sc-conductor secrets set slack_webhook "https://hooks.slack.com/..."

# Verify
sc-conductor secrets list
# Shows: jira_token, slack_webhook (values not displayed)
```

---

## User Setup

### New Team Member

```bash
# 1. Clone/navigate to project
git clone https://company/repo
cd repo

# 2. Install framework
pip install sc-conductor

# 3. Review project config
cat .conductor.yml

# 4. Set personal overrides (optional)
mkdir -p ~/.sc-conductor
cat > ~/.sc-conductor/config.yml << 'EOF'
secrets_plugin:
  type: env
output_plugins: []  # No Jira locally
EOF

# 5. Configure secrets
# Option A: Use env vars
export SLACK_WEBHOOK="https://..."

# Option B: Use local encrypted file
sc-conductor secrets set slack_webhook "https://..."

# 6. Test it
sc-conductor impact --analyze
# ✓ Works!
```

### One-Time Personal Setup

```bash
# Create ~/.sc-conductor/ directory structure
mkdir -p ~/.sc-conductor

# Create user config (optional)
cat > ~/.sc-conductor/config.yml << 'EOF'
# User preferences
editor: vim
output_format: json
default_parallel_workers: 4
EOF

# Create secrets (optional)
# - env vars (preferred for sensitive)
# - local encrypted file (if sharing machine)

# Grant proper permissions
chmod 700 ~/.sc-conductor
chmod 600 ~/.sc-conductor/config.yml
chmod 600 ~/.sc-conductor/secrets.enc
```

### IDE Setup

#### VSCode

```bash
# Test framework tasks
mkdir -p .vscode
cat > .vscode/tasks.json << 'EOF'
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Test Impact",
      "type": "shell",
      "command": "sc-conductor impact",
      "args": ["--analyze", "--show-scores"],
      "problemMatcher": [],
      "group": {
        "kind": "test",
        "isDefault": true
      }
    },
    {
      "label": "Run Affected Tests",
      "type": "shell",
      "command": "sc-conductor run",
      "args": ["--affected"]
    }
  ]
}
EOF

# In VSCode: Ctrl+Shift+B → "Test Impact"
```

#### PyCharm

```bash
# External tool configuration
Go to: Settings → Tools → External Tools
Add tool:
  Name: Test Impact Analysis
  Program: sc-conductor impact
  Arguments: --analyze --show-scores
  Working Directory: $ProjectFileDir$
```

---

## Team Setup

### Admin: Initial Setup (30 minutes)

```bash
# 1. Create project config
cd company/monorepo
sc-conductor init --defaults

# 2. Configure team integrations
cat > .conductor.yml << 'EOF'
output_plugins:
  - type: github_pr_comment
    on_event: impact_analysis
  
  - type: slack
    webhook_url: ${SLACK_WEBHOOK}
    on_event: test_failure
  
  - type: jira
    url: https://jira.company.com
    on_event: test_failure

compliance_plugins:
  - type: audit_trail
    retention_days: 90
EOF

# 3. Commit config to git
git add .conductor.yml .gitignore catalogs/
git commit -m "Add sc-conductor"
git push

# 4. Configure CI/CD
# (See CI/CD Integration section)

# 5. Inform team
echo "Test framework ready! See docs/TEST-FRAMEWORK-SETUP.md"
```

### Developer: First Time (5 minutes)

```bash
# 1. Get latest
git pull

# 2. Install framework
pip install sc-conductor

# 3. Review config
cat .conductor.yml

# 4. Verify
sc-conductor impact --analyze
# ✓ Should detect your changes

# 5. Run affected tests
sc-conductor run --affected

# 6. See help
sc-conductor help
```

### Daily Workflow

```bash
# Before commit
git add src/payment.py
sc-conductor impact --analyze
# Output: "5 tests affected"

# Run only affected tests
sc-conductor run --affected
# Output: "All 5 tests passed"

# Commit
git commit -m "Fix payment validation"
git push

# GitHub Actions runs full suite
# Automatically posts results to PR
```

---

## Enterprise Deployment

### Admin: Central Installation (2-4 hours)

```bash
# 1. Choose central location
INSTALL_DIR="/opt/sc-conductor"
mkdir -p $INSTALL_DIR

# 2. Clone repo
git clone <repo> $INSTALL_DIR
cd $INSTALL_DIR

# 3. Create symlinks to /usr/local/bin
for cmd in sc-conductor impact sc-conductor run sc-conductor approve; do
  sudo ln -s $INSTALL_DIR/bin/$cmd /usr/local/bin/$cmd
done

# 4. Verify
which sc-conductor
# Output: /usr/local/bin/sc-conductor
```

### System Config (/etc/sc-conductor/config.yml)

```yaml
# Shared across all users/projects
framework_version: "1.0"

# Default plugins (all projects can override)
output_plugins:
  - type: slack
    webhook_url: /etc/sc-conductor/slack-webhook.txt  # External file

compliance_plugins:
  - type: audit_trail
    retention_days: 365

# Vault settings (all projects)
secrets_plugin:
  type: vault
  vault_addr: https://vault-prod-01.internal
  vault_namespace: "sc-conductor"
```

**Setup**:
```bash
sudo mkdir -p /etc/sc-conductor
sudo cp config.example.yml /etc/sc-conductor/config.yml
sudo chown root:root /etc/sc-conductor/config.yml
sudo chmod 644 /etc/sc-conductor/config.yml
```

### Vault Setup (Enterprise Secrets)

```bash
# 1. Vault admin creates policy
vault policy write sc-conductor -<<'EOF'
# Allow sc-conductor to read/write secrets
path "secret/data/sc-conductor/prod/*" {
  capabilities = ["read", "create", "update"]
}

path "secret/data/sc-conductor/staging/*" {
  capabilities = ["read", "create"]
}
EOF

# 2. Enable OIDC auth (for users)
vault auth enable oidc
vault write auth/oidc/config \
  oidc_discovery_url="https://okta.company.com" \
  oidc_client_id="vault-app-id"

# 3. Create OIDC role
vault write auth/oidc/role/default \
  bound_audiences="vault-app-id" \
  user_claim="email" \
  allowed_redirect_uris="http://localhost:8250/oidc/callback"

# 4. Each user authenticates
vault login -method=oidc

# 5. Framework reads from Vault
sc-conductor will use VAULT_TOKEN automatically
```

### CI/CD Secrets Configuration

```bash
# For GitHub Actions: Add secrets
gh secret set VAULT_ADDR --body "https://vault-prod-01.internal"
gh secret set VAULT_TOKEN --body "s.xxxxxxxxxxxx"

# For GitLab CI: Add secrets
# Settings → CI/CD → Variables → Add Variable
# VAULT_ADDR: https://vault-prod-01.internal
# VAULT_TOKEN: s.xxxxxxxxxxxx

# For Jenkins: Add credentials
# Manage Jenkins → Manage Credentials
# Add: VAULT_ADDR, VAULT_TOKEN
```

---

## CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/sc-conductor.yml
name: Test Impact Analysis

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  impact:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0  # Full history for git diff
      
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install sc-conductor
        run: pip install sc-conductor
      
      - name: Configure Vault access
        env:
          VAULT_ADDR: ${{ secrets.VAULT_ADDR }}
          VAULT_TOKEN: ${{ secrets.VAULT_TOKEN }}
        run: |
          echo "✓ Vault configured"
      
      - name: Analyze test impact
        id: impact
        run: |
          sc-conductor impact --analyze --json > report.json
          echo "report_summary=$(cat report.json | jq .summary)" >> $GITHUB_OUTPUT
      
      - name: Comment on PR
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const report = JSON.parse(fs.readFileSync('report.json'));
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `🧪 **Test Impact Analysis**\n\n${report.summary}`
            });
      
      - name: Run affected tests
        run: sc-conductor run --affected --parallel 4
      
      - name: Block merge if failed
        if: failure()
        run: exit 1  # Prevents merge
```

### GitLab CI

```yaml
# .gitlab-ci.yml
sc-conductor impact:
  stage: test
  image: python:3.10
  
  before_script:
    - pip install sc-conductor
  
  script:
    - sc-conductor impact --analyze --json > report.json
    - sc-conductor run --affected --parallel 4
  
  artifacts:
    reports:
      junit: test-results.xml
    paths:
      - report.json
```

### Jenkins

```groovy
// Jenkinsfile
pipeline {
    agent any
    
    stages {
        stage('Install') {
            steps {
                sh 'pip install sc-conductor'
            }
        }
        
        stage('Analyze Impact') {
            steps {
                sh 'sc-conductor impact --analyze --json > report.json'
                archiveArtifacts 'report.json'
            }
        }
        
        stage('Run Tests') {
            steps {
                sh 'sc-conductor run --affected --parallel 4'
            }
        }
    }
}
```

---

## Troubleshooting

### Issue: Command not found

```bash
$ sc-conductor init
bash: command not found: sc-conductor

# Solution 1: Install via pip
pip install sc-conductor

# Solution 2: Use python module
python -m test_framework.cli init

# Solution 3: Use full path
/usr/local/bin/sc-conductor init
```

### Issue: No tests discovered

```bash
$ sc-conductor catalog --list
No tests found

# Debug: Check discovery patterns
cat .conductor.yml | grep -A5 "test_discovery"

# Solution 1: Adjust patterns
sc-conductor init --test-pattern "my_tests/**/*.py"

# Solution 2: List what framework sees
sc-conductor catalog --discover --verbose
# Should show files it's scanning
```

### Issue: Secrets not found

```bash
$ sc-conductor run --all
ERROR: JIRA_TOKEN not found

# Solution 1: Check if secret exists
sc-conductor secrets list
# If not: sc-conductor secrets set jira_token "..."

# Solution 2: Check fallback strategy
cat .conductor.yml | grep fallback_strategy
# If "fail": maybe Vault is down
# Check: echo $SC_CONDUCTOR_JIRA_TOKEN

# Solution 3: Check env var
echo $SC_CONDUCTOR_JIRA_TOKEN
# If empty: export SC_CONDUCTOR_JIRA_TOKEN="..."
```

### Issue: Git hooks not executing

```bash
$ git commit -m "test"
# Pre-commit hook should run, but doesn't

# Solution 1: Check if hooks exist
ls -la .git/hooks/pre-commit

# Solution 2: Make hooks executable
chmod +x .git/hooks/pre-commit

# Solution 3: Verify hook content
cat .git/hooks/pre-commit
# Should have #!/bin/bash

# Solution 4: Reinstall hooks
sc-conductor init --update
```

### Issue: Permission denied (Vault/AWS)

```bash
$ sc-conductor run --all
ERROR: Permission denied (Vault)

# Solution 1: Check token
echo $VAULT_TOKEN

# Solution 2: Re-authenticate
vault login -method=oidc

# Solution 3: Check policy
vault policy read sc-conductor
# Verify "secret/data/sc-conductor/prod/*" has "read" capability
```

---

## Verification Checklist

After installation/setup, verify:

```bash
# 1. Framework installed
sc-conductor --version
# Output: sc-conductor version 1.0.0 ✓

# 2. Configuration valid
sc-conductor config --validate
# Output: ✓ Configuration valid ✓

# 3. Tests discovered
sc-conductor catalog --list
# Output: Found 50 tests ✓

# 4. Impact analysis works
sc-conductor impact --analyze
# Output: X tests affected ✓

# 5. Tests run
sc-conductor run --all --dry-run
# Output: Would run N tests ✓

# 6. Secrets accessible
sc-conductor secrets list
# Output: jira_token, slack_webhook ✓

# 7. Git hooks installed
ls .git/hooks/pre-commit
# Output: -rwxr-xr-x ✓

# 8. Output plugins configured
cat .conductor.yml | grep output_plugins -A3
# Output: Lists your plugins ✓

# 9. Approval workflow active
sc-conductor validate --list --status APPROVED
# Output: All tests APPROVED ✓

# 10. Audit logging works
sc-conductor audit --today
# Output: Access logs ✓

# All checks passing? ✓ Ready to use!
```

---

## Next Steps

After successful installation:

1. **Read the docs**
   - [Usage Guide](./docs/USAGE.md)
   - [Configuration Reference](./docs/CONFIG-REFERENCE.md)
   - [Plugin Development](./docs/PLUGIN-DEVELOPMENT.md)

2. **Configure your environment**
   - Add secrets
   - Set up CI/CD
   - Configure IDE

3. **Integrate with workflow**
   - Enable git hooks
   - Add to pre-commit
   - Document for team

4. **Monitor and iterate**
   - Check audit logs weekly
   - Review test patterns
   - Optimize configurations

---

## Support

- **Documentation**: https://docs.sc-conductor.dev
- **Issues**: https://github.com/sc-conductor/sc-conductor/issues
- **Discussions**: https://github.com/sc-conductor/sc-conductor/discussions
- **Slack**: #sc-conductor on company Slack
- **Email**: support@sc-conductor.dev

---

## Frequently Asked Questions

**Q: Can I use sc-conductor with non-Python projects?**  
A: Yes! It supports Go, Rust, TypeScript, Java, and more via language plugins.

**Q: Do I need Vault for secrets?**  
A: No. Use env vars for simple setup, local encrypted file for team, Vault for enterprise.

**Q: How do I migrate to sc-conductor in an existing project?**  
A: Run `sc-conductor init --update` to preserve existing config while updating.

**Q: Can sc-conductor work offline?**  
A: Yes. Output plugins (Slack, Jira) require network, but impact analysis and test running work offline.

**Q: What's the performance impact?**  
A: Negligible. `sc-conductor impact` typically runs in <500ms, cached runs <50ms.

For more FAQs: https://docs.sc-conductor.dev/faq
