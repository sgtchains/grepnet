#!/bin/bash

#############################################################################
# GREPNET TEST LIBRARY
# Provides standardized testing functions for all test suites
#############################################################################

# Configuration variables (set by run_tests.sh)
: "${GREPNET:=/home/chains/dev/grepnet/grepnet}"
: "${TESTS_DIR:=$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd .. && pwd)/files}"
: "${RESULTS_FILE:=$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd .. && pwd)/log/test_results.log}"
: "${VERBOSE:=0}"
: "${TEST_TIMEOUT:=5}"  # Default timeout in seconds per test

# Test counters
PASSED_TESTS=0
FAILED_TESTS=0
SKIPPED_TESTS=0
TIMEOUT_TESTS=0

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

#############################################################################
# Core Logging Functions
#############################################################################

log_header() {
    local text="$1"
    echo -e "\n${BLUE}=== $text ===${NC}" | tee -a "$RESULTS_FILE"
}

log_info() {
    local text="$1"
    echo -e "${CYAN}ℹ $text${NC}" | tee -a "$RESULTS_FILE"
}

log_debug() {
    if [ "$VERBOSE" -eq 1 ]; then
        echo -e "${YELLOW}DEBUG: $1${NC}" | tee -a "$RESULTS_FILE"
    fi
}

log_raw() {
    local text="$1"
    echo "$text" | tee -a "$RESULTS_FILE"
}

#############################################################################
# Test Result Functions
#############################################################################

test_pass() {
    local name="$1"
    echo -e "${GREEN}✓ PASS${NC}: $name" | tee -a "$RESULTS_FILE"
    ((PASSED_TESTS++))
}

test_fail() {
    local name="$1"
    echo -e "${RED}✗ FAIL${NC}: $name" | tee -a "$RESULTS_FILE"
    ((FAILED_TESTS++))
}

test_skip() {
    local name="$1"
    local reason="${2:-No reason provided}"
    echo -e "${YELLOW}⊘ SKIP${NC}: $name ($reason)" | tee -a "$RESULTS_FILE"
    ((SKIPPED_TESTS++))
}

test_timeout() {
    local name="$1"
    echo -e "${RED}⏱ TIMEOUT${NC}: $name (exceeded ${TEST_TIMEOUT}s)" | tee -a "$RESULTS_FILE"
    ((TIMEOUT_TESTS++))
}

#############################################################################
# Timeout Execution Helper
#############################################################################

# run_with_timeout: Execute command with timeout
# Usage: run_with_timeout timeout_seconds "command"
# Returns: 0 on success, 124 on timeout, other codes from command
run_with_timeout() {
    local timeout_secs="$1"
    shift
    local command="$@"
    
    # Use timeout command if available, otherwise try with bash background
    if command -v timeout &> /dev/null; then
        timeout "$timeout_secs" bash -c "$command"
        return $?
    else
        # Fallback: run in background with manual timeout
        bash -c "$command" &
        local pid=$!
        local count=0
        
        while kill -0 $pid 2>/dev/null; do
            if [ $count -ge $timeout_secs ]; then
                kill -9 $pid 2>/dev/null
                return 124
            fi
            sleep 1
            ((count++))
        done
        
        wait $pid
        return $?
    fi
}

# run_command_captured: Execute command and capture stdout, stderr, and exit code separately
# Usage: run_command_captured "command" [timeout_seconds]
# Sets global variables: CMD_STDOUT, CMD_STDERR, CMD_EXIT
run_command_captured() {
    local command="$1"
    local timeout_secs="${2:-$TEST_TIMEOUT}"
    
    local tmpout=$(mktemp)
    local tmperr=$(mktemp)
    local tmpcode=$(mktemp)
    
    # Execute command with timeout, capturing stdout and stderr separately
    # Pass command directly to bash -c (no eval needed, bash -c already interprets as shell code)
    (
        timeout "$timeout_secs" bash -c "$command" >>"$tmpout" 2>>"$tmperr"
        echo $? > "$tmpcode"
    ) || true
    
    # Read captured outputs
    CMD_STDOUT=$(cat "$tmpout" 2>/dev/null || echo "")
    CMD_STDERR=$(cat "$tmperr" 2>/dev/null || echo "")
    CMD_EXIT=$(cat "$tmpcode" 2>/dev/null || echo "124")
    
    # Check for timeout
    if [ "$CMD_EXIT" = "124" ]; then
        CMD_EXIT=124
        CMD_STDERR="${CMD_STDERR}[TIMEOUT after ${timeout_secs}s]"
    fi
    
    # Cleanup
    rm -f "$tmpout" "$tmperr" "$tmpcode"
}

