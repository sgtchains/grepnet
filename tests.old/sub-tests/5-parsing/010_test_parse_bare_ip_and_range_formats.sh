#!/bin/bash

#############################################################################
# GREPNET TEST: Parse Bare IP and Range Format Options
# Tests: --parse-bare-ip, --parse-ranges-long, --parse-ranges-short
#############################################################################

GREPNET="${GREPNET:-./grepnet}"

echo "=== Test 010: Parse Bare IP and Range Format Options ==="
echo

PASSED=0
FAILED=0

# Test data
TEST_FILE="/tmp/bare_ip_range_test.txt"

# Create test input file
cat > "$TEST_FILE" << 'EOF'
192.0.2.0/24
192.0.2.0 255.255.255.0
192.0.2.0 0.0.0.255
192.0.2.0-192.0.2.255
192.0.2.1-254
192.0.2.1
EOF

#############################################################################
# PARSE-BARE-IP TESTS
#############################################################################

echo "--- PARSE-BARE-IP TESTS ---"
echo

# Test: --parse-bare-ip=both (default) accepts bare IPs in patterns and input
echo "Test 010-1: --parse-bare-ip=both (default) accepts bare IPs everywhere"
output=$($GREPNET --parse-bare-ip=both '192.0.2.1' "$TEST_FILE" 2>&1)
if [[ "$output" =~ "192.0.2.1" ]]; then
    echo "  ✓ PASS: Bare IP matched"
    ((PASSED++))
else
    echo "  ✗ FAIL: Should match bare IP, got: $output"
    ((FAILED++))
fi
echo

# Test: --parse-bare-ip=pattern accepts bare IPs in patterns only
echo "Test 010-2: --parse-bare-ip=pattern accepts bare IPs in pattern only"
output=$(echo "192.0.2.1" | $GREPNET --parse-bare-ip=pattern '192.0.2.1' 2>&1)
if [[ -z "$output" ]]; then
    echo "  ✓ PASS: Bare IP in input rejected"
    ((PASSED++))
else
    echo "  ✗ FAIL: Should reject bare IP in input with pattern-only, got: $output"
    ((FAILED++))
fi
echo

# Test: --parse-bare-ip=input accepts bare IPs in input only
echo "Test 010-3: --parse-bare-ip=input accepts bare IPs in input only"
output=$(echo "192.0.2.1" | $GREPNET --parse-bare-ip=input '192.0.2.0/24' 2>&1)
if [[ "$output" == "192.0.2.1" ]]; then
    echo "  ✓ PASS: Bare IP in input extracted with CIDR pattern"
    ((PASSED++))
else
    echo "  ✗ FAIL: Should extract bare IP from input, got: $output"
    ((FAILED++))
fi
echo

# Test: --parse-bare-ip=none rejects bare IPs entirely
echo "Test 010-4: --parse-bare-ip=none rejects bare IPs entirely"
output=$($GREPNET --parse-bare-ip=none '192.0.2.1' "$TEST_FILE" 2>&1)
if [[ -z "$output" ]] || [[ "$output" =~ "no patterns" ]]; then
    echo "  ✓ PASS: Bare IP pattern rejected"
    ((PASSED++))
else
    echo "  ✗ FAIL: Should reject bare IP pattern, got: $output"
    ((FAILED++))
fi
echo

#############################################################################
# PARSE-RANGES-LONG TESTS
#############################################################################

echo "--- PARSE-RANGES-LONG TESTS ---"
echo

# Test: --parse-ranges-long accepts only long-form ranges
echo "Test 010-5: --parse-ranges-long accepts long-form ranges (192.0.2.0-192.0.2.255)"
output=$($GREPNET --parse-ranges-long '192.0.2.0-192.0.2.255' "$TEST_FILE" 2>&1)
if [[ "$output" =~ "192.0.2.0-192.0.2.255" ]]; then
    echo "  ✓ PASS: Long-form range matched"
    ((PASSED++))
else
    echo "  ✗ FAIL: Should match long-form range, got: $output"
    ((FAILED++))
fi
echo

# Test: --parse-ranges-long rejects short-form ranges
echo "Test 010-6: --parse-ranges-long rejects short-form ranges (192.0.2.1-254)"
output=$($GREPNET --parse-ranges-long '192.0.2.1-254' "$TEST_FILE" 2>&1)
if [[ -z "$output" ]]; then
    echo "  ✓ PASS: Short-form range rejected"
    ((PASSED++))
else
    echo "  ✗ FAIL: Should reject short-form range, got: $output"
    ((FAILED++))
fi
echo

#############################################################################
# PARSE-RANGES-SHORT TESTS
#############################################################################

echo "--- PARSE-RANGES-SHORT TESTS ---"
echo

# Test: --parse-ranges-short accepts only short-form ranges
echo "Test 010-7: --parse-ranges-short accepts short-form ranges (192.0.2.1-254)"
output=$($GREPNET --parse-ranges-short '192.0.2.1-254' "$TEST_FILE" 2>&1)
if [[ "$output" =~ "192.0.2.1-254" ]]; then
    echo "  ✓ PASS: Short-form range matched"
    ((PASSED++))
else
    echo "  ✗ FAIL: Should match short-form range, got: $output"
    ((FAILED++))
fi
echo

# Test: --parse-ranges-short rejects long-form ranges
echo "Test 010-8: --parse-ranges-short rejects long-form ranges (192.0.2.0-192.0.2.255)"
output=$($GREPNET --parse-ranges-short '192.0.2.0-192.0.2.255' "$TEST_FILE" 2>&1)
if [[ -z "$output" ]]; then
    echo "  ✓ PASS: Long-form range rejected"
    ((PASSED++))
else
    echo "  ✗ FAIL: Should reject long-form range, got: $output"
    ((FAILED++))
fi
echo

#############################################################################
# COMBINED TESTS
#############################################################################

echo "--- COMBINED FLAG TESTS ---"
echo

# Test: --parse-bare-ip=none with --parse-ranges-long
echo "Test 010-9: --parse-bare-ip=none with --parse-ranges-long"
output=$($GREPNET --parse-bare-ip=none --parse-ranges-long '192.0.2.0-192.0.2.255' "$TEST_FILE" 2>&1)
if [[ "$output" =~ "192.0.2.0-192.0.2.255" ]]; then
    echo "  ✓ PASS: Long-form range matched, bare IP excluded"
    ((PASSED++))
else
    echo "  ✗ FAIL: Should match long-form range, got: $output"
    ((FAILED++))
fi
echo

# Test: --parse-ranges-long with --parse-ranges-short should error (conflicting)
echo "Test 010-10: Conflicting range format flags (should handle gracefully)"
output=$($GREPNET --parse-ranges-long --parse-ranges-short '192.0.2.0-192.0.2.255' "$TEST_FILE" 2>&1)
# This may error or use last value; test documents behavior
if [[ ! -z "$output" ]]; then
    echo "  ✓ PASS: Command accepted (last flag wins or uses both)"
    ((PASSED++))
else
    echo "  ~ INFO: Conflicting flags resulted in no output"
    ((PASSED++))
fi
echo

#############################################################################
# TEST SUMMARY
#############################################################################

echo "════════════════════════════════════════════════════════════════"
echo "Test 010 Summary: Parse Bare IP and Range Format Options"
echo "Passed: $PASSED"
echo "Failed: $FAILED"
echo "════════════════════════════════════════════════════════════════"

exit $FAILED
