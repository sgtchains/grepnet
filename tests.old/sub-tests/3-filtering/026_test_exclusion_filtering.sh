#!/bin/bash

# Test Phase 2: Exclusion Filtering

set -euo pipefail

GREPNET="${GREPNET:-$(dirname "$0")/../../grepnet}"
TESTS_DIR="$(dirname "$0")/../files"

PASSED=0
FAILED=0

test_case() {
    local name="$1"
    local cmd="$2"
    local expected_exit="$3"
    
    echo -n "Testing: $name ... "
    
    set +e
    eval "$cmd" > /tmp/test_output.txt 2>&1
    actual_exit=$?
    set -e
    
    if [[ $actual_exit -eq $expected_exit ]]; then
        echo "✓ PASS (exit: $actual_exit)"
        ((PASSED++))
    else
        echo "✗ FAIL"
        echo "  Expected exit code: $expected_exit, Got: $actual_exit"
        echo "  Output:"
        cat /tmp/test_output.txt | sed 's/^/    /'
        ((FAILED++))
    fi
}

echo "====== Phase 2: Exclusion Filtering Tests ======"
echo ""

# Create test files
TEST_REGEX_FILE="/tmp/grepnet_exclude_regex.txt"
cat > "$TEST_REGEX_FILE" << 'EOF'
# Exclude regex patterns
\.1$
^10\.
EOF

TEST_CIDR_FILE="/tmp/grepnet_exclude_cidr.txt"
cat > "$TEST_CIDR_FILE" << 'EOF'
# Network exclusions
192.0.2.0/24
10.0.0.0/8
EOF

echo "--- Regex Exclusion Tests ---"
# SPEC: Regex exclusion patterns are supported via --exclude-string flag
# SPEC-REF: GREPNET-SPEC.md - Exclusion Filtering: "Regex patterns in exclusions"
test_case "Regex exclusion - single pattern" \
    "echo -e '192.0.2.0\n192.0.2.1' | '$GREPNET' 0.0.0.0/0 --exclude-string '\.1\$'" \
    0
# SPEC: Regex exclusion that matches all results should return exit code 1 (no matches)
# SPEC-REF: GREPNET-SPEC.md - Exit Codes: "Exit code 1: no matches found"test_case "Regex exclusion - match excludes all" \
    "echo -e '192.0.2.0\n192.0.2.1' | '$GREPNET' 0.0.0.0/0 --exclude-string '192'" \
    1

# SPEC: Exclusion patterns can be read from a file via --exclude-strings-file
# SPEC-REF: GREPNET-SPEC.md - Exclusion Filtering: "Read exclusions from file (--exclude-strings-file)"
test_case "Regex exclusion - from file" \
    "echo -e '192.0.2.0\n192.0.2.1\n10.0.0.0' | '$GREPNET' 0.0.0.0/0 --exclude-strings-file '$TEST_REGEX_FILE'" \
    0

echo ""
echo "--- CIDR Exclusion Tests ---"
# SPEC: CIDR-specific exclusion (--exclude-cidr) excludes networks by CIDR notation only
# SPEC-REF: GREPNET-SPEC.md - Exclusion Filtering: "CIDR exclusions (--exclude-cidr)"
test_case "CIDR exclusion - single subnet" \
    "echo -e '192.0.2.0\n192.0.2.100\n10.0.0.0' | '$GREPNET' 0.0.0.0/0 --exclude-cidr 192.0.2.0/25" \
    0

# SPEC: CIDR exclusion that excludes all results returns exit code 1
# SPEC-REF: GREPNET-SPEC.md - Exit Codes: "Exit code 1: no matches found"
test_case "CIDR exclusion - all excluded" \
    "echo -e '192.0.2.0\n192.0.3.0' | '$GREPNET' 0.0.0.0/0 --exclude-cidr 192.0.0.0/16" \
    1

# SPEC: Bare IP addresses can be used in CIDR exclusion (treated as /32)
# SPEC-REF: GREPNET-SPEC.md - Network Formats: "Bare IP addresses"
test_case "CIDR exclusion - bare IP" \
    "echo -e '192.0.2.0\n192.0.2.1' | '$GREPNET' 0.0.0.0/0 --exclude-cidr 192.0.2.0" \
    0

# SPEC: CIDR exclusion patterns can be read from a file via --exclude-cidrs-file
# SPEC-REF: GREPNET-SPEC.md - Exclusion Filtering: "Read CIDR exclusions from file (--exclude-cidrs-file)"
test_case "CIDR exclusion - from file" \
    "echo -e '192.0.2.50\n172.16.0.0' | '$GREPNET' 0.0.0.0/0 --exclude-cidrs-file '$TEST_CIDR_FILE'" \
    0

echo ""
echo "--- Combined Exclusions ---"
# SPEC: Regex and CIDR exclusions can be combined to exclude by both patterns and networks
# SPEC-REF: GREPNET-SPEC.md - Exclusion Filtering: "Multiple exclusions can be combined"
test_case "Regex + CIDR exclusion" \
    "echo -e 'test 192.0.2.0\nnormal 192.0.2.1\n10.0.0.0' | '$GREPNET' 0.0.0.0/0 --exclude-string 'test' --exclude-cidr 192.0.2.1/32" \
    0

echo ""
echo "--- Strict CIDR Parsing (Should Fail) ---"
# SPEC: CIDR-only exclusion must reject ranges (use --exclude-string for ranges)
# SPEC-REF: GREPNET-SPEC.md - Parsing: "Strict CIDR mode: reject ranges and netmasks"
test_case "Reject range in --exclude-cidr" \
    "echo '192.0.2.0' | '$GREPNET' 0.0.0.0/0 --exclude-cidr '192.0.2.0-192.0.2.255'" \
    2

# SPEC: CIDR-only exclusion must reject netmasks (use --exclude-string for netmasks)
# SPEC-REF: GREPNET-SPEC.md - Parsing: "Strict CIDR mode: reject ranges and netmasks"
test_case "Reject netmask in --exclude-cidr" \
    "echo '192.0.2.0' | '$GREPNET' 0.0.0.0/0 --exclude-cidr '192.0.2.0 255.255.255.0'" \
    2

# SPEC: CIDR-only exclusion must reject hostmasks (use --exclude-string for hostmasks)
# SPEC-REF: GREPNET-SPEC.md - Parsing: "Strict CIDR mode: reject ranges and netmasks"
test_case "Reject hostmask in --exclude-cidr" \
    "echo '192.0.2.0' | '$GREPNET' 0.0.0.0/0 --exclude-cidr '192.0.2.0 0.0.0.255'" \
    2

echo ""
echo "====== Test Summary ======"
echo "Passed: $PASSED"
echo "Failed: $FAILED"
echo "Total:  $((PASSED + FAILED))"

if [[ $FAILED -eq 0 ]]; then
    echo "✓ All tests PASSED"
    exit 0
else
    echo "✗ Some tests FAILED"
    exit 1
fi
