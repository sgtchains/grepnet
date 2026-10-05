#!/bin/bash

#############################################################################
# GREPNET TEST: Parsing Options (v2.0 API)
#############################################################################

source "$TEST_LIB_DIR/lib_tests.sh"

log_header "PARSING OPTIONS"

# SPEC: By default, ranges are parsed in both long and short formats (--range-format=both is default)
# SPEC-REF: GREPNET-SPEC.md - Parsing Control: "range-format={long|short|both|none} (default: both)"
test_case "Parse ranges (default)" \
    "$GREPNET '192.0.2.0-192.0.2.255' '$TESTS_DIR/sample_networks.txt'" 0 \
    $'192.0.2.0/24\n192.0.2.0 255.255.255.0\n192.0.2.0 0.0.0.255\n192.0.2.0-192.0.2.255\nRoute to 192.0.2.0/24 via 10.0.0.0/8' ""

# SPEC: --range-format=long accepts only long-form ranges (192.0.2.1-192.0.2.254), not short form
# SPEC-REF: GREPNET-SPEC.md - Parsing Control: "long: Accept only long-form ranges (192.0.2.1-192.0.2.254)"
test_case "Parse long-form ranges only (--range-format=long)" \
    "$GREPNET --range-format=long '192.0.2.0-192.0.2.255' '$TESTS_DIR/sample_networks.txt'" 0 \
    $'192.0.2.0/24\n192.0.2.0 255.255.255.0\n192.0.2.0 0.0.0.255\n192.0.2.0-192.0.2.255\nRoute to 192.0.2.0/24 via 10.0.0.0/8' ""

# SPEC: --range-format=short accepts only short-form ranges (192.0.2.1-254), rejecting long form
# SPEC-REF: GREPNET-SPEC.md - Parsing Control: "short: Accept only short-form ranges (192.0.2.1-254)"
test_case "Parse short-form ranges only (--range-format=short)" \
    "$GREPNET --range-format=short '192.0.2.0-255' '$TESTS_DIR/sample_networks.txt'" 0 "" ""

# SPEC: --parse-cidr=none disables CIDR parsing entirely, rejecting CIDR patterns
# SPEC-REF: GREPNET-SPEC.md - Parsing Control: "--parse-cidr={pattern|input|both|none} (default: both)"
test_case "Disable CIDR parsing (--parse-cidr=none)" \
    "$GREPNET --parse-cidr=none '192.0.2.0/24' '$TESTS_DIR/sample_networks.txt'" 1 "" ""

# SPEC: --parse-cidr=both enables CIDR parsing (default); CIDR patterns are recognized and matched
# SPEC-REF: GREPNET-SPEC.md - Parsing Control: "--parse-cidr=both: Accept CIDR in pattern and input"
test_case "Parse CIDR enabled (default, --parse-cidr=both)" \
    "$GREPNET --parse-cidr=both '192.0.2.0/24' '$TESTS_DIR/sample_networks.txt'" 0 \
    $'192.0.2.0/24\n192.0.2.0 0.0.0.255\n192.0.2.0-192.0.2.255\nRoute to 192.0.2.0/24 via 10.0.0.0/8' ""

# SPEC: --parse-netmask=both enables parsing subnet mask format (IP followed by netmask); default behavior
# SPEC-REF: GREPNET-SPEC.md - Parsing Control: "--parse-netmask={pattern|input|both|none} (default: both)"
test_case "Parse netmask format (default)" \
    "$GREPNET --parse-netmask=both '192.0.2.0 255.255.255.0' '$TESTS_DIR/sample_networks.txt'" 0 \
    $'192.0.2.0/24\n192.0.2.0 0.0.0.255\n192.0.2.0-192.0.2.255\nRoute to 192.0.2.0/24 via 10.0.0.0/8' ""

# SPEC: --parse-netmask=none disables subnet mask parsing, rejecting patterns like "192.0.2.0 255.255.255.0"
# SPEC-REF: GREPNET-SPEC.md - Parsing Control: "none: Disable parsing in this format"
test_case "Disable netmask parsing (--parse-netmask=none)" \
    "$GREPNET --parse-netmask=none '192.0.2.0 255.255.255.0' '$TESTS_DIR/sample_networks.txt'" 1 "" ""

# SPEC: --parse-hostmask=both enables parsing inverse mask/hostmask format (IP followed by hostmask); default behavior
# SPEC-REF: GREPNET-SPEC.md - Parsing Control: "--parse-hostmask={pattern|input|both|none} (default: both)"
test_case "Parse hostmask format (default)" \
    "$GREPNET --parse-hostmask=both '192.0.2.0 0.0.0.255' '$TESTS_DIR/sample_networks.txt'" 0 \
    $'192.0.2.0/24\n192.0.2.0 0.0.0.255\n192.0.2.0-192.0.2.255\nRoute to 192.0.2.0/24 via 10.0.0.0/8' ""

# SPEC: --parse-hostmask=none disables hostmask parsing, rejecting patterns like "192.0.2.0 0.0.0.255"
# SPEC-REF: GREPNET-SPEC.md - Parsing Control: "none: Disable parsing in this format"
test_case "Disable hostmask parsing (--parse-hostmask=none)" \
    "$GREPNET --parse-hostmask=none '192.0.2.0 0.0.0.255' '$TESTS_DIR/sample_networks.txt'" 1 "" ""

# SPEC: When all parsing formats are disabled (--parse-cidr=none --parse-netmask=none --parse-hostmask=none --parse-ranges=none), no patterns are accepted
# SPEC-REF: GREPNET-SPEC.md - Parsing Control: "Disabling all formats leaves no valid pattern types"
test_case "Disable all parsing" \
    "$GREPNET --parse-cidr=none --parse-netmask=none --parse-hostmask=none --parse-ranges=none '192.0.2.0/24' '$TESTS_DIR/sample_networks.txt'" 1 "" ""
