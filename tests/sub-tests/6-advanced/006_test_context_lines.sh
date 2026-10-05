#!/bin/bash

#############################################################################
# GREPNET TEST: Context Lines
#############################################################################

source "$TEST_LIB_DIR/lib_tests.sh"

log_header "CONTEXT LINES (-A, -B, -C)"

# SPEC: -A N includes N lines after each matching line as context
# SPEC-REF: GREPNET-SPEC.md - Context Lines: "After context (-A N): Include N lines after each match"
test_case "After context (-A 2)" \
    "$GREPNET -A 2 '192.168.0.0/16' '$TESTS_DIR/context_test.txt'" 0 \
    $'192.168.1.0/24\n\n# Line 3: Before context line 1\n--\n192.168.0.0/16 is the network\n\n# Line 9: After context line 1' ""

# SPEC: -B N includes N lines before each matching line as context
# SPEC-REF: GREPNET-SPEC.md - Context Lines: "Before context (-B N): Include N lines before each match"
test_case "Before context (-B 2)" \
    "$GREPNET -B 2 '192.168.0.0/16' '$TESTS_DIR/context_test.txt'" 0 \
    $'# Test data for context testing\n# Line 1: Match candidate\n192.168.1.0/24\n--\n\n# Line 7: MATCH LINE\n192.168.0.0/16 is the network' ""

# SPEC: Using -B N -A M together includes both N lines before and M lines after each match
# SPEC-REF: GREPNET-SPEC.md - Context Lines: "Include N lines before and after (equivalent to -C N -A M)"
test_case "Both before and after (-B 1 -A 1)" \
    "$GREPNET -B 1 -A 1 '192.168.0.0/16' '$TESTS_DIR/context_test.txt'" 0 \
    $'# Line 1: Match candidate\n192.168.1.0/24\n\n--\n# Line 7: MATCH LINE\n192.168.0.0/16 is the network' ""

# SPEC: -C N is shorthand for -B N -A N; includes N lines both before and after each match
# SPEC-REF: GREPNET-SPEC.md - Context Lines: "Context shorthand (-C N): Include N lines before and after (equivalent to -B N -A N)"
test_case "Context shorthand (-C 1)" \
    "$GREPNET -C 1 '192.168.0.0/16' '$TESTS_DIR/context_test.txt'" 0 \
    $'# Line 1: Match candidate\n192.168.1.0/24\n\n--\n# Line 7: MATCH LINE\n192.168.0.0/16 is the network' ""

# SPEC: --no-group-separator omits the separator line (default is --) between context groups
# SPEC-REF: GREPNET-SPEC.md - Context Lines: "Group separator: Between context groups, print a separator line (default --). Disable with --no-group-separator"
test_case "No group separator (--no-group-separator)" \
    "$GREPNET --no-group-separator -B 1 '192.168.0.0/16' '$TESTS_DIR/context_test.txt'" 0 \
    $'# Line 1: Match candidate\n192.168.1.0/24\n# Line 7: MATCH LINE\n192.168.0.0/16 is the network' ""

# SPEC: -B 0 means no lines before each match (only the match itself)
# SPEC-REF: GREPNET-SPEC.md - Context Lines: "N lines before each match (N=0 means no before-context)"
test_case "Before context (zero lines, -B 0)" \
    "$GREPNET -B 0 '192.168.0.0/16' '$TESTS_DIR/context_test.txt'" 0 \
    $'192.168.1.0/24\n--\n192.168.0.0/16 is the network' ""

# SPEC: -A 0 means no lines after each match (only the match itself)
# SPEC-REF: GREPNET-SPEC.md - Context Lines: "N lines after each match (N=0 means no after-context)"
test_case "After context (zero lines, -A 0)" \
    "$GREPNET -A 0 '192.168.0.0/16' '$TESTS_DIR/context_test.txt'" 0 \
    $'192.168.1.0/24\n--\n192.168.0.0/16 is the network' ""

# SPEC: Large context values (-C 10) include 10 lines before and after each match
# SPEC-REF: GREPNET-SPEC.md - Context Lines: "Include N lines before and after"
test_case "Large context (-C 10)" \
    "$GREPNET -C 10 '192.168.0.0/16' '$TESTS_DIR/context_test.txt'" 0 \
    $'# Test data for context testing\n# Line 1: Match candidate\n192.168.1.0/24\n\n# Line 3: Before context line 1\nThis is a context line before\n\n# Line 5: Before context line 2\nAnother context line\n\n# Line 7: MATCH LINE\n192.168.0.0/16 is the network\n\n# Line 1: Match candidate\n192.168.1.0/24\n\n# Line 3: Before context line 1\nThis is a context line before\n\n# Line 5: Before context line 2\nAnother context line\n\n# Line 7: MATCH LINE\n192.168.0.0/16 is the network\n\n# Line 9: After context line 1\nThis is after the match\n\n# Line 11: After context line 2\nAnd another line after\n\n# Line 13: Another MATCH\n10.0.0.0/8 gateway' ""

# SPEC: --group-separator allows customization of the separator line between context groups
# SPEC-REF: GREPNET-SPEC.md - Context Lines: "Customize separator using --group-separator=<string>"
test_case "Custom group separator" \
    "$GREPNET --group-separator='--SPLIT--' -B 1 '192.168.0.0/16' '$TESTS_DIR/context_test.txt'" 0 \
    $'# Line 1: Match candidate\n192.168.1.0/24\n--SPLIT--\n# Line 7: MATCH LINE\n192.168.0.0/16 is the network' ""
