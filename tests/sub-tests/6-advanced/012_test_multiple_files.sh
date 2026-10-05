#!/bin/bash

#############################################################################
# GREPNET TEST: Multiple Files
#############################################################################

source "$TEST_LIB_DIR/lib_tests.sh"

log_header "MULTIPLE FILES"

# SPEC: grepnet searches multiple files; matching networks are found across all files
# SPEC-REF: GREPNET-SPEC.md - File Discovery and Scanning: "Process each file in sequence"
test_case "Search multiple files" \
    "$GREPNET '192.0.2.0/24' '$TESTS_DIR/file1.txt' '$TESTS_DIR/file2.txt'" 0 \
    $'/home/chains/dev/grepnet/tests/files/file2.txt:192.0.2.0/24' ""

# SPEC: When searching multiple files for the same pattern, matches from all files are included
# SPEC-REF: GREPNET-SPEC.md - File Discovery and Scanning: "Each file processed independently"
test_case "Multiple files with matches in all" \
    "$GREPNET '192.0.2.0/24' '$TESTS_DIR/file1.txt' '$TESTS_DIR/file2.txt' '$TESTS_DIR/file3.txt'" 0 \
    $'/home/chains/dev/grepnet/tests/files/file2.txt:192.0.2.0/24' ""

# SPEC: Filename prefix (format: filename:) is shown when searching multiple files
# SPEC-REF: GREPNET-SPEC.md - Output Control: "For multiple files, prefix each result with filename:"
test_case "Filename prefix for multiple files" \
    "$GREPNET '192.0.2.0/24' '$TESTS_DIR/file1.txt' '$TESTS_DIR/file2.txt' | grep ':'" 0 \
    $'/home/chains/dev/grepnet/tests/files/file2.txt:192.0.2.0/24' ""

# SPEC: --no-filename suppresses filename prefix even when searching multiple files
# SPEC-REF: GREPNET-SPEC.md - Output Control: "--no-filename: Never prefix filename"
test_case "Suppress filename (--no-filename)" \
    "$GREPNET --no-filename '192.0.2.0/24' '$TESTS_DIR/file1.txt' '$TESTS_DIR/file2.txt'" 0 \
    $'192.0.2.0/24' ""

# SPEC: -H forces filename prefix even when searching a single file
# SPEC-REF: GREPNET-SPEC.md - Output Control: "-H/--with-filename: Always prefix filename"
test_case "Force filename on single file (-H)" \
    "$GREPNET -H '192.0.2.0/24' '$TESTS_DIR/sample_networks.txt' | grep ':'" 0 \
    $'/home/chains/dev/grepnet/tests/files/sample_networks.txt:192.0.2.0/24\n/home/chains/dev/grepnet/tests/files/sample_networks.txt:192.0.2.0 255.255.255.0\n/home/chains/dev/grepnet/tests/files/sample_networks.txt:192.0.2.0 0.0.0.255\n/home/chains/dev/grepnet/tests/files/sample_networks.txt:192.0.2.0-192.0.2.255\n/home/chains/dev/grepnet/tests/files/sample_networks.txt:Route to 192.0.2.0/24 via 10.0.0.0/8' ""

# SPEC: Line numbers can be shown with multiple files; format includes filename:line:content
# SPEC-REF: GREPNET-SPEC.md - Output Control: "-n/--line-number: Print 1-based line number"
test_case "Multiple files with line numbers (-n)" \
    "$GREPNET -n '192.0.2.0/24' '$TESTS_DIR/file1.txt' '$TESTS_DIR/file2.txt'" 0 \
    $'/home/chains/dev/grepnet/tests/files/file2.txt:2:192.0.2.0/24' ""

# SPEC: Count mode (-c) shows counts per file when searching multiple files
# SPEC-REF: GREPNET-SPEC.md - Output Control: "-c/--count: Output count of matching lines (per file if multiple files)"
test_case "Multiple files with count (-c)" \
    "$GREPNET -c '192.0.2.0/24' '$TESTS_DIR/file1.txt' '$TESTS_DIR/file2.txt'" 0 \
    "/home/chains/dev/grepnet/tests/files/file2.txt:1" ""