# validate_exit_code: Check if actual exit code matches expected
# Usage: validate_exit_code expected_code actual_code "test_name"
validate_exit_code() {
    local expected="$1"
    local actual="$2"
    local name="$3"
    
    if [ "$actual" -eq "$expected" ]; then
        log_debug "Exit code OK: $actual"
        return 0
    else
        echo "Exit code mismatch: Expected $expected, Got $actual" | tee -a "$RESULTS_FILE"
        return 1
    fi
}

# validate_stdout_contains: Check if stdout contains string
# Usage: validate_stdout_contains "stdout_content" "search_string" "test_name"
validate_stdout_contains() {
    local stdout="$1"
    local search="$2"
    local name="$3"
    
    if echo "$stdout" | grep -q "$search"; then
        log_debug "STDOUT contains: $search"
        return 0
    else
        echo "STDOUT does not contain: $search" | tee -a "$RESULTS_FILE"
        echo "STDOUT was: $stdout" | tee -a "$RESULTS_FILE"
        return 1
    fi
}

# validate_stdout_not_contains: Check if stdout does NOT contain string
# Usage: validate_stdout_not_contains "stdout_content" "search_string" "test_name"
validate_stdout_not_contains() {
    local stdout="$1"
    local search="$2"
    local name="$3"
    
    if ! echo "$stdout" | grep -q "$search"; then
        log_debug "STDOUT does not contain (as expected): $search"
        return 0
    else
        echo "STDOUT contains (should not): $search" | tee -a "$RESULTS_FILE"
        echo "STDOUT was: $stdout" | tee -a "$RESULTS_FILE"
        return 1
    fi
}

# validate_stderr_contains: Check if stderr contains string
# Usage: validate_stderr_contains "stderr_content" "search_string" "test_name"
validate_stderr_contains() {
    local stderr="$1"
    local search="$2"
    local name="$3"
    
    if echo "$stderr" | grep -q "$search"; then
        log_debug "STDERR contains: $search"
        return 0
    else
        echo "STDERR does not contain: $search" | tee -a "$RESULTS_FILE"
        echo "STDERR was: $stderr" | tee -a "$RESULTS_FILE"
        return 1
    fi
}

# validate_stderr_not_contains: Check if stderr does NOT contain string
# Usage: validate_stderr_not_contains "stderr_content" "search_string" "test_name"
validate_stderr_not_contains() {
    local stderr="$1"
    local search="$2"
    local name="$3"
    
    if ! echo "$stderr" | grep -q "$search"; then
        log_debug "STDERR does not contain (as expected): $search"
        return 0
    else
        echo "STDERR contains (should not): $search" | tee -a "$RESULTS_FILE"
        echo "STDERR was: $stderr" | tee -a "$RESULTS_FILE"
        return 1
    fi
}

# validate_stdout_line_count: Check line count in stdout
# Usage: validate_stdout_line_count "stdout_content" expected_lines "test_name"
validate_stdout_line_count() {
    local stdout="$1"
    local expected="$2"
    local name="$3"
    
    local actual=$(echo "$stdout" | wc -l)
    if [ "$actual" -eq "$expected" ]; then
        log_debug "STDOUT line count OK: $actual"
        return 0
    else
        echo "STDOUT line count mismatch: Expected $expected, Got $actual" | tee -a "$RESULTS_FILE"
        return 1
    fi
}

#############################################################################
# Byte-Per-Byte Hexdump Validation Functions
#############################################################################

# compare_bytes_hexdump: Compare two strings byte-per-byte using hexdump
# Usage: compare_bytes_hexdump "expected" "actual" "stream_name" (stream_name = "STDOUT" or "STDERR")
# Returns: 0 if identical, 1 if different
compare_bytes_hexdump() {
    local expected="$1"
    local actual="$2"
    local stream_name="$3"
    
    # Create temporary files for hexdumps
    local expected_hex=$(mktemp)
    local actual_hex=$(mktemp)
    
    # Generate hexdumps
    echo -n "$expected" | hexdump -C > "$expected_hex"
    echo -n "$actual" | hexdump -C > "$actual_hex"
    
    # Compare hexdumps
    if ! diff -u "$expected_hex" "$actual_hex" > /dev/null 2>&1; then
        echo "$stream_name byte-per-byte mismatch (hexdump):" | tee -a "$RESULTS_FILE"
        echo "=== Expected $stream_name (hexdump) ===" | tee -a "$RESULTS_FILE"
        cat "$expected_hex" | tee -a "$RESULTS_FILE"
        echo "=== Actual $stream_name (hexdump) ===" | tee -a "$RESULTS_FILE"
        cat "$actual_hex" | tee -a "$RESULTS_FILE"
        echo "=== Hexdump Diff ===" | tee -a "$RESULTS_FILE"
        diff -u "$expected_hex" "$actual_hex" | tee -a "$RESULTS_FILE"
        
        # Also show as text for readability
        echo "=== Expected $stream_name (text) ===" | tee -a "$RESULTS_FILE"
        echo "$expected" | tee -a "$RESULTS_FILE"
        echo "=== Actual $stream_name (text) ===" | tee -a "$RESULTS_FILE"
        echo "$actual" | tee -a "$RESULTS_FILE"
        
        rm -f "$expected_hex" "$actual_hex"
        return 1
    fi
    
    log_debug "$stream_name byte-per-byte match verified (hexdump)"
    rm -f "$expected_hex" "$actual_hex"
    return 0
}

