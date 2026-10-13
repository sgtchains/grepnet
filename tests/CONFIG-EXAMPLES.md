# Configuration Examples for Different Team Sizes

**Purpose**: Real-world examples of `.conductor.yml` configurations  
**Scope**: Solo dev, small team, medium team, enterprise  
**Version**: 1.0 | October 7, 2026

---

## 1. Solo Developer (Freelancer / Side Project)

### Scenario
- Single developer working on personal project
- Local machine, no CI/CD
- Minimal overhead, maximum simplicity

### `.conductor.yml`

```yaml
# Solo Developer Configuration
framework_version: "1.0"
project_name: "my-cli-tool"

# Simple Python project
language: python
vcs_type: git

# Just git diff, no CI/CD
vcs_options: "--staged"

# No approval workflow overhead
approval_workflow:
  enabled: false

# No output plugins needed
output_plugins: []
compliance_plugins: []

# Local env vars for any secrets
secrets_plugin:
  type: env
  fallback_strategy: "none"

# Discover tests automatically
test_discovery:
  auto_detect: true
  patterns:
    - "tests/test_*.py"
    - "tests/**/*_test.py"
```

### Setup Time
```bash
pip install sc-conductor
cd my-project
sc-conductor init --defaults
# ✓ Done in 1 minute
```

### Daily Workflow
```bash
# Make changes
git add src/colorizer.py

# Quick check: which tests are affected?
sc-conductor impact --analyze
# Output: "3 tests affected"

# Run only those tests
sc-conductor run --affected
# ✓ All pass in 30 seconds instead of 5 minutes

git commit -m "Fix color parsing"
```

### Cost
- 0 external integrations
- 0 secrets to manage
- 0 approval overhead
- No CI/CD costs

---

## 2. Small Team (5-10 developers)

### Scenario
- Small company or startup team
- GitHub-based workflow
- Need some visibility into test results
- Basic CI/CD (GitHub Actions)

### `.conductor.yml`

```yaml
framework_version: "1.0"
project_name: "startup-backend"

# Multi-language support
language: auto
language_plugins:
  - python: src/**/*.py
  - go: cmd/**/*.go

# Git workflow
vcs_type: git
vcs_options: "--staged"

# Light approval workflow for new tests
approval_workflow:
  enabled: true
  state_machine: ["DRAFT", "APPROVED", "AUTOMATED"]
  require_approval: true
  bootstrap_approved: true  # Approve existing tests on init

# Minimal output: GitHub PR comments + Slack
output_plugins:
  - type: github_pr_comment
    on_event: impact_analysis
    comment_template: |
      🧪 **Test Impact Analysis**
      - Affected tests: {affected_count}
      - Estimated time: {est_time}s
  
  - type: slack
    webhook_url: ${SLACK_WEBHOOK}
    on_event: test_failure
    channel: "#dev-alerts"
    severity_threshold: error

# Basic audit trail
compliance_plugins:
  - type: audit_trail
    retention_days: 30

# Secrets from env + local file
secrets_plugin:
  type: local_file
  fallback_strategy: "env"
  cache_enabled: true
  cache_ttl_seconds: 300
  access_levels:
    read_only: true
    can_rotate: false

# Auto-discover tests
test_discovery:
  auto_detect: true

# Enable git hooks
git_hooks:
  pre_commit: true
  pre_push: false
```

### `.conductor.local.yml` (Gitignored)

```yaml
# Team member specific overrides

# Slack is optional per developer
output_plugins:
  - type: slack
    webhook_url: ${SLACK_WEBHOOK}
    on_event: test_failure
```

### Setup Time
```bash
# One-time admin setup
cd startup-backend
sc-conductor init
# Interactive, ~5 minutes

# Add secrets to shared location (if using Vault)
sc-conductor secrets set slack_webhook "https://..."
sc-conductor secrets set github_token "ghp_..."
```

