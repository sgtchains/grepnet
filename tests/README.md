# GrepNet Test Suite

A comprehensive bash-based testing framework for validating grepnet network-aware grep functionality across all features.

## Overview

This test suite provides **164+ test cases** covering all GrepNet functionality:

- **Basic Pattern Matching**: CIDR, IPv4, IPv6 patterns
- **Match Types**: Equals, subset, superset, overlap, unmatched (-e, -s, -S, -O, -u)
- **Inversion & Filtering**: Inverted matches (-v), quiet mode (-q)
- **Output Control**: Filenames, file listings, counts (-H, -l, -L, -c)
- **Line Prefixes**: Line numbers, byte offsets, tabs (-n, -b, -T)
- **Context Lines**: Before/after context, separators (-A, -B, -C, --group-separator)
- **Output Formats**: Text (default), JSON (-O json), table (-O table), only-matching (-o)
- **Parsing Options**: CIDR, netmask, hostmask, ranges (--parse-*)
- **IPv6 Support**: IPv6 CIDR, addresses, ranges
- **Multiple Files**: Batch processing, file discovery, recursive search
- **Extraction & Consolidation**: Network extraction (--extract), consolidation (--consolidate) with pattern filtering
- **Exclusion Filtering**: Text patterns (--exclude-string), network patterns (--exclude-cidr)
- **Error Handling**: Invalid files, missing patterns, bad flags
- **Phase 3 Pattern Filtering**: ✅ Complete - 9/9 tests passing

**Current Status**: 157 passing / 7 failing (95.7% pass rate)

---

## Directory Structure

```
tests/
├── run_tests.sh                 # Main test runner
├── README.md                    # This file
├── TEST-SUITE-SPEC.md           # Comprehensive test specification
│
├── sub-tests/                   # 21 individual test suites (~164 tests)
│   ├── 001_test_basic_matching.sh
│   ├── 002_test_match_types.sh
│   ├── ... (19 more test files)
│   └── 031_test_extract_consolidate_pattern.sh  ← Phase 3 (9 tests, all passing)
│
├── files/                       # Test data, documentation, logs
│   ├── *.txt                    # Network data files (20+ files)
│   ├── TEST_DATA.md             # Test data documentation
│   ├── TEST_REFERENCE.md        # Reference information
│   ├── VALIDATION_PROOF.md      # Validation proofs
│   └── *.log                    # Test output logs
│
├── lib/                         # Library files
│   └── lib_tests.sh             # Shared test utilities & helpers
│
├── log/                         # Test execution logs
│   └── test_results.log         # Aggregated test results
│
└── tmp/                         # Temporary files
    └── (auto-cleaned)
```

---

## Running Tests

### Run All Tests
```bash
cd /home/chains/dev/grepnet
GREPNET="/home/chains/dev/grepnet/grepnet" bash tests/run_tests.sh
```

### Run Single Test Suite
```bash
GREPNET="/home/chains/dev/grepnet/grepnet" bash tests/sub-tests/031_test_extract_consolidate_pattern.sh
```

### Run with Verbose Output
```bash
VERBOSE=1 GREPNET="/home/chains/dev/grepnet/grepnet" bash tests/run_tests.sh
```

### Test Results
- **Live output**: Real-time to stdout
- **Log file**: `tests/log/test_results.log`
- **Exit code**: 0 if all pass, non-zero if any fail

---

## Test Organization

Tests are organized by functional area in `sub-tests/` with naming pattern: `NNN_test_<category>.sh`

### Test Coverage by Category

| # | Category | File | Tests | Status |
|----|----------|------|-------|--------|
| 001 | Basic Matching | 001_test_basic_matching.sh | 8 | ✓ All passing |
| 002 | Match Types | 002_test_match_types.sh | 5 | ✗ 1 failure (Overlap -O) |
| 003 | Inversion Filtering | 003_test_inversion_filtering.sh | 7 | ✓ All passing |
| 004 | Output Control | 004_test_output_control.sh | 5+ | ✓ All passing |
| 005 | Line Prefixes | 005_test_line_prefixes.sh | 7+ | ✓ All passing |
| 006 | Context Lines | 006_test_context_lines.sh | 5+ | ✓ All passing |
| 007 | Output Formats | 007_test_output_formats.sh | 4+ | ✓ All passing |
| 008 | Parsing Options | 008_test_parsing_options.sh | 5 | ✗ 4 failures (parse flags) |
| 009 | Strict CIDR | 009_test_strict_cidr.sh | 4+ | ✓ All passing |
| 010 | Comments | 010_test_comments.sh | 2+ | ✓ All passing |
| 011 | IPv6 Support | 011_test_ipv6.sh | 4 | ✗ 1 failure (IPv6 ranges) |
| 012 | Multiple Files | 012_test_multiple_files.sh | 6+ | ✓ All passing |
| 013 | Exclusion Filtering | 013_test_exclusion_filtering.sh | 4+ | ✓ All passing |
| 014 | Help/Version | 014_test_help_version.sh | 3+ | ✓ All passing |
| 015 | Error Handling | 015_test_error_handling.sh | 6 | ✗ 1 failure (error message) |
| 016 | Mask Validation | 016_test_mask_validation.sh | 20+ | ✓ All passing |
| 017 | Pattern Edge Cases | 017_test_pattern_edge_cases.sh | 8+ | ✓ All passing |
| 018 | Match Prioritization | 018_test_match_type_prioritization.sh | 7+ | ✓ All passing |
| 020 | Context Validation | 020_test_context_output_validation.sh | 7+ | ✓ All passing |
| 021 | Multiline Comments | 021_test_multiline_block_comments.sh | 10+ | ✓ All passing |
| 022 | Grep Compatibility | 022_test_grep_compatibility.sh | 8+ | ✓ All passing |
| **031** | **Extract/Consolidate Pattern** | **031_test_extract_consolidate_pattern.sh** | **9** | **✓ 9/9 (100%)** |

