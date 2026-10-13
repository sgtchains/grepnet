#!/bin/bash

#############################################################################
# GREPNET TEST: Extract and Consolidate with Pattern Filtering
#############################################################################

source "$TEST_LIB_DIR/lib_tests.sh"

log_header "EXTRACT & CONSOLIDATE WITH PATTERN FILTERING"

# Create test data
TEST_FILE="$TESTS_DIR/extract_consolidate_test.txt"
cat > "$TEST_FILE" << 'EOF'
Route 192.0.2.0/24 to primary
Backup 198.51.100.0/24 via secondary
Network 10.0.0.0/8 with subnet 10.0.1.0 255.255.255.0
Range addresses 192.0.2.0-192.0.2.255
Duplicate entries: 192.0.2.0/31 and 192.0.2.1
Mixed formats: 192.0.2.0 192.0.2.1 192.0.2.0/31
Empty lines and comments
# This is a comment with 10.0.0.0/8
Last line: 172.16.0.0/12
EOF

#############################################################################
# Extract mode tests
#############################################################################

log_header "Extract Mode - No Pattern"

# SPEC: Extract mode (--extract) extracts all networks from input without filtering
# SPEC-REF: GREPNET-SPEC.md - Extraction Mode: "Extract networks from input (--extract)"
test_case "Extract all networks from simple input" \
    "echo -en '192.0.2.0 192.0.2.1\n' | $GREPNET --extract" 0 $'192.0.2.0/32\n192.0.2.1/32' ""

# SPEC: Extract should handle duplicate networks in input (appears twice)
# SPEC-REF: GREPNET-SPEC.md - Extraction Mode: "Deduplication: Only unique network-objects are output"
test_case "Extract dedup by network-object" \
    "echo -en '192.0.2.1\n192.0.2.1\n' | $GREPNET --extract" 0 $'192.0.2.1/32' ""

# SPEC: Extract should convert subnet mask notation to CIDR format
# SPEC-REF: GREPNET-SPEC.md - Extraction Mode: "Convert to CIDR output format"
test_case "Extract subnet mask converted to CIDR" \
    "echo -en '192.0.2.0 255.255.255.0\n' | $GREPNET --extract" 0 $'192.0.2.0/24' ""

# SPEC: Extract should convert inverse mask (hostmask) notation to CIDR format
# SPEC-REF: GREPNET-SPEC.md - Extraction Mode: "Convert to CIDR output format"
test_case "Extract hostmask converted to CIDR" \
    "echo -en '192.0.2.0 0.0.0.255\n' | $GREPNET --extract" 0 $'192.0.2.0/24' ""

# SPEC: Extract should convert plain IP addresses to /32 (single host)
# SPEC-REF: GREPNET-SPEC.md - Extraction Mode: "Plain IPs become /32"
test_case "Extract plain IP as /32" \
    "echo -en '192.0.2.1\n' | $GREPNET --extract" 0 $'192.0.2.1/32' ""

# SPEC: Extract should preserve all extracted networks even if they parse to different objects
# SPEC-REF: GREPNET-SPEC.md - Extraction Mode: "Extract networks from input (--extract)"
test_case "Extract multiple networks dedup" \
    "echo -en '192.0.2.0/31\n192.0.2.1\n' | $GREPNET --extract | sort" 0 $'192.0.2.0/31\n192.0.2.1/32' ""

#############################################################################
# Consolidate mode tests
#############################################################################

log_header "Consolidate Mode"

# SPEC: Consolidate mode (--consolidate) merges overlapping networks into minimal covering set
# SPEC-REF: GREPNET-SPEC.md - Consolidation Mode: "Consolidate overlapping networks (--consolidate)"
test_case "Consolidate overlapping networks" \
    "echo -en '192.0.2.0/31\n192.0.2.1/32\n' | $GREPNET --consolidate" 0 $'192.0.2.0/31' ""

# SPEC: Consolidate should merge adjacent /24 blocks into a /23 supernet
# SPEC-REF: GREPNET-SPEC.md - Consolidation Mode: "Merge adjacent networks"
test_case "Consolidate adjacent networks" \
    "echo -en '192.0.2.0/24\n192.0.3.0/24\n' | $GREPNET --consolidate" 0 $'192.0.2.0/23' ""

