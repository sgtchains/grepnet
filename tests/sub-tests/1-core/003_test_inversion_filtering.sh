#!/bin/bash

#############################################################################
# GREPNET TEST: Inversion and Filtering
#############################################################################

source "$TEST_LIB_DIR/lib_tests.sh"

log_header "INVERSION AND FILTERING (-v)"

# SPEC: Inversion flag (-v) inverts the selection to show networks that do NOT match the pattern
# SPEC-REF: GREPNET-SPEC.md - Inversion Filtering: "Invert selection (-v): show networks that do not match the pattern"
test_case "Invert match (-v)" \
    "$GREPNET -v '192.0.2.0/24' '$TESTS_DIR/sample_networks.txt'" 0 $'10.0.0.0/8\n172.16.0.0/12\n2001:db8::/32\n192.168.1.0 255.255.255.0\n10.0.0.0 255.0.0.0\n172.31.0.0 255.255.0.0\n10.0.0.0 0.255.255.255\n10.1.1.0-10.1.1.50\n172.16.0.0-172.16.255.255\n192.0.1.1\n198.51.100.5\n203.0.113.42\nMultiple: 192.168.1.0 255.255.255.0 and 172.16.0.0/12' ""

# SPEC: Quiet mode (-q) suppresses all output and exits with appropriate code; returns 0 if matches found
# SPEC-REF: GREPNET-SPEC.md - Output Control: "Quiet mode (-q): suppress normal output, exit code indicates result"
test_case "Quiet mode (-q) with match" \
    "$GREPNET -q '192.0.2.0/24' '$TESTS_DIR/sample_networks.txt'" 0

# SPEC: Quiet mode (-q) returns exit code 1 when no matches are found
# SPEC-REF: GREPNET-SPEC.md - Exit Codes: "Exit code 1: no matches found"
test_case "Quiet mode (-q) no match" \
    "$GREPNET -q '203.0.114.0/24' '$TESTS_DIR/sample_networks.txt'" 1

# SPEC: Quiet mode (-q) must suppress normal output completely, producing no stdout
# SPEC-REF: GREPNET-SPEC.md - Output Control: "Quiet mode (-q): suppress normal output"
test_case "Quiet mode suppresses output" \
    "$GREPNET -q '192.0.2.0/24' '$TESTS_DIR/sample_networks.txt'" 0 "" ""

# SPEC: Inversion (-v) can be combined with unmatched (-u) to show networks that match when inversion+unmatched is applied
# SPEC-REF: GREPNET-SPEC.md - Inversion Filtering: "Multiple flags can be combined"
test_case "Invert with unmatched (-v -u)" \
    "$GREPNET -v -u '192.0.2.0/24' '$TESTS_DIR/match_types.txt'" 0 $'192.0.2.0/24\n192.0.0.0/16\n192.0.2.0/25\n192.0.2.0-192.0.2.255\n192.0.2.5/24\n0.0.0.0/0\n192.0.2.1/32' ""

# SPEC: Inversion (-v) when no matches exist should return exit code 0 and show all lines (nothing matched, so invert to show everything)
# SPEC-REF: GREPNET-SPEC.md - Exit Codes: "Exit code 0: matches found (or with -v, non-matches found)"
test_case "Invert with no matches returns 0" \
    "$GREPNET -v '203.0.114.0/24' '$TESTS_DIR/sample_networks.txt'" 0 $'192.0.2.0/24\n10.0.0.0/8\n172.16.0.0/12\n2001:db8::/32\n192.0.2.0 255.255.255.0\n192.168.1.0 255.255.255.0\n10.0.0.0 255.0.0.0\n172.31.0.0 255.255.0.0\n192.0.2.0 0.0.0.255\n10.0.0.0 0.255.255.255\n192.0.2.0-192.0.2.255\n10.1.1.0-10.1.1.50\n172.16.0.0-172.16.255.255\n192.0.1.1\n198.51.100.5\n203.0.113.42\nRoute to 192.0.2.0/24 via 10.0.0.0/8\nMultiple: 192.168.1.0 255.255.255.0 and 172.16.0.0/12' ""
