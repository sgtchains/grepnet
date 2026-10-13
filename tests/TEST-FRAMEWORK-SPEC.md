# CLI Test Framework Specification

**Project**: Universal, Human-Validated Testing System for CLI Tools  
**Version**: 1.0  
**Date**: October 7, 2026  
**Status**: SPECIFICATION (not yet implemented)  
**Scope**: Reusable framework for testing any command-line application

---

## 1. Overview

This document specifies the design of a ground-up testing framework for CLI tools. It is:

- **Universal**: Works with any CLI application (grepnet, curl, grep, custom tools, etc.)
- **Unified**: Single test library, consistent interfaces, no duplication
- **Human-Validated**: Captures human approval/rejection of test results
- **Persistent**: Maintains validation history per test
- **Integrated**: Works with both automated and manual execution
- **Scalable**: Designed to handle 1000+ tests efficiently across multiple projects
- **Maintainable**: Clear architecture, easy for new maintainers
- **Reusable**: Framework portable across projects
- **API-First**: Designed as backend for future web UI (HTTPS, REST API)
- **Cloud-Ready**: Architecture supports eventual multi-user, distributed deployment

---

## 2. Core Concepts

### 2.1 Test

A **test** is an automated verification that a CLI tool behaves correctly for a specific input/scenario.

**Structure**:
```
Test ID: Unique integer 001-999
Test Name: Human-readable description
Category: Organized by feature/functionality
Command: Shell command to run the tool
Expected Result: What correct output looks like
Spec Reference: Link to application documentation
```

**Example** (grepnet):
```
ID: 001
Name: Basic CIDR pattern matching
Category: core
Command: grepnet '192.0.2.0/24' files/sample.txt
Expected: 192.0.2.0/24
Spec: GREPNET-SPEC.md section 3.2 (Network Format Detection)
```

**Example** (curl):
```
ID: 001
Name: Basic HTTP GET request
Category: core
Command: curl -s http://example.com/api
Expected: {"status":"ok"}
Spec: Docs/API.md section 2.1
```

**Example** (custom tool):
```
ID: 001
Name: Version flag output
Category: core
Command: mytool --version
Expected: mytool version 1.0
Spec: README.md (Getting Started)
```

### 2.2 Validation

A **validation** is a human's recorded approval: "This test is well-designed and ready for automation."

**Structure**:
```
Test ID: Which test was validated
Status: approved | rejected | needs_revision
Validator: Username or identifier
Timestamp: ISO 8601 UTC
Notes: Why approved/rejected, suggestions
Approval Hash: SHA256 of test definition (to detect changes)
```

**Workflow**:
1. Developer writes test (defines command, expected output)
2. Test runs in isolation (manual or semi-automatic)
3. Human validator reviews: 
   - Is the command correct?
   - Are expected results accurate?
   - Is the test well-isolated?
   - Can this be reliably automated?
4. Validator approves (locks test) or requests revision
5. Once approved, test enters automated suite
6. Automated runs continue indefinitely
7. Test result failures don't require re-validation (but may trigger investigation)
8. If test definition changes, re-validation required

**Key Point**: Validation is *pre-automation approval*, not *post-result verification*.

### 2.3 Test Suite

A **test suite** is the complete collection of all tests, organized by:
- Approval state (draft, approved, archived)
- Category/functionality
- Project

**Properties**:
- Total test count: Designed for 1000+
- Approved tests: Tests ready for automation
- Draft tests: Tests awaiting human approval
- Categories: Organized by feature
- Dependencies: None (tests should be independent)
- Execution time: Target < 5 minutes for 1000 tests

### 2.4 Test State Machine

```
DRAFT
  ↓ (human approves)
APPROVED  ← (test definition unchanged)
  ↓ (enters automated suite)
AUTOMATED
  ↓ (test definition changes)
APPROVAL_NEEDED  ← (needs re-validation)
  ↓ (human re-approves)
APPROVED
  ↓ (back to automated)
AUTOMATED
  ↓ (marked obsolete/deprecated)
ARCHIVED
```

**States**:
- `DRAFT`: New test, awaiting human approval
- `APPROVED`: Validated by human, locked, ready for automation
- `AUTOMATED`: Running in test suite, results tracked
- `APPROVAL_NEEDED`: Test definition changed, needs re-validation before automation resumes
- `ARCHIVED`: No longer used

**Transitions**:
- DRAFT → APPROVED: Human validator approves
- APPROVED → AUTOMATED: Test enters suite (automatic)
- AUTOMATED → APPROVAL_NEEDED: Test definition/command/expected output changes
- APPROVAL_NEEDED → APPROVED: Human re-approves changes
- Any → ARCHIVED: Explicitly marked obsolete

---

## 3. Architecture

### 3.1 File Organization

```
framework/                         # Reusable framework (can be symlinked)
├── __init__.py
├── test_runner.py                 # Execute tests (automated)
├── test_validator.py              # Interactive validation tool
├── result_tracker.py              # JSON result management
├── test_registry.py               # Test catalog
├── cli_executor.py                # Execute arbitrary CLI commands
└── README.md                       # Framework usage guide

projects/
├── grepnet/
│   ├── tests/
│   │   ├── TEST-FRAMEWORK-SPEC.md (this file, symlinked from framework/)
│   │   ├── lib/
│   │   │   ├── test-common.sh     # Bash utilities
│   │   │   └── README.md
│   │   ├── catalog/
│   │   │   ├── 001-010.yml        # Test definitions
│   │   │   └── ...
│   │   ├── sub-tests/             # Test scripts
│   │   │   ├── 001_basic_cidr.sh
│   │   │   └── ...
│   │   ├── data/                  # Test input files
│   │   └── results/
│   │       ├── latest.json
│   │       ├── history/
│   │       └── reports/
│   └── ...
│
├── mytool/
│   ├── tests/
│   │   ├── TEST-FRAMEWORK-SPEC.md (symlink to ../../framework/TEST-FRAMEWORK-SPEC.md)
│   │   ├── lib/
│   │   ├── catalog/
│   │   ├── sub-tests/
│   │   ├── data/
│   │   └── results/
│   └── ...
│
└── anothertool/
    ├── tests/
    │   └── (same structure)
    └── ...
```

### 3.2 Component Roles