# SPEC: Consolidate should convert subnet masks to CIDR before merging
# SPEC-REF: GREPNET-SPEC.md - Consolidation Mode: "Handle all input formats"
test_case "Consolidate handles subnet masks" \
    "echo -en '192.0.2.0 255.255.255.0\n192.0.3.0/24\n' | $GREPNET --consolidate" 0 $'192.0.2.0/23' ""

# SPEC: Consolidate with single address should output it as /32
# SPEC-REF: GREPNET-SPEC.md - Extraction Mode: "Plain IPs become /32"
test_case "Consolidate single address" \
    "echo -en '192.0.2.1\n' | $GREPNET --consolidate" 0 $'192.0.2.1/32' ""

#############################################################################
# Empty Pattern Set Tests (Special Architectural Case)
#############################################################################

log_header "Empty Pattern Set (/dev/null)"

# SPEC: Extract with empty pattern file should extract nothing (no patterns to match)
# SPEC-REF: GREPNET-SPEC.md - Extraction Mode: "Pattern filtering at network level"
test_case "Extract with empty pattern file (/dev/null) returns 1" \
    "echo -en '192.0.2.0/24\n198.51.100.0/24\n' | $GREPNET -f /dev/null --extract" 1 "" ""

# SPEC: Consolidate with empty pattern file should consolidate nothing (no patterns to match)
# SPEC-REF: GREPNET-SPEC.md - Consolidation Mode: "Pattern filtering at network level"
test_case "Consolidate with empty pattern file (/dev/null) returns 1" \
    "echo -en '192.0.2.0/24\n192.0.3.0/24\n' | $GREPNET -f /dev/null --consolidate" 1 "" ""

#############################################################################
# -o flag tests
#############################################################################

log_header "Only Matching (-o) Flag"

# SPEC: Only matching mode (-o) outputs matched networks in their original format (not extracted)
# SPEC-REF: GREPNET-SPEC.md - Output Formats: "Only matching (-o): show only the matched networks"
test_case "Only matching outputs original text" \
    "printf '192.0.2.0/24' | $GREPNET -o 192.0.2.0/24" 0 $'192.0.2.0/24' ""

# SPEC: Only matching mode (-o) preserves original format (subnet masks stay as subnet masks)
# SPEC-REF: GREPNET-SPEC.md - Output Formats: "--format=original: preserve original format"
test_case "Only matching keeps subnet mask format" \
    "printf '192.0.2.0 255.255.255.0' | $GREPNET -o 192.0.2.0/24" 0 $'192.0.2.0 255.255.255.0' ""

# SPEC: Only matching mode (-o) shows each matching network instance separately (including duplicates)
# SPEC-REF: GREPNET-SPEC.md - Output Formats: "Only matching (-o): show only the matched networks"
test_case "Only matching with duplicates shows each" \
    "echo -en '192.0.2.1\n192.0.2.1\n' | $GREPNET -o 192.0.2.0/24" 0 $'192.0.2.1\n192.0.2.1' ""

# SPEC: Only matching mode (-o) outputs each matched network on its own line
# SPEC-REF: GREPNET-SPEC.md - Output Formats: "Only matching (-o): show only the matched networks"
test_case "Only matching shows multiple networks per line" \
    "echo -en '192.0.2.0 192.0.2.1' | $GREPNET -o 192.0.2.0/24" 0 $'192.0.2.0\n192.0.2.1' ""

#############################################################################
# IPv6 tests
#############################################################################

log_header "IPv6 Support"

# SPEC: Extract mode supports IPv6 plain addresses converted to /128
# SPEC-REF: GREPNET-SPEC.md - IPv6 Support: "IPv6 addresses and CIDR notation"
test_case "Extract IPv6 plain address" \
    "echo -en '2001:db8::1\n' | $GREPNET --extract" 0 $'2001:db8::1/128' ""

# SPEC: Extract mode supports IPv6 CIDR notation
# SPEC-REF: GREPNET-SPEC.md - IPv6 Support: "IPv6 addresses and CIDR notation"
test_case "Extract IPv6 CIDR" \
    "echo -en '2001:db8::/32\n' | $GREPNET --extract" 0 $'2001:db8::/32' ""

# SPEC: Consolidate mode handles mixed IPv4/IPv6 input by processing each address family separately
# SPEC-REF: GREPNET-SPEC.md - IPv6 Support: "IPv6 addresses and CIDR notation"
test_case "Consolidate IPv4 and IPv6 mixed (should separate versions)" \
    "echo -en '192.0.2.0/24\n2001:db8::/32\n' | $GREPNET --consolidate" 0 $'192.0.2.0/24\n2001:db8::/32' ""

