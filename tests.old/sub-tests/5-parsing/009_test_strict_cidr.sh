#!/bin/bash

#############################################################################
# GREPNET TEST: Strict CIDR Validation (v2.0 API)
#############################################################################

source "$TEST_LIB_DIR/lib_tests.sh"

log_header "STRICT CIDR VALIDATION"

# SPEC: Default behavior (--strict-cidr=none) normalizes malformed CIDR without error
# SPEC-REF: GREPNET-SPEC.md - Strictness Control: "No strictness (--strict-cidr=none, default): Permissive parsing, normalize malformed CIDR"
test_case "Non-strict mode (default, normalizes)" \
    "$GREPNET '192.0.2.5/24' '$TESTS_DIR/match_types.txt'" 0 \
    $'192.0.2.0/24\n192.0.0.0/16\n192.0.2.0/25\n192.0.2.0-192.0.2.255\n192.0.2.5/24\n0.0.0.0/0\n192.0.2.1/32' ""

# SPEC: --strict-cidr=pattern with --strict-cidr-action=fail rejects malformed CIDR patterns with exit code 2
# SPEC-REF: GREPNET-SPEC.md - Strictness Control: "Pattern strictness: Validate patterns for malformed CIDR" and "fail: Exit immediately with error code 2"
test_case "Strict pattern mode with fail (--strict-cidr=pattern --strict-cidr-action=fail)" \
    "$GREPNET --strict-cidr=pattern --strict-cidr-action=fail '192.0.2.5/24' '$TESTS_DIR/match_types.txt'" 2

# SPEC: --strict-cidr=input validates file content for malformed CIDR; default action normalizes
# SPEC-REF: GREPNET-SPEC.md - Strictness Control: "Input strictness: Validate input file content for malformed CIDR"
test_case "Strict input mode with normalize (--strict-cidr=input)" \
    "$GREPNET --strict-cidr=input '192.0.2.0/24' '$TESTS_DIR/match_types.txt'" 0 \
    $'192.0.2.0/24\n192.0.0.0/16\n192.0.2.0/25\n192.0.2.0-192.0.2.255\n192.0.2.5/24\n0.0.0.0/0\n192.0.2.1/32' ""

# SPEC: --strict-cidr=both validates both pattern and input; with default normalize action
# SPEC-REF: GREPNET-SPEC.md - Strictness Control: "Both strictness: Validate both patterns and input"
test_case "Strict both modes with normalize (--strict-cidr=both)" \
    "$GREPNET --strict-cidr=both '192.0.2.0/24' '$TESTS_DIR/sample_networks.txt'" 0 \
    $'192.0.2.0/24\n192.0.2.0 255.255.255.0\n192.0.2.0 0.0.0.255\n192.0.2.0-192.0.2.255\nRoute to 192.0.2.0/24 via 10.0.0.0/8' ""

# SPEC: Combining --strict-cidr=both with --strict-cidr-action=fail rejects any malformed CIDR in pattern or input
# SPEC-REF: GREPNET-SPEC.md - Strictness Control: "Both strictness + fail action: Exit immediately on first malformed CIDR"
test_case "Strict with fail action (--strict-cidr=both --strict-cidr-action=fail)" \
    "$GREPNET --strict-cidr=both --strict-cidr-action=fail '192.0.2.5/24' '$TESTS_DIR/match_types.txt'" 2