# test_case_strict: Execute command and validate exit code, ENTIRE stdout, and ENTIRE stderr (byte-per-byte with hexdump)
# Usage: test_case_strict "Test name" "command" expected_exit_code expected_stdout expected_stderr [timeout_seconds]
# Validates: Complete exit code, stdout (byte-per-byte), and stderr (byte-per-byte) with hexdump verification
test_case_strict() {
    local name="$1"
    local command="$2"
    local expected_exit="$3"
    local expected_stdout="$4"
    local expected_stderr="${5:-}"
    local timeout_secs="${6:-$TEST_TIMEOUT}"
    
    echo -e "\n${YELLOW}Testing: $name${NC}" | tee -a "$RESULTS_FILE"
    # Always output the human-readable command for manual verification
    local display_command="$command"
    # Replace full paths with relative paths for readability
    display_command="${display_command//\/home\/chains\/dev\/grepnet\/grepnet/../grepnet}"
    display_command="${display_command//\/home\/chains\/dev\/grepnet\/tests\/files\//files/}"
    echo -e "\n${CYAN}$display_command${NC}" | tee -a "$RESULTS_FILE"
    log_debug "Command: $command (timeout: ${timeout_secs}s)"
    
    # Execute command with timeout and capture all outputs
    run_command_captured "$command" "$timeout_secs"
    
    # Check for timeout
    if [ "$CMD_EXIT" -eq 124 ]; then
        log_raw "Command timed out after ${timeout_secs}s"
        test_timeout "$name"
        return 1
    fi
    
    local all_ok=1
    
    # Validate exit code
    if [ "$CMD_EXIT" -ne "$expected_exit" ]; then
        echo "Exit code mismatch: Expected $expected_exit, Got $CMD_EXIT" | tee -a "$RESULTS_FILE"
        all_ok=0
    fi
    
    # Validate stdout byte-per-byte with hexdump
    if ! compare_bytes_hexdump "$expected_stdout" "$CMD_STDOUT" "STDOUT"; then
        all_ok=0
    fi
    
    # Validate stderr byte-per-byte with hexdump
    if ! compare_bytes_hexdump "$expected_stderr" "$CMD_STDERR" "STDERR"; then
        all_ok=0
    fi
    
    if [ "$all_ok" -eq 1 ]; then
        test_pass "$name"
        return 0
    else
        test_fail "$name"
        return 1
    fi
}

#############################################################################
# Main Test Execution Functions
#############################################################################