#############################################################################
# Pattern Filtering Tests
#############################################################################

log_header "Pattern Filtering for Extract Mode"

# SPEC: Extract with pattern filtering (-P) outputs only networks matching the pattern
# SPEC-REF: GREPNET-SPEC.md - Extraction Mode: "Filter by pattern before extraction"
test_case "Extract with pattern: only matching network" \
    "echo -en '192.0.2.0/24\n198.51.100.0/24\n' | $GREPNET -P 192.0.2.0/24 --extract" 0 $'192.0.2.0/24' ""

# SPEC: Extract with pattern (-P) outputs all networks that match the pattern
# SPEC-REF: GREPNET-SPEC.md - Extraction Mode: "Filter by pattern before extraction"
test_case "Extract with pattern: multiple matching networks" \
    "echo -en '192.0.2.0/24\n192.0.2.128/25\n198.51.100.0/24\n' | $GREPNET -P 192.0.2.0/24 --extract | sort" 0 $'192.0.2.0/24\n192.0.2.128/25' ""

# SPEC: Extract with pattern (-P) outputs subset networks (addresses within pattern network)
# SPEC-REF: GREPNET-SPEC.md - Match Type: "Subset match: networks contained within pattern"
test_case "Extract with pattern: subset networks match" \
    "echo -en '192.0.2.1\n192.0.2.2\n198.51.100.1\n' | $GREPNET -P 192.0.2.0/24 --extract | sort" 0 $'192.0.2.1/32\n192.0.2.2/32' ""

# SPEC: Extract with pattern that matches nothing returns exit code 1
# SPEC-REF: GREPNET-SPEC.md - Exit Codes: "Exit code 1: no matches found"
test_case "Extract with pattern: no matches returns 1" \
    "echo -en '198.51.100.0/24\n203.0.113.0/24\n' | $GREPNET -P 192.0.2.0/24 --extract" 1 "" ""

# SPEC: Extract with pattern still outputs duplicate instances
# SPEC-REF: GREPNET-SPEC.md - Extraction Mode: "Extract networks from input (--extract)"
test_case "Extract with pattern: dedup still works" \
    "echo -en '192.0.2.1\n192.0.2.1\n' | $GREPNET -P 192.0.2.0/24 --extract" 0 $'192.0.2.1/32' ""

log_header "Pattern Filtering for Consolidate Mode"

# SPEC: Consolidate with pattern filtering (-P) outputs consolidated result of only matching networks
# SPEC-REF: GREPNET-SPEC.md - Consolidation Mode: "Filter by pattern before consolidation"
test_case "Consolidate with pattern: only matching networks" \
    "echo -en '192.0.2.0/25\n192.0.2.128/25\n198.51.100.0/24\n' | $GREPNET -P 192.0.2.0/24 --consolidate" 0 $'192.0.2.0/24' ""

# SPEC: Consolidate with pattern excludes non-matching networks before consolidation
# SPEC-REF: GREPNET-SPEC.md - Consolidation Mode: "Filter by pattern before consolidation"
test_case "Consolidate with pattern: partial overlap excluded" \
    "echo -en '192.0.2.0/24\n198.51.100.0/24\n198.51.100.128/25\n' | $GREPNET -P 198.51.100.0/24 --consolidate" 0 $'198.51.100.0/24' ""

# SPEC: Consolidate with pattern that matches nothing returns exit code 1
# SPEC-REF: GREPNET-SPEC.md - Exit Codes: "Exit code 1: no matches found"
test_case "Consolidate with pattern: no matches returns 1" \
    "echo -en '10.0.0.0/8\n172.16.0.0/12\n' | $GREPNET -P 192.0.2.0/24 --consolidate" 1 "" ""

# SPEC: Consolidate with pattern handles mixed address families by filtering each separately
# SPEC-REF: GREPNET-SPEC.md - IPv6 Support: "Mixed IPv4/IPv6 processing"
test_case "Consolidate with pattern: mixed IPv4/IPv6" \
    "echo -en '192.0.2.0/24\n2001:db8::/32\n192.0.2.128/25\n' | $GREPNET -P 192.0.2.0/24 --consolidate" 0 $'192.0.2.0/24' ""

log_header "TESTING COMPLETE"