| Component | Language | Purpose | Responsibilities |
|-----------|----------|---------|------------------|
| **test_runner.py** | Python | Automated execution | Run tests, collect output, compare expected |
| **test_validator.py** | Python | Interactive validation | Show results to human, prompt for pass/fail, log decision |
| **result_tracker.py** | Python | Result persistence | Save JSON, read history, compute statistics |
| **test_registry.py** | Python | Test catalog | Load test metadata, validate definitions |
| **cli_executor.py** | Python | CLI abstraction | Execute any CLI command portably (handles env, paths, etc.) |
| **test-common.sh** | Bash | Test utilities | Setup/teardown, assertions, logging for bash tests |
| **NNN_*.sh** | Bash | Individual tests | Each test is standalone bash script |

### 3.3 Execution Flows

#### 3.3.1 Test Approval Workflow

```
1. Developer creates test (catalog entry + script)
2. Test placed in DRAFT state
3. test_validator.py --approve NNN
4. Display test definition:
   - Command
   - Expected output
   - Description
   - Spec reference
5. Validator reviews and either:
   a. Approve (test → APPROVED state)
   b. Reject (test stays DRAFT, feedback to developer)
   c. Request revision
6. Once APPROVED, test auto-enters AUTOMATED state
7. If test definition changes: test → APPROVAL_NEEDED (must be re-approved)
```

#### 3.3.2 Automated Run (CI/CD)

```
1. test_runner.py --mode=auto --project=grepnet
2. Load all APPROVED or AUTOMATED tests from catalog/
3. For each test:
   a. Execute: ./sub-tests/NNN_*.sh
   b. Capture: exit code + stdout + stderr
   c. Compare: actual vs expected
   d. Record: result in results/latest.json
   e. Track: pass/fail per test
4. Generate report
5. Exit with status (0=all pass, 1=any fail)
```

#### 3.3.3 Manual Test Execution (for debugging)

```
1. cd tests/sub-tests
2. bash 001_basic_matching.sh
3. Test script sources: ../lib/test-common.sh
4. Script reports: PASS/FAIL directly
5. Exits with 0 or 1
```

#### 3.3.4 Test Definition Change Detection

```
1. On test approval, hash test definition (YAML + script)
2. Store hash in approval record
3. Before each automated run, compare:
   - Current definition hash
   - Approved definition hash
4. If mismatch: test → APPROVAL_NEEDED state
5. Block from automated suite until re-approved
```

---

## 4. Test Definition Format

### 4.1 Catalog (YAML)

**File**: `tests/catalog/001-010.yml`

Each project customizes this for its own CLI. Examples:

**grepnet example**:
```yaml
tests:
  001:
    name: "Basic CIDR pattern matching"
    category: core
    description: |
      Test that grepnet correctly identifies and matches CIDR notation
      patterns (e.g., 192.0.2.0/24) in both patterns and files.
    
    command: |
      grepnet '192.0.2.0/24' tests/data/sample_networks.txt
    
    expected:
      exit_code: 0
      stdout: |
        192.0.2.0/24
        192.0.2.0 255.255.255.0
      stderr: ""
    
    spec_reference: "GREPNET-SPEC.md#section-3.2"
```

**curl example**:
```yaml
tests:
  001:
    name: "Basic HTTP GET"
    category: core
    description: Test simple GET request
    
    command: |
      curl -s https://httpbin.org/get
    
    expected:
      exit_code: 0
      stdout_contains: "headers"
      stderr: ""
    
    spec_reference: "README.md#basic-usage"
```

**mytool example**:
```yaml
tests:
  001:
    name: "Version output"
    category: core
    
    command: |
      mytool --version
    
    expected:
      exit_code: 0
      stdout_matches: "mytool version \\d+\\.\\d+"
    
    spec_reference: "docs/cli-reference.md"
```

### 4.2 Test Script Structure (Bash)

**File**: `tests/sub-tests/001_basic_matching.sh`

Generic structure (works with any CLI):

```bash
#!/bin/bash
# Test 001: Basic matching
# Category: core
# Spec: docs/reference.md

set -euo pipefail

# Source unified test library
TEST_DIR="$(cd "$(dirname "$0")/.." && pwd)"
source "${TEST_DIR}/lib/test-common.sh"

# Initialize test environment
test_init

# Configure which CLI to test
# This is set by environment or test framework
# Examples:
#   TESTCMD="grepnet"
#   TESTCMD="curl"
#   TESTCMD="mytool"
TESTCMD="${TESTCMD:-grepnet}"

# Run test
output=$("${TESTCMD}" '192.0.2.0/24' "${TEST_DIR}/data/sample.txt" 2>&1)
exit_code=$?

# Validate
assert_exit_code 0 "$exit_code"
assert_output_contains "192.0.2.0/24" "$output"

# Report result
test_passed
```

This same test script can run different CLIs by changing TESTCMD environment variable.

---

## 5. Test Approval Format

### 5.1 Approval History File

**File**: `tests/results/approvals/001_basic_matching.json`

```json
{
  "test_id": 1,
  "test_name": "Basic CIDR pattern matching",
  "test_file": "001_basic_matching.sh",
  "catalog_file": "catalog/001-010.yml",
  "category": "core",
  
  "approval_history": [
    {
      "approval_id": "2026-10-07T14:30:00Z-alice-v1",
      "timestamp": "2026-10-07T14:30:00Z",
      "approver": "alice",
      "status": "approved",
      "notes": "Test is well-isolated and correctly specified",
      "definition_hash": "sha256:abcd1234...",
      "command": "grepnet '192.0.2.0/24' tests/data/sample.txt",
      "expected_exit_code": 0,
      "expected_output_contains": ["192.0.2.0/24"]
    },
    {
      "approval_id": "2026-10-07T10:00:00Z-bob-v1",
      "timestamp": "2026-10-07T10:00:00Z",
      "approver": "bob",
      "status": "rejected",
      "notes": "Expected output too vague, needs to specify exact match",
      "definition_hash": "sha256:xyz789...",
      "feedback": "Please use exact output match, not 'contains'"
    }
  ],
  
  "current_state": {
    "state": "approved",
    "approved_by": "alice",
    "approved_at": "2026-10-07T14:30:00Z",
    "approved_definition_hash": "sha256:abcd1234...",
    "definition_hash_match": true,
    "automation_eligible": true,
    "last_run": "2026-10-07T16:15:23Z",
    "last_run_status": "pass"
  },
  
  "statistics": {
    "total_reviews": 2,
    "approved_count": 1,
    "rejected_count": 1,
    "current_approval_rate": 0.5,
    "first_approval": "2026-10-07T14:30:00Z",
    "last_review": "2026-10-07T14:30:00Z"
  }
}
```

### 5.2 Automated Run Result File

**File**: `tests/results/latest.json`

