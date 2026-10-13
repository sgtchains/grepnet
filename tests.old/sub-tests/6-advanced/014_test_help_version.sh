#!/bin/bash

#############################################################################
# GREPNET TEST: Help and Version
#############################################################################

source "$TEST_LIB_DIR/lib_tests.sh"

log_header "HELP AND VERSION"

# SPEC: The -h flag displays help with usage information
# SPEC-REF: GREPNET-SPEC.md - Program Initialization: "Help output format must include usage"
test_stdout_contains "Help flag (-h)" \
    "$GREPNET -h" 0 "usage: grepnet"

# SPEC: The --help flag provides full help information with same content as -h
# SPEC-REF: GREPNET-SPEC.md - Program Initialization: "--help must function identically to -h"
test_stdout_contains "Full help (--help)" \
    "$GREPNET --help" 0 "usage: grepnet"

# SPEC: The --version flag outputs the version in format: grepnet X.Y.Z
# SPEC-REF: GREPNET-SPEC.md - Program Initialization: "Version output format: program_name version_number"
test_case "Version flag (--version)" \
    "$GREPNET --version" 0 $'grepnet 3.0.0' ""

# SPEC: Help output includes usage information describing the program and its operation
# SPEC-REF: GREPNET-SPEC.md - Help Output: "Must include usage information"
test_stdout_contains "Help contains usage information" \
    "$GREPNET --help" 0 "grepnet"

# SPEC: Help output includes documentation of pattern parameter usage
# SPEC-REF: GREPNET-SPEC.md - Help Output: "Must document pattern argument"
test_stdout_contains "Help contains pattern description" \
    "$GREPNET --help" 0 "pattern"

# SPEC: Version output includes numeric version number in standard semver format (major.minor.patch)
# SPEC-REF: GREPNET-SPEC.md - Version Output: "Format must include version number"
test_stdout_contains "Version output" \
    "$GREPNET --version" 0 "[0-9]\\."