### Developer Workflow
```bash
# Dev 1: Make changes, check impact
git add src/payment.py
sc-conductor impact --analyze
# Output: "5 tests affected"

# Run affected tests locally
sc-conductor run --affected
# ✓ All pass

# Push to GitHub
git push origin feature/payments
# GitHub Actions runs full suite + posts PR comment

# Team sees: "✓ Test Impact: 5 tests affected, all passing"
```

### Admin Workflow
```bash
# Review new tests
sc-conductor approve --interactive
# Shows: "test_payment_webhook.py"
# Decides: Approve or request changes

# Monitor team testing patterns
sc-conductor run --results --json | jq '.failure_rate'
```

### Cost
- GitHub Actions: Free for public repos, ~$20-50/month for private
- Slack: Free tier sufficient
- No storage costs
- Minimal ops overhead

---

## 3. Medium Team (20-50 developers)

### Scenario
- Growing company with multiple services
- Multi-language codebase (Python + Go + TS)
- Strict compliance requirements (SOC2)
- Need centralized test results and audit trail

### `.conductor.yml`

```yaml
framework_version: "1.0"
project_name: "company-platform"

# Multi-language monorepo
language: auto
language_plugins:
  - python: services/*/src/**/*.py
  - go: services/*/cmd/**/*.go
  - typescript: services/*/ui/**/*.ts

# Git with multiple branch support
vcs_type: git
vcs_options: "--staged"

# Strict approval workflow + audit
approval_workflow:
  enabled: true
  state_machine: ["DRAFT", "APPROVED", "AUTOMATED", "DEPRECATED"]
  require_approval: true
  bootstrap_approved: false  # Manual review of existing tests
  approver_groups:
    - name: "backend-reviewers"
      members: ["alice", "bob"]
    - name: "frontend-reviewers"
      members: ["charlie", "diana"]
  require_multi_approval: false  # Single approval sufficient
  auto_approve_similar: true     # Auto-approve if similar test exists

# Rich output integrations
output_plugins:
  - type: github_pr_comment
    on_event: impact_analysis
  
  - type: jira
    url: https://jira.company.com
    project: TEST
    on_event: test_failure
    auto_create_ticket: true
    labels: [automated, test-failure]
    assignee_group: backend-reviewers
  
  - type: slack
    webhook_url: ${SLACK_WEBHOOK}
    on_event: test_failure
    channel: "#eng-alerts"
    mention_group: "@oncall"
  
  - type: postgres
    url: postgresql://localhost/test_results
    on_event: test_result
    batch_size: 100

# Comprehensive compliance
compliance_plugins:
  - type: sbom
    format: cyclonedx
    output_file: sbom.json
  
  - type: security
    framework: SOC2
    max_risk_score: 0.3
    check_secrets: true
    check_licenses: true
  
  - type: audit_trail
    framework: SOC2
    retention_days: 365
    include_test_results: true
  
  - type: coverage
    min_threshold: 0.85
    exclude_patterns: ["**/migrations/*", "**/__init__.py"]

# Vault for secrets (secure)
secrets_plugin:
  type: vault
  vault_addr: ${VAULT_ADDR}
  vault_token: ${VAULT_TOKEN}
  secret_path: "secret/data/sc-conductor/prod"
  fallback_strategy: "fail"  # Strict: no fallback
  cache_enabled: true
  cache_ttl_seconds: 600    # 10 min cache
  refresh_before_expiry: true
  access_levels:
    read_only: true
    can_rotate: false       # Only admins rotate
  rotation:
    enabled: true
    notify_on_rotation: true
    grace_period_seconds: 120

# RBAC for production
rbac:
  enabled: true
  admin_groups: ["platform-leads"]
  approver_groups: ["backend-reviewers", "frontend-reviewers"]
  developer_group: "engineers"

# Git hooks
git_hooks:
  pre_commit: true
  pre_push: true
  post_merge: true

# CI/CD integration
ci_cd:
  platform: github_actions
  gate_pr_merge: true       # Require test results before merge
  block_on_failure: true
```

