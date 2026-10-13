#!/bin/bash

#############################################################################
# GREPNET TEST: Pattern File from Stdin (-f -)
#############################################################################

source "$TEST_LIB_DIR/lib_tests.sh"

log_header "PATTERN FILE FROM STDIN (-f -)"

# SPEC: Pattern file flag (-f -) should read patterns from stdin
# SPEC-REF: Unix convention (like grep): echo "pattern" | grep -f -
# ISSUE: Currently fails with "Cannot read pattern file -: No such file or directory"
test_case "Single pattern from stdin (-f -)" \
    "echo '192.0.2.0/24' | $GREPNET -f - '$TESTS_DIR/sample_networks.txt'" 0 \
    $'192.0.2.0/24\n192.0.2.0 255.255.255.0\n192.0.2.0 0.0.0.255\n192.0.2.0-192.0.2.255\nRoute to 192.0.2.0/24 via 10.0.0.0/8' \
    ""

# SPEC: Multiple patterns can be piped to -f -
# Each line in stdin becomes a separate pattern
test_case "Multiple patterns from stdin (-f -)" \
    "echo -e '192.0.2.0/24\n10.0.0.0/8' | $GREPNET -f - '$TESTS_DIR/sample_networks.txt'" 0 \
    $'192.0.2.0/24\n10.0.0.0/8\n192.0.2.0 255.255.255.0\n10.0.0.0 255.0.0.0\n192.0.2.0 0.0.0.255\n10.0.0.0 0.255.255.255\n192.0.2.0-192.0.2.255\n10.1.1.0-10.1.1.50\nRoute to 192.0.2.0/24 via 10.0.0.0/8' \
    ""

# SPEC: Comments in stdin patterns should be ignored (lines starting with #)
test_case "Patterns with comments from stdin (-f -)" \
    "echo -e '# Comment\n192.0.2.0/24\n# Another comment\n10.0.0.0/8' | $GREPNET -f - '$TESTS_DIR/sample_networks.txt'" 0 \
    $'192.0.2.0/24\n10.0.0.0/8\n192.0.2.0 255.255.255.0\n10.0.0.0 255.0.0.0\n192.0.2.0 0.0.0.255\n10.0.0.0 0.255.255.255\n192.0.2.0-192.0.2.255\n10.1.1.0-10.1.1.50\nRoute to 192.0.2.0/24 via 10.0.0.0/8' \
    ""

# SPEC: Empty lines in stdin patterns should be ignored
test_case "Patterns with empty lines from stdin (-f -)" \
    "echo -e '192.0.2.0/24\n\n10.0.0.0/8' | $GREPNET -f - '$TESTS_DIR/sample_networks.txt'" 0 \
    $'192.0.2.0/24\n10.0.0.0/8\n192.0.2.0 255.255.255.0\n10.0.0.0 255.0.0.0\n192.0.2.0 0.0.0.255\n10.0.0.0 0.255.255.255\n192.0.2.0-192.0.2.255\n10.1.1.0-10.1.1.50\nRoute to 192.0.2.0/24 via 10.0.0.0/8' \
    ""

# SPEC: No match from stdin patterns returns exit code 1
test_case "No match with stdin patterns (-f -)" \
    "echo '203.0.114.0/24' | $GREPNET -f - '$TESTS_DIR/sample_networks.txt'" 1 \
    "" \
    ""

# SPEC: Invalid pattern from stdin should exit with code 2 (error)
test_case "Invalid pattern from stdin (-f -)" \
    "echo 'not-a-valid-network' | $GREPNET -f - '$TESTS_DIR/sample_networks.txt'" 2 \
    "" \
    "grepnet: error: no patterns to search for"

# SPEC: Mixing -f - with file arguments (file is the input, not pattern source)
# After -f, all positional args are treated as input files
test_case "Pattern stdin with explicit file (-f -)" \
    "echo '10.0.0.0/8' | $GREPNET -f - '$TESTS_DIR/file1.txt'" 0 \
    $'10.0.0.0/8' \
    ""

# SPEC: -f - should work with multiple input files
test_case "Pattern stdin with multiple files (-f -)" \
    "echo '192.0.2.0/24' | $GREPNET -f - '$TESTS_DIR/file1.txt' '$TESTS_DIR/file2.txt'" 0 \
    "$TESTS_DIR/file2.txt:192.0.2.0/24" \
    ""

log_header "EXPLICIT FILE SPECIFICATION (-F)"

# SPEC: Explicit file specification (-F) with stdin patterns (-f -)
# -F FILE allows explicit file specification; can be used with -f - for patterns from stdin
test_case "Explicit file with stdin patterns (-F with -f -)" \
    "echo '10.0.0.0/8' | $GREPNET -f - -F '$TESTS_DIR/file1.txt'" 0 \
    $'10.0.0.0/8' \
    ""

# SPEC: Multiple explicit files with stdin patterns (-F repeated with -f -)
test_case "Multiple explicit files with stdin patterns (-F repeated with -f -)" \
    "echo '192.0.2.0/24' | $GREPNET -f - -F '$TESTS_DIR/file1.txt' -F '$TESTS_DIR/file2.txt'" 0 \
    "$TESTS_DIR/file2.txt:192.0.2.0/24" \
    ""

# SPEC: Mixing -F and positional file args (both should be processed)
test_case "Mixing -F and positional files (-F with positional)" \
    "echo '192.0.2.0/24' | $GREPNET -f - -F '$TESTS_DIR/file1.txt' '$TESTS_DIR/file2.txt'" 0 \
    "$TESTS_DIR/file2.txt:192.0.2.0/24" \
    ""

# SPEC: -F with pattern from regular argument (not from stdin)
# When not using -f -, positional args after pattern are input files
test_case "Explicit file specification with positional pattern (-F)" \
    "$GREPNET -F '$TESTS_DIR/file1.txt' '10.0.0.0/8'" 0 \
    $'10.0.0.0/8' \
    ""

# SPEC: Multiple -F flags accumulate input files
test_case "Multiple -F flags accumulate files" \
    "$GREPNET -F '$TESTS_DIR/file1.txt' -F '$TESTS_DIR/file2.txt' '192.0.2.0/24'" 0 \
    "$TESTS_DIR/file2.txt:192.0.2.0/24" \
    ""

