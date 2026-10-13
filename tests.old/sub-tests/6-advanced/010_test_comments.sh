#!/bin/bash

#############################################################################
# GREPNET TEST: Comment Handling
#############################################################################

source "$TEST_LIB_DIR/lib_tests.sh"

log_header "COMMENT HANDLING"

# SPEC: By default, comment lines are filtered (excluded from search results)
# SPEC-REF: GREPNET-SPEC.md - Comment Handling: "By default, comment lines are filtered (excluded from search). Override with --no-filter-comments"
test_case "Find networks ignoring comments" \
    "$GREPNET '192.168.1.0/24' '$TESTS_DIR/comments_test.txt'" 0 \
    $'192.168.1.0/24 should match\n192.168.0.0/16 -- gateway network' ""

# SPEC: --no-filter-comments includes comment lines in search results; comments are not stripped
# SPEC-REF: GREPNET-SPEC.md - Comment Handling: "Override with --no-filter-comments to include comment lines"
test_case "Include comment lines (--no-filter-comments)" \
    "$GREPNET --no-filter-comments=both '10.1.0.0/16' '$TESTS_DIR/comments_test.txt'" 0 \
    $'Route: 10.0.0.0/8  # inline comment with 172.16.0.0/12\n10.1.0.0/16 ! internal network' ""

# SPEC: Networks appearing only in comments are not matched when comment filtering is enabled (default)
# SPEC-REF: GREPNET-SPEC.md - Comment Handling: "By default, comment lines are filtered"
test_case "No matches in comments with filter" \
    "$GREPNET '203.0.114.0/24' '$TESTS_DIR/comments_test.txt'" 1

# SPEC: With --no-filter-comments, networks in commented lines are matched and included in results
# SPEC-REF: GREPNET-SPEC.md - Comment Handling: "Override with --no-filter-comments to match networks in comments"
test_case "Match networks in commented lines when no-filter is used" \
    "$GREPNET --no-filter-comments=both '203.0.113.0/24' '$TESTS_DIR/comments_test.txt'" 0 \
    $'203.0.113.0/24' ""
