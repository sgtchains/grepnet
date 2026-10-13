#!/bin/bash

# Test Phase 3: Extended Comment Filtering
# Tests extended comment support: -- (SQL), // (C-style), ; (INI), <!-- --> (HTML)
# Tests single-line and block comments, inline comments, and filtering control

set -uo pipefail

GREPNET="${GREPNET:-/home/chains/dev/grepnet/grepnet}"
TEST_DIR="$(cd "$(dirname "$0")" && pwd)"
TESTS_DIR="$(cd "$TEST_DIR/../.." && pwd)"

# Test tracking
PASSED=0
FAILED=0

echo "====== Phase 3: Extended Comment Filtering Tests ======"
echo ""

# Test 1: SQL Comments (-- prefix)
echo -n "Test 1 - SQL comments (--) filtered: "
SQL_TEST="/tmp/grepnet_sql_test.txt"
cat > "$SQL_TEST" << 'EOF'
-- SQL comment with 192.0.2.0
192.0.2.1
-- Another SQL comment
192.0.2.2
   -- Indented SQL comment with 10.0.0.0
10.0.0.1
INSERT INTO ips VALUES ('192.0.2.3'); -- Inline SQL comment
10.0.0.2
EOF
result=$("$GREPNET" '0.0.0.0/0' "$SQL_TEST" 2>/dev/null | wc -l) || result=999
# Should get 5 lines (192.0.2.1, 192.0.2.2, 10.0.0.1, 192.0.2.3 from inline, 10.0.0.2)
if [[ "$result" -eq 5 ]]; then
    echo "✓ PASS (5 lines)"
    ((PASSED++))
else
    echo "✗ FAIL (got $result, expected 5)"
    ((FAILED++))
fi

# Test 2: SQL comments with --no-filter-comments
echo -n "Test 2 - SQL comments not filtered with flag: "
result=$("$GREPNET" --no-filter-comments=both '0.0.0.0/0' "$SQL_TEST" 2>/dev/null | wc -l) || result=999
# Should get 7 lines (all IPs including from comment lines)
if [[ "$result" -eq 7 ]]; then
    echo "✓ PASS (7 lines)"
    ((PASSED++))
else
    echo "✗ FAIL (got $result, expected 7)"
    ((FAILED++))
fi

# Test 3: C-style comments (// prefix)
echo -n "Test 3 - C-style comments (//) filtered: "
CSTYLE_TEST="/tmp/grepnet_cstyle_test.txt"
cat > "$CSTYLE_TEST" << 'EOF'
// C++ comment with 192.0.2.0
192.0.2.1
// Terraform comment
192.0.2.2
   // Indented C-style with 10.0.0.0
10.0.0.1
config = "192.0.2.3"; // Inline C-style
10.0.0.2
EOF
result=$("$GREPNET" '0.0.0.0/0' "$CSTYLE_TEST" 2>/dev/null | wc -l) || result=999
# Should get 5 lines (192.0.2.1, 192.0.2.2, 10.0.0.1, 192.0.2.3 from inline, 10.0.0.2)
if [[ "$result" -eq 5 ]]; then
    echo "✓ PASS (5 lines)"
    ((PASSED++))
else
    echo "✗ FAIL (got $result, expected 5)"
    ((FAILED++))
fi

# Test 4: C-style comments with --no-filter-comments
echo -n "Test 4 - C-style comments not filtered: "
result=$("$GREPNET" --no-filter-comments=both '0.0.0.0/0' "$CSTYLE_TEST" 2>/dev/null | wc -l) || result=999
if [[ "$result" -eq 7 ]]; then
    echo "✓ PASS (7 lines)"
    ((PASSED++))
else
    echo "✗ FAIL (got $result, expected 7)"
    ((FAILED++))
fi

# Test 5: INI comments (; prefix)
echo -n "Test 5 - INI comments (;) filtered: "
INI_TEST="/tmp/grepnet_ini_test.txt"
cat > "$INI_TEST" << 'EOF'
; INI comment with 192.0.2.0
192.0.2.1
; Another INI comment
192.0.2.2
   ; Indented INI with 10.0.0.0