```json
{
  "run_id": "2026-10-07T16:00:00Z",
  "run_mode": "automated",
  "timestamp": "2026-10-07T16:00:00Z",
  "duration_seconds": 245.23,
  "grepnet_version": "2.0.0",
  
  "summary": {
    "total_tests": 1250,
    "passed": 1230,
    "failed": 15,
    "skipped": 5,
    "approval_needed": 0,
    "pass_rate": 0.984
  },
  
  "test_results": [
    {
      "test_id": 1,
      "name": "Basic CIDR pattern matching",
      "category": "core",
      "status": "pass",
      "exit_code": 0,
      "duration_ms": 125,
      "approval_state": "approved",
      "definition_hash_match": true
    },
    {
      "test_id": 2,
      "name": "CIDR from stdin",
      "category": "core",
      "status": "fail",
      "exit_code": 1,
      "duration_ms": 89,
      "approval_state": "approved",
      "definition_hash_match": true,
      "expected_output": "192.0.2.0/24",
      "actual_output": "192.0.2.0/24\nExtra output",
      "investigation_needed": true
    },
    {
      "test_id": 50,
      "name": "New feature test",
      "category": "parsing",
      "status": "skipped",
      "reason": "Test in DRAFT state, not approved yet",
      "approval_state": "draft",
      "definition_hash_match": true
    }
  ],
  
  "failed_tests": [2, 45, 102],
  "approval_needed_tests": [125, 203]
}
```

---

## 6. Validator Interface (Test Approval)

### 6.1 Interactive Approval Session

```
$ python framework/test_validator.py --approve 001

========================================================
TEST APPROVAL REVIEW
========================================================

Test ID: 001
Name: Basic CIDR pattern matching
State: DRAFT
Category: core

Command:
  grepnet '192.0.2.0/24' tests/data/sample_networks.txt

Expected:
  Exit Code: 0
  Output Contains: "192.0.2.0/24"
  Output Contains: "192.0.2.0 255.255.255.0"

Spec Reference:
  GREPNET-SPEC.md#section-3.2

Description:
  Test that grepnet correctly identifies and matches CIDR notation
  patterns (e.g., 192.0.2.0/24) in both patterns and files.

---

APPROVAL DECISION: 
  (a)pprove / (r)eject / (n)eeds_revision / (s)kip: _
```

If approved:
```
Additional notes (optional): _

Definition Hash: sha256:abcd1234...
Approval recorded and test transitioned to APPROVED state.
Test will enter automated suite on next run.
```

### 6.2 Command-Line Modes

```bash
# Approve single test
python framework/test_validator.py --approve 001

# Approve all DRAFT tests in category
python framework/test_validator.py --approve-category core

# Approve all DRAFT tests
python framework/test_validator.py --approve-all

# Show approval history for a test
python framework/test_validator.py --test=001 --approval-history

# Review tests needing re-approval (definition changed)
python framework/test_validator.py --approval-needed

# Generate approval report
python framework/test_validator.py --report
```

---

## 7. Test Library Functions (test-common.sh)

### 7.1 Initialization

```bash
test_init                          # Set up test environment
test_cleanup                       # Clean up after test
```

### 7.2 Execution & Logging

```bash
run_grepnet [args...]              # Execute grepnet, capture output
log_info "message"                 # Log info level
log_error "message"                # Log error level
```

### 7.3 Assertions

```bash
assert_exit_code EXPECTED ACTUAL   # Verify exit code
assert_output EXPECTED ACTUAL      # Verify exact output
assert_contains HAYSTACK NEEDLE    # Verify substring
assert_matches PATTERN OUTPUT      # Verify regex
assert_empty OUTPUT                # Verify no output
```

### 7.4 Reporting

```bash
test_passed [message]              # Record pass
test_failed [message]              # Record fail
test_skipped [reason]              # Record skip
```

---

## 8. Pass Criteria

### 8.1 Automated Mode

A test **passes** in automated mode if:
1. Exit code matches expected
2. Output matches expected (exact or via regex)
3. Stderr matches expected (or is empty if not specified)

### 8.2 Validation Mode

A test **passes** in validation mode if:
- Human(s) explicitly validate it as "pass"

### 8.3 Consensus Pass Rate

For a test to be considered "stable":
- At least 2 validations from independent validators
- At least 80% of validations say "pass"
- Last 3 validations all say "pass"

---

## 9. Reporting

### 9.1 Console Report (after run)

```
========================================================
TEST RUN SUMMARY
========================================================
Run Time: 2026-10-07 16:00:00 UTC
Mode: automated
Duration: 45 seconds

Total Tests: 50
✓ Passed:  48
✗ Failed:  2
⊘ Skipped: 0

Pass Rate: 96.0%

Failed Tests:
  #002: CIDR from stdin (new failure - needs review)
  #045: IPv6 range format (regression - was passing)

========================================================
```

### 9.2 HTML Report (generated)

- Visual pass/fail timeline per test
- Validation history per test (with diff highlighting)
- Trend charts (pass rate over time)
- Validator statistics (who validated, consensus metrics)

---

## 10. Integration Points (API-First Design)

### 10.1 CLI Usage (Current)

```bash
# Approve tests via CLI
python framework/test_validator.py --approve 001

# Run automated suite
python framework/test_runner.py --mode=auto --project=grepnet

# Query results via CLI
python framework/test_runner.py --report
```

### 10.2 REST API (For Future Web UI)

```
POST /api/v1/tests/{id}/approve
  { "approver": "alice", "notes": "..." }

GET /api/v1/tests?state=draft
  Returns all tests awaiting approval

GET /api/v1/tests/{id}/approval-history
  Returns approval history for a test

POST /api/v1/runs
  { "mode": "auto", "project": "grepnet" }
  Starts automated test run

GET /api/v1/runs/{run_id}/results
  Returns results for a run

GET /api/v1/projects
  Lists all projects with framework
```

### 10.3 Database Schema (For Scaling 1000+ Tests)

Eventually, for large-scale multi-user scenarios:
- JSON files → SQLite (default, single-machine)
- SQLite → PostgreSQL (multi-user, networked)
- Test runner distributed across workers
- Approval workflow with role-based access control

Current implementation stays JSON-based for simplicity and portability.

### 10.4 With CI/CD Pipeline

```bash
# Before merge
python framework/test_runner.py --mode=auto --project=grepnet --fail-on-failures

# Exit 0: All approved tests pass
# Exit 1: Test failure detected
# Exit 2: Approval-needed tests detected (must re-approve changes before merge)
```

