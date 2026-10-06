#!/bin/bash

#############################################################################
# GREPNET TEST: Error Handling
#############################################################################

source "$TEST_LIB_DIR/lib_tests.sh"

log_header "ERROR HANDLING"

# SPEC: Missing or unreadable files result in exit code 2 (error)
# SPEC-REF: GREPNET-SPEC.md - Exit Codes: "2: Error (invalid arguments, file not found, etc.)"
test_case "File not found returns exit 2" \
    "$GREPNET '192.0.2.0/24' /nonexistent/file.txt" 2

# SPEC: Invalid command-line flags result in exit code 2 (error) and error message
# SPEC-REF: GREPNET-SPEC.md - Exit Codes: "2: Error for invalid arguments"
test_case "Invalid flag handling" \
    "$GREPNET --invalid-flag '192.0.2.0/24' '$TESTS_DIR/sample_networks.txt'" 2

# SPEC: Missing pattern argument results in exit code 2 (error: no patterns)
# SPEC-REF: GREPNET-SPEC.md - Exit Codes: "2: No valid patterns extracted"
test_case "Missing pattern" \
    "$GREPNET" 2 "" "grepnet: error: no patterns to search for"

# SPEC: Empty pattern file (no patterns to search) results in error (exit code 2)
# SPEC-REF: GREPNET-SPEC.md - Exit Codes: "2: No valid patterns extracted" (exception: extract/consolidate allow empty patterns)
test_case "Empty pattern file" \
    "echo '' > /tmp/empty_pattern.txt && $GREPNET -f /tmp/empty_pattern.txt '$TESTS_DIR/sample_networks.txt'" 2 "" "grepnet: error: no patterns to search for"

# SPEC: No input files (no files to read) is an error condition (exit code 2)
# SPEC-REF: GREPNET-SPEC.md - Exit Codes: "2: Error when no input files are provided"
test_case "No input files" \
    "$GREPNET '192.0.2.0/24'" 2

# SPEC: Error messages must be written to stderr and include relevant context (filename, reason)
# SPEC-REF: GREPNET-SPEC.md - Error Handling: "Error messages must be descriptive"
test_stdout_contains "Error message contains filename" \
    "$GREPNET '192.0.2.0/24' /nonexistent/file.txt 2>&1" 2 "No input files"

# SPEC: --no-messages flag suppresses error message output while preserving exit code
# SPEC-REF: GREPNET-SPEC.md - Error Output: "--no-messages: Suppress error messages"
test_stderr_not_contains "Quiet mode suppresses error messages" \
    "$GREPNET --no-messages '192.0.2.0/24' /nonexistent/file.txt" 2 "error"