### `~/.sc-conductor/config.yml` (User's Home Dir)

```yaml
# Shared across all projects for this user

# Local development settings
secrets_plugin:
  type: local_file
  cache_enabled: true

# Development overrides (don't auto-create Jira tickets)
output_plugins:
  - type: slack
    webhook_url: ${SLACK_DEV_WEBHOOK}
    on_event: test_failure

# RBAC: Everyone is developer locally
rbac:
  enabled: false
```

### Admin Setup

```bash
# Central admin setup (happens once)
mkdir -p /opt/sc-conductor
git clone <repo> /opt/sc-conductor
chmod a+rx /opt/sc-conductor

# System config
sudo mkdir -p /etc/sc-conductor
sudo cp /opt/sc-conductor/config.default.yml /etc/sc-conductor/config.yml
```

### Developer Setup

```bash
# Each developer (first time)
pip install sc-conductor

cd company/platform

# Review existing config
cat .conductor.yml

# Personalize for local dev (optional)
cp ~/.sc-conductor/config.yml .conductor.local.yml
# Edit to skip Jira ticketing locally
```

### CI/CD Workflow

```yaml
# .github/workflows/sc-conductor.yml (auto-generated by init)
name: Test Impact Analysis

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  impact:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Install framework
        run: pip install sc-conductor
      
      - name: Configure secrets (Vault)
        env:
          VAULT_ADDR: ${{ secrets.VAULT_ADDR }}
          VAULT_TOKEN: ${{ secrets.VAULT_TOKEN }}
        run: echo "✓ Vault configured"
      
      - name: Analyze impact
        run: sc-conductor impact --analyze --json > report.json
      
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
              body: `🧪 **Test Impact**\n\n${report.summary}`
            });
      
      - name: Create Jira tickets if needed
        env:
          JIRA_TOKEN: ${{ secrets.JIRA_TOKEN }}
        run: sc-conductor run --affected --output-plugins jira
      
      - name: Block merge if tests fail
        if: failure()
        run: |
          echo "❌ Tests failed - PR cannot be merged"
          exit 1
```

### Compliance Reports (Monthly)

```bash
# Generate SOC2 compliance report
sc-conductor report --type audit_trail --output compliance/audit_$(date +%Y-%m).json

# Generate SBOM for security scanning
sc-conductor report --type sbom --output sbom.cyclonedx.json

# Coverage report
sc-conductor report --type coverage --output coverage.json
```

### Cost
- Vault: Self-hosted (free) or cloud ~$500/month
- GitHub Actions: ~$100-300/month for medium team
- Slack: Free tier or Pro
- Jira: ~$1000+/year (company-wide)
- Postgres: Managed (~$20-50/month) or self-hosted
- Total: $500-2000/month

---

## 4. Enterprise Organization (100+ developers)

### Scenario
- Large organization with multiple teams
- Strict compliance (SOC2, ISO27001, HIPAA)
- Multiple environments (dev, staging, prod)
- Distributed deployment across data centers
- Need advanced RBAC, audit, and analytics

### `.conductor.yml` (Simplified View)

