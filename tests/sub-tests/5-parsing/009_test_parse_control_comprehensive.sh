#!/bin/bash

#############################################################################
# GREPNET TEST: Comprehensive Parse Control Options (--parse-cidr, --parse-netmask, --parse-hostmask, --parse-ranges)
# Tests all combinations of parsing control flags
#############################################################################

GREPNET="${GREPNET:-./grepnet}"

echo "=== Test 009: Comprehensive Parse Control Options ==="
echo

PASSED=0
FAILED=0

# Test data
TEST_CIDR="192.0.2.0/24"
TEST_NETMASK="192.0.2.0 255.255.255.0"
TEST_HOSTMASK="192.0.2.0 0.0.0.255"
TEST_RANGE="192.0.2.0-192.0.2.255"
TEST_BARE_IP="192.0.2.1"
TEST_FILE="/tmp/parse_test_input.txt"

# Create test input file with all formats
cat > "$TEST_FILE" << 'EOF'
192.0.2.0/24
192.0.2.0 255.255.255.0
192.0.2.0 0.0.0.255
192.0.2.0-192.0.2.255
192.0.2.1
EOF

#############################################################################
# PARSE-CIDR TESTS
#############################################################################

echo "--- PARSE-CIDR TESTS ---"
echo

# Test: --parse-cidr=none rejects CIDR pattern
echo "Test 009-1: --parse-cidr=none rejects CIDR pattern"
output=$($GREPNET --parse-cidr=none '192.0.2.0/24' "$TEST_FILE" 2>&1)
if [[ -z "$output" ]] || [[ "$output" =~ "no patterns" ]]; then
    echo "  ✓ PASS: CIDR pattern rejected"
    ((PASSED++))
else
    echo "  ✗ FAIL: Should reject CIDR pattern, got: $output"
    ((FAILED++))
fi
echo

# Test: --parse-cidr=none with CIDR input and range pattern gives no match
echo "Test 009-2: --parse-cidr=none with CIDR input and range pattern gives no match"
output=$(echo "$TEST_CIDR" | $GREPNET --parse-cidr=none '192.0.2.0-192.0.2.255' 2>&1)
if [[ -z "$output" ]]; then
    echo "  ✓ PASS: Range pattern doesn't match CIDR input"
    ((PASSED++))
else
    echo "  ✗ FAIL: Should not match, got: $output"
    ((FAILED++))
fi
echo

# Test: --parse-cidr=pattern only allows CIDR in patterns
echo "Test 009-3: --parse-cidr=pattern allows CIDR in pattern only"
output=$(echo "$TEST_CIDR" | $GREPNET --parse-cidr=pattern '192.0.2.0-192.0.2.255' 2>&1)
if [[ -z "$output" ]]; then
    echo "  ✓ PASS: CIDR in input rejected"
    ((PASSED++))
else
    echo "  ✗ FAIL: Should reject CIDR in input with pattern-only, got: $output"
    ((FAILED++))
fi
echo

# Test: --parse-cidr=pattern allows CIDR pattern to match netmask in input
echo "Test 009-4: --parse-cidr=pattern CIDR pattern matches netmask format"
output=$($GREPNET --parse-cidr=pattern '192.0.2.0/24' "$TEST_FILE" 2>&1)
if [[ "$output" =~ "192.0.2.0 255.255.255.0" ]]; then
    echo "  ✓ PASS: CIDR pattern matched netmask format"
    ((PASSED++))
else
    echo "  ✗ FAIL: Should match netmask format, got: $output"
    ((FAILED++))
fi
echo

# Test: --parse-cidr=input only allows CIDR in input
echo "Test 009-5: --parse-cidr=input allows CIDR in input only"
output=$(echo "$TEST_CIDR" | $GREPNET --parse-cidr=input '192.0.2.1' 2>&1)
if [[ "$output" == "$TEST_CIDR" ]]; then
    echo "  ✓ PASS: CIDR in input extracted with bare IP pattern"
    ((PASSED++))
else
    echo "  ✗ FAIL: Should extract CIDR with bare IP pattern, got: $output"
    ((FAILED++))
fi
echo

# Test: --parse-cidr=both allows CIDR everywhere
echo "Test 009-6: --parse-cidr=both allows CIDR in pattern and input"
output=$(echo "$TEST_CIDR" | $GREPNET --parse-cidr=both '192.0.2.0-192.0.2.255' 2>&1)
if [[ "$output" == "$TEST_CIDR" ]]; then
    echo "  ✓ PASS: CIDR works in both"
    ((PASSED++))
else
    echo "  ✗ FAIL: Should match with CIDR, got: $output"
    ((FAILED++))
fi
echo