10.0.0.1
setting=value ; Inline INI comment
10.0.0.2
EOF
result=$("$GREPNET" '0.0.0.0/0' "$INI_TEST" 2>/dev/null | wc -l) || result=999
# Should get 4 lines
if [[ "$result" -eq 4 ]]; then
    echo "✓ PASS (4 lines)"
    ((PASSED++))
else
    echo "✗ FAIL (got $result, expected 4)"
    ((FAILED++))
fi

# Test 6: INI comments with --no-filter-comments
echo -n "Test 6 - INI comments not filtered: "
result=$("$GREPNET" --no-filter-comments=both '0.0.0.0/0' "$INI_TEST" 2>/dev/null | wc -l) || result=999
if [[ "$result" -eq 6 ]]; then
    echo "✓ PASS (6 lines)"
    ((PASSED++))
else
    echo "✗ FAIL (got $result, expected 6)"
    ((FAILED++))
fi

# Test 7: HTML block comments (<!-- ... -->)
echo -n "Test 7 - HTML block comments filtered: "
HTML_TEST="/tmp/grepnet_html_test.txt"
cat > "$HTML_TEST" << 'EOF'
<!-- HTML comment with 192.0.2.0 -->
192.0.2.1
<!--
  Multi-line HTML block
  with 192.0.2.2
-->
192.0.2.3
<config> 192.0.2.4 <!-- inline HTML comment --> </config>
192.0.2.5
EOF
result=$("$GREPNET" '0.0.0.0/0' "$HTML_TEST" 2>/dev/null | wc -l) || result=999
# Should get 4 lines (192.0.2.1, 192.0.2.3, 192.0.2.4 from inline, 192.0.2.5)
if [[ "$result" -eq 4 ]]; then
    echo "✓ PASS (4 lines)"
    ((PASSED++))
else
    echo "✗ FAIL (got $result, expected 4)"
    ((FAILED++))
fi

# Test 8: HTML block comments with --no-filter-comments
echo -n "Test 8 - HTML block comments not filtered: "
result=$("$GREPNET" --no-filter-comments=both '0.0.0.0/0' "$HTML_TEST" 2>/dev/null | wc -l) || result=999
# Should get 6 lines (HTML comment line, IP line, middle IP from multi-line, IP line, config line, IP line)
if [[ "$result" -eq 6 ]]; then
    echo "✓ PASS (6 lines)"
    ((PASSED++))
else
    echo "✗ FAIL (got $result, expected 6)"
    ((FAILED++))
fi

# Test 9: C-style block comments (/* ... */)
echo -n "Test 9 - C-style block comments filtered: "
CBLOCK_TEST="/tmp/grepnet_cblock_test.txt"
cat > "$CBLOCK_TEST" << 'EOF'
/* C-style block with 192.0.2.0 */
192.0.2.1
/*
 * Multi-line C block
 * with 192.0.2.2
 */
192.0.2.3
int ip = 192.0.2.4; /* inline C comment */ int x;
192.0.2.5
EOF
result=$("$GREPNET" '0.0.0.0/0' "$CBLOCK_TEST" 2>/dev/null | wc -l) || result=999
# Should get 4 lines
if [[ "$result" -eq 4 ]]; then
    echo "✓ PASS (4 lines)"
    ((PASSED++))
else
    echo "✗ FAIL (got $result, expected 4)"
    ((FAILED++))
fi

# Test 10: C-style block comments with --no-filter-comments
echo -n "Test 10 - C-style block comments not filtered: "
result=$("$GREPNET" --no-filter-comments=both '0.0.0.0/0' "$CBLOCK_TEST" 2>/dev/null | wc -l) || result=999
if [[ "$result" -eq 6 ]]; then
    echo "✓ PASS (6 lines)"
    ((PASSED++))
else
    echo "✗ FAIL (got $result, expected 6)"
    ((FAILED++))
fi

# Test 11: Mixed comment types in one file
echo -n "Test 11 - Mixed comment types filtered: "
MIXED_TEST="/tmp/grepnet_mixed_test.txt"
cat > "$MIXED_TEST" << 'EOF'
# Unix comment
-- SQL comment
// C-style comment
; INI comment
! Cisco comment
remark Cisco remark
192.0.2.1
<!-- HTML comment -->
192.0.2.2
/* C block comment */
192.0.2.3
EOF
result=$("$GREPNET" '0.0.0.0/0' "$MIXED_TEST" 2>/dev/null | wc -l) || result=999
# Should get only 3 IP lines
if [[ "$result" -eq 3 ]]; then
    echo "✓ PASS (3 lines)"
    ((PASSED++))
