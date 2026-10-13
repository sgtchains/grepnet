#!/bin/bash

#############################################################################
# GREPNET TEST: IPv6 Support
#############################################################################

source "$TEST_LIB_DIR/lib_tests.sh"

log_header "IPv6 SUPPORT"

# SPEC: grepnet supports IPv6 CIDR notation matching (e.g., 2001:db8::/32)
# SPEC-REF: GREPNET-SPEC.md - CIDR Notation Parsing: "IPv6 CIDR format with prefix 0-128"
test_case "IPv6 CIDR match" \
    "$GREPNET '2001:db8::/32' '$TESTS_DIR/ipv6_test.txt'" 0 \
    $'2001:db8::/32\n2001:db8:85a3::8a2e:370:7334\n2001:db8:85a3::/48\n2001:db8:1234::/48\n2001:db8:1234:5678::/64\n2001:db8::1-2001:db8::ff' ""

# SPEC: Single IPv6 addresses are recognized and matched (converted to /128 networks)
# SPEC-REF: GREPNET-SPEC.md - Plain IP Address Parsing: "Convert to /128 (IPv6) network object"
test_case "IPv6 single address" \
    "$GREPNET '::1' '$TESTS_DIR/ipv6_test.txt'" 0 \
    $'::1' ""

# SPEC: IPv6 range format (IP-IP notation) is recognized when range parsing is enabled
# SPEC-REF: GREPNET-SPEC.md - IP Range Parsing: "Format: start_ip-end_ip; IPv4 or IPv6 addresses"
test_case "IPv6 range format" \
    "$GREPNET --parse-ranges=both '2001:db8::1-2001:db8::ff' '$TESTS_DIR/ipv6_test.txt'" 0 \
    $'2001:db8::/32\n2001:db8::1-2001:db8::ff' ""

# SPEC: Compressed IPv6 format (e.g., 2001:db8::) is recognized and matched
# SPEC-REF: GREPNET-SPEC.md - CIDR Notation Parsing: "IPv6 addresses using standard notation (compressed or full)"
test_case "IPv6 compressed format" \
    "$GREPNET '2001:db8::' '$TESTS_DIR/ipv6_test.txt'" 0 \
    $'2001:db8::/32' ""

# SPEC: Both IPv4 and IPv6 networks can be searched in the same file; matching is type-aware
# SPEC-REF: GREPNET-SPEC.md - Network Comparison: "Family is the same (IPv4 vs IPv6)"
test_case "Mixed IPv4 and IPv6" \
    "$GREPNET '192.0.2.0/24' '$TESTS_DIR/mixed_ip_test.txt'" 0 \
    $'192.0.2.0/24' ""
