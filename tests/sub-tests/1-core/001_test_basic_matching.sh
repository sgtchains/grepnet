#!/bin/bash

#############################################################################
# GREPNET TEST: Basic Pattern Matching
#############################################################################

source "$TEST_LIB_DIR/lib_tests.sh"

log_header "BASIC PATTERN MATCHING"

# SPEC: Networks matching the CIDR pattern should be returned (lines with networks in the pattern's range)
# SPEC-REF: GREPNET-SPEC.md - Core Behavior: "grepnet searches for network addresses in text files"
test_case "Basic CIDR pattern match" \
    "$GREPNET '192.0.2.0/24' '$TESTS_DIR/sample_networks.txt'" 0 \
    $'192.0.2.0/24\n192.0.2.0 255.255.255.0\n192.0.2.0 0.0.0.255\n192.0.2.0-192.0.2.255\nRoute to 192.0.2.0/24 via 10.0.0.0/8' \
    ""

# SPEC: Bare IP addresses should match if they fall within the pattern network
# SPEC-REF: GREPNET-SPEC.md - Network Formats: "Bare IP addresses (e.g., 192.0.2.1)"
test_case "Match IPv4 address" \
    "$GREPNET '192.0.1.1' '$TESTS_DIR/sample_networks.txt'" 0 \
    $'192.0.1.1' \
    ""

test_case "No match returns exit code 1" \
    "$GREPNET '203.0.114.0/24' '$TESTS_DIR/sample_networks.txt'" 1 \
    "" \
    ""

test_case "Pattern file input (-f)" \
    "echo '192.0.2.0/24' > /tmp/pattern.txt && $GREPNET -f /tmp/pattern.txt '$TESTS_DIR/sample_networks.txt'" 0 \
    $'192.0.2.0/24\n192.0.2.0 255.255.255.0\n192.0.2.0 0.0.0.255\n192.0.2.0-192.0.2.255\nRoute to 192.0.2.0/24 via 10.0.0.0/8' \
    ""

test_case "Pattern via -P flag" \
    "$GREPNET -P '192.0.2.0/24' '$TESTS_DIR/sample_networks.txt'" 0 \
    $'192.0.2.0/24\n192.0.2.0 255.255.255.0\n192.0.2.0 0.0.0.255\n192.0.2.0-192.0.2.255\nRoute to 192.0.2.0/24 via 10.0.0.0/8' \
    ""

test_case "Multiple patterns (-P multiple times)" \
    "$GREPNET -P '192.0.2.0/24' -P '10.0.0.0/8' '$TESTS_DIR/sample_networks.txt'" 0 \
    $'192.0.2.0/24\n10.0.0.0/8\n192.0.2.0 255.255.255.0\n10.0.0.0 255.0.0.0\n192.0.2.0 0.0.0.255\n10.0.0.0 0.255.255.255\n192.0.2.0-192.0.2.255\n10.1.1.0-10.1.1.50\nRoute to 192.0.2.0/24 via 10.0.0.0/8' \
    ""

test_case "Stdin input" \
    "echo '192.0.2.0/24' | $GREPNET '192.0.2.0/24'" 0 \
    $'192.0.2.0/24' \
    ""

# SPEC: Empty pattern file in normal search mode results in error (exit code 2)
# SPEC-REF: GREPNET-SPEC.md - Exit Codes: "2: No valid patterns extracted" (except in --extract/--consolidate modes)
test_case "Empty pattern file" \
    "echo '' > /tmp/empty_pattern.txt && $GREPNET -f /tmp/empty_pattern.txt '$TESTS_DIR/sample_networks.txt'" 2 \
    "" \
    "grepnet: error: no patterns to search for"