### 10.5 Developer Workflow

```bash
# Developer writes new test
vi tests/catalog/051-060.yml
vi tests/sub-tests/051_new_feature.sh

# Test placed in DRAFT state automatically
# (framework detects new files)

# Developer runs it manually to verify
bash tests/sub-tests/051_new_feature.sh

# Reviewer approves test
python framework/test_validator.py --approve 051

# Test enters APPROVED state, added to automated suite on next run
python framework/test_runner.py --mode=auto

# Test now runs in all future automated runs
```

### 10.6 Multi-Project Orchestration

```bash
# Run all tests for all projects
python framework/test_runner.py --mode=auto --all-projects

# Run with filtering
python framework/test_runner.py --mode=auto --project=grepnet --category=core

# Parallel execution (future enhancement)
python framework/test_runner.py --mode=auto --workers=4
```

---

## 12. Implementation Phases

### Phase 1: Foundation (Week 1-2)
- [ ] Create Python framework skeleton
- [ ] Implement test_runner.py (automated execution)
- [ ] Implement result_tracker.py (JSON I/O, file storage)
- [ ] Implement cli_executor.py (portable CLI invocation)
- [ ] Create test-common.sh bash library
- [ ] Create test registry and state management

### Phase 2: Test Approval Workflow (Week 2-3)
- [ ] Implement test_validator.py (interactive approval)
- [ ] Implement approval history tracking (JSON)
- [ ] Implement test state machine (DRAFT → APPROVED → AUTOMATED)
- [ ] Implement definition hash tracking (detect changes)
- [ ] Add approval CLI commands
- [ ] Add approval reporting

### Phase 3: GrepNet Migration (Week 3-4)
- [ ] Port all 50 grepnet tests from tests.old/
- [ ] Create catalog YAML files
- [ ] Mass approve tests (one-time bootstrap)
- [ ] Verify all tests pass in automated mode
- [ ] Generate documentation

### Phase 4: Scale & Reusability (Week 4-5)
- [ ] Test with 1000+ test dataset
- [ ] Performance optimization (parallel runs)
- [ ] Multi-project orchestration
- [ ] Project scaffolding (--init)
- [ ] HTML report generation
- [ ] Trend analysis and visualizations

### Phase 5: API & Web Ready (Week 5-6)
- [ ] REST API endpoints (approval, runs, results)
- [ ] Package for distribution
- [ ] Documentation for external projects
- [ ] CI/CD integration examples
- [ ] Prepare for web UI wrapping

---

## 13. Success Criteria

| Metric | Target | Current |
|--------|--------|---------|
| Test count (initial) | 50 (grepnet) | 0 (starting from scratch) |
| Test count (scalability) | 1000+ | TBD |
| Approval workflow | Fully functional | TBD |
| Test execution time | <5 min for 1000 tests | N/A |
| Test add time | <5 min per test | N/A |
| Framework reusability | Works for 2+ projects | TBD |
| API completeness | REST endpoints working | TBD |
| Documentation completeness | >90% | TBD |
| Web UI ready | Can be wrapped in HTTPS UI | TBD |

---

## 15. Test Impact Analysis (Optional Plugin System)

### Overview

The framework supports optional **language-specific plugins** for intelligent test selection based on code changes. When developers modify code, plugins automatically:
1. Parse the codebase and build a call graph
2. Detect changes via git diff or file modification timestamps
3. Trace which functions are affected
4. Map affected functions to impacted tests
5. Recommend which tests to run (or run them automatically in CI)

This enables **selective test execution** (run only affected tests), **test prioritization** (run high-impact tests first), and **orphaned test detection** (identify tests with no code dependency).

### Plugin System Architecture

The impact analysis system uses **two complementary plugin systems**:

1. **VCS (Version Control System) Plugins** - Detect changes in the codebase
2. **Language Plugins** - Parse code and build call graphs

This separation allows:
- Support for multiple VCS (Git, Mercurial, Perforce, local file mtime)
- Support for multiple languages (Python, Go, Rust, TypeScript, etc.)
- Swappable implementations for testing and CI/CD environments

```
ImpactAnalyzer (orchestrator)
├── VcsPlugin (detect changes)
│   ├── GitPlugin (staged/unstaged changes)
│   ├── HgPlugin (Mercurial)
│   ├── P4Plugin (Perforce)
│   ├── FileMtimePlugin (file modification time)
│   └── ManualPlugin (explicit change specification)
└── LanguagePlugin (analyze code)
    ├── PythonPlugin (AST analysis)
    ├── GoPlugin (go/parser)
    ├── RustPlugin (rust-analyzer)
    └── TypeScriptPlugin (TypeScript compiler)
```

### Use Cases

| Use Case | Benefit | Example |
|----------|---------|---------|
| **After git commit** | Run only affected tests | Changed `colorizer.py` → Run 2 tests instead of 50 |
| **In CI/CD** | Faster feedback loop | 2min for affected tests vs 10min for full suite |
| **Before push** | Catch breaking changes early | Pre-commit hook: "This change affects 8 tests" |
| **Test review** | Link code to tests | Show: "This function tested by test_xyz.sh" |
| **Orphan detection** | Clean up unused tests | Report: "test_abc.sh has no code dependency" |
| **Regression analysis** | Understand test failures | "Why did test_xyz fail? It depends on..." |

### Plugin Architecture

#### VCS (Version Control System) Plugins

VCS plugins detect which files and functions changed in the codebase. The framework supports multiple VCS implementations:

**VCS Plugin Interface**:

```python
class VcsPlugin(ABC):
    """Abstract base for version control system plugins."""
    
    @abstractmethod
    def get_diff(self, options: str = "") -> str:
        """
        Get diff output representing changes.
        
        Args:
            options: VCS-specific options
                e.g., "--cached" for git (staged changes)
                e.g., "--unstaged" for git (working directory changes)
                e.g., "-r . -r .^" for Mercurial (last commit)
        
        Returns:
            Diff output as string
        """
        pass
    
    @abstractmethod
    def get_changed_files(self, options: str = "") -> List[str]:
        """Get list of changed file paths."""
        pass
    
    def get_vcs_name(self) -> str:
        """Return VCS name (e.g., 'git', 'hg', 'p4')."""
        pass
```

**Available VCS Plugins**:

