#!/bin/bash

#############################################################################
# GREPNET TEST: Grep Compatibility - Separator Behavior
# Tests to ensure grepnet matches standard grep behavior for separators
#############################################################################

source "$TEST_LIB_DIR/lib_tests.sh"

log_header "GREP COMPATIBILITY: SEPARATOR BEHAVIOR"

# Create test data file
cat > "$TESTS_DIR/grep_compat_test.txt" << 'EOF'
line1 192.0.2.0/24
line2
line3 10.0.0.0/8
EOF

# SPEC: Without context flags, no separator is printed between matches (matches grep behavior)
# SPEC-REF: GREPNET-SPEC.md - Context Lines: "Separator printed only when context flags are used"
expected_no_sep=$'line1 192.0.2.0/24\nline3 10.0.0.0/8'
test_case "Grep compat: No separator without context flags" \
    "$GREPNET '0.0.0.0/0' '$TESTS_DIR/grep_compat_test.txt'" 0 \
    "$expected_no_sep"

# SPEC: With -A0 (after-context zero), separator is printed between matches (grep compatibility)
# SPEC-REF: GREPNET-SPEC.md - Context Lines: "Even with -A0, separator appears between separate matches"
expected_sep=$'line1 192.0.2.0/24\n--\nline3 10.0.0.0/8'
test_case "Grep compat: Separator with -A0 flag" \
    "$GREPNET -A0 '0.0.0.0/0' '$TESTS_DIR/grep_compat_test.txt'" 0 \
    "$expected_sep"

# SPEC: With -B0 (before-context zero), separator is printed between matches (grep compatibility)
# SPEC-REF: GREPNET-SPEC.md - Context Lines: "Even with -B0, separator appears between separate matches"
test_case "Grep compat: Separator with -B0 flag" \
    "$GREPNET -B0 '0.0.0.0/0' '$TESTS_DIR/grep_compat_test.txt'" 0 \
    "$expected_sep"

# SPEC: With -C0 (context zero on both sides), separator is printed between matches (grep compatibility)
# SPEC-REF: GREPNET-SPEC.md - Context Lines: "Even with -C0, separator appears between separate matches"
test_case "Grep compat: Separator with -C0 flag" \
    "$GREPNET -C0 '0.0.0.0/0' '$TESTS_DIR/grep_compat_test.txt'" 0 \
    "$expected_sep"

# Multi-line block comment edge case from issue
cat > "$TESTS_DIR/grep_compat_multiline.txt" << 'EOF'
text 192.0.2.0 /*
 255.0.255.0
 */ text 192.0.2.10
EOF

# SPEC: Block comments spanning multiple lines are handled correctly with context flags
# SPEC-REF: GREPNET-SPEC.md - Comment Handling: "Block comment state tracked across lines"
# Note: By default, comments are filtered, so line 2 (entirely inside comment) doesn't match
# Only lines 1 and 3 match, producing two matches with separator
expected_multiline=$'text 192.0.2.0 /*\n--\n */ text 192.0.2.10'
test_case "Grep compat: Multi-line block comment with -A0" \
    "$GREPNET -A0 '0.0.0.0/0' '$TESTS_DIR/grep_compat_multiline.txt'" 0 \
    "$expected_multiline"

# No separator for single match even with context flags
cat > "$TESTS_DIR/grep_compat_single.txt" << 'EOF'
line1 192.0.2.0/24
line2
line3
EOF

# SPEC: When only one match is found, no separator is printed even with context flags
# SPEC-REF: GREPNET-SPEC.md - Context Lines: "Separator printed only between separate match groups"
test_case "Grep compat: No separator for single match with -A0" \
    "$GREPNET -A0 '0.0.0.0/0' '$TESTS_DIR/grep_compat_single.txt'" 0 \
    "line1 192.0.2.0/24"

# SPEC: Space-separated flag format (-A 0) works the same as combined format (-A0)
# SPEC-REF: GREPNET-SPEC.md - Command-Line Interface: "Flags accept both combined and space-separated argument formats"
expected_sep=$'line1 192.0.2.0/24\n--\nline3 10.0.0.0/8'
test_case "Grep compat: Separator with -A 0 (space-separated)" \
    "$GREPNET -A 0 '0.0.0.0/0' '$TESTS_DIR/grep_compat_test.txt'" 0 \
    "$expected_sep"

# SPEC: Long-format flags (--after-context=N) work the same as short flags (-AN)
# SPEC-REF: GREPNET-SPEC.md - Command-Line Interface: "Long flags supported for all options"
test_case "Grep compat: Separator with --after-context=0" \
    "$GREPNET --after-context=0 '0.0.0.0/0' '$TESTS_DIR/grep_compat_test.txt'" 0 \
    "$expected_sep"

log_footer "GREP COMPATIBILITY: SEPARATOR BEHAVIOR" 2>/dev/null || true