#############################################################################
# PARSE-NETMASK TESTS
#############################################################################

echo "--- PARSE-NETMASK TESTS ---"
echo

# Test: --parse-netmask=none rejects netmask format
echo "Test 009-7: --parse-netmask=none rejects netmask pattern"
output=$($GREPNET --parse-netmask=none '192.0.2.0 255.255.255.0' "$TEST_FILE" 2>&1)
if [[ -z "$output" ]] || [[ "$output" =~ "no patterns" ]]; then
    echo "  ✓ PASS: Netmask pattern rejected"
    ((PASSED++))
else
    echo "  ✗ FAIL: Should reject netmask pattern, got: $output"
    ((FAILED++))
fi
echo

# Test: --parse-netmask=none rejects netmask in input
echo "Test 009-8: --parse-netmask=none rejects netmask in input"
output=$(echo "$TEST_NETMASK" | $GREPNET --parse-netmask=none '192.0.2.0-192.0.2.255' 2>&1)
if [[ -z "$output" ]]; then
    echo "  ✓ PASS: Netmask not extracted from input"
    ((PASSED++))
else
    echo "  ✗ FAIL: Should reject netmask in input, got: $output"
    ((FAILED++))
fi
echo

# Test: --parse-netmask=pattern only allows netmask in patterns
echo "Test 009-9: --parse-netmask=pattern allows netmask in pattern only"
output=$(echo "$TEST_NETMASK" | $GREPNET --parse-netmask=pattern '192.0.2.0 255.255.255.0' 2>&1)
if [[ -z "$output" ]]; then
    echo "  ✓ PASS: Netmask in input rejected"
    ((PASSED++))
else
    echo "  ✗ FAIL: Should reject netmask in input with pattern-only, got: $output"
    ((FAILED++))
fi
echo

# Test: --parse-netmask=both allows netmask everywhere
echo "Test 009-10: --parse-netmask=both allows netmask in pattern and input"
output=$(echo "$TEST_NETMASK" | $GREPNET --parse-netmask=both '192.0.2.0-192.0.2.255' 2>&1)
if [[ "$output" == "$TEST_NETMASK" ]]; then
    echo "  ✓ PASS: Netmask works in both"
    ((PASSED++))
else
    echo "  ✗ FAIL: Should match with netmask, got: $output"
    ((FAILED++))
fi
echo

#############################################################################
# PARSE-HOSTMASK TESTS
#############################################################################

echo "--- PARSE-HOSTMASK TESTS ---"
echo

# Test: --parse-hostmask=none rejects hostmask format
echo "Test 009-11: --parse-hostmask=none rejects hostmask pattern"
output=$($GREPNET --parse-hostmask=none '192.0.2.0 0.0.0.255' "$TEST_FILE" 2>&1)
if [[ -z "$output" ]] || [[ "$output" =~ "no patterns" ]]; then
    echo "  ✓ PASS: Hostmask pattern rejected"
    ((PASSED++))
else
    echo "  ✗ FAIL: Should reject hostmask pattern, got: $output"
    ((FAILED++))
fi
echo

# Test: --parse-hostmask=none rejects hostmask in input
echo "Test 009-12: --parse-hostmask=none rejects hostmask in input"
output=$(echo "$TEST_HOSTMASK" | $GREPNET --parse-hostmask=none '192.0.2.0-192.0.2.255' 2>&1)
if [[ -z "$output" ]]; then
    echo "  ✓ PASS: Hostmask not extracted from input"
    ((PASSED++))
else
    echo "  ✗ FAIL: Should reject hostmask in input, got: $output"
    ((FAILED++))
fi
echo

# Test: --parse-hostmask=pattern only allows hostmask in patterns
echo "Test 009-13: --parse-hostmask=pattern allows hostmask in pattern only"
output=$(echo "$TEST_HOSTMASK" | $GREPNET --parse-hostmask=pattern '192.0.2.0 0.0.0.255' 2>&1)
if [[ -z "$output" ]]; then
    echo "  ✓ PASS: Hostmask in input rejected"
    ((PASSED++))
else
    echo "  ✗ FAIL: Should reject hostmask in input with pattern-only, got: $output"
    ((FAILED++))
fi
echo

# Test: --parse-hostmask=both allows hostmask everywhere
echo "Test 009-14: --parse-hostmask=both allows hostmask in pattern and input"
output=$(echo "$TEST_HOSTMASK" | $GREPNET --parse-hostmask=both '192.0.2.0-192.0.2.255' 2>&1)
if [[ "$output" == "$TEST_HOSTMASK" ]]; then
    echo "  ✓ PASS: Hostmask works in both"
    ((PASSED++))
else
    echo "  ✗ FAIL: Should match with hostmask, got: $output"
    ((FAILED++))
