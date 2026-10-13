# GrepNet Test Suite Architecture

## Overview

This document describes the unified, standardized test infrastructure for grepnet. The suite supports both automated and human-validated testing with comprehensive logging and result tracking.

---

## 1. Test Organization

### Directory Structure

```
tests/
├── TEST-SUITE-ARCHITECTURE.md    # This file
├── TEST-SUITE-INVENTORY.md       # What tests exist, what they test
├── test-validator.sh             # Human validation framework
├── lib/
│   ├── test-common.sh            # Unified standard test library (SINGLE SOURCE OF TRUTH)
│   └── lib_tests.sh              # [DEPRECATED - consolidated into test-common.sh]
├── sub-tests/
│   ├── 1-core/                   # Basic matching, filtering, inversion
│   ├── 2-output/                 # Output formatting, context, colors
│   ├── 3-filtering/              # Exclusions, binary detection, comments
│   ├── 4-extraction/             # Extract mode, consolidation, format conversion
│   ├── 5-parsing/                # Parse control flags (CIDR, netmask, hostmask, ranges, bare-ip)
│   └── 6-advanced/               # IPv6, error handling, edge cases
├── run_tests.sh                  # Master test runner (automated mode)
├── run_tests_interactive.sh      # Human validation mode (NEW)
├── results/                      # Test result logs (auto-created)
│   ├── results.json              # Machine-readable results
│   ├── results.log               # Human-readable log
│   └── validation-history/       # Historical validation results per test
└── files/                        # Test data files
```

### Test Categories

| Category | Purpose | Test Count | File Pattern |
|----------|---------|-----------|--------------|
| 1-core | Basic matching, filtering | ~5 | `001_` through `006_` |
| 2-output | Output modes, formatting | ~8 | `004_`, `005_`, `007_`, `020_`, `023_`, `027_`, `030_`, `040_` |
| 3-filtering | Exclusions, binary, comments | ~6 | `013_`, `026_`, `028_`, `029_`, `031_`, `032_` |
| 4-extraction | Extract, consolidate, format | ~6 | `031_`, `033_`, `034_`, `035_`, `036_`, `037_` |
| 5-parsing | Parse control flags | ~7 | `008_`, `009_`, `009b_`, `010_`, `016_`, `032a_`, `032b_` |
| 6-advanced | IPv6, edge cases, compliance | ~10 | `006_`, `010_`, `011_`, `012_`, `014_`, `015_`, `017_`, `018_`, `021_`, `022_` |
| **TOTAL** | All categories | **42** | Various patterns |

---

## 2. Unified Test Library (test-common.sh)

**Location**: `tests/lib/test-common.sh`

**Purpose**: Single source of truth for all test utilities. Eliminates duplication between `lib_tests.sh` and inline test logic.

### Core Functions

```bash
# Setup and teardown
test_setup()                 # Initialize test environment
test_teardown()              # Clean up after test
test_init_data()             # Create standard test data files

# Test execution
test_case()                  # Execute a single test with standard format
test_case_verbose()          # Execute test with verbose output

# Assertions
assert_exit_code()           # Verify exit code
assert_output()              # Verify exact output match
assert_output_contains()     # Verify output contains substring
assert_output_matches()      # Verify output matches regex
assert_file_contains()       # Verify file contains substring
assert_empty()               # Verify empty output
assert_json()                # Verify JSON validity

# Test reporting
report_pass()                # Log test pass
report_fail()                # Log test fail
report_skip()                # Log test skip
get_test_summary()           # Get pass/fail/skip counts

# Utilities
create_test_file()           # Create temp test file with content
cleanup_temp_files()         # Remove all temp test files
run_grepnet()                # Execute grepnet with standard error handling
get_line_count()             # Count lines in output
```

### Usage Example

```bash
#!/bin/bash
source "$(dirname "$0")/lib/test-common.sh"

test_setup

test_case "CIDR pattern matching" \
    "grepnet '192.0.2.0/24' files/sample_networks.txt" \
    0 \
    $'192.0.2.0/24\n192.0.2.0 255.255.255.0'

test_case "Bare IP extraction" \
    "grepnet '192.0.2.1' files/sample_networks.txt" \
    0 \
    "192.0.2.1"

test_teardown
```

---

## 3. Test File Naming Convention

**Standard Format**: `NNN_test_name.sh`

Where:
- `NNN` = Global test sequence number (001-042+)
- `test_name` = Descriptive test purpose

### Numbering Scheme

- **001-006**: 1-core tests
- **007-014**: 2-output tests  
- **015-020**: 3-filtering tests
- **021-026**: 4-extraction tests
- **027-033**: 5-parsing tests
- **034-042**: 6-advanced tests
- **043+**: New tests added to suite

