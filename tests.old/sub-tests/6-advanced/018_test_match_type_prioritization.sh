#!/bin/bash

#############################################################################
# GREPNET TEST: Match Type Prioritization with Multiple Patterns
#############################################################################

source "$TEST_LIB_DIR/lib_tests.sh"

log_header "MATCH TYPE PRIORITIZATION"

# When a network matches multiple patterns with different match types,
# the HIGHEST-PRIORITY match type should be used for coloring.
# Priority: EQUALS > SUBSET > SUPERSET > OVERLAP > UNMATCHED

# SPEC: When a network matches multiple patterns with different match types, EQUALS has highest priority
# SPEC-REF: GREPNET-SPEC.md - Match Type Prioritization: "Priority order: EQUALS > SUBSET > SUPERSET > OVERLAP > UNMATCHED"
test_case "Multiple patterns: EQUALS takes priority over SUPERSET" \
    "echo '192.0.2.0' | $GREPNET '192.0.2.0,0.0.0.0/0'" 0 \
    $'192.0.2.0' ""

# SPEC: Multiple networks in input can match different pattern types; all matching networks shown
# SPEC-REF: GREPNET-SPEC.md - Pattern Matching: "Any network matching any pattern is included"
test_case "Multiple patterns: both networks in line, different match types" \
    "echo 'text 192.0.2.0 255.0.255.0 text' | $GREPNET '192.0.2.0,0.0.0.0/0'" 0 \
    $'text 192.0.2.0 255.0.255.0 text' ""

# Coloring validation: 192.0.2.0 should be colored with EQUALS (me=01;32m green)
# even though it also matches 0.0.0.0/0 (which would be SUPERSET/mS=01;34m blue)

# SPEC: When a network matches multiple patterns, the highest-priority match type determines coloring
# SPEC-REF: GREPNET-SPEC.md - Color Output: "Match type coloring uses highest priority when network matches multiple patterns"
test_output_with_colors \
    "EQUALS color prioritized when matching multiple patterns" \
    "echo '192.0.2.0' | $GREPNET --color=always '192.0.2.0,0.0.0.0/0'" \
    0 \
    "192.0.2.0" \
    1

# SPEC: Matching multiple patterns results in union of matching networks; each match shown
# SPEC-REF: GREPNET-SPEC.md - Pattern Matching: "Multiple patterns are OR'd together"
test_case "Both networks match when patterns have different priorities" \
    "echo 'text 192.0.2.0 255.0.255.0 text' | $GREPNET '192.0.2.0,0.0.0.0/0'" 0 \
    $'text 192.0.2.0 255.0.255.0 text' ""

# SPEC: Match type priority is based on semantic relationship, not pattern order
# SPEC-REF: GREPNET-SPEC.md - Match Type Prioritization: "Ranking is semantic, independent of pattern order"
test_case "EQUALS wins even if 0.0.0.0/0 pattern comes first" \
    "echo '192.0.2.0' | $GREPNET '0.0.0.0/0,192.0.2.0'" 0 \
    $'192.0.2.0' ""

# SPEC: EQUALS has highest priority over both SUBSET and SUPERSET relationships
# SPEC-REF: GREPNET-SPEC.md - Match Type Prioritization: "EQUALS > SUBSET > SUPERSET"
test_case "EQUALS prioritized over both SUBSET and SUPERSET" \
    "echo '192.0.2.1' | $GREPNET '192.0.2.1,192.0.2.0/24,0.0.0.0/0'" 0 \
    $'192.0.2.1' ""

# SPEC: SUBSET has higher priority than SUPERSET when network matches both types
# SPEC-REF: GREPNET-SPEC.md - Match Type Prioritization: "SUBSET > SUPERSET"
test_case "SUBSET prioritized over SUPERSET" \
    "echo '192.0.2.1' | $GREPNET '192.0.2.0/24,0.0.0.0/0'" 0 \
    $'192.0.2.1' ""

log_header "Summary"
echo "Passed: $PASSED_TESTS / Failed: $FAILED_TESTS / Skipped: $SKIPPED_TESTS / Timeouts: $TIMEOUT_TESTS"

[ $FAILED_TESTS -gt 0 ] || [ $TIMEOUT_TESTS -gt 0 ]
