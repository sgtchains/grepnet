#!/bin/bash

# Test malformed network patterns (MIB-like, too many octets, etc.)
# These should NOT extract networks due to invalid format

source "$TEST_LIB_DIR/lib_tests.sh"

log_header "MALFORMED NETWORK PATTERNS"

run_test() {

# SPEC: Network patterns must have exactly 4 octets; patterns with 5+ octets (like 192.0.2.1.232/24) are invalid
# SPEC-REF: GREPNET-SPEC.md - Plain IP Address Parsing: "Pattern must be 4 octets separated by dots"
# Test 1: Pattern with 5 octets before slash (should extract nothing or only valid part)
test_case "Five dotted octets with CIDR suffix" \
    "echo 'test 192.0.2.1.232/24' | $GREPNET --extract --color never" 1 \
    "" ""

# SPEC: Bare patterns with 5+ octets are rejected during parsing; no networks extracted
# SPEC-REF: GREPNET-SPEC.md - Pattern Parsing: "Malformed addresses rejected"
# Test 2: Pattern with 5 octets (no CIDR suffix)
test_case "Five dotted octets without CIDR" \
    "echo '192.0.2.1.232' | $GREPNET --extract --color never" 1 \
    "" ""

# SPEC: Valid CIDR patterns with exactly 4 octets are properly extracted
# SPEC-REF: GREPNET-SPEC.md - CIDR Notation Parsing: "CIDR format validated with 4 octets"
# Test 3: Valid CIDR should still work
test_case "Valid CIDR format" \
    "echo '192.0.2.0/24' | $GREPNET --extract --color never" 0 \
    "192.0.2.0/24" ""

# SPEC: SNMP OID-like patterns (multiple octets but not valid network formats) are rejected
# SPEC-REF: GREPNET-SPEC.md - Pattern Parsing: "Patterns must match network format (CIDR, mask, range, or IP)"
# Test 4: SNMP OID-like pattern (4+ octets)
test_case "SNMP OID pattern rejection" \
    "echo '1.3.6.1.2.1.1.0' | $GREPNET --extract --color never" 1 \
    "" ""

# SPEC: Bare IP addresses (4 octets without CIDR/mask/range) are extracted as /32 networks
# SPEC-REF: GREPNET-SPEC.md - Plain IP Address Parsing: "Bare IPs become /32 networks"
# Test 5: Valid IP should still extract (as /32 network)
test_case "Valid bare IP as /32" \
    "echo '192.0.2.1' | $GREPNET --extract --color never" 0 \
    "192.0.2.1/32" ""

# SPEC: Malformed patterns (like SNMP OIDs) should not interfere with valid CIDR extraction from same line
# SPEC-REF: GREPNET-SPEC.md - Pattern Parsing: "Only valid formats extracted; invalid patterns skipped"
# Test 6: MIB pattern in middle of line with valid CIDR
test_case "Mixed line with MIB and valid CIDR" \
    "echo 'config 1.3.6.1.2.1 policy 192.0.2.0/24' | $GREPNET --extract --color never" 0 \
    "192.0.2.0/24" ""

}

run_test

echo "════════════════════════════════════════════════════════════════"
