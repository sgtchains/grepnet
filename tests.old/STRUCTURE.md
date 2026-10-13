# GrepNet Test Suite - Directory Structure

## Overview

```
tests/
├── run_tests.sh                 # Main test runner (discovers & runs all tests)
├── README.md                    # Original test suite documentation
├── TEST-SUITE-SPEC.md          # Test suite specification
├── VALIDATION-REPORT.md        # Validation results report
├── STRUCTURE.md                # This file
│
├── files/                       # Test data files
│   ├── *.txt                   # Network samples, test inputs
│   └── TEST_DATA.md            # Documentation of test data
│
├── lib/                         # Test utilities library
│   └── lib_tests.sh            # Test framework functions (log_header, test_case, etc.)
│
├── log/                         # Test results and logs
│   └── test_results.log        # Full test output and results
│
├── sub-tests/                   # Test files organized by category
│   ├── README.md               # Organization and guidance for sub-tests
│   │
│   ├── 1-core/                 # Core functionality (3 tests)
│   │   ├── 001_test_basic_matching.sh
│   │   ├── 002_test_match_types.sh
│   │   └── 003_test_inversion_filtering.sh
│   │
│   ├── 2-output/               # Output formatting (7 tests)
│   │   ├── 004_test_output_control.sh
│   │   ├── 005_test_line_prefixes.sh
│   │   ├── 007_test_output_formats.sh
│   │   ├── 020_test_context_output_validation.sh
│   │   ├── 023_test_color_validation.sh
│   │   ├── 027_test_output_features.sh
│   │   └── 030_test_multiple_matches_per_line.sh
│   │
│   ├── 3-filtering/            # Exclusion & discovery (4 tests)
│   │   ├── 013_test_exclusion_filtering.sh
│   │   ├── 026_test_exclusion_filtering.sh
│   │   ├── 028_test_file_discovery.sh
│   │   └── 029_test_binary_handling.sh
│   │
│   ├── 4-extraction/           # Extraction & formats (5 tests)
│   │   ├── 031_test_extract_consolidate_pattern.sh
│   │   ├── 033_test_range_extraction_and_formatting.sh
│   │   ├── 034_test_abbreviated_range_formats.sh
│   │   ├── 035_test_cidr_format_conversion.sh
│   │   └── 036_test_format_original.sh
│   │
│   ├── 5-parsing/              # Parsing & validation (5 tests)
│   │   ├── 008_test_parsing_options.sh
│   │   ├── 009_test_strict_cidr.sh
│   │   ├── 016_test_mask_validation.sh
│   │   ├── 032_test_malformed_patterns.sh
│   │   └── 032_test_multiple_format_occurrences.sh
│   │
│   └── 6-advanced/             # Advanced features (10 tests)
│       ├── 006_test_context_lines.sh
│       ├── 010_test_comments.sh
│       ├── 011_test_ipv6.sh
│       ├── 012_test_multiple_files.sh
│       ├── 014_test_help_version.sh
│       ├── 015_test_error_handling.sh
│       ├── 017_test_pattern_edge_cases.sh
│       ├── 018_test_match_type_prioritization.sh
│       ├── 021_test_multiline_block_comments.sh
│       └── 022_test_grep_compatibility.sh
│
└── tmp/                         # Temporary test files and outputs
```

## Key Changes from Previous Organization

### Before
- All 34 test files in a single flat `sub-tests/` directory
- Hard to navigate and categorize related tests
- Numbering gaps (missing 019, 024, 025) created confusion

### After
- Tests organized into 6 logical categories
- Clear visual hierarchy in test runner output
- Easier to find and maintain related tests
- Scalable structure for adding new tests

## How Tests Are Discovered and Run

1. **Test Runner** (`run_tests.sh`):
   - Located in `tests/` directory
   - Uses `find` to recursively locate all `*_test_*.sh` files
   - Discovers tests from all category subdirectories

2. **Category Display**:
   - Automatically extracts category from file path
   - Groups output by category during test discovery
   - Makes it clear which functional area each test covers

3. **Test Execution**:
   - Tests run independently in their respective directories
   - Environment variables exported: `GREPNET`, `TESTS_DIR`, `TEST_LIB_DIR`, etc.
   - Each test sources `lib_tests.sh` using `$TEST_LIB_DIR` environment variable

## Test Results Summary

| Category | Tests | Coverage |
|----------|-------|----------|
| 1-core | 3 | Core matching logic |
| 2-output | 7 | Output formatting & display |
| 3-filtering | 4 | Exclusion & file discovery |
| 4-extraction | 5 | Network extraction & formats |
| 5-parsing | 5 | Network parsing & validation |
| 6-advanced | 10 | Advanced features & edge cases |
| **Total** | **34** | **100% spec coverage** |

All tests passing ✅