| Plugin | VCS | Use Case | Options |
|--------|-----|----------|---------|
| `GitPlugin` | Git | Standard CI/CD, local development | `--cached`, `--unstaged`, `--head~1..head` |
| `HgPlugin` | Mercurial | Companies using Hg | `-r . -r .^` (last changeset) |
| `P4Plugin` | Perforce | Enterprise environments | `-du` (unified diff) |
| `FileMtimePlugin` | File mtime | Local development, no VCS | (uses filesystem timestamps) |
| `ManualPlugin` | Manual | Testing, CI automation | Explicit change lists |

**Configuration**:

```yaml
impact_analysis:
  # Auto-detect VCS type or explicitly specify
  vcs_type: git              # git, hg, p4, mtime, manual
  vcs_options: "--cached"    # VCS-specific options
  
  # Or provide custom VCS plugin
  # vcs_plugin: CustomVcsPlugin(...)
```

**Example: Using Different VCS**

```python
from framework.impact import ImpactAnalyzer, ImpactConfig, GitPlugin, ManualPlugin

# Git-based analysis (most common)
config = ImpactConfig(vcs_type='git', vcs_options='--unstaged')
analyzer = ImpactAnalyzer(config=config, root_dir='.')

# Manual plugin for CI/CD testing
manual_vcs = ManualPlugin(changed_files=['src/colorizer.py'])
config = ImpactConfig(vcs_plugin=manual_vcs)
analyzer = ImpactAnalyzer(config=config, root_dir='.')

# Mercurial
config = ImpactConfig(vcs_type='hg', vcs_options='-r . -r .^')
analyzer = ImpactAnalyzer(config=config, root_dir='.')
```

**Creating a Custom VCS Plugin**:

```python
from framework.impact.vcs_plugins import VcsPlugin

class SvnPlugin(VcsPlugin):
    """Custom SVN plugin (example)."""
    
    def __init__(self, working_dir: str = '.'):
        self.working_dir = working_dir
    
    def get_diff(self, options: str = "") -> str:
        """Get svn diff output."""
        import subprocess
        result = subprocess.run(
            ['svn', 'diff'] + options.split(),
            cwd=self.working_dir,
            capture_output=True,
            text=True
        )
        return result.stdout
    
    def get_changed_files(self, options: str = "") -> List[str]:
        """Get svn status."""
        result = subprocess.run(
            ['svn', 'status'],
            cwd=self.working_dir,
            capture_output=True,
            text=True
        )
        
        files = []
        for line in result.stdout.split('\n'):
            if line and line[0] in 'MADR':
                files.append(line[7:])
        return files
```

#### Language Plugin Interface

Each language plugin implements this interface:

```python
class LanguagePlugin(ABC):
    """Base class for language-specific test impact analyzers."""
    
    @abstractmethod
    def parse_codebase(self, root_dir: str) -> "CallGraph":
        """
        Parse all source files and build a call graph.
        
        Returns: CallGraph with all functions and their dependencies
        Raises: LanguagePluginError if parsing fails
        """
        pass
    
    @abstractmethod
    def extract_changed_functions(self, git_diff: str) -> Set[str]:
        """
        Extract changed functions from git diff output.
        
        Args: git diff output (or file path to diff file)
        Returns: Set of qualified function names (e.g., "module.Class.method")
        """
        pass
    
    def get_language(self) -> str:
        """Return language name (e.g., 'python', 'go', 'rust')"""
        return self.__class__.__name__.replace('Plugin', '').lower()
```

#### Call Graph Data Structure

```python
@dataclass
class Function:
    """Represents a single function/method in the codebase."""
    qualified_name: str  # "module.submodule.Class.method"
    file_path: str       # "src/grepnet/core/colorizer.py"
    line_number: int     # First line of function definition
    calls: Set[str]      # Set of qualified names this function calls
    called_by: Set[str]  # Set of qualified names that call this function

@dataclass
class CallGraph:
    """Complete call graph for the codebase."""
    functions: Dict[str, Function]  # name → Function
    build_time: float               # Time to build (seconds)
    language: str                   # "python", "go", etc.
    
    def find_transitive_dependents(self, function: str, depth: int = -1) -> Set[str]:
        """Find all functions that depend on this function (directly or indirectly)."""
        # Recursive traversal up the call graph
        pass
```

#### Impact Analysis Engine

```python
class ImpactAnalyzer:
    """Orchestrates language plugins and determines test impact."""
    
    def __init__(self, config: "ImpactConfig"):
        self.config = config
        self.plugins = self._load_plugins()
        self.test_linker = TestLinker()  # Maps functions to tests
    
    def analyze_changes(self, git_diff: str = None) -> "ImpactReport":
        """
        Analyze code changes and return affected tests.
        
        Args:
            git_diff: git diff output (if None, uses current staged changes)
        
        Returns:
            ImpactReport with affected tests, confidence scores, etc.
        """
        pass

@dataclass
class ImpactReport:
    """Result of impact analysis."""
    changed_files: List[str]              # ["src/grepnet/core/colorizer.py"]
    changed_functions: List[str]          # ["colorizer.py::apply_color()"]
    affected_tests: List[str]             # ["tests/sub-tests/2-output/023_...sh"]
    confidence_scores: Dict[str, float]   # Test name → confidence (0.0-1.0)
    total_affected: int                   # Number of tests to run
    execution_time_estimate: float        # Estimated runtime (seconds)
    summary: str                          # Human-readable description
```

#### Test Linking

Tests can be linked to code in multiple ways:

```bash
#!/bin/bash
# Method 1: Explicit dependency comment
# @depends: grepnet.core.colorizer

# Method 2: Filename-based inference (optional)
# 023_test_color_validation.sh → likely tests colorizer module

# Method 3: Grep pattern (fallback)
# If test calls `grepnet --color`, link to any function handling --color flag
```

### Plugin Implementation Guide

#### Python Plugin (Reference Implementation)

```python
# plugins/python_plugin.py

import ast
import os
from typing import Set, Dict, List

class PythonPlugin(LanguagePlugin):
    """Python language support using AST analysis."""
    
    def parse_codebase(self, root_dir: str) -> CallGraph:
        """Parse Python files and build call graph using AST."""
        functions = {}
        
        for py_file in self._find_python_files(root_dir):
            with open(py_file) as f:
                tree = ast.parse(f.read(), filename=py_file)
            
            # Extract functions and their calls
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func = self._extract_function(node, py_file, root_dir)
                    functions[func.qualified_name] = func
        
        return CallGraph(functions=functions, language='python', build_time=0.5)
    
    def extract_changed_functions(self, git_diff: str) -> Set[str]:
        """Extract Python functions modified in git diff."""
        changed = set()
        # Parse diff, find @@@ lines with function names
        for line in git_diff.split('\n'):
            if line.startswith('@@'):
                # Extract function context
                func_name = self._parse_function_from_diff_hunk(line)
                if func_name:
                    changed.add(func_name)
        return changed
```

