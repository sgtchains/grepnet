#!/bin/bash

#############################################################################
# GREPNET TEST: Output Control
#############################################################################

source "$TEST_LIB_DIR/lib_tests.sh"

log_header "OUTPUT CONTROL (-H, -l, -L, -c)"

# SPEC: With filename flag (-H) prepends the filename to each output line
# SPEC-REF: GREPNET-SPEC.md - Output Control: "With filename (-H): prepend filename to each output line"
test_case "With filename (-H)" \
    "$GREPNET -H '192.0.2.0/24' '$TESTS_DIR/sample_networks.txt'" 0 \
    $'/home/chains/dev/grepnet/tests/files/sample_networks.txt:192.0.2.0/24\n/home/chains/dev/grepnet/tests/files/sample_networks.txt:192.0.2.0 255.255.255.0\n/home/chains/dev/grepnet/tests/files/sample_networks.txt:192.0.2.0 0.0.0.255\n/home/chains/dev/grepnet/tests/files/sample_networks.txt:192.0.2.0-192.0.2.255\n/home/chains/dev/grepnet/tests/files/sample_networks.txt:Route to 192.0.2.0/24 via 10.0.0.0/8' ""

# SPEC: List files only (-l) shows only filenames that contain matches, one per line
# SPEC-REF: GREPNET-SPEC.md - Output Control: "List files only (-l): show filenames that contain matches"
test_case "List files only (-l)" \
    "$GREPNET -l '192.0.2.0/24' '$TESTS_DIR/file1.txt' '$TESTS_DIR/file2.txt'" 0 \
    $'/home/chains/dev/grepnet/tests/files/file2.txt' ""

# SPEC: Files without matches (-L) shows only filenames that do NOT contain matches
# SPEC-REF: GREPNET-SPEC.md - Output Control: "Files without matches (-L): show filenames that do not contain matches"
test_case "Files without matches (-L)" \
    "$GREPNET -L '192.0.2.0/24' '$TESTS_DIR/file1.txt' '$TESTS_DIR/file2.txt' '$TESTS_DIR/file3.txt'" 0 \
    $'/home/chains/dev/grepnet/tests/files/file1.txt\n/home/chains/dev/grepnet/tests/files/file3.txt' ""

# SPEC: Count matches (-c) shows count of matching networks (similar to grep -c)
# SPEC-REF: GREPNET-SPEC.md - Output Control: "Count matches (-c): show count of matching lines"
test_case "Count matches (-c)" \
    "$GREPNET -c '192.168.0.0/16' '$TESTS_DIR/file1.txt'" 0 \
    $'2' ""

# SPEC: Count matches with multiple files shows filename prefix with count for each file
# SPEC-REF: GREPNET-SPEC.md - Output Control: "Count matches (-c): show count of matching lines"
test_case "Multiple files count" \
    "$GREPNET -c '192.0.2.0/24' '$TESTS_DIR/file1.txt' '$TESTS_DIR/file2.txt'" 0 \
    $'/home/chains/dev/grepnet/tests/files/file2.txt:1' ""

# SPEC: No filename prefix should appear when processing a single file without -H flag
# SPEC-REF: GREPNET-SPEC.md - Output Control: "With single file and no -H: no filename prefix"
test_case "No filename prefix (single file)" \
    "$GREPNET '192.0.2.0/24' '$TESTS_DIR/sample_networks.txt' | grep -v '.*:'" 0 $'192.0.2.0/24\n192.0.2.0 255.255.255.0\n192.0.2.0 0.0.0.255\n192.0.2.0-192.0.2.255\nRoute to 192.0.2.0/24 via 10.0.0.0/8' ""

# SPEC: Force filename on single file (-H) should add filename prefix even for single files
# SPEC-REF: GREPNET-SPEC.md - Output Control: "With filename (-H): prepend filename to each output line"
test_case "Force filename on single file (-H)" \
    "$GREPNET -H '192.0.2.0/24' '$TESTS_DIR/sample_networks.txt' | grep ':'" 0 $'/home/chains/dev/grepnet/tests/files/sample_networks.txt:192.0.2.0/24\n/home/chains/dev/grepnet/tests/files/sample_networks.txt:192.0.2.0 255.255.255.0\n/home/chains/dev/grepnet/tests/files/sample_networks.txt:192.0.2.0 0.0.0.255\n/home/chains/dev/grepnet/tests/files/sample_networks.txt:192.0.2.0-192.0.2.255\n/home/chains/dev/grepnet/tests/files/sample_networks.txt:Route to 192.0.2.0/24 via 10.0.0.0/8' ""

# SPEC: Suppress filename flag (--no-filename) removes filename prefix even with multiple files
# SPEC-REF: GREPNET-SPEC.md - Output Control: "Suppress filename (--no-filename): remove filename prefix"
test_case "Suppress filename (--no-filename)" \
    "$GREPNET --no-filename '192.0.2.0/24' '$TESTS_DIR/file1.txt' '$TESTS_DIR/file2.txt'" 0 $'192.0.2.0/24' ""
