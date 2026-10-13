#!/bin/bash

#############################################################################
# GREPNET TEST: Explicit File Specification (-F flag)
#############################################################################

source "$TEST_LIB_DIR/lib_tests.sh"

log_header "EXPLICIT FILE SPECIFICATION (-F)"

# SPEC: Explicit file specification (-F) for input files
# SPEC-REF: Specify input files explicitly using -F (repeatable)
# ISSUE: Currently not integrated - args.input_files_explicit parsed but never used

test_case "Single -F with positional pattern" \
    "$GREPNET -F '$TESTS_DIR/file1.txt' '192.168.1.0/24'" 0 \
    $'192.168.1.0/24' \
    ""

test_case "Multiple -F flags accumulate files" \
    "$GREPNET -F '$TESTS_DIR/file1.txt' -F '$TESTS_DIR/file2.txt' '192.0.2.0/24'" 0 \
    "$TESTS_DIR/file2.txt:192.0.2.0/24" \
    ""

test_case "Multiple -F with different patterns" \
    "$GREPNET -F '$TESTS_DIR/file1.txt' -F '$TESTS_DIR/file2.txt' '10.0.0.0/8'" 0 \
    "$TESTS_DIR/file1.txt:10.0.0.0/8" \
    ""

test_case "-F with pattern from stdin (-f -)" \
    "echo '192.0.2.0/24' | $GREPNET -f - -F '$TESTS_DIR/file2.txt'" 0 \
    $'192.0.2.0/24' \
    ""

test_case "-F with -P pattern flag" \
    "$GREPNET -P '192.168.1.0/24' -F '$TESTS_DIR/file1.txt'" 0 \
    $'192.168.1.0/24' \
    ""

test_case "Multiple -F with multiple -P patterns" \
    "$GREPNET -P '192.0.2.0/24' -P '192.168.1.0/24' -F '$TESTS_DIR/file1.txt' -F '$TESTS_DIR/file2.txt'" 0 \
    "$(echo -e "$TESTS_DIR/file1.txt:192.168.1.0/24\n$TESTS_DIR/file2.txt:192.0.2.0/24")" \
    ""

test_case "-F with no matches returns exit 1" \
    "$GREPNET -F '$TESTS_DIR/file1.txt' '203.0.114.0/24'" 1 \
    "" \
    ""

test_case "-F with invalid file returns exit 2" \
    "$GREPNET -F /nonexistent/file.txt '192.0.2.0/24'" 2 \
    "" \
    "grepnet: Cannot read /nonexistent/file.txt: [Errno 2] No such file or directory: '/nonexistent/file.txt'"

test_case "Mixing -F and positional file arguments" \
    "$GREPNET -F '$TESTS_DIR/file1.txt' '192.0.2.0/24' '$TESTS_DIR/file2.txt'" 0 \
    "$TESTS_DIR/file2.txt:192.0.2.0/24" \
    ""

test_case "-F with --extract mode" \
    "$GREPNET --extract -F '$TESTS_DIR/sample_networks.txt' '0.0.0.0/0'" 0 \
    $'192.0.2.0/24\n10.0.0.0/8\n172.16.0.0/12\n192.168.1.0/24\n172.31.0.0/16\n10.1.1.0/27\n10.1.1.32/28\n10.1.1.48/31\n10.1.1.50/32\n172.16.0.0/16\n192.0.1.1/32\n198.51.100.5/32\n203.0.113.42/32' \
    ""

test_case "-F with -H (show filename)" \
    "$GREPNET -H -F '$TESTS_DIR/file1.txt' '192.168.1.0/24'" 0 \
    "$TESTS_DIR/file1.txt:192.168.1.0/24" \
    ""

test_case "-F with -n (line numbers)" \
    "$GREPNET -n -F '$TESTS_DIR/file2.txt' '192.0.2.0/24'" 0 \
    $'2:192.0.2.0/24' \
    ""

test_case "-F with -o (only matching)" \
    "$GREPNET -o -F '$TESTS_DIR/file1.txt' '192.168.1.0/24'" 0 \
    $'192.168.1.0/24' \
    ""