#### Go Plugin Skeleton

```python
class GoPlugin(LanguagePlugin):
    """Go language support using go/parser."""
    # Similar structure, uses external 'go parse' tools or golang.org/x/tools
    pass
```

#### Rust Plugin Skeleton

```python
class RustPlugin(LanguagePlugin):
    """Rust language support using syn crate (via subprocess)."""
    # Uses 'rust-analyzer' or 'syn' crate to parse
    pass
```

#### TypeScript Plugin Skeleton

```python
class TypeScriptPlugin(LanguagePlugin):
    """TypeScript language support using TypeScript compiler."""
    # Uses 'typescript' npm package or tsc to extract AST
    pass
```

### Configuration

```yaml
# test-config.yml or grepnet/.sc-conductor impact.yml
impact_analysis:
  enabled: true
  language: python              # Language: python, go, rust, typescript
  
  # VCS Plugin Configuration
  vcs_type: git                 # VCS type: git, hg, p4, mtime, manual
  vcs_options: "--cached"       # VCS-specific options
                                # git: --cached (staged), --unstaged, --head~1..head
                                # hg: -r . -r .^ (last changeset)
                                # p4: -du (unified diff)
                                # mtime: (uses file modification time)
                                # manual: (explicit list of changes)
  
  # Tracking
  track_transitive: true        # Follow A→B→C chains
  transitive_depth: -1          # -1 = unlimited, 0 = direct only
  
  # Accuracy/Performance
  min_confidence: 0.75          # Don't recommend tests below this
  cache_enabled: true
  cache_dir: .test-cache/
  cache_ttl: 86400              # Seconds (1 day)
  
  # Test linking
  dependency_comment: "@depends"    # Look for "# @depends: module.func"
  infer_from_filename: true         # Use filename heuristics
  grep_patterns: true               # Grep test files for function calls
  
  # Output
  include_confidence_scores: true
  include_transitive_path: true     # Show "A→B→C affected because..."
```

**Python Configuration Example**:

```python
from framework.impact import ImpactAnalyzer, ImpactConfig, GitPlugin

# Auto-detect git changes (staged)
config = ImpactConfig(language='python', vcs_type='git')
analyzer = ImpactAnalyzer(config=config, root_dir='.')

# Use unstaged changes instead
config = ImpactConfig(language='python', vcs_type='git', vcs_options='--unstaged')
analyzer = ImpactAnalyzer(config=config, root_dir='.')

# Use Mercurial
config = ImpactConfig(language='python', vcs_type='hg', vcs_options='-r . -r .^')
analyzer = ImpactAnalyzer(config=config, root_dir='.')

# Use custom VCS plugin
custom_vcs = GitPlugin(working_dir='/path/to/repo')
config = ImpactConfig(language='python', vcs_plugin=custom_vcs)
analyzer = ImpactAnalyzer(config=config, root_dir='/path/to/repo')
```

### CLI Integration

```bash
# Run affected tests only (after git changes)
$ grepnet test --affected
Analyzing changes...
Changed functions: 2
Affected tests: 5 (8 others unchanged)
Confidence: 0.92
Run 5 tests? (y/n) y
[Running 5 tests...]

# Show impact analysis without running
$ grepnet test --impact
Changed files:
  src/grepnet/core/colorizer.py

Changed functions:
  colorizer.apply_color (line 42)
  colorizer._format_code (line 89)

Affected tests (5):
  ✓ tests/sub-tests/2-output/023_test_color_validation.sh (confidence: 0.95)
  ✓ tests/sub-tests/2-output/027_test_output_features.sh (confidence: 0.89)
  ✓ tests/sub-tests/2-output/004_test_output_control.sh (confidence: 0.78)
  ? tests/sub-tests/2-output/005_test_line_prefixes.sh (confidence: 0.65)
  ? tests/sub-tests/1-core/002_test_pattern_stdin.sh (confidence: 0.42)

Unaffected (45): [list...]

# Pre-commit hook
$ git hook install --impact
$ git commit  # Automatically shows impact analysis

# In CI
$ grepnet test --affected --parallel --timeout=60s
```

### Accuracy Considerations

| Scenario | Challenge | Mitigation |
|----------|-----------|-----------|
| Monkey patching | Can't track runtime modifications | Disable for modules using it |
| Dynamic imports | `__import__(variable)` | Conservative: link entire module |
| Reflection | Java/Go reflection hard to track | Confidence score < 0.5 |
| External changes | Dependency upgrade affects behavior | Out of scope (use explicit markers) |
| Test interdependence | Test A affects test B | Out of scope (orthogonal problem) |

**Philosophy**: Accept false positives (run extra tests) over false negatives (miss real failures).

### Performance Characteristics

| Metric | Target | Notes |
|--------|--------|-------|
| Initial parse time | <5 seconds | Cached after first run |
| Incremental parse | <1 second | Only changed files |
| Change detection | <0.5 seconds | git diff output already available |
| Impact calculation | <1 second | Set operations |
| E2E (detect + analyze) | <2 seconds | On cached codebase |
| Caching effectiveness | 90%+ | Most commits affect <5 files |

For 1000+ tests with 50,000+ functions:
- Memory: ~50-100 MB (call graph in memory)
- Cache size: ~5-10 MB (JSON)
- Rebuild: ~3-5 seconds (from scratch)

### Future Extensions

- **Machine learning mode**: Learn test-to-code patterns over time
- **Coverage correlation**: Combine with coverage data for smarter linking
- **Test clustering**: Group related tests for parallel execution
- **Historical analysis**: Track which tests catch which types of bugs
- **IDE integration**: Show impact analysis in editor (VSCode extension)

---

## 16. Output Plugin System

### 16.1 Purpose

Output plugins push test results and impact analysis to external systems:
- **Ticketing**: Create/update Jira tickets on test failures
- **Notification**: Post to Slack, email, webhooks
- **Storage**: Archive results to databases, cloud storage
- **Compliance**: Generate audit trails, SBOM, security reports

