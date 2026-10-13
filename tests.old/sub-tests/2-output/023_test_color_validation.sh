#!/bin/bash

#############################################################################
# Quick test to validate colored output
#############################################################################

source "$TEST_LIB_DIR/lib_tests.sh"

log_header "COLOR OUTPUT VALIDATION"

# SPEC: Default match should be displayed with superset color (indicating match type)
# SPEC-REF: GREPNET-SPEC.md - Color Support: "Default match display with colors"
# Test 1: Verify default match has superset color (for subset match 192.0.2.0 in 0.0.0.0/0)
test_output_with_colors \
    "Default match with colors" \
    "echo '192.0.2.0' | $GREPNET --color=always 0.0.0.0/0" \
    0 \
    "192.0.2.0" \
    1

# SPEC: Normalized networks should be displayed with underline marker when using colors
# SPEC-REF: GREPNET-SPEC.md - Color Support: "Normalized network indication"
# Test 2: Verify normalized CIDR has underline
test_output_with_colors \
    "Normalized CIDR with underline" \
    "echo '192.0.2.1/24' | $GREPNET --color=always 192.0.2.0" \
    0 \
    "192.0.2.1/24" \
    1

# SPEC: Color must be disabled with --color=never flag
# SPEC-REF: GREPNET-SPEC.md - Color Support: "Disable colors with --color=never"
# Test 3: Verify --color=never disables colors
test_output_with_colors \
    "No colors with --color=never" \
    "echo '192.0.2.0' | $GREPNET --color=never 0.0.0.0/0" \
    0 \
    "192.0.2.0" \
    0

log_header "Summary"
echo "Passed: $PASSED_TESTS / Failed: $FAILED_TESTS / Skipped: $SKIPPED_TESTS / Timeouts: $TIMEOUT_TESTS"

# Exit with failure if any tests failed or timed out
[ $FAILED_TESTS -gt 0 ] || [ $TIMEOUT_TESTS -gt 0 ]
