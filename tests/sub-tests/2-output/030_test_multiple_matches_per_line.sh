#!/bin/bash

#############################################################################
# GREPNET TEST: Multiple Matches Per Line
# Tests handling of multiple networks on a single line
#############################################################################

source "$TEST_LIB_DIR/lib_tests.sh"

log_header "MULTIPLE MATCHES PER LINE"

# Test 1: -o flag with multiple matches on same line
run_command_captured "printf 'text 192.0.2.0 10.0.0.1' | $GREPNET -o 0.0.0.0/0"
if validate_exit_code 0 "$CMD_EXIT" "Multiple networks with -o"; then
    if validate_stdout_contains "$CMD_STDOUT" "192.0.2.0" "Contains first network" && \
       validate_stdout_contains "$CMD_STDOUT" "10.0.0.1" "Contains second network"; then
        test_pass "Multiple networks on single line with -o"
    else
        test_fail "Multiple networks on single line with -o"
    fi
else
    test_fail "Multiple networks on single line with -o"
fi

# Test 2: Verify both networks are output (line count = 2)
run_command_captured "printf 'text 192.0.2.0 10.0.0.1' | $GREPNET -o 0.0.0.0/0 | wc -l"
if [ "$CMD_STDOUT" -eq 2 ] 2>/dev/null; then
    test_pass "Verify -o outputs both networks"
else
    test_fail "Verify -o outputs both networks"
fi

# Test 3: Multiple matches with line numbers
run_command_captured "printf 'text 192.0.2.0 10.0.0.1' | $GREPNET -n -o 0.0.0.0/0"
if validate_exit_code 0 "$CMD_EXIT" "Multiple matches with -n"; then
    test_pass "Multiple matches with -n flag"
else
    test_fail "Multiple matches with -n flag"
fi

# Test 4: Multiple matches across multiple lines
run_command_captured "printf 'line1 192.0.2.0 10.0.0.1\nline2 172.16.0.0 203.0.113.0' | $GREPNET -o 0.0.0.0/0"
if validate_exit_code 0 "$CMD_EXIT" "Multiple lines with multiple matches"; then
    test_pass "Multiple lines with multiple matches each"
else
    test_fail "Multiple lines with multiple matches each"
fi

# Test 5: Verify count is correct (4 networks across 2 lines)
run_command_captured "printf 'line1 192.0.2.0 10.0.0.1\nline2 172.16.0.0 203.0.113.0' | $GREPNET -o 0.0.0.0/0 | wc -l"
if [ "$CMD_STDOUT" -eq 4 ] 2>/dev/null; then
    test_pass "Count matches correctly (4 total)"
else
    test_fail "Count matches correctly (4 total)"
fi

# Test 6: With -m flag limiting output
run_command_captured "printf 'text 192.0.2.0 10.0.0.1 172.16.0.0' | $GREPNET -o -m 2 0.0.0.0/0 | wc -l"
if [ "$CMD_STDOUT" -eq 2 ] 2>/dev/null; then
    test_pass "Multiple matches with -m flag (limit to 2)"
else
    test_fail "Multiple matches with -m flag (limit to 2)"
fi

# Test 7: Multiple matches in file
printf "network 192.0.2.0 and 10.0.0.1\nmore 172.16.0.0 plus 203.0.113.0\n" > "$TESTS_DIR/multi_match_test.txt"
run_command_captured "$GREPNET -o 0.0.0.0/0 '$TESTS_DIR/multi_match_test.txt'"
if validate_exit_code 0 "$CMD_EXIT" "Multiple matches in file"; then
    test_pass "Multiple matches in file with -o"
else
    test_fail "Multiple matches in file with -o"
fi

# Test 8: -H flag with multiple matches per line
run_command_captured "$GREPNET -H -o 0.0.0.0/0 '$TESTS_DIR/multi_match_test.txt'"
if validate_exit_code 0 "$CMD_EXIT" "-H with multiple matches" && \
   validate_stdout_contains "$CMD_STDOUT" "multi_match_test.txt" "Filename in output"; then
    test_pass "Multiple matches with -H (show filename)"
else
    test_fail "Multiple matches with -H (show filename)"
fi

# Test 9: Multiple matches with --show-content
run_command_captured "printf 'text 192.0.2.0 10.0.0.1' | $GREPNET --extract --show-content 0.0.0.0/0"
if validate_exit_code 0 "$CMD_EXIT" "--show-content with --extract"; then
    test_pass "Multiple matches with --show-content"
else
    test_fail "Multiple matches with --show-content"
fi

# Test 10: No matches returns exit code 1
run_command_captured "printf 'text no-networks-here' | $GREPNET -o 0.0.0.0/0"
if validate_exit_code 1 "$CMD_EXIT" "No matches exit code"; then
    test_pass "No matches returns correct exit code"
else
    test_fail "No matches returns correct exit code"
fi

# Cleanup
rm -f "$TESTS_DIR/multi_match_test.txt"

# Test footer summary
echo -e "\n${BLUE}MULTIPLE MATCHES PER LINE - Result: ${GREEN}✓ PASS${NC}"