```yaml
framework_version: "1.0"
project_name: "enterprise-platform"
environment: "prod"  # prod | staging | dev

# Multiple language support
language: auto
language_plugins:
  - python: services/*/src/**/*.py
  - go: services/*/cmd/**/*.go
  - typescript: services/*/ui/**/*.ts
  - java: services/*/src/**/*.java
  - rust: services/*/src/**/*.rs

# Git with branch-based config
vcs_type: git
vcs_options: "--staged"

# Sophisticated approval workflow
approval_workflow:
  enabled: true
  state_machine: ["DRAFT", "APPROVED", "AUTOMATED", "DEPRECATED", "SKIPPED_BUG"]
  require_approval: true
  bootstrap_approved: false
  
  approver_routing:
    # Different approvers by service/module
    - pattern: "services/payments/*"
      approver_group: "payments-team"
      require_multi_approval: 2
    
    - pattern: "services/security/*"
      approver_group: "security-team"
      require_multi_approval: 3
    
    - pattern: "services/api/*"
      approver_group: "backend-team"
      require_multi_approval: 1
  
  escalation_policy:
    - level: "critical"
      escalate_to: "eng-leads"
      after_hours: "oncall"

# Distributed output plugins
output_plugins:
  - type: github_pr_comment
    on_event: impact_analysis
  
  - type: jira
    url: https://jira.enterprise.com
    instance: "prod"
  
  - type: slack
    webhook_url: ${SLACK_WEBHOOK}
    channel_mapping:
      payments: "#payments-alerts"
      security: "#security-alerts"
      api: "#backend-alerts"
  
  - type: postgres
    url: postgresql://analytics-prod.internal/test_results
    replicate_to: ["postgresql://analytics-dr.internal/"]
  
  - type: s3
    bucket: "enterprise-test-results"
    region: "us-east-1"
    archive_after_days: 90

# Comprehensive compliance (multiple frameworks)
compliance_plugins:
  - type: sbom
    format: cyclonedx
    scan_transitive: true
    output_file: sbom.json
  
  - type: security
    framework: ["SOC2", "ISO27001", "HIPAA"]
    max_risk_score: 0.1
    secret_scanning: true
    license_validation: true
  
  - type: coverage
    min_threshold: 0.90
    fail_if_coverage_decreases: true
  
  - type: audit_trail
    frameworks: ["SOC2", "ISO27001"]
    retention_days: 2555  # 7 years
    immutable_log: true   # Append-only

# Advanced RBAC
rbac:
  enabled: true
  sso_integration: "okta"  # Okta/LDAP/AAD
  
  roles:
    admin:
      permissions: ["create", "approve", "rotate_secrets", "delete"]
    approver:
      permissions: ["approve", "view"]
    developer:
      permissions: ["run_tests", "view_results"]
    viewer:
      permissions: ["view_results"]
  
  team_assignments:
    - team: "payments"
      approvers: 2
      admins: ["alice@company.com"]
    
    - team: "security"
      approvers: 3
      admins: ["bob@company.com", "charlie@company.com"]

# Enterprise secrets management
secrets_plugin:
  type: vault
  vault_cluster: "prod"
  vault_addr: https://vault-prod-01.internal:8200
  vault_namespace: "sc-conductor"
  auth_method: "oidc"  # OIDC via Okta
  secret_path: "secret/data/sc-conductor/{environment}/{service}"
  
  fallback_strategy: "fail"
  cache:
    enabled: true
    ttl_seconds: 300
    refresh_before_expiry: true
  
  rotation:
    enabled: true
    schedule: "monthly"
    notify_on_rotation: true

# Distributed/High Availability
distribution:
  mode: "distributed"
  workers: 4
  task_queue: "redis"
  redis_cluster: "redis-prod.internal:6379"
  
# Advanced analytics
analytics:
  enabled: true
  elasticsearch:
    url: "https://elasticsearch-prod.internal"
    index: "sc-conductor-results"
  
  dashboards:
    - "test_health_by_service"
    - "approval_latency"
    - "failure_patterns"
    - "compliance_status"
```

### Multi-Environment Strategy

**Development** (`.sc-conductor impact.dev.yml`):
```yaml
environment: dev
approval_workflow:
  enabled: false  # No approval in dev

output_plugins:
  - type: slack
    channel: "#dev-testing"

secrets_plugin:
  type: env  # Simple for dev

compliance_plugins: []  # Skip in dev
```

**Staging** (`.sc-conductor impact.staging.yml`):
```yaml
environment: staging
approval_workflow:
  enabled: true
  require_approval: true

output_plugins:
  - type: slack
    channel: "#staging-alerts"
  - type: postgres
    url: postgresql://analytics-staging/test_results

compliance_plugins:
  - type: audit_trail  # Track for audit
```

