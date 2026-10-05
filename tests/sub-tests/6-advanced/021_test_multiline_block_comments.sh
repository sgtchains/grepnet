#!/bin/bash

#############################################################################
# GREPNET TEST: Multi-Line Block Comments (Edge Cases)
# Tests for issues discovered during context flag implementation
#############################################################################

source "$TEST_LIB_DIR/lib_tests.sh"

log_header "MULTI-LINE BLOCK COMMENT EDGE CASES"

# Test 1: Block comment starts mid-line, ends on separate line
test_case "Block comment: starts mid-line"     "$GREPNET -P '0.0.0.0/0' '$TESTS_DIR/multiline_block_test1.txt'" 0     "line1 192.0.2.0/24 /*"

# Test 2: Block comment ends mid-line with content after
test_case "Block comment: ends mid-line with content after"     "$GREPNET -P '0.0.0.0/0' '$TESTS_DIR/multiline_block_test2.txt'" 0     $'line1 192.0.2.0/24\nline4 */ 203.0.113.0/24 after block'

# Test 3: Multiple block comments in same file
test_case "Block comment: multiple blocks in file"     "$GREPNET -P '0.0.0.0/0' '$TESTS_DIR/multiline_block_test3.txt'" 0     $'network1 192.0.2.0/24 /* first block\n*/ network2 172.16.0.0/12\n*/ network3 203.0.113.0/24'

# Test 4: Nested block comment markers
test_case "Block comment: nested markers"     "$GREPNET -P '0.0.0.0/0' '$TESTS_DIR/multiline_block_test4.txt'" 0     $'first 192.0.2.0/24 /* outer /* nested\nsecond 172.16.0.0/12'

# Test 5: Extract with --no-filter-comments
test_case "Block comment: extract with --no-filter-comments"     "$GREPNET --no-filter-comments -P '0.0.0.0/0' '$TESTS_DIR/multiline_block_test1.txt'" 0     $'line1 192.0.2.0/24 /*\nline2  inside block 10.0.0.0/8\nline3  also inside 172.16.0.0/12'

# Test 6: State resets between files
test_case "Block comment: state resets between files"     "$GREPNET --no-filename '0.0.0.0/0' '$TESTS_DIR/multiline_block_test1.txt' '$TESTS_DIR/multiline_block_test3.txt'" 0     $'line1 192.0.2.0/24 /*\n*/ network2 172.16.0.0/12\n*/ network3 203.0.113.0/24'

log_footer "MULTI-LINE BLOCK COMMENT EDGE CASES" 2>/dev/null || true
