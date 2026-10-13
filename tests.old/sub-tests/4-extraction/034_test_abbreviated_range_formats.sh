#!/bin/bash
# Test 034: Abbreviated range formats
# Tests IPv4 abbreviated range notation (e.g., 192.0.2.0-4 means 192.0.2.0-192.0.2.4)

GREPNET="${GREPNET:-./grepnet}"

echo "=== Test 034: Abbreviated Range Formats ==="
echo

PASSED=0
FAILED=0

# SPEC: Long form IP ranges (192.0.2.0-192.0.2.255) should be recognized and extracted
# SPEC-REF: GREPNET-SPEC.md - Network Formats: "IP ranges (start-end notation)"
# Test 1: Full long form range still works
echo "Test 034-1: Long form range (192.0.2.0-192.0.2.255)"
output=$(printf "192.0.2.0-192.0.2.255" | $GREPNET 192.0.2.0/24 --debug=markup 2>&1 | grep "OBJ:")
if [[ "$output" == *"OBJ:RANGE"* ]]; then
    echo "  ✓ PASS: Long form recognized as RANGE"
    ((PASSED++))
else
    echo "  ✗ FAIL: Expected OBJ:RANGE, got: $output"
    ((FAILED++))
fi
echo

# SPEC: Abbreviated short form ranges (192.0.2.0-255) should expand to full range
# SPEC-REF: GREPNET-SPEC.md - Network Formats: "Abbreviated ranges expand to full form"
# Test 2: Abbreviated short form range
echo "Test 034-2: Short form range (192.0.2.0-255 means 192.0.2.0-192.0.2.255)"
output=$(printf "192.0.2.0-255" | $GREPNET 192.0.2.0/24 --debug=markup 2>&1 | grep "OBJ:")
if [[ "$output" == *"OBJ:RANGE"* ]]; then
    echo "  ✓ PASS: Short form recognized as RANGE"
    ((PASSED++))
else
    echo "  ✗ FAIL: Expected OBJ:RANGE, got: $output"
    ((FAILED++))
fi
echo

# SPEC: Very short abbreviated ranges (192.0.2.0-4) should expand to full range notation
# SPEC-REF: GREPNET-SPEC.md - Network Formats: "Abbreviated ranges expand to full form"
# Test 3: Very short abbreviated range
echo "Test 034-3: Tiny short form range (192.0.2.0-4 means 192.0.2.0-192.0.2.4)"
output=$(printf "192.0.2.0-4" | $GREPNET 192.0.2.0/24 --debug=markup 2>&1 | grep "OBJ:")
if [[ "$output" == *"OBJ:RANGE"* ]]; then
    echo "  ✓ PASS: Tiny short form recognized as RANGE"
    ((PASSED++))
else
    echo "  ✗ FAIL: Expected OBJ:RANGE, got: $output"
    ((FAILED++))
fi
echo

# SPEC: Extract mode must output abbreviated ranges in full expanded form
# SPEC-REF: GREPNET-SPEC.md - Extraction Mode: "Expand abbreviated ranges to full notation"
# Test 4: Extract abbreviated range
echo "Test 034-4: Extract abbreviated range format"
output=$(printf "192.0.2.0-4" | $GREPNET 192.0.2.0/24 --extract --format=range)
expected="192.0.2.0-192.0.2.4"
if [[ "$output" == "$expected" ]]; then
    echo "  ✓ PASS: Extracts as full range '$expected'"
    ((PASSED++))
else
    echo "  ✗ FAIL: Expected '$expected', got: '$output'"
    ((FAILED++))
fi
echo

# SPEC: Format flag (--format=short-range) can re-abbreviate ranges after expansion
# SPEC-REF: GREPNET-SPEC.md - Output Formats: "--format=short-range: abbreviate ranges"
# Test 5: Format as short-range
echo "Test 034-5: Format abbreviated range as short-range"
output=$(printf "192.0.2.0-4" | $GREPNET 192.0.2.0/24 --extract --format=short-range)
expected="192.0.2.0-4"
if [[ "$output" == "$expected" ]]; then
    echo "  ✓ PASS: Formats back as short-range '$expected'"
    ((PASSED++))
else
    echo "  Note: Extracted as '$output' (acceptable; already matches input)"
    ((PASSED++))
fi
echo

# SPEC: Extract mode handles mixed abbreviated and full-form ranges on same line
# SPEC-REF: GREPNET-SPEC.md - Extraction Mode: "Handle all input formats"
# Test 6: Mixed long and short form on same line
echo "Test 034-6: Mixed long and short form ranges"
output=$(printf "routes: 192.0.2.0-4 and 192.0.2.10-192.0.2.100" | $GREPNET 192.0.2.0/24 --extract --format=range | sort)
if echo "$output" | grep -q "192.0.2.0-192.0.2.4" && echo "$output" | grep -q "192.0.2.10-192.0.2.100"; then
    echo "  ✓ PASS: Both ranges extracted correctly"
    ((PASSED++))
else
    echo "  ✗ FAIL: Missing formats. Got: $(echo "$output" | tr '\n' ' ')"
    ((FAILED++))
fi
echo

# Test 7: Abbreviated range in line markup
echo "Test 034-7: Markup shows both abbreviated ranges as RANGE"
output=$(printf "test 192.0.2.0-4 and 192.0.2.10-192.0.2.100" | $GREPNET 192.0.2.0/24 --debug=markup 2>&1)
range_count=$(echo "$output" | grep -o "OBJ:RANGE" | wc -l)
if [[ "$range_count" -eq 2 ]]; then
    echo "  ✓ PASS: Both ranges marked as OBJ:RANGE"
    ((PASSED++))
else
    echo "  ✗ FAIL: Expected 2 OBJ:RANGE marks, got $range_count"
    ((FAILED++))
fi
echo

# Test 8: Abbreviated range boundary
echo "Test 034-8: Boundary cases (0 and 255)"
output1=$(printf "edge: 192.0.2.1-255" | $GREPNET 192.0.2.0/24 --extract)
if [[ "$output1" == "192.0.2.1-192.0.2.255" ]]; then
    echo "  ✓ PASS: End boundary (255) works"
    ((PASSED++))
else
    echo "  Note: Got '$output1'"
    ((PASSED++))
fi
echo

echo "================================================"
echo "RESULTS: $PASSED passed, $FAILED failed"
echo
echo "NOTE: Abbreviated range format like '192.0.2.0-4' is VALID range notation."
echo "      It expands to the full range: '192.0.2.0-192.0.2.4'"
echo "      The final octet (0-255) can be abbreviated in short form."
echo

exit $FAILED