---

## Test Data Files

Located in `files/` directory:

### Network Input Files
- **sample_networks.txt**: Basic formats (CIDR, subnet mask, ranges, plain IPs)
- **match_types.txt**: Networks for testing match type logic
- **ipv6_test.txt**: IPv6 addresses and CIDR networks
- **mixed_ip_test.txt**: Mixed IPv4/IPv6 data
- **extract_consolidate_test.txt**: Networks for extraction/consolidation
- **overlap_test_data.txt**: Overlapping networks for testing
- Plus 14+ other test data files

### Context Files
- **context_test.txt**: Test data for -A, -B, -C options
- **separator_test.txt**: Test data for group separators
- **file1.txt, file2.txt, file3.txt**: Multi-file test data

### Comment Test Files
- **comments_test.txt**: Various comment styles (Python, C, SQL, Cisco, Lisp)
- **multiline_block_test*.txt**: Multiline block comment variations

### Grep Compatibility Files
- **grep_compat_test.txt**, **grep_compat_single.txt**, **grep_compat_multiline.txt**

---

## Key Test Suites

### Phase 3: Extract/Consolidate with Pattern Filtering
**File**: `sub-tests/031_test_extract_consolidate_pattern.sh`
**Status**: ✅ **9/9 PASSING (100%)**

Tests network-level pattern filtering for:
- Extract mode with single/multiple patterns
- Consolidate mode with patterns
- Pattern filtering semantics (network-level, not line-level)
- Exit codes for no-match scenarios
- Deduplication with patterns

All tests validate that:
1. Only networks matching the pattern are extracted/consolidated
2. Filtering is per-network, not per-line
3. Deduplication still works correctly
4. Proper exit codes (0 = found, 1 = not found)

---

## Detailed Test Specification

For comprehensive test documentation including:
- Individual test descriptions
- Expected behaviors for each test
- Known failures and root causes
- Future test considerations
- Development workflow

→ See [TEST-SUITE-SPEC.md](TEST-SUITE-SPEC.md)

---

## Current Test Results

**164 tests across 21 test suites**:
- ✓ **157 passing** (95.7%)
- ✗ **7 failing** (4.3%)

### Failures Summary
1. Overlap match (-O) - test_002
2-5. Parsing options flags - test_008 (4 failures)
6. IPv6 range format - test_011
7. Error message formatting - test_015

### Full Results
See `tests/log/test_results.log` after running test suite.

---

## Test Framework

### Test Helpers (in lib/lib_tests.sh)
- `assert_equals()` - Compare expected vs actual
- `assert_exit_code()` - Verify exit code
- `assert_matches_regex()` - Regex pattern matching
- `run_grepnet()` - Execute grepnet safely
- `create_test_file()` - Generate test data

### Test Pattern
```bash
Testing: <description>
<command execution>
<assertion>
✓ PASS: <description> (exit: 0)
```

---

## CI/CD Integration

```bash
#!/bin/bash
cd grepnet/tests
GREPNET="/path/to/grepnet" bash run_tests.sh
exit_code=$?
cat log/test_results.log
exit $exit_code
```

---

## Troubleshooting

### Tests not found
- Ensure grepnet binary exists at specified path
- Check GREPNET variable: `echo $GREPNET`

### Tests failing with path errors
- Run from grepnet root: `cd /home/chains/dev/grepnet`
- Use absolute path for GREPNET variable

### Missing test data
- All test data in `files/` directory
- Verify files exist: `ls tests/files/*.txt`

---

## Adding New Tests

1. Create test file in `sub-tests/` with pattern: `NNN_test_<name>.sh`
2. Source test utilities: `source "$(dirname "$0")/../lib/lib_tests.sh"`
3. Add test data to `files/` as needed
4. Update TEST-SUITE-SPEC.md with new test information
5. Run `run_tests.sh` to verify integration

---

## References

- [Test Suite Specification](TEST-SUITE-SPEC.md) - Full test documentation
- [Main GrepNet Spec](../GREPNET-SPEC.md) - Complete API reference
- [Test Data Reference](files/TEST_DATA.md) - Input data documentation
- [Validation Proofs](files/VALIDATION_PROOF.md) - Proof of correct behavior
