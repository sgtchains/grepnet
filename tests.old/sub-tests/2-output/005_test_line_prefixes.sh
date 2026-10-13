#!/bin/bash

#############################################################################
# GREPNET TEST: Line Prefixes
#############################################################################

source "$TEST_LIB_DIR/lib_tests.sh"

log_header "LINE PREFIXES (-n, -b, -T, -Z)"

# SPEC: Line numbers (-n) prepends 1-based line number to each output line
# SPEC-REF: GREPNET-SPEC.md - Line Prefixes: "Line numbers (-n): prepend 1-based line number"
test_case "Line numbers (-n)" \
    "$GREPNET -n '192.0.2.0/24' '$TESTS_DIR/sample_networks.txt'" 0 \
    $'5:192.0.2.0/24\n11:192.0.2.0 255.255.255.0\n17:192.0.2.0 0.0.0.255\n21:192.0.2.0-192.0.2.255\n31:Route to 192.0.2.0/24 via 10.0.0.0/8' ""

# SPEC: Byte offset (-b) prepends byte offset of the line in the file to each output line
# SPEC-REF: GREPNET-SPEC.md - Line Prefixes: "Byte offset (-b): prepend byte offset"
test_case "Byte offset (-b)" \
    "$GREPNET -b '192.0.2.0/24' '$TESTS_DIR/sample_networks.txt'" 0 \
    $'126:192.0.2.0/24\n207:192.0.2.0 255.255.255.0\n332:192.0.2.0 0.0.0.255\n388:192.0.2.0-192.0.2.255\n567:Route to 192.0.2.0/24 via 10.0.0.0/8' ""

# SPEC: Line number and byte offset (-n -b) can be combined to show both prefixes in order: line:byte
# SPEC-REF: GREPNET-SPEC.md - Line Prefixes: "Optional prefixes (additive, in order)"
test_case "Line number and byte offset (-n -b)" \
    "$GREPNET -n -b '192.0.2.0/24' '$TESTS_DIR/sample_networks.txt'" 0 \
    $'5:126:192.0.2.0/24\n11:207:192.0.2.0 255.255.255.0\n17:332:192.0.2.0 0.0.0.255\n21:388:192.0.2.0-192.0.2.255\n31:567:Route to 192.0.2.0/24 via 10.0.0.0/8' ""

# SPEC: Initial tab (-T) replaces the prefix separator (colon) with a tab character
# SPEC-REF: GREPNET-SPEC.md - Line Prefixes: "Initial tab (-T): use tab instead of colon after prefix"
test_case "Initial tab (-T) with line numbers" \
    "$GREPNET -n -T '192.0.2.0/24' '$TESTS_DIR/sample_networks.txt'" 0 \
    $'5\t192.0.2.0/24\n11\t192.0.2.0 255.255.255.0\n17\t192.0.2.0 0.0.0.255\n21\t192.0.2.0-192.0.2.255\n31\tRoute to 192.0.2.0/24 via 10.0.0.0/8' ""

# SPEC: Initial tab (-T) with byte offset works the same way
# SPEC-REF: GREPNET-SPEC.md - Line Prefixes: "Initial tab (-T): use tab instead of colon after prefix"
test_case "Initial tab (-T) with byte offset" \
    "$GREPNET -b -T '192.0.2.0/24' '$TESTS_DIR/sample_networks.txt'" 0 \
    $'126\t192.0.2.0/24\n207\t192.0.2.0 255.255.255.0\n332\t192.0.2.0 0.0.0.255\n388\t192.0.2.0-192.0.2.255\n567\tRoute to 192.0.2.0/24 via 10.0.0.0/8' ""

# SPEC: Initial tab (-T) with both line numbers and byte offsets separates both prefix components with tabs
# SPEC-REF: GREPNET-SPEC.md - Line Prefixes: "Initial tab (-T): use tab instead of colon after prefix"
test_case "Initial tab (-T) with both prefixes" \
    "$GREPNET -n -b -T '192.0.2.0/24' '$TESTS_DIR/sample_networks.txt'" 0 \
    $'126\t5:192.0.2.0/24\n207\t11:192.0.2.0 255.255.255.0\n332\t17:192.0.2.0 0.0.0.255\n388\t21:192.0.2.0-192.0.2.255\n567\t31:Route to 192.0.2.0/24 via 10.0.0.0/8' ""

# SPEC: Line numbers must be 1-based and accurate for each matched line
# SPEC-REF: GREPNET-SPEC.md - Line Prefixes: "Line numbers (-n): prepend 1-based line number"
test_case "Line numbers in output" \
    "$GREPNET -n '192.0.2.0/24' '$TESTS_DIR/sample_networks.txt' | grep '^[0-9]'" 0 \
    $'5:192.0.2.0/24\n11:192.0.2.0 255.255.255.0\n17:192.0.2.0 0.0.0.255\n21:192.0.2.0-192.0.2.255\n31:Route to 192.0.2.0/24 via 10.0.0.0/8' ""

# SPEC: Byte offsets must be accurate for the start of each matched line in the file
# SPEC-REF: GREPNET-SPEC.md - Line Prefixes: "Byte offset (-b): prepend byte offset"
test_case "Byte offsets in output" \
    "$GREPNET -b '192.0.2.0/24' '$TESTS_DIR/sample_networks.txt' | grep '^[0-9]'" 0 \
    $'126:192.0.2.0/24\n207:192.0.2.0 255.255.255.0\n332:192.0.2.0 0.0.0.255\n388:192.0.2.0-192.0.2.255\n567:Route to 192.0.2.0/24 via 10.0.0.0/8' ""