### 16.2 Plugin Interface

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class OutputPlugin(ABC):
    """Base class for output/notification plugins"""
    
    @abstractmethod
    def push_impact_report(self, report: ImpactReport) -> None:
        """Push test impact analysis to external system"""
        pass
    
    @abstractmethod
    def push_test_failure(self, test_name: str, failure_details: Dict[str, Any]) -> None:
        """Report a test failure to external system"""
        pass
    
    @abstractmethod
    def push_test_result(self, test_name: str, result: TestResult) -> None:
        """Push individual test result to external system"""
        pass
    
    @abstractmethod
    def get_plugin_name(self) -> str:
        """Return plugin identifier"""
        return "base_output"
```

### 16.3 Built-in Implementations (Phase 4+)

**Ticketing Plugins**:
- `JiraOutputPlugin`: Create/update tickets on test failures
  - Auto-create issue with test name, error details, stack trace
  - Link to PR/commit that caused failure
  - Assign to team based on failure type

- `GitHubIssuesPlugin`: Post issues on repository
  - Create GitHub issue on test failure
  - Include test output, logs, reproduction steps

- `GitLabIssuesPlugin`: Same for GitLab

**Notification Plugins**:
- `SlackOutputPlugin`: Post to Slack channels/threads
  - Test impact analysis on PR comment
  - Failure notifications to team
  - Daily test health summary

- `EmailOutputPlugin`: Send email notifications
  - Test failure alerts
  - Daily/weekly reports
  - Recipient list per team

- `WebhookOutputPlugin`: Generic HTTP webhook
  - Push to any HTTP endpoint
  - Custom payload formatting
  - Retry logic for failures

**Storage Plugins**:
- `PostgresOutputPlugin`: Store results in database
  - Time-series test results
  - Query historical patterns
  - Analytics queries

- `S3OutputPlugin`: Archive results to cloud storage
  - Long-term archival
  - Cross-region replication

- `MongoOutputPlugin`: NoSQL storage
  - Flexible schema
  - Document-based queries

### 16.4 Configuration

```yaml
# .sc-conductor impact.yml
output_plugins:
  - type: slack
    webhook_url: ${SLACK_WEBHOOK}
    channel: "#test-results"
    on_event: test_failure           # test_failure | test_result | impact_analysis
    severity_threshold: error        # debug | info | warning | error
    mention_on_failure: "@test-team"
  
  - type: jira
    url: https://jira.company.com
    project: TEST
    on_event: test_failure
    auto_create_ticket: true
    assignee: test-team
    labels: [automated, test-failure]
  
  - type: postgres
    url: postgresql://localhost/test_results
    on_event: test_result
    batch_size: 100
    timeout_seconds: 30
  
  - type: github_pr_comment
    on_event: impact_analysis
    comment_template: |
      🧪 **Test Impact Analysis**
      Affected Tests: {affected_count}
      {affected_tests}
```

---

## 17. Compliance Plugin System

### 17.1 Purpose

Compliance plugins generate standardized reports for enterprise and regulatory requirements:
- **Security**: Vulnerability scanning, dependency audits, secret detection
- **Compliance Frameworks**: SOC2, ISO27001, HIPAA, PCI-DSS
- **Software Bill of Materials (SBOM)**: CycloneDX, SPDX formats
- **Test Coverage**: Coverage metrics, untested code paths
- **Audit Trail**: Who approved tests, when they ran, results

### 17.2 Plugin Interface

```python
class CompliancePlugin(ABC):
    """Base class for compliance/reporting plugins"""
    
    @abstractmethod
    def generate_report(self) -> Dict[str, Any]:
        """Generate compliance report"""
        pass
    
    @abstractmethod
    def validate_compliance(self) -> Tuple[bool, List[str]]:
        """
        Validate compliance.
        Returns: (is_compliant, violations)
        """
        pass
    
    @abstractmethod
    def get_plugin_name(self) -> str:
        """Return plugin identifier"""
        return "base_compliance"
```

### 17.3 Built-in Implementations (Phase 4.5+)

**SBOM Generator Plugin**:
```python
class SbomPlugin(CompliancePlugin):
    """Generate Software Bill of Materials (CycloneDX or SPDX)"""
    
    def generate_report(self) -> Dict:
        return {
            "sbom_version": "1.4",
            "format": "cyclonedx",  # or 'spdx'
            "generated_at": "2026-10-07T10:30:00Z",
            "components": [
                {"name": "pytest", "version": "7.0.0", "scope": "test", 
                 "cves": []},
                {"name": "requests", "version": "2.28.0", "scope": "test",
                 "cves": ["CVE-2023-32681"]},
            ]
        }
```

**Security Compliance Plugin**:
```python
class SecurityCompliancePlugin(CompliancePlugin):
    """Check security compliance (secrets, insecure deps, licenses)"""
    
    def generate_report(self) -> Dict:
        return {
            "framework": "SOC2",
            "scan_date": "2026-10-07T10:30:00Z",
            "secrets_found": [],           # Hardcoded API keys, passwords
            "insecure_dependencies": [],   # Known CVEs in deps
            "license_violations": [],      # GPL in proprietary project
            "outdated_packages": [
                {"name": "requests", "current": "2.26.0", 
                 "latest": "2.31.0"}
            ],
            "risk_score": 0.15,            # 0.0-1.0
            "compliance_status": "PASS"    # if risk < threshold
        }
```

**Coverage Report Plugin**:
```python
class CoveragePlugin(CompliancePlugin):
    """Generate test coverage reports"""
    
    def generate_report(self) -> Dict:
        return {
            "coverage_report": {
                "line_coverage": 0.87,      # percentage
                "branch_coverage": 0.72,
                "uncovered_critical_paths": [
                    "src/core/consolidate.py:45-67"
                ],
                "compliance_status": "PASS" # if coverage >= threshold
            },
            "min_threshold": 0.85
        }
```

**Audit Trail Plugin**:
```python
class AuditTrailPlugin(CompliancePlugin):
    """Generate compliance audit reports (SOC2, ISO27001, etc)"""
    
    def generate_report(self) -> Dict:
        return {
            "framework": "SOC2",
            "audit_period": "2026-10-01 to 2026-10-07",
            "events": [
                {
                    "timestamp": "2026-10-07T10:30:00Z",
                    "action": "approve",
                    "test": "test_consolidate",
                    "user": "alice@company.com",
                    "reason": "Ready for automation"
                },
                {
                    "timestamp": "2026-10-07T10:35:00Z",
                    "action": "run",
                    "tests_passed": 50,
                    "tests_failed": 0,
                    "initiated_by": "ci-system"
                }
            ],
            "total_events": 2
        }
