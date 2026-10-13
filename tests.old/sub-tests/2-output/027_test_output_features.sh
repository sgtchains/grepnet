#!/bin/bash

# Test Phase 3: Output Features
# Tests -o, --show-content, -Z, --label, -m, -a, -I

set -euo pipefail

# Get grepnet binary from standard location
if [ -z "${GREPNET:-}" ]; then
    if [ -f "$(dirname "$0")/../../grepnet" ]; then
        GREPNET="$(dirname "$0")/../../grepnet"
    elif command -v grepnet &>/dev/null; then
        GREPNET="grepnet"
    else
        GREPNET="/home/chains/bin/grepnet"
    fi
fi

TESTS_DIR="$(dirname "$0")/../files"

PASSED=0
FAILED=0

test_case() {
    local name="$1"
    local cmd="$2"
    local expected_exit="$3"
    
    echo -n "Testing: $name ... "
    
    set +e
    timeout 5 bash -c "$cmd" > /tmp/test_output.txt 2>&1
    actual_exit=$?
    set -e
    
    if [[ $actual_exit -eq $expected_exit ]]; then
        echo "✓ PASS"
        ((PASSED++))
    else
        echo "✗ FAIL (exit: $actual_exit, expected: $expected_exit)"
        ((FAILED++))
    fi
}

echo "====== Phase 3: Output Features Tests ======"
echo ""

echo "--- -o (Only Matching) Tests ---"
test_case "-o basic" \
    "echo '192.0.2.0' | '$GREPNET' -o 0.0.0.0/0" \
    0

test_case "-o multiple" \
    "echo -e '192.0.2.0\n192.0.2.1' | $GREPNET -o 0.0.0.0/0" \
    0

test_case "-o with -n" \
    "echo '192.0.2.0' | $GREPNET -o -n 0.0.0.0/0" \
    0

echo ""
echo "--- --label Tests ---"
test_case "--label stdin" \
    "echo '192.0.2.0' | $GREPNET --label test-input -H 0.0.0.0/0 | grep -q test-input" \
    0

echo ""
echo "--- -Z (Null Separator) Tests ---"
test_case "-Z with separator" \
    "echo '192.0.2.0' | $GREPNET -Z -H 0.0.0.0/0 | od -c | grep -q '\\\\0'" \
    0

echo ""
echo "--- -m (Max Count) Tests ---"
test_case "-m limits output" \
    "echo -e '192.0.2.0\n192.0.2.1\n192.0.2.2' | $GREPNET -m 2 0.0.0.0/0 | wc -l | grep -q '^2$'" \
    0

test_case "-m with fewer matches" \
    "echo -e '192.0.2.0\n192.0.2.1' | $GREPNET -m 5 0.0.0.0/0 | wc -l | grep -q '^2$'" \
    0

echo ""
echo "--- --show-content Tests ---"
test_case "--show-content extract mode" \
    "echo 'text 192.0.2.0 more' | $GREPNET --extract --show-content | grep -q '|'" \
    0

echo ""
echo "--- -T (Initial Tab) Tests ---"
test_case "-T replaces separator" \
    "echo '192.0.2.0' | $GREPNET -T -H -n 0.0.0.0/0 | grep -q $'\\t'" \
    0

echo ""
echo "--- -a (Binary as Text) Tests ---"
test_case "-a processes binary" \
    "printf '192.0.2.0\x00binary' | $GREPNET -a 0.0.0.0/0 | wc -l | grep -q '^1$'" \
    0

echo ""
echo "--- -I (Binary Nomatch) Tests ---"
test_case "-I skips binary" \
    "$GREPNET -I /dev/null 0.0.0.0/0" \
    1

echo ""
echo "--- -F (Input File) Tests ---"
TEST_FILE="/tmp/grepnet_test_in.txt"
cat > "$TEST_FILE" << 'EOF'
192.0.2.0
10.0.0.0
EOF

test_case "-F single file" \
    "$GREPNET -F '$TEST_FILE' 0.0.0.0/0 | wc -l | grep -q '^2$'" \
    0

echo ""
echo "====== Test Summary ======"
echo "Passed: $PASSED"
echo "Failed: $FAILED"

rm -f "$TEST_FILE"

if [[ $FAILED -eq 0 ]]; then
    echo "✓ All tests PASSED"
    exit 0
else
    echo "✗ Some tests FAILED"
    exit 1
fi

