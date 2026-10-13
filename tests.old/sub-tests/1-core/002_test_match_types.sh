#!/bin/bash

#############################################################################
# GREPNET TEST: Match Type Flags
#############################################################################

source "$TEST_LIB_DIR/lib_tests.sh"

log_header "MATCH TYPE FLAGS (-e, -s, -S, -O, -u)"

# SPEC: Exact match (-e) selects networks that are exactly equal to the pattern
# SPEC-REF: GREPNET-SPEC.md - Match Type Flags: "Exact match (-e): select networks that are exactly equal to the pattern"
test_case "Exact match (-e)" \
    "$GREPNET -e '192.0.2.0/24' '$TESTS_DIR/match_types.txt'" 0 $'192.0.2.0/24\n192.0.2.0-192.0.2.255\n192.0.2.5/24' ""

# SPEC: Subset match (-s) selects networks that are contained within (strict subset of) the pattern
# SPEC-REF: GREPNET-SPEC.md - Match Type Flags: "Subset match (-s): select networks that are contained within the pattern"
test_case "Subset match (-s)" \
    "$GREPNET -s '192.0.2.0/24' '$TESTS_DIR/match_types.txt'" 0 $'192.0.2.0/25\n192.0.2.1/32' ""

# SPEC: Superset match (-S) selects networks that contain (are supersets of) the pattern
# SPEC-REF: GREPNET-SPEC.md - Match Type Flags: "Superset match (-S): select networks that contain the pattern"
test_case "Superset match (-S)" \
    "$GREPNET -S '192.0.2.0/24' '$TESTS_DIR/match_types.txt'" 0 $'192.0.0.0/16\n0.0.0.0/0' ""

# SPEC: Overlap match (-O) selects networks that have any address in common with the pattern but are neither subsets nor supersets
# SPEC-REF: GREPNET-SPEC.md - Match Type Flags: "Overlap match (-O): select networks that overlap with the pattern (but are not subsets/supersets)"
test_case "Overlap match (-O)" \
    "$GREPNET -O '192.0.2.0/24' '$TESTS_DIR/match_types.txt'" 1 "" ""

# SPEC: Multiple match type flags (-e, -s, -S, -O) can be combined; the result is the union of matching networks
# SPEC-REF: GREPNET-SPEC.md - Match Type Flags: "Multiple match types can be combined; the result is the union"
test_case "Combined match types (-e -s)" \
    "$GREPNET -e -s '192.0.2.0/24' '$TESTS_DIR/match_types.txt'" 0 $'192.0.2.0/24\n192.0.2.0/25\n192.0.2.0-192.0.2.255\n192.0.2.5/24\n192.0.2.1/32' ""

# SPEC: Superset and overlap can be combined to select networks that contain or overlap with the pattern
# SPEC-REF: GREPNET-SPEC.md - Match Type Flags: "Multiple match types can be combined; the result is the union"
test_case "Superset and overlap (-S -O)" \
    "$GREPNET -S -O '192.0.2.0/24' '$TESTS_DIR/match_types.txt'" 0 $'192.0.0.0/16\n0.0.0.0/0' ""

# SPEC: Unmatched networks flag (-u) inverts the selection to show networks that do NOT match any of the specified match types
# SPEC-REF: GREPNET-SPEC.md - Match Type Flags: "Unmatched networks flag (-u): invert to show networks that do not match"
test_case "Unmatched networks (-u)" \
    "$GREPNET -u '192.0.2.0/24' '$TESTS_DIR/match_types.txt'" 0 $'255.255.255.255/32\n10.0.0.0-10.0.100.255\n10.0.0.0-10.0.100.255' ""

test_case "Only equals (-e only, no others)" \
    "$GREPNET -e '192.0.2.0/24' '$TESTS_DIR/match_types.txt'" 0 $'192.0.2.0/24\n192.0.2.0-192.0.2.255\n192.0.2.5/24' ""
