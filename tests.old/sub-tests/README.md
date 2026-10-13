# GrepNet Test Suite Organization

The test suite is now organized into **6 functional categories** for better maintainability and discoverability.

## Categories

### 1-core (3 tests)
**Core search and matching functionality**
- `001_test_basic_matching.sh` - Basic CIDR patterns, IPv4 addresses, stdin input
- `002_test_match_types.sh` - EQUALS, SUBSET, SUPERSET, OVERLAP match types
- `003_test_inversion_filtering.sh` - Inversion logic with `-v` flag

### 2-output (7 tests)
**Line and content formatting options**
- `004_test_output_control.sh` - Output modes (-o, -q, etc.)
- `005_test_line_prefixes.sh` - Line numbers (-n), byte offsets (-b)
- `007_test_output_formats.sh` - Various output formatting combinations
- `020_test_context_output_validation.sh` - Context line output validation
- `023_test_color_validation.sh` - Color output and ANSI codes
- `027_test_output_features.sh` - Output feature combinations
- `030_test_multiple_matches_per_line.sh` - Multiple networks per line handling

### 3-filtering (4 tests)
**Exclusion and file discovery**
- `013_test_exclusion_filtering.sh` - Text and network exclusion filtering
- `026_test_exclusion_filtering.sh` - Additional exclusion filter tests
- `028_test_file_discovery.sh` - File inclusion/exclusion patterns
- `029_test_binary_handling.sh` - Binary file detection and handling

### 4-extraction (5 tests)
**Network extraction, consolidation, and format conversion**
- `031_test_extract_consolidate_pattern.sh` - Extract and consolidate modes
- `033_test_range_extraction_and_formatting.sh` - Range notation extraction
- `034_test_abbreviated_range_formats.sh` - Abbreviated range formats
- `035_test_cidr_format_conversion.sh` - CIDR format conversions
- `036_test_format_original.sh` - Original format preservation

### 5-parsing (5 tests)
**Network parsing, validation, and control**
- `008_test_parsing_options.sh` - Parse control flags (--parse-cidr, etc.)
- `009_test_strict_cidr.sh` - Strict CIDR validation modes
- `016_test_mask_validation.sh` - Subnet mask and hostmask parsing
- `032_test_malformed_patterns.sh` - Malformed pattern detection
- `032_test_multiple_format_occurrences.sh` - Multiple format types per line

### 6-advanced (10 tests)
**Advanced features, compatibility, and edge cases**
- `006_test_context_lines.sh` - Before/after context output (-B, -A, -C)
- `010_test_comments.sh` - Comment handling and filtering
- `011_test_ipv6.sh` - IPv6 address parsing and matching
- `012_test_multiple_files.sh` - Multiple file processing
- `014_test_help_version.sh` - Help and version output
- `015_test_error_handling.sh` - Error conditions and exit codes
- `017_test_pattern_edge_cases.sh` - Edge cases in pattern matching
- `018_test_match_type_prioritization.sh` - Match type priority rules
- `021_test_multiline_block_comments.sh` - Multiline comment blocks
- `022_test_grep_compatibility.sh` - Grep compatibility mode

## Running Tests

### Run all tests
```bash
cd /home/chains/dev/grepnet/tests
bash run_tests.sh
```

### Run tests from a specific category
```bash
# Run only core tests
bash run_tests.sh | grep "1-core" -A 100

# Run a specific test file
bash sub-tests/1-core/001_test_basic_matching.sh
```

## Test Results

Tests results are saved to:
- `tests/log/test_results.log` - Full test output
- `tests/test_results.log` - Summary results

## Adding New Tests

1. Determine which category your test belongs to
2. Create a test file in the appropriate category directory
3. Follow the naming convention: `NNN_test_description.sh`
4. Use the next available number in the sequence
5. Source `lib_tests.sh` using: `source "$TEST_LIB_DIR/lib_tests.sh"`
6. Use `log_header` and `test_case` functions from lib_tests.sh

Example:
```bash
#!/bin/bash
# tests/sub-tests/2-output/040_test_new_feature.sh

source "$TEST_LIB_DIR/lib_tests.sh"

log_header "NEW FEATURE TESTS"

test_case "Description of test" \
    "command to run" \
    "expected_exit_code" \
    "expected_stdout" \
    "expected_stderr"
```

## Test Statistics

- **Total tests**: 34
- **Core tests**: 3
- **Output tests**: 7
- **Filtering tests**: 4
- **Extraction tests**: 5
- **Parsing tests**: 5
- **Advanced tests**: 10
