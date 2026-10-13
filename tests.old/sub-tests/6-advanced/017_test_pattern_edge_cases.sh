#!/bin/bash

#############################################################################
# GREPNET TEST: Pattern Parsing Edge Cases
#############################################################################

source "$TEST_LIB_DIR/lib_tests.sh"

log_header "PATTERN PARSING EDGE CASES"

# Pattern strings are parsed using extract_networks(), just like input files.
# Multiple networks in the pattern string (comma-separated or otherwise)
# become multiple pattern entries. Any input network matching ANY pattern is included.

# SPEC: Patterns can contain multiple comma-separated networks; each is treated as a separate pattern
# SPEC-REF: GREPNET-SPEC.md - Pattern Parsing: "Multiple networks in pattern are each applied"
test_case "Pattern with comma: extracts two patterns (192.0.2.0 and 0.0.0.0/0)" \
    "echo '192.0.2.0' | $GREPNET '192.0.2.0,0.0.0.0/0'" 0 \
    $'192.0.2.0' ""

# SPEC: When pattern includes 0.0.0.0/0 (all networks), all networks match
# SPEC-REF: GREPNET-SPEC.md - Network Comparison: "0.0.0.0/0 is superset of all IPv4 networks"
test_case "Both networks match when pattern includes 0.0.0.0/0" \
    "echo 'text 192.0.2.0 255.0.255.0 text' | $GREPNET '192.0.2.0,0.0.0.0/0'" 0 \
    $'text 192.0.2.0 255.0.255.0 text' ""

# SPEC: Invalid pattern (only delimiter, no networks) results in error exit code 2
# SPEC-REF: GREPNET-SPEC.md - Exit Codes: "2: No valid patterns extracted"
test_case "Invalid pattern: only comma, no valid networks" \
    "echo '192.0.2.0' | $GREPNET ','" 2

# SPEC: Patterns with semicolon separators; IP before semicolon is extracted
# SPEC-REF: GREPNET-SPEC.md - Pattern Parsing: "Patterns may contain separator characters"
test_case "Pattern with semicolon: extracts IP before semicolon" \
    "echo '192.0.2.0' | $GREPNET '192.0.2.0;10.0.0.0'" 0 \
    $'192.0.2.0' ""

# SPEC: Patterns with pipe separator; IP before pipe is extracted as separate network
# SPEC-REF: GREPNET-SPEC.md - Pattern Parsing: "Separators create distinct networks"
test_case "Pattern with pipe: extracts IP before pipe" \
    "echo '192.0.2.0' | $GREPNET '192.0.2.0|10.0.0.0'" 0 \
    $'192.0.2.0' ""

# SPEC: Patterns with spaces are parsed as subnet mask format (IP followed by mask)
# SPEC-REF: GREPNET-SPEC.md - Subnet Mask Parsing: "Format: IP_address mask_value (space-separated)"
test_case "Pattern with spaces: parsed as subnet mask format" \
    "echo '192.0.2.0' | $GREPNET '192.0.2.0 255.255.255.0'" 0 \
    $'192.0.2.0' ""

# SPEC: Empty pattern string (no networks extracted) is an error condition (exit code 2)
# SPEC-REF: GREPNET-SPEC.md - Exit Codes: "2: Error when no valid pattern found"
test_case "Empty pattern string: no patterns extracted, error exit" \
    "echo '192.0.2.0' | $GREPNET ''" 2

# SPEC: Pattern with only whitespace extracts no networks; results in error (exit code 2)
# SPEC-REF: GREPNET-SPEC.md - Exit Codes: "2: No valid patterns extracted"
test_case "Pattern with only spaces: extracts nothing, error exit" \
    "echo '192.0.2.0' | $GREPNET '   '" 2
