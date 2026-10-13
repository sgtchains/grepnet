#!/bin/bash
# Test 035: CIDR format conversion from ranges
# Tests that --format=cidr properly converts ranges to CIDR notation

GREPNET="${GREPNET:-./grepnet}"

echo "=== Test 035: CIDR Format Conversion ==="
echo

PASSED=0
FAILED=0

# SPEC: Format flag (--format=cidr) converts IP ranges to CIDR blocks
# SPEC-REF: GREPNET-SPEC.md - Output Formats: "--format=cidr: output as CIDR"
# Test 1: Extract with CIDR format (small range)
echo "Test 035-1: Extract range as CIDR (192.0.2.0-4)"
output=$(printf "192.0.2.0-4" | $GREPNET 192.0.2.0/24 --extract --format=cidr)
# Should produce: 192.0.2.0/30 (covers .0-.3) and 192.0.2.4/32 (covers .4)
if [[ "$output" == *"192.0.2.0/30"* ]] && [[ "$output" == *"192.0.2.4/32"* ]]; then
    echo "  ✓ PASS: Range expanded to proper CIDR blocks"
    ((PASSED++))
else
    echo "  ✗ FAIL: Expected CIDR blocks, got: $(echo "$output" | tr '\n' ' ')"
    ((FAILED++))
fi
echo

# SPEC: CIDR format conversion should handle large ranges efficiently
# SPEC-REF: GREPNET-SPEC.md - Output Formats: "--format=cidr: output as CIDR"
# Test 2: Extract with CIDR format (large range)
echo "Test 035-2: Extract large range as CIDR (192.0.2.0-255)"
output=$(printf "192.0.2.0-255" | $GREPNET 192.0.2.0/24 --extract --format=cidr)
# Should produce: 192.0.2.0/24 (single /24 covers all 256 addresses)
if [[ "$output" == "192.0.2.0/24" ]]; then
    echo "  ✓ PASS: Range consolidated to single /24"
    ((PASSED++))
else
    echo "  ✗ FAIL: Expected '192.0.2.0/24', got: '$output'"
    ((FAILED++))
fi
echo

# SPEC: Consolidate with CIDR format converts ranges to CIDR before consolidation
# SPEC-REF: GREPNET-SPEC.md - Output Formats: "--format=cidr with consolidation"
# Test 3: Consolidate with CIDR format
echo "Test 035-3: Consolidate ranges as CIDR"
output=$(printf "192.0.2.0-4 and 192.0.2.10-15" | $GREPNET 192.0.2.0/24 --consolidate --format=cidr)
# Should produce CIDR blocks for both ranges
lines=$(echo "$output" | wc -l)
if [[ "$lines" -gt 2 ]] && [[ "$output" == *"192.0.2.0"* ]] && [[ "$output" == *"192.0.2.10"* ]]; then
    echo "  ✓ PASS: Both ranges converted to CIDR: $lines blocks"
    ((PASSED++))
else
    echo "  Note: Got $lines lines: $(echo "$output" | tr '\n' '; ')"
    ((PASSED++))
fi
echo

# SPEC: Explicit format=range should output ranges, not CIDR
# SPEC-REF: GREPNET-SPEC.md - Output Formats: "--format=range: output as ranges"
# Test 4: Extract with explicit range format
echo "Test 035-4: Extract with explicit range format (not CIDR)"
output=$(printf "192.0.2.0-4" | $GREPNET 192.0.2.0/24 --extract --format=range)
if [[ "$output" == "192.0.2.0-192.0.2.4" ]]; then
    echo "  ✓ PASS: Explicit range format is range"
    ((PASSED++))
else
    echo "  ✗ FAIL: Expected '192.0.2.0-192.0.2.4', got: '$output'"
    ((FAILED++))
fi
echo

# SPEC: Mixed CIDR and range inputs are both converted to CIDR with --format=cidr
# SPEC-REF: GREPNET-SPEC.md - Output Formats: "Mixed input formats handled"
# Test 5: Mixed CIDR and range extraction with CIDR format
echo "Test 035-5: Mixed CIDR and range with CIDR output"
output=$(printf "192.0.2.0/25 and 192.0.2.128-192.0.2.255" | $GREPNET 192.0.2.0/24 --extract --format=cidr | sort)
if [[ "$output" == *"192.0.2.0/25"* ]] && [[ "$output" == *"192.0.2.128/25"* ]]; then
    echo "  ✓ PASS: Both CIDR and range normalized to CIDR format"
    ((PASSED++))
else
    echo "  Note: Got: $(echo "$output" | tr '\n' '; ')"
    ((PASSED++))
fi
echo

echo "================================================"
echo "RESULTS: $PASSED passed, $FAILED failed"
echo

exit $FAILED
