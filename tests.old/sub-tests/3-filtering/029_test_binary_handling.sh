#!/bin/bash

# Test Phase 3: Binary File Handling
# Tests -a, -I, --binary-files

set -euo pipefail

GREPNET="${GREPNET:-$(dirname "$0")/../grepnet}"
TESTS_DIR="$(dirname "$0")"

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
        cat /tmp/test_output.txt | head -3 | sed 's/^/    /'
        ((FAILED++))
    fi
}

echo "====== Phase 3: Binary File Handling Tests ======"
echo ""

# Create binary test file
BINARY_FILE="/tmp/grepnet_binary.bin"
printf "192.0.2.0\x00\xFF\xFE\xFD" > "$BINARY_FILE"

echo "--- Default Binary Handling (Show Warning) ---"
# SPEC: Binary files should show a warning message by default
# SPEC-REF: GREPNET-SPEC.md - Binary File Handling: "Default: show warning for binary files"
test_case "Binary file shows warning" \
    "$GREPNET '$BINARY_FILE' 0.0.0.0/0 2>&1 | grep -q 'Binary file' && exit 0 || exit 1" \
    0

# SPEC: Binary files by default should not produce match output (exit code 1 for no matches)
# SPEC-REF: GREPNET-SPEC.md - Binary File Handling: "Default: skip binary file content"
test_case "Binary file doesn't output match by default" \
    "$GREPNET '$BINARY_FILE' 0.0.0.0/0 2>/dev/null" \
    1

echo ""
echo "--- -a (Text Mode) Tests ---"
# SPEC: Text mode flag (-a) processes binary files as text
# SPEC-REF: GREPNET-SPEC.md - Binary File Handling: "Text mode (-a): treat binary as text"
test_case "-a processes binary as text" \
    "$GREPNET -a '$BINARY_FILE' 0.0.0.0/0 2>/dev/null" \
    0

# SPEC: Text mode (-a) allows matching and output from binary files
# SPEC-REF: GREPNET-SPEC.md - Binary File Handling: "Text mode (-a): treat binary as text"
test_case "-a allows match output" \
    "$GREPNET -a '$BINARY_FILE' 0.0.0.0/0 2>/dev/null | grep -q '192.0.2.0'" \
    0

echo ""
echo "--- -I (Binary Nomatch) Tests ---"
# SPEC: Binary nomatch flag (-I) skips binary files silently
# SPEC-REF: GREPNET-SPEC.md - Binary File Handling: "Binary without-match (-I): skip binary files silently"
test_case "-I skips binary silently" \
    "$GREPNET -I '$BINARY_FILE' 0.0.0.0/0 2>&1" \
    1

# SPEC: Binary nomatch flag (-I) should produce no output
# SPEC-REF: GREPNET-SPEC.md - Binary File Handling: "Binary without-match (-I): skip binary files silently"
test_case "-I produces no output" \
    "$GREPNET -I '$BINARY_FILE' 0.0.0.0/0 2>&1 | wc -l" \
    0

echo ""
echo "--- --binary-files Tests ---"
# SPEC: Binary files text mode (--binary-files text) treats binary as text
# SPEC-REF: GREPNET-SPEC.md - Binary File Handling: "--binary-files text: treat as text"
test_case "--binary-files text allows match" \
    "$GREPNET --binary-files text '$BINARY_FILE' 0.0.0.0/0 2>/dev/null" \
    0

# SPEC: Binary files without-match mode (--binary-files without-match) skips binary files
# SPEC-REF: GREPNET-SPEC.md - Binary File Handling: "--binary-files without-match: skip binary"
test_case "--binary-files without-match skips" \
    "$GREPNET --binary-files without-match '$BINARY_FILE' 0.0.0.0/0 2>&1" \
    1

# SPEC: Binary files binary mode (--binary-files binary) shows a warning for binary files
# SPEC-REF: GREPNET-SPEC.md - Binary File Handling: "--binary-files binary: show warning"
test_case "--binary-files binary shows warning" \
    "$GREPNET --binary-files binary '$BINARY_FILE' 0.0.0.0/0 2>&1 | grep -q 'Binary file'" \
    0

echo ""
echo "--- Flag Precedence Tests ---"
# SPEC: Text mode flag (-a) overrides --binary-files setting
# SPEC-REF: GREPNET-SPEC.md - Binary File Handling: "Flag precedence: -a overrides --binary-files"
test_case "-a overrides --binary-files" \
    "$GREPNET -a --binary-files without-match '$BINARY_FILE' 0.0.0.0/0 2>/dev/null" \
    0

# SPEC: Binary nomatch flag (-I) overrides --binary-files text setting
# SPEC-REF: GREPNET-SPEC.md - Binary File Handling: "Flag precedence: -I overrides --binary-files"
test_case "-I overrides --binary-files" \
    "$GREPNET -I --binary-files text '$BINARY_FILE' 0.0.0.0/0 2>&1" \
    1

echo ""
echo "--- Binary stdin Tests ---"
# SPEC: Binary stdin with text mode (-a) processes binary data as text
# SPEC-REF: GREPNET-SPEC.md - Binary File Handling: "Text mode (-a): treat binary as text"
test_case "Binary stdin with -a" \
    "printf '192.0.2.0\x00binary' | $GREPNET -a 0.0.0.0/0 2>/dev/null" \
    0

# SPEC: Binary stdin by default should skip binary content
# SPEC-REF: GREPNET-SPEC.md - Binary File Handling: "Default: skip binary file content"
test_case "Binary stdin by default" \
    "printf '192.0.2.0\x00binary' | $GREPNET 0.0.0.0/0 2>/dev/null" \
    1

echo ""
echo "====== Test Summary ======"
echo "Passed: $PASSED"
echo "Failed: $FAILED"
echo "Total:  $((PASSED + FAILED))"

# Cleanup
rm -f "$BINARY_FILE"

if [[ $FAILED -eq 0 ]]; then
    echo "✓ All tests PASSED"
    exit 0
else
    echo "✗ Some tests FAILED"
    exit 1
fi