**Key**: Each test has a UNIQUE number. No duplicates across categories.

### Current Cleanup Required

**Files to Rename/Consolidate**:
- `1-core/002_test_pattern_stdin.sh` → Merge into `001_test_basic_matching.sh`
- `3-filtering/013_test_exclusion_filtering.sh` + `3-filtering/026_test_exclusion_filtering.sh` → Consolidate to single test
- `3-filtering/031_test_comment_filtering.sh` + `4-extraction/031_test_extract_consolidate_pattern.sh` → Both use `031_`, needs renumbering
- `3-filtering/032_test_extended_comments.sh` + `5-parsing/032_test_malformed_patterns.sh` + `5-parsing/032_test_multiple_format_occurrences.sh` → THREE tests use `032_`!

**Action**: Renumber duplicates to use global sequence 001-042+.

---

## 4. Human Validation Framework

**New Tool**: `tests/test-validator.sh`

Enables human review and approval of test results with persistent logging.

### Workflow

```
$ bash test-validator.sh [test_number|category|all]

=== Test 007: Output Format Validation ===
Command: ./grepnet --format=range '192.0.2.0/24' files/sample_networks.txt
Expected Output: 192.0.2.0-192.0.2.255
Actual Output:   192.0.2.0-192.0.2.255
Match: ✓ YES

Does this test pass? (y/n/skip/show-details): 
```

### Features

1. **Interactive Review**
   - Display test command
   - Show expected vs actual output
   - Prompt user for validation
   - Options: pass (y), fail (n), skip, show-details

2. **Result Logging** (`tests/results/validation-history/`)
   - Per-test validation history
   - Timestamp, user, result, notes
   - Format: `NNN_test_name.json`

3. **Pass Rate Tracking**
   - Current pass rate per test
   - Historical trend (last 10 runs)
   - Auto-calculated confidence (% of runs passed)

4. **Automation Integration**
   - Read historical validation results
   - Skip tests already validated as passing
   - Flag tests with conflicting results
   - Generate reports

### Result File Format

**File**: `tests/results/validation-history/007_output_format_validation.json`

```json
{
  "test_id": 7,
  "test_file": "007_test_output_formats.sh",
  "test_name": "Output Format Validation",
  "validations": [
    {
      "timestamp": "2026-10-07T14:30:00Z",
      "validator": "alice",
      "result": "pass",
      "notes": "Output matches expected format",
      "command_output_hash": "sha256:abcd1234..."
    },
    {
      "timestamp": "2026-10-07T15:15:00Z",
      "validator": "alice",
      "result": "pass",
      "notes": "Verified again before commit"
    },
    {
      "timestamp": "2026-10-06T10:00:00Z",
      "validator": "bob",
      "result": "fail",
      "notes": "Output format was incorrect in previous version",
      "conflict_resolution": "OVERRIDDEN - alice revalidated and passed"
    }
  ],
  "statistics": {
    "total_validations": 3,
    "passed": 2,
    "failed": 1,
    "pass_rate": 0.667,
    "last_result": "pass",
    "last_validator": "alice",
    "last_timestamp": "2026-10-07T15:15:00Z"
  }
}
```

### Usage Examples

```bash
# Validate single test
bash test-validator.sh 7

# Validate entire category
bash test-validator.sh 2-output

# Validate all tests
bash test-validator.sh all

# Show validation history for test 7
bash test-validator.sh 7 --history

# Auto-run with historical results (skip already-passing tests)
bash test-validator.sh all --auto-skip-passing
```

---

## 5. Automated Test Execution (run_tests.sh)

**Purpose**: Automated execution without human validation. Uses only:
- Automated assertions (exit code, output matching)
- No human interaction
- Quick pass/fail results

### Enhanced Features

1. **JSON Result Output** (`tests/results/results.json`)
   ```json
   {
     "suite_run": "2026-10-07T16:00:00Z",
     "total_tests": 42,
     "passed": 41,
     "failed": 1,
     "skipped": 0,
     "pass_rate": 0.976,
     "tests": [
       {
         "id": 1,
         "name": "Basic Matching",
         "status": "pass",
         "duration_ms": 125,
         "expected_exit": 0,
         "actual_exit": 0
       }
     ]
   }
   ```

2. **Human-Validated Test Support**
   - Check `validation-history/` before running
   - If test has 80%+ pass rate in history, skip automated run
   - If test newly failing after passing, flag for human review

3. **Exit Code Summary**
   - `0`: All tests passed (or all skipped tests are expected)
   - `1`: At least one test failed
   - `2`: Invalid test suite state (missing files, etc.)

---

## 6. Migration Path