**Production** (`.sc-conductor impact.prod.yml`):
```yaml
environment: prod
approval_workflow:
  enabled: true
  require_multi_approval: 2  # Extra rigor

output_plugins:
  # All plugins enabled
  - type: jira
  - type: slack
  - type: postgres
  - type: s3

compliance_plugins:
  # All compliance checks enabled
  - type: sbom
  - type: security
  - type: coverage
  - type: audit_trail

secrets_plugin:
  type: vault
  cache_ttl_seconds: 300  # No aggressive caching in prod
```

### Administrator Dashboard

```bash
# Monitor compliance status
sc-conductor dashboard --show=compliance
# → SOC2: ✓ PASS, ISO27001: ✓ PASS, HIPAA: ⚠ REVIEW

# Generate quarterly audit
sc-conductor report --type audit_trail --quarter Q4 --output audit_q4_2026.json

# Analyze test failure patterns
sc-conductor analytics --metric failures_by_service --period 30d

# Manage user access
sc-conductor rbac --list-users
sc-conductor rbac --promote alice@company.com --role approver

# Rotate secrets with grace period
sc-conductor secrets --rotate jira_token --grace-period 120
# → Token rotated, old one active for 2 minutes
# → All services get new token automatically
```

### Cost
- Vault Enterprise: ~$5000/year (or self-hosted)
- GitHub Enterprise: ~$20-40k/year
- Jira Enterprise: ~$10k+/year
- Slack Enterprise: ~$3-5k/year
- Postgres/RDS: ~$500-2000/month
- S3/Cloud Storage: ~$100-500/month
- Elasticsearch: ~$1000-5000/month
- **Total: $50-100k/year**

But **ROI**: Prevents 1-2 critical bugs = ROI in first week

---

## Comparison Matrix

| Aspect | Solo Dev | Small Team | Medium Team | Enterprise |
|--------|----------|-----------|------------|-----------|
| **Setup Time** | 1-2 min | 5-10 min | 30 min | 2-4 hours |
| **Languages** | 1 | 2-3 | 3-5 | 5+ |
| **Approval** | No | Light | Strict | Multi-level |
| **Secrets** | Env vars | Local file | Vault | Vault cluster + OIDC |
| **Integrations** | 0 | 2-3 | 4-5 | 6+ |
| **Compliance** | No | Audit trail | SOC2 | SOC2 + ISO + HIPAA |
| **RBAC** | N/A | No | Basic | Full + SSO |
| **Distribution** | N/A | No | No | Yes (HA/workers) |
| **Cost** | Free | <$500/mo | $1-2k/mo | $50-100k/year |
| **Developers** | 1 | 5-10 | 20-50 | 100+ |

---

## Migration Path

**From Solo → Small Team**:
```bash
# Add approval workflow
sc-conductor init --update
# Follow prompts, keep existing tests

# Add Slack
.conductor.yml → output_plugins: [slack]
export SLACK_WEBHOOK="https://..."
```

**From Small → Medium**:
```bash
# Add Vault and multi-approval
sc-conductor init --update --secrets vault
# Migrate secrets from local_file to Vault
sc-conductor secrets migrate --from local_file --to vault

# Add Jira and coverage requirements
# Update .conductor.yml with compliance
```

**From Medium → Enterprise**:
```bash
# Enable distributed mode
sc-conductor init --update --distribution redis
# Set up Redis cluster
# Configure RBAC via OIDC
# Integrate with analytics
```

---

## Recommendations

1. **Start with defaults** (solo dev config)
2. **Only add what you need** (approval if team, Vault if secrets matter)
3. **Migrate gradually** (init --update preserves settings)
4. **Review quarterly** (compliance requirements change)

Most teams need **small team config**. Enterprise config only if:
- 100+ developers
- Strict compliance (SOC2/ISO/HIPAA)
- Multiple environments with promotion
- Multi-team approval chains