# test_case: Execute command and validate exit code, stdout (byte-per-byte), and stderr (byte-per-byte)
# Usage: test_case "Test name" "command" expected_exit_code expected_stdout [expected_stderr] [timeout_seconds]
# Validates: Complete exit code, stdout (byte-per-byte with hexdump), stderr (byte-per-byte with hexdump)
# NOTE: This now does FULL byte-per-byte comparison for ALL tests
test_case() {
    local name="$1"
    local command="$2"
    local expected_exit="$3"
    local expected_stdout="$4"
    local expected_stderr="${5:-}"
    local timeout_secs="${6:-$TEST_TIMEOUT}"
    
    echo -e "\n${YELLOW}Testing: $name${NC}" | tee -a "$RESULTS_FILE"
    # Always output the human-readable command for manual verification
    local display_command="$command"
    # Replace full paths with relative paths for readability
    display_command="${display_command//\/home\/chains\/dev\/grepnet\/grepnet/../grepnet}"
    display_command="${display_command//\/home\/chains\/dev\/grepnet\/tests\/files\//files/}"
    echo -e "\n${CYAN}$display_command${NC}" | tee -a "$RESULTS_FILE"
    log_debug "Command: $command (timeout: ${timeout_secs}s)"
    
    # Execute command with timeout and capture all outputs
    run_command_captured "$command" "$timeout_secs"
    
    # Check for timeout
    if [ "$CMD_EXIT" -eq 124 ]; then
        log_raw "Command timed out after ${timeout_secs}s"
        test_timeout "$name"
        return 1
    fi
    
    local all_ok=1
    
    # Validate exit code
    if [ "$CMD_EXIT" -ne "$expected_exit" ]; then
        echo "Exit code mismatch: Expected $expected_exit, Got $CMD_EXIT" | tee -a "$RESULTS_FILE"
        all_ok=0
    fi
    
    # Validate stdout byte-per-byte with hexdump
    if ! compare_bytes_hexdump "$expected_stdout" "$CMD_STDOUT" "STDOUT"; then
        all_ok=0
    fi
    
    # Validate stderr byte-per-byte with hexdump (if expected_stderr provided)
    if [ -n "$expected_stderr" ] || [ ${#@} -ge 5 ]; then
        if ! compare_bytes_hexdump "$expected_stderr" "$CMD_STDERR" "STDERR"; then
            all_ok=0
        fi
    fi
    
    if [ "$all_ok" -eq 1 ]; then
        [ "$VERBOSE" -eq 1 ] && log_raw "Output bytes verified via hexdump"
        test_pass "$name (exit: $CMD_EXIT)"
        return 0
    else
        test_fail "$name"
        return 1
    fi
}

# test_full_output: Execute command and validate exit code, ENTIRE stdout, and ENTIRE stderr
# Usage: test_full_output "Test name" "command" expected_exit_code expected_stdout expected_stderr [timeout_seconds]
# Validates: Complete exit code, stdout, and stderr output
test_full_output() {
    local name="$1"
    local command="$2"
    local expected_exit="$3"
    local expected_stdout="$4"
    local expected_stderr="$5"
    local timeout_secs="${6:-$TEST_TIMEOUT}"
    
    echo -e "\n${YELLOW}Testing: $name${NC}" | tee -a "$RESULTS_FILE"
    # Always output the human-readable command for manual verification
    local display_command="$command"
    # Replace full paths with relative paths for readability
    display_command="${display_command//\/home\/chains\/dev\/grepnet\/grepnet/../grepnet}"
    display_command="${display_command//\/home\/chains\/dev\/grepnet\/tests\/files\//files/}"
    echo -e "\n${CYAN}$display_command${NC}" | tee -a "$RESULTS_FILE"
    log_debug "Command: $command (timeout: ${timeout_secs}s)"
    
    # Execute command with timeout and capture all outputs
    run_command_captured "$command" "$timeout_secs"
    
    # Check for timeout
    if [ "$CMD_EXIT" -eq 124 ]; then
        log_raw "Command timed out after ${timeout_secs}s"
        test_timeout "$name"
        return 1
    fi
    
    local all_ok=1
    
    # Validate exit code
    if [ "$CMD_EXIT" -ne "$expected_exit" ]; then
        echo "Exit code mismatch: Expected $expected_exit, Got $CMD_EXIT" | tee -a "$RESULTS_FILE"
        all_ok=0
    fi
    
    # Validate stdout
    if [ "$CMD_STDOUT" != "$expected_stdout" ]; then
        echo "STDOUT mismatch:" | tee -a "$RESULTS_FILE"
        echo "Expected:" | tee -a "$RESULTS_FILE"
        echo "$expected_stdout" | tee -a "$RESULTS_FILE"
        echo "Got:" | tee -a "$RESULTS_FILE"
        echo "$CMD_STDOUT" | tee -a "$RESULTS_FILE"
        all_ok=0
    fi
    
    # Validate stderr
    if [ "$CMD_STDERR" != "$expected_stderr" ]; then
        echo "STDERR mismatch:" | tee -a "$RESULTS_FILE"
        echo "Expected:" | tee -a "$RESULTS_FILE"
        echo "$expected_stderr" | tee -a "$RESULTS_FILE"
        echo "Got:" | tee -a "$RESULTS_FILE"
        echo "$CMD_STDERR" | tee -a "$RESULTS_FILE"
        all_ok=0
    fi
    
    if [ "$all_ok" -eq 1 ]; then
        test_pass "$name"
        return 0
    else
        test_fail "$name"
        return 1
    fi
}

# test_output_matches_regex: Execute and validate exit code, stdout matches regex, stderr matches regex
# Usage: test_output_matches_regex "Test name" "command" expected_exit_code stdout_regex stderr_regex [timeout_seconds]
test_output_matches_regex() {
    local name="$1"
    local command="$2"
    local expected_exit="$3"
    local stdout_regex="$4"
    local stderr_regex="$5"
    local timeout_secs="${6:-$TEST_TIMEOUT}"
    
    echo -e "\n${YELLOW}Testing: $name${NC}" | tee -a "$RESULTS_FILE"
    # Always output the human-readable command for manual verification
    local display_command="$command"
    # Replace full paths with relative paths for readability
    display_command="${display_command//\/home\/chains\/dev\/grepnet/grepnet/../grepnet}"
    display_command="${display_command//\/home\/chains\/dev\/grepnet\/tests\/files/files}"
    echo -e "\n${CYAN}$display_command${NC}" | tee -a "$RESULTS_FILE"
    log_debug "Command: $command (timeout: ${timeout_secs}s)"
    
    # Execute command with timeout and capture all outputs
    run_command_captured "$command" "$timeout_secs"
    
    # Check for timeout
    if [ "$CMD_EXIT" -eq 124 ]; then
        log_raw "Command timed out after ${timeout_secs}s"
        test_timeout "$name"
        return 1
    fi
    
    local all_ok=1
    
    # Validate exit code
    if [ "$CMD_EXIT" -ne "$expected_exit" ]; then
        echo "Exit code mismatch: Expected $expected_exit, Got $CMD_EXIT" | tee -a "$RESULTS_FILE"
        all_ok=0
    fi
    
    # Validate stdout regex
    if [ -n "$stdout_regex" ] && ! echo "$CMD_STDOUT" | grep -E "$stdout_regex" > /dev/null; then
        echo "STDOUT does not match regex: $stdout_regex" | tee -a "$RESULTS_FILE"
        echo "STDOUT was:" | tee -a "$RESULTS_FILE"
        echo "$CMD_STDOUT" | tee -a "$RESULTS_FILE"
        all_ok=0
    fi
    
    # Validate stderr regex
    if [ -n "$stderr_regex" ] && ! echo "$CMD_STDERR" | grep -E "$stderr_regex" > /dev/null; then
        echo "STDERR does not match regex: $stderr_regex" | tee -a "$RESULTS_FILE"
        echo "STDERR was:" | tee -a "$RESULTS_FILE"
        echo "$CMD_STDERR" | tee -a "$RESULTS_FILE"
        all_ok=0
    fi
    
    if [ "$all_ok" -eq 1 ]; then
        test_pass "$name"
        return 0
    else
        test_fail "$name"
        return 1
    fi
}

# test_stdout_contains: Execute and validate exit code + stdout contains string
# Usage: test_stdout_contains "Test name" "command" expected_exit_code "search_string" [timeout_seconds]
test_stdout_contains() {
    local name="$1"
    local command="$2"
    local expected_exit="$3"
    local search_string="$4"
    local timeout_secs="${5:-$TEST_TIMEOUT}"
    
    echo -e "\n${YELLOW}Testing: $name${NC}" | tee -a "$RESULTS_FILE"
    log_debug "Command: $command (timeout: ${timeout_secs}s)"
    log_debug "Searching STDOUT for: $search_string"
    
    # Execute command with timeout
    run_command_captured "$command" "$timeout_secs"
    
    # Check for timeout
    if [ "$CMD_EXIT" -eq 124 ]; then
        log_raw "Command timed out after ${timeout_secs}s"
        test_timeout "$name"
        return 1
    fi
    
    local all_ok=1
    
    # Validate exit code
    if [ "$CMD_EXIT" -ne "$expected_exit" ]; then
        echo "Exit code mismatch: Expected $expected_exit, Got $CMD_EXIT" | tee -a "$RESULTS_FILE"
        all_ok=0
    fi
    
    # Validate stdout contains string
    if ! echo "$CMD_STDOUT" | grep -q "$search_string"; then
        echo "String not found in STDOUT: $search_string" | tee -a "$RESULTS_FILE"
        echo "Full STDOUT was:" | tee -a "$RESULTS_FILE"
        echo "$CMD_STDOUT" | tee -a "$RESULTS_FILE"
        all_ok=0
    fi
    
    if [ "$all_ok" -eq 1 ]; then
        test_pass "$name"
        return 0
    else
        test_fail "$name"
        return 1
    fi
}

# test_stdout_not_contains: Execute and validate exit code + stdout does NOT contain string
# Usage: test_stdout_not_contains "Test name" "command" expected_exit_code "search_string" [timeout_seconds]
test_stdout_not_contains() {
    local name="$1"
    local command="$2"
    local expected_exit="$3"
    local search_string="$4"
    local timeout_secs="${5:-$TEST_TIMEOUT}"
    
    echo -e "\n${YELLOW}Testing: $name${NC}" | tee -a "$RESULTS_FILE"
    log_debug "Command: $command (timeout: ${timeout_secs}s)"
    log_debug "Verifying STDOUT does NOT contain: $search_string"
    
    # Execute command with timeout
    run_command_captured "$command" "$timeout_secs"
    
    # Check for timeout
    if [ "$CMD_EXIT" -eq 124 ]; then
        log_raw "Command timed out after ${timeout_secs}s"
        test_timeout "$name"
        return 1
    fi
    
    local all_ok=1
    
    # Validate exit code
    if [ "$CMD_EXIT" -ne "$expected_exit" ]; then
        echo "Exit code mismatch: Expected $expected_exit, Got $CMD_EXIT" | tee -a "$RESULTS_FILE"
        all_ok=0
    fi
    
    # Validate stdout does NOT contain string
    if echo "$CMD_STDOUT" | grep -q "$search_string"; then
        echo "String found in STDOUT (should not be): $search_string" | tee -a "$RESULTS_FILE"
        echo "Full STDOUT was:" | tee -a "$RESULTS_FILE"
        echo "$CMD_STDOUT" | tee -a "$RESULTS_FILE"
        all_ok=0
    fi
    
    if [ "$all_ok" -eq 1 ]; then
        test_pass "$name"
        return 0
    else
        test_fail "$name"
        return 1
    fi
}

# test_stderr_contains: Execute and validate exit code + stderr contains string
# Usage: test_stderr_contains "Test name" "command" expected_exit_code "search_string" [timeout_seconds]
test_stderr_contains() {
    local name="$1"
    local command="$2"
    local expected_exit="$3"
    local search_string="$4"
    local timeout_secs="${5:-$TEST_TIMEOUT}"
    
    echo -e "\n${YELLOW}Testing: $name${NC}" | tee -a "$RESULTS_FILE"
    log_debug "Command: $command (timeout: ${timeout_secs}s)"
    log_debug "Searching STDERR for: $search_string"
    
    # Execute command with timeout
    run_command_captured "$command" "$timeout_secs"
    
    # Check for timeout
    if [ "$CMD_EXIT" -eq 124 ]; then
        log_raw "Command timed out after ${timeout_secs}s"
        test_timeout "$name"
        return 1
    fi
    
    local all_ok=1
    
    # Validate exit code
    if [ "$CMD_EXIT" -ne "$expected_exit" ]; then
        echo "Exit code mismatch: Expected $expected_exit, Got $CMD_EXIT" | tee -a "$RESULTS_FILE"
        all_ok=0
    fi
    
    # Validate stderr contains string
    if ! echo "$CMD_STDERR" | grep -q "$search_string"; then
        echo "String not found in STDERR: $search_string" | tee -a "$RESULTS_FILE"
        echo "Full STDERR was:" | tee -a "$RESULTS_FILE"
        echo "$CMD_STDERR" | tee -a "$RESULTS_FILE"
        all_ok=0
    fi
    
    if [ "$all_ok" -eq 1 ]; then
        test_pass "$name"
        return 0
    else
        test_fail "$name"
        return 1
    fi
}

# test_stderr_not_contains: Execute and validate exit code + stderr does NOT contain string
# Usage: test_stderr_not_contains "Test name" "command" expected_exit_code "search_string" [timeout_seconds]
test_stderr_not_contains() {
    local name="$1"
    local command="$2"
    local expected_exit="$3"
    local search_string="$4"
    local timeout_secs="${5:-$TEST_TIMEOUT}"
    
    echo -e "\n${YELLOW}Testing: $name${NC}" | tee -a "$RESULTS_FILE"
    log_debug "Command: $command (timeout: ${timeout_secs}s)"
    log_debug "Verifying STDERR does NOT contain: $search_string"
    
    # Execute command with timeout
    run_command_captured "$command" "$timeout_secs"
    
    # Check for timeout
    if [ "$CMD_EXIT" -eq 124 ]; then
        log_raw "Command timed out after ${timeout_secs}s"
        test_timeout "$name"
        return 1
    fi
    
    local all_ok=1
    
    # Validate exit code
    if [ "$CMD_EXIT" -ne "$expected_exit" ]; then
        echo "Exit code mismatch: Expected $expected_exit, Got $CMD_EXIT" | tee -a "$RESULTS_FILE"
        all_ok=0
    fi
    
    # Validate stderr does NOT contain string
    if echo "$CMD_STDERR" | grep -q "$search_string"; then
        echo "String found in STDERR (should not be): $search_string" | tee -a "$RESULTS_FILE"
        echo "Full STDERR was:" | tee -a "$RESULTS_FILE"
        echo "$CMD_STDERR" | tee -a "$RESULTS_FILE"
        all_ok=0
    fi
    
    if [ "$all_ok" -eq 1 ]; then
        test_pass "$name"
        return 0
    else
        test_fail "$name"
        return 1
    fi
}

# test_file_exists: Verify a file exists and is readable
# Usage: test_file_exists "Test name" "/path/to/file"
test_file_exists() {
    local name="$1"
    local filepath="$2"
    
    echo -e "\n${YELLOW}Testing: $name${NC}" | tee -a "$RESULTS_FILE"
    log_debug "Checking file: $filepath"
    
    if [ -f "$filepath" ] && [ -r "$filepath" ]; then
        test_pass "$name"
        return 0
    else
        echo "File not found or not readable: $filepath" | tee -a "$RESULTS_FILE"
        test_fail "$name"
        return 1
    fi
}

# test_grepnet_installed: Verify grepnet binary exists and is executable
# Usage: test_grepnet_installed
test_grepnet_installed() {
    echo -e "\n${YELLOW}Verifying grepnet installation${NC}" | tee -a "$RESULTS_FILE"
    log_debug "Looking for: $GREPNET"
    
    if [ ! -f "$GREPNET" ]; then
        echo "ERROR: grepnet binary not found at: $GREPNET" | tee -a "$RESULTS_FILE"
        test_fail "grepnet installation"
        return 1
    fi
    
    if [ ! -x "$GREPNET" ]; then
        echo "ERROR: grepnet is not executable: $GREPNET" | tee -a "$RESULTS_FILE"
        test_fail "grepnet executable"
        return 1
    fi
    
    test_pass "grepnet installation"
    
    # Show version
    local version
    version=$("$GREPNET" --version 2>&1 || echo "version unknown")
    log_info "grepnet: $version"
    
    return 0
}

#############################################################################
# Setup and Teardown
#############################################################################

# setup_test_environment: Create test data directory if needed
setup_test_environment() {
    log_info "Setting up test environment..."
    
    if [ ! -d "$TESTS_DIR" ]; then
        mkdir -p "$TESTS_DIR"
        log_info "Created tests directory: $TESTS_DIR"
    fi
    
    # Clear results file
    > "$RESULTS_FILE"
    
    return 0
}

# get_test_summary: Print test summary statistics
get_test_summary() {
    local total=$((PASSED_TESTS + FAILED_TESTS + SKIPPED_TESTS + TIMEOUT_TESTS))
    
    echo -e "\n${BLUE}========================================${NC}" | tee -a "$RESULTS_FILE"
    echo -e "${BLUE}TEST SUMMARY${NC}" | tee -a "$RESULTS_FILE"
    echo -e "${BLUE}========================================${NC}" | tee -a "$RESULTS_FILE"
    echo -e "${GREEN}Passed:  $PASSED_TESTS${NC}" | tee -a "$RESULTS_FILE"
    echo -e "${RED}Failed:  $FAILED_TESTS${NC}" | tee -a "$RESULTS_FILE"
    echo -e "${RED}Timeout: $TIMEOUT_TESTS${NC}" | tee -a "$RESULTS_FILE"
    echo -e "${YELLOW}Skipped: $SKIPPED_TESTS${NC}" | tee -a "$RESULTS_FILE"
    echo -e "${CYAN}Total:   $total${NC}" | tee -a "$RESULTS_FILE"
    echo -e "${BLUE}========================================${NC}" | tee -a "$RESULTS_FILE"
    
    if [ "$FAILED_TESTS" -gt 0 ] || [ "$TIMEOUT_TESTS" -gt 0 ]; then
        return 1
    fi
    return 0
}

# export_test_counters: Export counters for use by parent process
export_test_counters() {
    export PASSED_TESTS
    export FAILED_TESTS
    export SKIPPED_TESTS
    export TIMEOUT_TESTS
}

#############################################################################
# Utility Helpers
#############################################################################

# assert_equals: Compare two values
# Usage: assert_equals "Test name" "expected" "actual"
assert_equals() {
    local name="$1"
    local expected="$2"
    local actual="$3"
    
    if [ "$expected" = "$actual" ]; then
        test_pass "$name"
        return 0
    else
        echo "Expected: [$expected], Got: [$actual]" | tee -a "$RESULTS_FILE"
        test_fail "$name"
        return 1
    fi
}

# assert_not_equals: Compare two values are different
# Usage: assert_not_equals "Test name" "unexpected" "actual"
assert_not_equals() {
    local name="$1"
    local unexpected="$2"
    local actual="$3"
    
    if [ "$unexpected" != "$actual" ]; then
        test_pass "$name"
        return 0
    else
        echo "Should not equal: [$unexpected]" | tee -a "$RESULTS_FILE"
        test_fail "$name"
        return 1
    fi
}

# validate_colored_output: Check if output contains ANSI color codes
# Usage: validate_colored_output "output_string" "test_name"
validate_colored_output() {
    local output="$1"
    local name="$2"
    
    # Check for ESC character (0x1B = octal 033)
    if printf '%s' "$output" | od -An -tx1 | grep -q '1b'; then
        log_debug "Output contains ANSI color codes"
        return 0
    else
        echo "Output missing ANSI color codes" | tee -a "$RESULTS_FILE"
        return 1
    fi
}

# validate_output_contains_plain_text: Check output for specific text (ignoring color codes)
# Usage: validate_output_contains_plain_text "output_string" "search_text" "test_name"
validate_output_contains_plain_text() {
    local output="$1"
    local search="$2"
    local name="$3"
    
    # Strip ANSI color codes and search
    local plain=$(echo "$output" | sed 's/\x1b\[[0-9;]*m//g')
    
    if echo "$plain" | grep -q "$search"; then
        log_debug "Output contains text (ignoring colors): $search"
        return 0
    else
        echo "Output does not contain text: $search" | tee -a "$RESULTS_FILE"
        echo "Plain output was: $(echo "$plain" | head -3)" | tee -a "$RESULTS_FILE"
        return 1
    fi
}

# test_output_with_colors: Validate exit code and colored output format
# Usage: test_output_with_colors "Test name" "command" expected_exit_code "expected_text" [expect_colors]
# expect_colors: 1=expect colors, 0=expect no colors, omit=don't check
test_output_with_colors() {
    local name="$1"
    local command="$2"
    local expected_exit="$3"
    local expected_text="$4"
    local expect_colors="${5:-1}"
    local timeout_secs="${6:-$TEST_TIMEOUT}"
    
    echo -e "\n${YELLOW}Testing: $name${NC}" | tee -a "$RESULTS_FILE"
    log_debug "Command: $command (timeout: ${timeout_secs}s)"
    
    run_command_captured "$command" "$timeout_secs"
    
    if [ "$CMD_EXIT" -eq 124 ]; then
        log_raw "Command timed out after ${timeout_secs}s"
        test_timeout "$name"
        return 1
    fi
    
    local all_ok=1
    
    # Check exit code
    if [ "$CMD_EXIT" -ne "$expected_exit" ]; then
        echo "Exit code mismatch: Expected $expected_exit, Got $CMD_EXIT" | tee -a "$RESULTS_FILE"
        all_ok=0
    fi
    
    # Check text content (strip colors)
    local plain=$(echo "$CMD_STDOUT" | sed 's/\x1b\[[0-9;]*m//g')
    if [ -n "$expected_text" ] && ! echo "$plain" | grep -q "$expected_text"; then
        echo "Output missing expected text: $expected_text" | tee -a "$RESULTS_FILE"
        echo "Plain output: $(echo "$plain" | head -2)" | tee -a "$RESULTS_FILE"
        all_ok=0
    fi
    
    # Check for color codes if expected
    if [ "$expect_colors" -eq 1 ]; then
        if ! printf '%s' "$CMD_STDOUT" | od -An -tx1 | grep -q '1b'; then
            echo "Output missing ANSI color codes" | tee -a "$RESULTS_FILE"
            all_ok=0
        fi
    elif [ "$expect_colors" -eq 0 ]; then
        if printf '%s' "$CMD_STDOUT" | od -An -tx1 | grep -q '1b'; then
            echo "Output unexpectedly contains ANSI color codes" | tee -a "$RESULTS_FILE"
            all_ok=0
        fi
    fi
    
    if [ "$all_ok" -eq 1 ]; then
        test_pass "$name"
        return 0
    else
        log_raw "STDOUT:\n$CMD_STDOUT"
        log_raw "STDERR:\n$CMD_STDERR"
        test_fail "$name"
        return 1
    fi
}

# create_test_file: Create a temporary test file with content
# Usage: create_test_file "content" | returns filepath
create_test_file() {
    local content="$1"
    local filepath="/tmp/grepnet_test_$$.txt"
    echo "$content" > "$filepath"
    echo "$filepath"
}

# cleanup_test_file: Remove temporary test file
# Usage: cleanup_test_file "filepath"
cleanup_test_file() {
    local filepath="$1"
    [ -f "$filepath" ] && rm -f "$filepath"
}

#############################################################################
# Export functions for subshells
#############################################################################

export -f log_header log_info log_debug log_raw
export -f test_pass test_fail test_skip test_timeout
export -f run_with_timeout run_command_captured
export -f validate_exit_code validate_stdout_contains validate_stdout_not_contains
export -f validate_stderr_contains validate_stderr_not_contains validate_stdout_line_count
export -f test_case test_full_output test_output_matches_regex
export -f test_stdout_contains test_stdout_not_contains
export -f test_stderr_contains test_stderr_not_contains
export -f test_file_exists test_grepnet_installed
export -f setup_test_environment get_test_summary export_test_counters
export -f assert_equals assert_not_equals
export -f create_test_file cleanup_test_file
