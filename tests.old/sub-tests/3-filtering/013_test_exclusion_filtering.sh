#!/bin/bash

#############################################################################
# GREPNET TEST: Exclusion Filtering
#############################################################################

source "$TEST_LIB_DIR/lib_tests.sh"

log_header "EXCLUSION FILTERING"

# SPEC: Exclude network flag (--exclude-string) removes results matching the specified network
# SPEC-REF: GREPNET-SPEC.md - Exclusion Filtering: "Exclude networks (--exclude-string)"
# Note: --exclude-string uses REGEX matching against original text, so it only excludes the exact format
# In this case, only "192.0.2.0/24" is excluded, but "192.0.2.0 255.255.255.0" etc. are kept
test_case "Exclude network (--exclude-string)" \
    "$GREPNET --exclude-string '192.0.2.0/24' '192.0.0.0/16' '$TESTS_DIR/sample_networks.txt'" 0 \
    $'192.0.2.0 255.255.255.0\n192.0.2.0 0.0.0.255\n192.0.2.0-192.0.2.255\n192.0.1.1' ""

# SPEC: Exclude multiple patterns can be specified with multiple --exclude-string flags
# SPEC-REF: GREPNET-SPEC.md - Exclusion Filtering: "Multiple exclusions can be combined"
test_case "Exclude multiple patterns" \
    "$GREPNET --exclude-string '192.0.2.0/24' --exclude-string '10.0.0.0/8' '192.0.0.0/16' '$TESTS_DIR/sample_networks.txt'" 0 \
    $'192.0.2.0 255.255.255.0\n192.0.2.0 0.0.0.255\n192.0.2.0-192.0.2.255\n192.0.1.1' ""

# SPEC: Exclusion patterns can be read from a file via --exclude-strings-file
# SPEC-REF: GREPNET-SPEC.md - Exclusion Filtering: "Read exclusions from file (--exclude-strings-file)"
test_case "Exclude via file" \
    "echo '192.0.2.0/24' > /tmp/exclude.txt && $GREPNET --exclude-strings-file /tmp/exclude.txt '192.0.0.0/16' '$TESTS_DIR/sample_networks.txt'" 0 \
    $'192.0.2.0 255.255.255.0\n192.0.2.0 0.0.0.255\n192.0.2.0-192.0.2.255\n192.0.1.1' ""

# SPEC: Exclude patterns can use regex patterns for matching networks
# SPEC-REF: GREPNET-SPEC.md - Exclusion Filtering: "Regex patterns in exclusions"
test_case "Exclude with regex pattern" \
    "$GREPNET --exclude-string '192.0.[2-3]' '192.0.0.0/16' '$TESTS_DIR/sample_networks.txt'" 0 \
    $'192.0.1.1' ""

# SPEC: Exclusion works with extract mode to remove specific networks from the output
# SPEC-REF: GREPNET-SPEC.md - Extraction Mode + Exclusion Filtering: "Combined operations"
# Note: Extract mode requires stdin for input, so we pipe the file content
test_case "Extract mode with exclusion" \
    "cat '$TESTS_DIR/sample_networks.txt' | $GREPNET --extract --exclude-string '192.0.2.0/24'" 0 \
    $'10.0.0.0/8\n172.16.0.0/12\n2001:db8::/32\n192.168.1.0/24\n172.31.0.0/16\n10.1.1.0/27\n10.1.1.32/28\n10.1.1.48/31\n10.1.1.50/32\n172.16.0.0/16\n192.0.1.1/32\n198.51.100.5/32\n203.0.113.42/32' ""