fi
echo

#############################################################################
# PARSE-RANGES TESTS
#############################################################################

echo "--- PARSE-RANGES TESTS ---"
echo

# Test: --parse-ranges=none extracts bare IP from range pattern
echo "Test 009-15: --parse-ranges=none extracts bare IP from range pattern"
output=$($GREPNET --parse-ranges=none '192.0.2.0-192.0.2.255' "$TEST_FILE" 2>&1)
if [[ "$output" =~ "192.0.2.0" ]]; then
    echo "  ✓ PASS: Bare IP extracted from range pattern"
    ((PASSED++))
else
    echo "  ✗ FAIL: Should extract bare IP, got: $output"
    ((FAILED++))
fi
echo

# Test: --parse-ranges=none with range input and CIDR pattern matches bare IP
echo "Test 009-16: --parse-ranges=none with range input and CIDR pattern"
output=$(echo "$TEST_RANGE" | $GREPNET --parse-ranges=none '192.0.2.0/24' 2>&1)
if [[ "$output" =~ "192.0.2.0" ]]; then
    echo "  ✓ PASS: Bare IP extracted from range (range format disabled)"
    ((PASSED++))
else
    echo "  ✗ FAIL: Should extract bare IP, got: $output"
    ((FAILED++))
fi
echo

# Test: --parse-ranges=pattern range input with range pattern extracts
echo "Test 009-17: --parse-ranges=pattern allows range in pattern only"
output=$(echo "$TEST_RANGE" | $GREPNET --parse-ranges=pattern '192.0.2.0-192.0.2.255' 2>&1)
if [[ "$output" == "$TEST_RANGE" ]]; then
    echo "  ✓ PASS: Range pattern matches range in input"
    ((PASSED++))
else
    echo "  ✗ FAIL: Should match range pattern, got: $output"
    ((FAILED++))
fi
echo

# Test: --parse-ranges=both allows ranges everywhere
echo "Test 009-18: --parse-ranges=both allows ranges in pattern and input"
output=$(echo "$TEST_RANGE" | $GREPNET --parse-ranges=both '192.0.2.0/24' 2>&1)
if [[ "$output" == "$TEST_RANGE" ]]; then
    echo "  ✓ PASS: Range works in both"
    ((PASSED++))
else
    echo "  ✗ FAIL: Should match with range, got: $output"
    ((FAILED++))
fi
echo

#############################################################################
# COMBINED TESTS
#############################################################################

echo "--- COMBINED PARSE CONTROL TESTS ---"
echo

# Test: Multiple formats disabled
echo "Test 009-19: All formats disabled returns no patterns"
output=$($GREPNET --parse-cidr=none --parse-netmask=none --parse-hostmask=none --parse-ranges=none '192.0.2.0/24' "$TEST_FILE" 2>&1)
if [[ -z "$output" ]] || [[ "$output" =~ "no patterns" ]]; then
    echo "  ✓ PASS: All formats disabled, pattern rejected"
    ((PASSED++))
else
    echo "  ✗ FAIL: Should reject pattern with all disabled, got: $output"
    ((FAILED++))
fi
echo

# Test: Only ranges allowed
echo "Test 009-20: Only ranges allowed matches range"
output=$(echo "$TEST_RANGE" | $GREPNET --parse-cidr=none --parse-netmask=none --parse-hostmask=none --parse-ranges=both '192.0.2.0-192.0.2.255' 2>&1)
if [[ "$output" == "$TEST_RANGE" ]]; then
    echo "  ✓ PASS: Range matched when only ranges enabled"
    ((PASSED++))
else
    echo "  ✗ FAIL: Should match range, got: $output"
    ((FAILED++))
fi
echo

# Test: Pattern-only formats
echo "Test 009-21: All formats pattern-only allows patterns to match"
output=$($GREPNET --parse-cidr=pattern --parse-netmask=pattern --parse-hostmask=pattern --parse-ranges=pattern '192.0.2.0/24' "$TEST_FILE" 2>&1)
if [[ ! -z "$output" ]]; then
    echo "  ✓ PASS: Pattern-only formats matched"
    ((PASSED++))
else
    echo "  ✗ FAIL: Should match pattern, got: $output"
    ((FAILED++))
fi
echo

# Cleanup
rm -f "$TEST_FILE"

# Summary
echo "════════════════════════════════════════════════════════════════"
echo "Test 009 Summary: Comprehensive Parse Control Options"
echo "Passed: $PASSED"
echo "Failed: $FAILED"
echo "════════════════════════════════════════════════════════════════"

if [[ $FAILED -eq 0 ]]; then
    exit 0
else
    exit 1
fi