```

### 17.4 Configuration

```yaml
# .sc-conductor impact.yml
compliance_plugins:
  - type: sbom
    format: cyclonedx          # cyclonedx | spdx
    output_file: sbom.json
    scan_transitive: true
  
  - type: security
    framework: SOC2            # SOC2 | ISO27001 | HIPAA | PCI-DSS
    output_file: security_report.json
    max_risk_score: 0.3
    check_secrets: true
    check_licenses: true
    license_allowlist: [MIT, Apache-2.0, BSD-3-Clause]
  
  - type: coverage
    output_file: coverage_report.json
    min_threshold: 0.85
    exclude_patterns: [__init__.py, */migrations/*]
  
  - type: audit_trail
    framework: SOC2
    output_file: audit_trail.json
    retention_days: 365
    include_test_results: true
```

---

## 18. Constraints & Assumptions

### Constraints
- Must work with bash test scripts
- Cannot require external services (TestRail, cloud platforms)
- Must work offline

### Assumptions
- Language plugins have access to source code (local filesystem)
- Git is available for change detection (can fall back to file timestamps)
- Test files are discoverable by pattern (*.sh in test directories)
- Function names in tests somewhat match function names in code (for inference)

---

## 19. Implementation Status

### Completed
✅ **Core Framework Components**
- `framework/impact/base.py` - Plugin interface and call graph data structures
- `framework/impact/python_plugin.py` - Python AST parser and change detector
- `framework/impact/analyzer.py` - Impact analysis orchestrator
- `framework/impact/linker.py` - Test linker with three strategies
- `framework/impact/impact_cli.py` - CLI tool for interactive analysis
- `framework/impact/test_impact.py` - Unit test suite
- `framework/impact/README.md` - Complete documentation and examples

✅ **Test Framework Specification (TEST-FRAMEWORK-SPEC.md)**
- Sections 1-7: Core architecture and test execution model
- Section 8: CLI integration patterns
- Sections 9-13: Scalability, success criteria, and constraints
- Section 15: Plugin system detailed specification

### Ready for Implementation
🟢 **Phase 1: Foundation** (Week 1-2)
- [ ] Integration with test_runner.py
- [ ] Caching layer (.test-cache/callgraph.json)
- [ ] Configuration file parsing (.sc-conductor impact.yml)
- [ ] CI/CD integration (pre-commit hooks, GitHub Actions)

🟢 **Phase 2: Language Plugins** (Week 3-4)
- [ ] Go plugin (using go/parser)
- [ ] Rust plugin (using rust-analyzer)
- [ ] TypeScript plugin (using TypeScript compiler)
- [ ] C/C++ plugin (using clang)

🟢 **Phase 3: Advanced Features** (Week 4-6)
- [ ] Machine learning mode (learn from test results)
- [ ] Coverage correlation (combine with code coverage)
- [ ] Parallel execution orchestration
- [ ] Web UI integration (REST API)

---

## 17. Architecture Integration

The test impact analysis plugin system integrates with the overall test framework:

```
test_runner.py (Main)
├── test_validator.py (Approval)
├── result_tracker.py (Results)
├── ImpactAnalyzer (NEW - optional)
│   ├── LanguagePlugin
│   │   ├── PythonPlugin (implemented)
│   │   ├── GoPlugin (future)
│   │   ├── RustPlugin (future)
│   │   └── ...
│   ├── TestLinker (dependency mapping)
│   └── CallGraph (code analysis)
└── test-common.sh (Bash utilities)
```

### Usage in CI/CD Workflow

```bash
# Before: Run full test suite (slow)
$ grepnet test
[50 tests, 2 minutes]

# After: Run only affected tests (fast)
$ grepnet test --affected
Analyzing changes...
5/50 tests affected (10%)
[5 tests, 20 seconds]
```

### Integration Points

1. **test_runner.py** calls `ImpactAnalyzer.analyze_changes()` if `--affected` flag used
2. **result_tracker.py** stores impact analysis data for trend analysis
3. **test_validator.py** optionally shows impact when approving tests
4. **.sc-conductor impact.yml** config file for project-specific settings

---

## 18. File Structure

```
tests/
├── TEST-FRAMEWORK-SPEC.md (this file)
├── framework/
│   ├── impact/
│   │   ├── __init__.py              # Package entry point
│   │   ├── base.py                  # Plugin interface & call graph
│   │   ├── analyzer.py              # Main orchestrator
│   │   ├── linker.py                # Test dependency linker
│   │   ├── python_plugin.py         # Python language plugin
│   │   ├── impact_cli.py            # CLI tool
│   │   ├── test_impact.py           # Unit tests
│   │   └── README.md                # Complete documentation
│   ├── result_tracker.py            # Result persistence
│   ├── test_validator.py            # Test approval CLI
│   ├── test_runner.py               # Main test executor
│   └── cli_executor.py              # Portable CLI invocation
├── .sc-conductor impact.yml                 # Configuration
├── run_tests.sh                     # Main entry point
└── [test subdirectories...]
```

### New Files Added in This Session

| File | Purpose | Lines |
|------|---------|-------|
| `framework/impact/__init__.py` | Package exports | 20 |
| `framework/impact/base.py` | Plugin interface, data structures | 160 |
| `framework/impact/python_plugin.py` | Python AST parser, change detector | 300 |
| `framework/impact/analyzer.py` | Orchestrator, impact calculation | 250 |
| `framework/impact/linker.py` | Test dependency mapping | 200 |
| `framework/impact/impact_cli.py` | Interactive CLI | 250 |
| `framework/impact/test_impact.py` | Unit tests | 350 |
| `framework/impact/README.md` | Documentation & examples | 700 |

**Total new code**: ~2,230 lines (including tests and documentation)
- JSON results must be version-controlled friendly (plain text)
- Framework must be copyable/symlink-able across projects

### Assumptions
- Python 3.8+ available
- Validators are trusted (no adversarial validation)
- Test environment is stable (reproducible results)
- Network access not required
- Single machine operation (no distributed testing)
- CLI tools are reasonably portable (or test adapts environment)

---

## 17. Open Questions & Notes

- Should test results be committed to git, or generated on demand?
- How many validators needed for consensus on critical tests?
- Should historical validation data be archived, or kept fresh?
- Performance: Should automated runs cache results between runs?
- For projects with different CLI invocation patterns, how much customization needed?
- Should there be a project registry of known projects using the framework?

---

**Document Status**: SPECIFICATION COMPLETE - Ready for implementation

**Universal Applicability**: This framework is designed to be reusable across any CLI-based project (grepnet, curl, custom tools, etc.). The YAML catalog and bash test scripts are tailored per project, but the Python framework and test library are shared/symlinked.

