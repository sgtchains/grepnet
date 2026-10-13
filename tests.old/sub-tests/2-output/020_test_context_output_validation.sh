#!/bin/bash

#############################################################################
# GREPNET TEST: Context Output Validation
# Validates actual output content for context handling, not just exit codes
#############################################################################

source "$TEST_LIB_DIR/lib_tests.sh"

log_header "CONTEXT OUTPUT VALIDATION (-B, -A, -C)"

# Create test data with clear line numbers
cat > "$TESTS_DIR/context_validation.txt" << 'EOF'
Line 1
Line 2  
Line 3: 192.168.1.0/24 <- MATCH 1
Line 4
Line 5
Line 6: 10.0.0.0/8 <- MATCH 2
Line 7
Line 8
Line 9
Line 10: 172.16.0.0/12 <- MATCH 3
EOF

# Test 1: -B 1 should include one line before match
test_output_matches_regex "Context: -B 1 includes line before" \
    "$GREPNET -B 1 -P '192.168.1.0/24' '$TESTS_DIR/context_validation.txt'" \
    0 \
    "Line 2" \
    ""

# Test 2: -A 1 should include one line after match  
test_output_matches_regex "Context: -A 1 includes line after" \
    "$GREPNET -A 1 -P '192.168.1.0/24' '$TESTS_DIR/context_validation.txt'" \
    0 \
    "Line 4" \
    ""

# Test 3: Multiple matches with gap should show separator
test_output_matches_regex "Context: Separator between distant matches" \
    "$GREPNET -B 0 -A 0 -P '192.168.1.0/24' -P '172.16.0.0/12' '$TESTS_DIR/context_validation.txt'" \
    0 \
    "\-\-" \
    ""

# Test 4: No separator when matches are close (within after context)
test_output_matches_regex "Context: No separator for close matches" \
    "$GREPNET -A 10 -P '192.168.1.0/24' -P '10.0.0.0/8' '$TESTS_DIR/context_validation.txt'" \
    0 \
    "192.168.1.0/24" \
    ""

# Test 5: -B 2 -A 2 includes full context
test_output_matches_regex "Context: -B 2 -A 2 complete context" \
    "$GREPNET -B 2 -A 2 -P '10.0.0.0/8' '$TESTS_DIR/context_validation.txt'" \
    0 \
    "Line 4" \
    ""

# Test 6: Custom separator
test_output_matches_regex "Context: Custom separator" \
    "$GREPNET --group-separator='===SEP===' -B 0 -A 0 -P '192.168.1.0/24' -P '172.16.0.0/12' '$TESTS_DIR/context_validation.txt'" \
    0 \
    "===SEP===" \
    ""

# Test 7: No group separator flag
test_output_matches_regex "Context: No separator with flag" \
    "$GREPNET --no-group-separator -B 0 -A 0 -P '192.168.1.0/24' -P '172.16.0.0/12' '$TESTS_DIR/context_validation.txt'" \
    0 \
    "192.168.1.0/24" \
    ""
