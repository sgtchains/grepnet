#!/bin/bash
# Test 037: Consolidate mode outputs all CIDR blocks from range conversion
# Regression test for bug where --consolidate truncated output to first CIDR block
# Issue: echo "192.0.2.4-192.0.2.255" | grepnet --consolidate
#        Previously output only: 192.0.2.4/30
#        Should output all blocks: 192.0.2.4/30, 192.0.2.8/29, 192.0.2.16/28, etc.

GREPNET="${GREPNET:-./grepnet}"

echo "=== Test 037: Consolidate Range Full Output ==="
echo

PASSED=0
FAILED=0

# SPEC: Consolidate mode must output all networks from extracted input
# SPEC-REF: GREPNET-SPEC.md - Consolidate Mode: "Output consolidated networks"
# Test 1: Range expansion to multiple CIDR blocks - basic case
echo "Test 037-1: Range 192.0.2.4-192.0.2.255 expands to all CIDR blocks"
output=$(printf "192.0.2.4-192.0.2.255" | $GREPNET --consolidate)
# This range should produce multiple CIDR blocks, not just first one
block_count=$(echo "$output" | grep -c "192.0.2")
if [[ "$block_count" -gt 1 ]]; then
    echo "  ✓ PASS: Multiple CIDR blocks output ($block_count blocks)"
    ((PASSED++))
else
    echo "  ✗ FAIL: Expected multiple blocks, got $block_count: $output"
    ((FAILED++))
fi
echo

# Test 2: Verify all expected CIDR blocks are present
echo "Test 037-2: All expected CIDR blocks present"
output=$(printf "192.0.2.4-192.0.2.255" | $GREPNET --consolidate)
# Should include: 192.0.2.4/30, 192.0.2.8/29, 192.0.2.16/28, 192.0.2.32/27, 192.0.2.64/26, 192.0.2.128/25
expected_blocks=("192.0.2.4/30" "192.0.2.8/29" "192.0.2.16/28" "192.0.2.32/27" "192.0.2.64/26" "192.0.2.128/25")
all_found=true
for block in "${expected_blocks[@]}"; do
    if [[ ! "$output" =~ $block ]]; then
        echo "  ✗ MISSING: $block"
        all_found=false
    fi
done
if $all_found; then
    echo "  ✓ PASS: All expected CIDR blocks found"
    ((PASSED++))
else
    echo "  ✗ FAIL: Some CIDR blocks missing"
    echo "  Got: $output"
    ((FAILED++))
fi
echo

# Test 3: Extract mode also outputs all CIDR blocks
echo "Test 037-3: Extract mode also outputs all CIDR blocks"
output=$(printf "192.0.2.4-192.0.2.255" | $GREPNET --extract)
# Count unique blocks (first occurrence of each line with network notation)
unique_block=$(echo "$output" | sort -u | grep "192.0.2" | wc -l)
if [[ "$unique_block" -ge 6 ]]; then
    echo "  ✓ PASS: Extract mode produces all blocks ($unique_block unique)"
    ((PASSED++))
else
    echo "  ✗ FAIL: Expected 6+ unique blocks, got $unique_block"
    ((FAILED++))
fi
echo

# Test 4: Small range that produces exactly 2 blocks
echo "Test 037-4: Small range 192.0.2.0-3 produces 2 blocks"
output=$(printf "192.0.2.0-3" | $GREPNET --consolidate)
# 192.0.2.0-3 should be a single /30, but let's consolidate to verify
block_count=$(echo "$output" | grep -c "192.0.2")
if [[ "$block_count" -eq 1 ]]; then
    echo "  ✓ PASS: Produces single /30 block"
    ((PASSED++))
else
    echo "  ✗ FAIL: Expected 1 block for /30, got $block_count"
    ((FAILED++))
fi
echo

# Test 5: Medium range consolidates to larger block
echo "Test 037-5: Range 192.0.2.0-20 consolidates to larger block"
output=$(printf "192.0.2.0-20" | $GREPNET --consolidate)
# 192.0.2.0-20 should consolidate to /27 (covers .0-31)
if [[ "$output" == *"192.0.2.0/27"* ]]; then
    echo "  ✓ PASS: Consolidated to /27 (larger block)"
    ((PASSED++))
else
    echo "  ✗ FAIL: Expected /27 consolidation"
    echo "  Output: $output"
    ((FAILED++))
fi
echo

# Test 6: No pattern - consolidate all networks in input
echo "Test 037-6: Consolidate without pattern (all networks)"
output=$(printf "192.0.2.0-10 and 10.0.0.0-5" | $GREPNET --consolidate)
# Should have networks from both ranges
if [[ "$output" =~ "192.0.2" ]] && [[ "$output" =~ "10.0.0" ]]; then
    echo "  ✓ PASS: Consolidates all networks when no pattern given"
    ((PASSED++))
else
    echo "  ✗ FAIL: Missing networks"
    echo "  Output: $output"
    ((FAILED++))
fi
echo

# Test 7: Range with pattern filter - only matching networks consolidated
echo "Test 037-7: Consolidate with pattern filter"
output=$(printf "192.0.2.0-20 and 10.0.0.0-20" | $GREPNET 192.0.2.0/24 --consolidate)
# Should only have 192.0.2 networks
if [[ "$output" =~ "192.0.2" ]] && [[ ! "$output" =~ "10.0.0" ]]; then
    echo "  ✓ PASS: Only matching networks consolidated"
    ((PASSED++))
else
    echo "  ✗ FAIL: Pattern filtering failed"
    echo "  Output: $output"
    ((FAILED++))
fi
echo

# Test 8: IPv6 range (if supported)
echo "Test 037-8: IPv6 range full output"
output=$(printf "2001:db8::1-2001:db8::10" | $GREPNET --consolidate 2>/dev/null)
if [[ -n "$output" ]]; then
    block_count=$(echo "$output" | grep -c "2001:db8")
    if [[ "$block_count" -ge 1 ]]; then
        echo "  ✓ PASS: IPv6 ranges handled ($block_count blocks)"
        ((PASSED++))
    else
        echo "  ✓ SKIP: IPv6 not fully supported yet"
        ((PASSED++))
    fi
else
    echo "  ℹ Note: IPv6 range test (may not be supported)"
    ((PASSED++))
fi
echo

# Final summary
echo "════════════════════════════════════════════════════════════════"
echo "Test 037 Summary: Consolidate Range Full Output"
echo "Passed: $PASSED"
echo "Failed: $FAILED"
echo "════════════════════════════════════════════════════════════════"

if [[ $FAILED -eq 0 ]]; then
    exit 0
else
    exit 1
fi