### Phase 1: Consolidate Test Lib
- [ ] Create `tests/lib/test-common.sh` (unified library)
- [ ] Audit existing test functions
- [ ] Consolidate duplicates
- [ ] Update all 42 test files to source `test-common.sh`
- [ ] Remove `lib_tests.sh` (keep as archive if needed)

### Phase 2: Rename/Consolidate Tests
- [ ] Audit duplicate test numbers
- [ ] Create renumbering map
- [ ] Rename test files (001-042+ sequence)
- [ ] Update `run_tests.sh` to reference new names

### Phase 3: Create Validation Framework
- [ ] Implement `test-validator.sh`
- [ ] Create `tests/results/` directory structure
- [ ] Implement result logging
- [ ] Add validation history tracking

### Phase 4: Integration
- [ ] Create `run_tests_interactive.sh`
- [ ] Create `TEST-SUITE-INVENTORY.md`
- [ ] Update documentation
- [ ] Train users on validation workflow

---

## 7. Test Suite Inventory

**See**: `TEST-SUITE-INVENTORY.md` for detailed coverage map showing:
- What each test validates
- Which spec sections it covers
- Test dependencies
- Known issues/workarounds
- Maintenance notes

---

## 8. Best Practices

### For Test Authors

1. **Use test-common.sh functions** - Never inline test logic
2. **One test file per feature** - Don't mix concerns
3. **Clear test names** - Describe what's being validated
4. **Document spec references** - Link to GREPNET-SPEC.md
5. **Use consistent test data** - Reference `tests/files/`
6. **Log interesting failures** - Add notes for future debugging

### For Test Runners

1. **Always run full suite before commits** - `bash run_tests.sh`
2. **Use interactive mode for debugging** - `bash test-validator.sh NNN`
3. **Review failed tests immediately** - Don't defer
4. **Document test blockers** - Add to test file comments
5. **Track validation history** - Helps identify flaky tests

### For CI/CD Integration

1. **Automated runs** - `bash run_tests.sh` (no human interaction)
2. **Fail on regression** - Any test_status change from pass→fail
3. **Archive results** - Keep historical run data
4. **Notify on human validation needed** - Flag new/changed tests
5. **Gate on coverage** - Ensure 90%+ pass rate before merge

---

## 9. Known Issues & Cleanup

### Duplicate Test Numbers (CRITICAL)

| Number | Files | Action |
|--------|-------|--------|
| 002 | `1-core/002_test_pattern_stdin.sh`, `1-core/002_test_match_types.sh` | Rename one to `003` |
| 031 | `3-filtering/031_test_comment_filtering.sh`, `4-extraction/031_test_extract_consolidate_pattern.sh` | Rename to `020` and `024` |
| 032 | THREE files (3-filtering, 5-parsing x2) | Rename to `021`, `025`, `026` |
| 006 | `1-core/006_test_explicit_files.sh`, `6-advanced/006_test_context_lines.sh` | Rename to `006` and `039` |

### Inconsistent Test Organization

- Output tests scattered (004, 005, 007, 020, 023, 027, 030, 040)
- Filtering tests scattered (013, 026, 028, 029, 031, 032)
- Some categories have no dedicated directory

### Recommended Organization After Cleanup

```
1-core/     001-005  (basic matching, filtering)
2-output/   007-014  (output, formatting, context)
3-filtering/ 015-020 (exclusions, binary, comments)
4-extraction/ 021-027 (extract, consolidate, format)
5-parsing/  028-035  (parse control, mask validation)
6-advanced/ 036-042+ (IPv6, error, edge cases)
```

---

## 10. Support & Maintenance

### Troubleshooting

**Q: Why did a test that passed now fail?**
- A: Check validation history for that test number
- See `tests/results/validation-history/NNN_*.json`
- Compare timestamps to code changes

**Q: How do I skip a flaky test?**
- A: Mark with `@skip` in test file header
- Add explanation comment
- Document in TEST-SUITE-INVENTORY.md

**Q: How do I add a new test?**
- A: Create `NNN_test_name.sh` (use next available number)
- Source `tests/lib/test-common.sh`
- Use `test_case()` function for assertions
- Add entry to TEST-SUITE-INVENTORY.md

---

## Summary

| Aspect | Current | Target |
|--------|---------|--------|
| Test files | 42 scattered | 42 organized, uniquely numbered |
| Test lib | Duplicated | Unified (`test-common.sh`) |
| Human validation | Manual | Automated with logging (`test-validator.sh`) |
| Result tracking | Ad-hoc | JSON + history (`validation-history/`) |
| Pass rate tracking | Not tracked | Per-test statistics |
| CI/CD ready | Partially | Fully integrated |

