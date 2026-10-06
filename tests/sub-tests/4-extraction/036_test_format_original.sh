#!/bin/bash
#############################################################################
# GREPNET TEST: Format Original Option
# Tests the --format=original flag to output networks in their original parsed format
#############################################################################

source "$TEST_LIB_DIR/lib_tests.sh"

log_header "FORMAT ORIGINAL OPTION"

# SPEC: --format=original outputs networks in their original parsed format
# SPEC-REF: GREPNET-SPEC.md - Output Formats: "Output networks in their original parsed format (e.g., CIDR inputs as CIDR, ranges as ranges, subnet masks as subnet masks)"
# Test 1: Extract with --format=original for CIDR notation
test_case "Extract CIDR notation with --format=original" \
    "echo '192.0.2.0/24' | $GREPNET --extract --format=original" 0 \
    '192.0.2.0/24' \
    ""

# SPEC: --format=original preserves subnet mask format (IP followed by subnet mask)
# SPEC-REF: GREPNET-SPEC.md - Output Formats: "subnet masks as subnet masks"
# Test 2: Extract with --format=original for subnet mask format
test_case "Extract subnet mask with --format=original" \
    "echo '192.0.2.0 255.255.255.0' | $GREPNET --extract --format=original" 0 \
    '192.0.2.0 255.255.255.0' \
    ""

# SPEC: --format=original preserves inverse mask format (IP followed by inverse mask/wildcard)
# SPEC-REF: GREPNET-SPEC.md - Output Formats: "inverse mask format"
# Test 3: Extract with --format=original for inverse mask format
test_case "Extract inverse mask with --format=original" \
    "echo '192.0.2.0 0.0.0.255' | $GREPNET --extract --format=original" 0 \
    '192.0.2.0 0.0.0.255' \
    ""

# SPEC: --format=original preserves range format (IP1-IP2 notation)
# SPEC-REF: GREPNET-SPEC.md - Output Formats: "ranges as ranges"
# Test 4: Extract with --format=original for range format
test_case "Extract range with --format=original" \
    "echo '192.0.2.0-192.0.2.255' | $GREPNET --extract --format=original" 0 \
    '192.0.2.0-192.0.2.255' \
    ""

# SPEC: --format=original preserves abbreviated range format (IP-lastOctet notation)
# SPEC-REF: GREPNET-SPEC.md - Output Formats: "abbreviated ranges preserved in original format"
# Test 5: Extract with --format=original for abbreviated range
test_case "Extract abbreviated range with --format=original" \
    "echo '192.0.2.0-4' | $GREPNET --extract --format=original" 0 \
    '192.0.2.0-4' \
    ""

# SPEC: --format=original preserves bare IP address format (single IP without CIDR/range notation)
# SPEC-REF: GREPNET-SPEC.md - Output Formats: "bare IP address format preserved"
# Test 6: Extract with --format=original for bare IP
test_case "Extract bare IP with --format=original" \
    "echo '192.0.2.5' | $GREPNET --extract --format=original" 0 \
    '192.0.2.5' \
    ""

# SPEC: --format=original cannot be used with --consolidate because consolidated networks lose their original format identity
# SPEC-REF: GREPNET-SPEC.md - Output Formats: "Cannot be used with --consolidate because consolidated networks lose their original format identity"
# Test 7: --format=original with --consolidate should error
test_case "--format=original with --consolidate should error" \
    "echo -e '192.0.2.0/24\n192.0.3.0/24' | $GREPNET --consolidate --format=original" 2 \
    "" \
    "grepnet: error: --format original cannot be used with --consolidate"

# SPEC: --format=original works correctly with extract mode for single networks
# SPEC-REF: GREPNET-SPEC.md - Output Formats: "Output networks in their original parsed format"
# Test 8: Verify single networks work
test_case "Extract single range with --format=original" \
    "echo '192.0.2.0-192.0.2.255' | $GREPNET --extract --format=original" 0 \
    '192.0.2.0-192.0.2.255' \
    ""

# SPEC: Different format options output different representations (--format=original vs --format=cidr)
# SPEC-REF: GREPNET-SPEC.md - Output Formats: "Range 192.0.2.0-192.0.2.255 becomes 192.0.2.0/24 in CIDR format"
# Test 9: Compare with CIDR format
test_case "Compare: original vs cidr format" \
    "echo '192.0.2.0-192.0.2.255' | $GREPNET --extract --format=cidr" 0 \
    '192.0.2.0/24' \
    ""
