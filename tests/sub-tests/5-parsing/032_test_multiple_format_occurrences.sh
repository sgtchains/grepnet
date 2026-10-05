#!/bin/bash

# Test: Multiple occurrences of same network in different formats should all be marked
# Regression test for issue where duplicate formats weren't all marked
# Issue: When same network appears multiple times in different formats (e.g., CIDR + subnet mask),
# only one occurrence was being marked. This test ensures all variations are marked.

source "$TEST_LIB_DIR/lib_tests.sh"

log_header "MULTIPLE FORMAT OCCURRENCES"

run_test() {

# SPEC: Duplicate networks in same format should all be marked/matched (no deduplication in output)
# SPEC-REF: GREPNET-SPEC.md - Output Control: "Each matching line and its content shown without deduplication"
# Test 1: Same CIDR appearing twice should mark both
test_case "Same CIDR twice" \
    "echo -e '192.0.2.0/24 and 192.0.2.0/24' | $GREPNET '192.0.2.0/25'" 0 \
    "192.0.2.0/24 and 192.0.2.0/24" \
    ""

# SPEC: Same network in different formats (CIDR + subnet mask) should both be recognized and marked
# SPEC-REF: GREPNET-SPEC.md - Network Parsing Pipeline: "Normalized networks matched regardless of input format"
# Test 2: CIDR + subnet mask of same network should mark both
test_case "CIDR and subnet mask" \
    "echo -e '192.0.2.0/24 and 192.0.2.0 255.255.255.0' | $GREPNET '192.0.2.0/25'" 0 \
    "192.0.2.0/24 and 192.0.2.0 255.255.255.0" \
    ""

# SPEC: Multiple instances of the same network (interleaved with different networks) should all be marked
# SPEC-REF: GREPNET-SPEC.md - Output Control: "All matching lines shown; non-matching lines may be shown with context"
# Test 3: Interleaved different networks should only mark matching ones
test_case "Interleaved networks" \
    "echo -e '192.0.2.0/24 and 10.0.0.0/8 and 192.0.2.0/24' | $GREPNET '192.0.2.0/25'" 0 \
    "192.0.2.0/24 and 10.0.0.0/8 and 192.0.2.0/24" \
    ""

# SPEC: Hostmask format (inverse mask) variations of same network should be recognized alongside CIDR format
# SPEC-REF: GREPNET-SPEC.md - Inverse/Hostmask Parsing: "Hostmask format normalized to same network as CIDR"
# Test 4: Inverse mask variant
test_case "Inverse mask variant" \
    "echo -e '192.0.2.0 0.0.0.255 and 192.0.2.0/24' | $GREPNET '192.0.2.0/25'" 0 \
    "192.0.2.0 0.0.0.255 and 192.0.2.0/24" \
    ""

}

run_test

