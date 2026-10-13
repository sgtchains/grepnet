#!/bin/bash

#############################################################################
# GREPNET TEST: Output Formats
#############################################################################

source "$TEST_LIB_DIR/lib_tests.sh"

log_header "OUTPUT FORMATS (-o, --extract, --consolidate, --format)"

# SPEC: Only matching mode (-o) shows only the matched networks, not the entire line
# SPEC-REF: GREPNET-SPEC.md - Output Formats: "Only matching (-o): show only the matched networks"
test_case "Only matching (-o)" \
    "$GREPNET -o '192.0.2.0/24' '$TESTS_DIR/sample_networks.txt'" 0 \
    $'192.0.2.0/24\n192.0.2.0 255.255.255.0\n192.0.2.0 0.0.0.255\n192.0.2.0-192.0.2.255\n192.0.2.0/24' ""

# SPEC: Only matching output must contain IP addresses or CIDR notation
# SPEC-REF: GREPNET-SPEC.md - Output Formats: "Only matching (-o): show only the matched networks"
# ^^^ revalidate that this is what the spec actually says ^^^
test_case "Only matching output contains IP/CIDR" \
    "$GREPNET -o '192.0.2.0/24' '$TESTS_DIR/sample_networks.txt' | grep -E '[0-9]+\\.[0-9]+'" 0 $'192.0.2.0/24\n192.0.2.0 255.255.255.0\n192.0.2.0 0.0.0.255\n192.0.2.0-192.0.2.255\n192.0.2.0/24' ""

# SPEC: Extract mode (--extract) extracts networks from complex text patterns
# SPEC-REF: GREPNET-SPEC.md - Extraction Mode: "Extract networks from complex patterns (--extract)"
test_case "Extract mode (--extract)" \
    "$GREPNET --extract '192.0.2.0/24' '$TESTS_DIR/sample_networks.txt'" 0 $'192.0.2.0/24' ""

# SPEC: Consolidate mode (--consolidate) combines overlapping networks into minimal sets
# SPEC-REF: GREPNET-SPEC.md - Consolidation Mode: "Consolidate overlapping networks (--consolidate)"
test_case "Consolidate mode (--consolidate)" \
    "$GREPNET --consolidate '192.0.2.0/24' '$TESTS_DIR/sample_networks.txt'" 0 $'192.0.2.0/24' ""

# SPEC: Extract with --format cidr outputs networks in CIDR notation (default)
# SPEC-REF: GREPNET-SPEC.md - Network Output Format: "cidr (default): Output networks as CIDR notation"
test_case "Extract with --format cidr" \
    "$GREPNET --extract --format cidr '192.0.2.0/24' '$TESTS_DIR/sample_networks.txt'" 0 $'192.0.2.0/24' ""

# SPEC: Extract with --format range outputs networks as IP ranges
# SPEC-REF: GREPNET-SPEC.md - Network Output Format: "range: Output networks as IP ranges"
test_case "Extract with --format range" \
    "$GREPNET --extract --format range '192.0.2.0/24' '$TESTS_DIR/sample_networks.txt'" 0 $'192.0.2.0-192.0.2.255' ""

# SPEC: Extract with --format short-range outputs abbreviated ranges (IPv4 only, last octet)
# SPEC-REF: GREPNET-SPEC.md - Network Output Format: "short-range: Output networks as abbreviated ranges"
test_case "Extract with --format short-range" \
    "$GREPNET --extract --format short-range '192.0.2.0/24' '$TESTS_DIR/sample_networks.txt'" 0 $'192.0.2.0-255' ""

# SPEC: Extract with --format original outputs networks in their original parsed format
# SPEC-REF: GREPNET-SPEC.md - Network Output Format: "original: Output networks in their original parsed format"
test_case "Extract with --format original" \
    "$GREPNET --extract --format original '192.0.2.0/24' '$TESTS_DIR/sample_networks.txt'" 0 $'192.0.2.0/24' ""

# SPEC: Consolidate with --format cidr outputs consolidated networks as CIDR notation (default)
# SPEC-REF: GREPNET-SPEC.md - Network Output Format: "cidr (default): Output networks as CIDR notation"
test_case "Consolidate with --format cidr" \
    "$GREPNET --consolidate --format cidr '192.0.2.0/24' '$TESTS_DIR/sample_networks.txt'" 0 $'192.0.2.0/24' ""

# SPEC: Consolidate with --format range outputs consolidated networks as IP ranges
# SPEC-REF: GREPNET-SPEC.md - Network Output Format: "range: Output networks as IP ranges"
test_case "Consolidate with --format range" \
    "$GREPNET --consolidate --format range '192.0.2.0/24' '$TESTS_DIR/sample_networks.txt'" 0 $'192.0.2.0-192.0.2.255' ""

# SPEC: Consolidate with --format short-range outputs consolidated networks as abbreviated ranges
# SPEC-REF: GREPNET-SPEC.md - Network Output Format: "short-range: Output networks as abbreviated ranges"
test_case "Consolidate with --format short-range" \
    "$GREPNET --consolidate --format short-range '192.0.2.0/24' '$TESTS_DIR/sample_networks.txt'" 0 $'192.0.2.0-255' ""

# SPEC: Text output is the default format and shows entire matching lines
# SPEC-REF: GREPNET-SPEC.md - Output Formats: "Text output (default): show entire matching lines"
test_case "Text output (default)" \
    "$GREPNET '192.0.2.0/24' '$TESTS_DIR/sample_networks.txt'" 0 $'192.0.2.0/24\n192.0.2.0 255.255.255.0\n192.0.2.0 0.0.0.255\n192.0.2.0-192.0.2.255\nRoute to 192.0.2.0/24 via 10.0.0.0/8' ""

# SPEC: Max count limit (-m N) stops processing and stops output after N matches
# SPEC-REF: GREPNET-SPEC.md - Output Control: "Max count (-m N): limit number of outputs"
test_case "Max count limit (-m 1)" \
    "$GREPNET -m 1 '192.0.2.0/24' '$TESTS_DIR/file1.txt' '$TESTS_DIR/file2.txt'" 0 "$TESTS_DIR/file2.txt:192.0.2.0/24" ""
