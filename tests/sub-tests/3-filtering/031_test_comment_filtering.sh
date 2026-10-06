#!/bin/bash

# Test Phase 3: Comment Filtering
# Tests comment handling: #, !, remark, rem, description, desc (case-insensitive)
# Tests --no-filter-comments flag

set -uo pipefail

GREPNET="${GREPNET:-/home/chains/dev/grepnet/grepnet}"
TEST_DIR="$(cd "$(dirname "$0")" && pwd)"
TESTS_DIR="$(cd "$TEST_DIR/../.." && pwd)"

# Test tracking
PASSED=0
FAILED=0

echo "====== Phase 3: Comment Filtering Tests ======"
echo ""

# Create test files with various comment formats
COMMENT_TEST_FILE="/tmp/grepnet_comment_test.txt"
cat > "$COMMENT_TEST_FILE" << 'EOF'
# Standard Unix comment with 192.0.2.0
192.0.2.1
! Cisco comment with 192.0.2.2
192.0.2.3
remark This is a Cisco remark 192.0.2.4
192.0.2.5
rem Short form remark 192.0.2.6
192.0.2.7
description Cisco description 192.0.2.8
192.0.2.9
desc Short form description 192.0.2.10
192.0.2.11
REMARK Uppercase Cisco remark 192.0.2.12
192.0.2.13
DESCRIPTION Uppercase Cisco description 192.0.2.14
192.0.2.15
REM Uppercase short form 192.0.2.16
192.0.2.17
DESC Uppercase short form desc 192.0.2.18
192.0.2.19
   # Indented Unix comment 192.0.2.20
192.0.2.21
   ! Indented Cisco comment 192.0.2.22
192.0.2.23
   remark Indented Cisco remark 192.0.2.24
192.0.2.25
EOF

echo "--- Comment Filtering Enabled (Default) ---"

# Test 1: Basic filtering
echo -n "Test 1 - Hash comments filtered: "
result=$("$GREPNET" '0.0.0.0/0' "$COMMENT_TEST_FILE" 2>/dev/null | grep -v '^#' | wc -l) || result=999
if [[ "$result" -eq 13 ]]; then
    echo "✓ PASS (13 lines)"
    ((PASSED++))
else
    echo "✗ FAIL (got $result, expected 13)"
    ((FAILED++))
fi

# Test 2: No ! at start
echo -n "Test 2 - Cisco ! filtered: "
result=$("$GREPNET" '0.0.0.0/0' "$COMMENT_TEST_FILE" 2>/dev/null | grep -v '^!' | wc -l) || result=999
if [[ "$result" -eq 13 ]]; then
    echo "✓ PASS (13 lines)"
    ((PASSED++))
else
    echo "✗ FAIL (got $result, expected 13)"
    ((FAILED++))
fi

# Test 3: Remark comments not present
echo -n "Test 3 - Remark comments filtered: "
result=$("$GREPNET" '0.0.0.0/0' "$COMMENT_TEST_FILE" 2>/dev/null | grep -i '^remark' | wc -l)
result=${result:-0}  # Default to 0 if empty
if [[ "$result" -eq 0 ]]; then
    echo "✓ PASS (0 remark lines)"
    ((PASSED++))
else
    echo "✗ FAIL (got $result, expected 0)"
    ((FAILED++))
fi

# Test 4: Description comments not present
echo -n "Test 4 - Description filtered: "
result=$("$GREPNET" '0.0.0.0/0' "$COMMENT_TEST_FILE" 2>/dev/null | grep -i '^description' | wc -l)
result=${result:-0}  # Default to 0 if empty
if [[ "$result" -eq 0 ]]; then
    echo "✓ PASS (0 description lines)"
    ((PASSED++))
else
    echo "✗ FAIL (got $result, expected 0)"
    ((FAILED++))
fi

# Test 5: Total count
echo -n "Test 5 - Total lines (filtering enabled): "
result=$("$GREPNET" '0.0.0.0/0' "$COMMENT_TEST_FILE" 2>/dev/null | wc -l) || result=999
if [[ "$result" -eq 13 ]]; then
    echo "✓ PASS (13 lines)"
    ((PASSED++))
else
    echo "✗ FAIL (got $result, expected 13)"
    ((FAILED++))
fi

echo ""
echo "--- Comment Filtering Disabled (--no-filter-comments) ---"

# Test 6: All lines with flag
echo -n "Test 6 - All lines included: "
result=$("$GREPNET" --no-filter-comments '0.0.0.0/0' "$COMMENT_TEST_FILE" 2>/dev/null | wc -l) || result=999
if [[ "$result" -eq 26 ]]; then
    echo "✓ PASS (26 lines)"
    ((PASSED++))
else
    echo "✗ FAIL (got $result, expected 26)"
    ((FAILED++))
fi

echo ""
echo "--- Edge Cases ---"

# Test 7: Non-comment lines that contain special chars
EDGE_CASE_FILE="/tmp/grepnet_edge_case.txt"
cat > "$EDGE_CASE_FILE" << 'EOF'
network# interface 192.0.2.1
system! status 192.0.2.2
configuration-remark not a comment 192.0.2.3
feature: description text 192.0.2.4
192.0.2.5
EOF

echo -n "Test 7 - Non-comment special chars: "
result=$("$GREPNET" '0.0.0.0/0' "$EDGE_CASE_FILE" 2>/dev/null | wc -l) || result=999
if [[ "$result" -eq 5 ]]; then
    echo "✓ PASS (5 lines)"
    ((PASSED++))
else
    echo "✗ FAIL (got $result, expected 5)"
    ((FAILED++))
fi

# Test 8: Mixed case Cisco keywords
MIXED_CASE_FILE="/tmp/grepnet_mixed_case.txt"
cat > "$MIXED_CASE_FILE" << 'EOF'
Remark 192.0.2.1
REMARK 192.0.2.2
ReMarK 192.0.2.3
Description 192.0.2.4
DESCRIPTION 192.0.2.5
DeScRiPtIoN 192.0.2.6
Rem 192.0.2.7
REM 192.0.2.8
ReM 192.0.2.9
Desc 192.0.2.10
DESC 192.0.2.11
DeSc 192.0.2.12
192.0.2.13
EOF

echo -n "Test 8 - Mixed case keywords filtered: "
result=$("$GREPNET" '0.0.0.0/0' "$MIXED_CASE_FILE" 2>/dev/null | wc -l) || result=999
if [[ "$result" -eq 1 ]]; then
    echo "✓ PASS (1 line)"
    ((PASSED++))
else
    echo "✗ FAIL (got $result, expected 1)"
    ((FAILED++))
fi

# Test 9: Mixed case with flag
echo -n "Test 9 - Mixed case with --no-filter-comments: "
result=$("$GREPNET" --no-filter-comments '0.0.0.0/0' "$MIXED_CASE_FILE" 2>/dev/null | wc -l) || result=999
if [[ "$result" -eq 13 ]]; then
    echo "✓ PASS (13 lines)"
    ((PASSED++))
else
    echo "✗ FAIL (got $result, expected 13)"
    ((FAILED++))
fi

echo ""
echo "=== Summary ==="
printf "PASSED: %d\nFAILED: %d\n" "$PASSED" "$FAILED"

# Exit with success if all tests passed
[[ "$FAILED" -eq 0 ]]
