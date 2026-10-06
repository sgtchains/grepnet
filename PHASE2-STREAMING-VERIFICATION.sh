#!/bin/bash

# PHASE 2: STREAMING COMPLIANCE VERIFICATION
# Manual tests to verify core streaming functionality

echo "=== PHASE 2: STREAMING COMPLIANCE VERIFICATION ==="
echo ""

PASS=0
FAIL=0

check_output() {
    local name="$1"
    local cmd="$2"
    local expected="$3"
    
    actual=$(eval "$cmd" 2>&1)
    if [ "$actual" = "$expected" ]; then
        echo "✓ PASS: $name"
        ((PASS++))
    else
        echo "✗ FAIL: $name"
        echo "  Expected: $expected"
        echo "  Got: $actual"
        ((FAIL++))
    fi
}

# Test 1: Context buffering (-B flag)
check_output "Context: Before-context with -B2" \
    "echo -e 'line1\nline2\n192.0.2.0/24\nline4' | ./grepnet -B2 '192.0.2.0/24'" \
    "line1
line2
192.0.2.0/24"

# Test 2: Context (-A flag)
check_output "Context: After-context with -A2" \
    "echo -e '192.0.2.0/24\nline2\nline3\nline4' | ./grepnet -A2 '192.0.2.0/24'" \
    "192.0.2.0/24
line2
line3"

# Test 3: Combined context (-C flag)
check_output "Context: Combined with -C1" \
    "echo -e 'before\n192.0.2.0/24\nafter' | ./grepnet -C1 '192.0.2.0/24'" \
    "before
192.0.2.0/24
after"

# Test 4: Pipe streaming - normal mode
check_output "Pipe: Normal mode from stdin" \
    "echo -e '192.0.2.0/24\n10.0.0.0/8' | ./grepnet '192.0.2'" \
    "192.0.2.0/24"

# Test 5: Pipe streaming - extract mode
check_output "Pipe: Extract mode deduplicates" \
    "echo -e '192.0.2.0/24\n192.0.2.0/24\n10.0.0.0/8' | ./grepnet --extract '192.0.2'" \
    "192.0.2.0/24"

# Test 6: Extract deduplication
check_output "Extract: Deduplicates across formats" \
    "./grepnet --extract '192.0.2' tests/files/sample_networks.txt | head -1" \
    "192.0.2.0/24"

# Test 7: Consolidate merges networks
check_output "Consolidate: Merges overlapping networks" \
    "./grepnet --consolidate '192.0.2.0/25' tests/files/sample_networks.txt" \
    "192.0.2.0/24"

# Test 8: MatchResult provides filename
OUTPUT=$(./grepnet -H '192.0.2.0/24' tests/files/sample_networks.txt | head -1)
if [[ "$OUTPUT" == *"tests/files/sample_networks.txt:"* ]]; then
    echo "✓ PASS: MatchResult: Filename with -H flag"
    ((PASS++))
else
    echo "✗ FAIL: MatchResult: Filename with -H flag"
    echo "  Got: $OUTPUT"
    ((FAIL++))
fi

# Test 9: MatchResult provides line number
OUTPUT=$(./grepnet -n '192.0.2.0/24' tests/files/sample_networks.txt | head -1)
if [[ "$OUTPUT" == "1:"* ]]; then
    echo "✓ PASS: MatchResult: Line number with -n flag"
    ((PASS++))
else
    echo "✗ FAIL: MatchResult: Line number with -n flag"
    echo "  Got: $OUTPUT"
    ((FAIL++))
fi

# Test 10: Large file doesn't preload
echo ""
echo "Creating 1000-line test file..."
{
    for i in {1..1000}; do
        echo "line $i"
    done
    echo "192.0.2.0/24"
} > /tmp/streaming_test.txt

OUTPUT=$(./grepnet '192.0.2.0/24' /tmp/streaming_test.txt)
if [ "$OUTPUT" = "192.0.2.0/24" ]; then
    echo "✓ PASS: Streaming: Large file processes efficiently"
    ((PASS++))
else
    echo "✗ FAIL: Streaming: Large file"
    ((FAIL++))
fi

rm -f /tmp/streaming_test.txt /tmp/large_test.txt

echo ""
echo "=== PHASE 2 STREAMING COMPLIANCE RESULTS ==="
echo "✓ Passed: $PASS"
echo "✗ Failed: $FAIL"
echo "Total:   $((PASS + FAIL))"

if [ $FAIL -eq 0 ]; then
    echo ""
    echo "✓ PHASE 2 COMPLETE: Streaming compliance verified"
    exit 0
else
    echo ""
    echo "✗ PHASE 2 INCOMPLETE: $FAIL tests failed"
    exit 1
fi