else
    echo "✗ FAIL (got $result, expected 3)"
    ((FAILED++))
fi

# Test 12: Mixed with --no-filter-comments
echo -n "Test 12 - Mixed comments not filtered: "
result=$("$GREPNET" --no-filter-comments=both '0.0.0.0/0' "$MIXED_TEST" 2>/dev/null | wc -l) || result=999
# Should get only the 3 IP lines (no IPs in comment lines, so unfiltering doesn't change output)
if [[ "$result" -eq 3 ]]; then
    echo "✓ PASS (3 lines)"
    ((PASSED++))
else
    echo "✗ FAIL (got $result, expected 3)"
    ((FAILED++))
fi

# Test 13: Non-comment special chars preserved (# in middle)
echo -n "Test 13 - Hash in middle preserved: "
SPECIAL_TEST="/tmp/grepnet_special_test.txt"
cat > "$SPECIAL_TEST" << 'EOF'
# Comment line
192.0.2.0/24#note
value#192.0.2.1
192.0.2.2
; Comment line
value;192.0.2.3
EOF
result=$("$GREPNET" '0.0.0.0/0' "$SPECIAL_TEST" 2>/dev/null | grep -c "192.0.2") || result=999
# Should get 4 matches
if [[ "$result" -eq 4 ]]; then
    echo "✓ PASS (4 matches)"
    ((PASSED++))
else
    echo "✗ FAIL (got $result, expected 4)"
    ((FAILED++))
fi

# Test 14: Whitespace requirements for inline comments
echo -n "Test 14 - Whitespace requirement for inline: "
WHITESPACE_TEST="/tmp/grepnet_whitespace_test.txt"
cat > "$WHITESPACE_TEST" << 'EOF'
192.0.2.1 # inline with space
192.0.2.2# no space before hash
192.0.2.3 -- inline SQL
192.0.2.4-- no space before SQL
192.0.2.5 // inline C-style
192.0.2.6// no space before C
192.0.2.7 ; inline INI
192.0.2.8; no space before semi
EOF
result=$("$GREPNET" '0.0.0.0/0' "$WHITESPACE_TEST" 2>/dev/null | wc -l) || result=999
# Should get all 8 lines (no-space versions not treated as comments)
if [[ "$result" -eq 8 ]]; then
    echo "✓ PASS (8 lines)"
    ((PASSED++))
else
    echo "✗ FAIL (got $result, expected 8)"
    ((FAILED++))
fi

# Test 15: Nested or consecutive block comments
echo -n "Test 15 - Block comment handling: "
BLOCK_NEST="/tmp/grepnet_block_nest.txt"
cat > "$BLOCK_NEST" << 'EOF'
192.0.2.1
/* First block with 192.0.2.99 */
192.0.2.2
/* Second block */ 192.0.2.3
192.0.2.4
<!-- HTML block with 192.0.2.99 -->
192.0.2.5
<!-- Another HTML --> 192.0.2.6
EOF
result=$("$GREPNET" '0.0.0.0/0' "$BLOCK_NEST" 2>/dev/null | wc -l) || result=999
# Should get 6 lines (1,2,3,4,5,6 - block comments removed, but inline 192.0.2.3 and 192.0.2.6 stay)
if [[ "$result" -eq 6 ]]; then
    echo "✓ PASS (6 lines)"
    ((PASSED++))
else
    echo "✗ FAIL (got $result, expected 6)"
    ((FAILED++))
fi

# Cleanup
rm -f "$SQL_TEST" "$CSTYLE_TEST" "$INI_TEST" "$HTML_TEST" "$CBLOCK_TEST" "$MIXED_TEST" "$SPECIAL_TEST" "$WHITESPACE_TEST" "$BLOCK_NEST"

echo ""
echo "=== Summary ==="
printf "PASSED: %d\nFAILED: %d\n" "$PASSED" "$FAILED"

# Exit with success if all tests passed
[[ "$FAILED" -eq 0 ]]
