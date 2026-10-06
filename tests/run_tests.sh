#!/bin/bash

#############################################################################
# GREPNET COMPREHENSIVE TEST SUITE RUNNER
# Discovers and runs all test files (*_test_*.sh)
# Aggregates results and provides summary
#############################################################################

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GREPNET="${GREPNET:-/home/chains/dev/grepnet/grepnet}"
TESTS_DIR="$SCRIPT_DIR/files"
RESULTS_FILE="$SCRIPT_DIR/test_results.log"
TEST_TIMEOUT="${TEST_TIMEOUT:-30}"
VERBOSE="${VERBOSE:-0}"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Aggregate counters
TOTAL_PASSED=0
TOTAL_FAILED=0
TOTAL_SKIPPED=0
TOTAL_TIMEOUT=0

#############################################################################
# Main Test Runner
#############################################################################

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║        GREPNET COMPREHENSIVE TEST SUITE                       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Clear results file
> "$RESULTS_FILE"

# Verify grepnet is installed
echo -e "${CYAN}Verifying grepnet installation...${NC}"
if [ ! -f "$GREPNET" ]; then
    echo -e "${RED}ERROR: grepnet binary not found at: $GREPNET${NC}"
    exit 2
fi
if [ ! -x "$GREPNET" ]; then
    echo -e "${RED}ERROR: grepnet is not executable: $GREPNET${NC}"
    exit 2
fi
GREPNET_VERSION=$("$GREPNET" --version 2>&1 || echo "version unknown")
echo -e "${GREEN}✓${NC} grepnet found: $GREPNET"
echo -e "${GREEN}✓${NC} Version: $GREPNET_VERSION"
echo ""

# Setup environment for test scripts
export GREPNET
export TESTS_DIR
export TEST_LIB_DIR="$SCRIPT_DIR/lib"  # For sourcing lib_tests.sh from any subdirectory
export RESULTS_FILE
export TEST_TIMEOUT
export VERBOSE

# Discover test files (from categorical subdirectories and root)
echo -e "${CYAN}Discovering test files...${NC}"
mapfile -t test_files < <(find "$SCRIPT_DIR/sub-tests" -name "*_test_*.sh" -type f | sort)

if [ ${#test_files[@]} -eq 0 ]; then
    echo -e "${RED}ERROR: No test files found in sub-tests/ matching pattern *_test_*.sh${NC}"
    exit 2
fi

echo -e "${GREEN}Found ${#test_files[@]} test file(s):${NC}"
current_category=""
for test_file in "${test_files[@]}"; do
    test_name=$(basename "$test_file" .sh)
    # Extract category from path (e.g., "sub-tests/1-core/..." -> "1-core")
    category=$(dirname "$test_file" | sed 's|.*/||')
    if [ "$category" != "$current_category" ]; then
        current_category="$category"
        echo -e "  ${YELLOW}${current_category}:${NC}"
    fi
    echo -e "    ${CYAN}→${NC} $test_name"
done
echo ""

# Set up log directory if not exists
mkdir -p "$SCRIPT_DIR/log"
RESULTS_FILE="$SCRIPT_DIR/log/test_results.log"

#############################################################################
# Run All Tests
#############################################################################

echo -e "${BLUE}Running tests...${NC}"
echo "=" | tee -a "$RESULTS_FILE"

test_num=1
for test_file in "${test_files[@]}"; do
    test_name=$(basename "$test_file" .sh)
    
    echo ""
    echo -e "${BLUE}[${test_num}/${#test_files[@]}]${NC} Running: ${CYAN}$test_name${NC}"
    echo "" | tee -a "$RESULTS_FILE"
    
    # Run test file (sourced in subshell to isolate environment)
    if (source "$test_file"); then
        file_status="${GREEN}✓ PASS${NC}"
    else
        file_status="${RED}✗ FAIL${NC}"
    fi
    
    echo -e "  Result: $file_status"
    
    ((test_num++))
done

# Parse results from log file (test functions write ✓ PASS and ✗ FAIL to log)
# Use printf to ensure clean numeric values
TOTAL_PASSED=$(grep -c "✓ PASS" "$RESULTS_FILE" 2>/dev/null | tr -d ' ')
TOTAL_FAILED=$(grep -c "✗ FAIL" "$RESULTS_FILE" 2>/dev/null | tr -d ' ')
TOTAL_SKIPPED=$(grep -c "⊘ SKIP" "$RESULTS_FILE" 2>/dev/null | tr -d ' ')
TOTAL_TIMEOUT=$(grep -c "⏱ TIMEOUT" "$RESULTS_FILE" 2>/dev/null | tr -d ' ')

# Ensure variables are numeric (default to 0 if empty)
TOTAL_PASSED=${TOTAL_PASSED:-0}
TOTAL_FAILED=${TOTAL_FAILED:-0}
TOTAL_SKIPPED=${TOTAL_SKIPPED:-0}
TOTAL_TIMEOUT=${TOTAL_TIMEOUT:-0}

# Convert to integers
TOTAL_PASSED=$((TOTAL_PASSED + 0))
TOTAL_FAILED=$((TOTAL_FAILED + 0))
TOTAL_SKIPPED=$((TOTAL_SKIPPED + 0))
TOTAL_TIMEOUT=$((TOTAL_TIMEOUT + 0))

#############################################################################
# Summary Report
#############################################################################

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                        FINAL TEST SUMMARY${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"

local_total=$((TOTAL_PASSED + TOTAL_FAILED + TOTAL_SKIPPED + TOTAL_TIMEOUT))

echo -e "  ${GREEN}Passed:  ${TOTAL_PASSED}${NC}"
echo -e "  ${RED}Failed:  ${TOTAL_FAILED}${NC}"
echo -e "  ${RED}Timeout: ${TOTAL_TIMEOUT}${NC}"
echo -e "  ${YELLOW}Skipped: ${TOTAL_SKIPPED}${NC}"
echo -e "  ${CYAN}Total:   ${local_total}${NC}"

echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"

# Save summary to results file
echo "" | tee -a "$RESULTS_FILE"
echo "FINAL SUMMARY" | tee -a "$RESULTS_FILE"
echo "Passed:  $TOTAL_PASSED" | tee -a "$RESULTS_FILE"
echo "Failed:  $TOTAL_FAILED" | tee -a "$RESULTS_FILE"
echo "Timeout: $TOTAL_TIMEOUT" | tee -a "$RESULTS_FILE"
echo "Skipped: $TOTAL_SKIPPED" | tee -a "$RESULTS_FILE"
echo "Total:   $local_total" | tee -a "$RESULTS_FILE"

# Print results file location
echo ""
echo -e "${CYAN}Full results saved to:${NC} $RESULTS_FILE"
echo ""

# Exit with appropriate code
if [ "$TOTAL_FAILED" -gt 0 ] || [ "$TOTAL_TIMEOUT" -gt 0 ]; then
    echo -e "${RED}Tests FAILED${NC}"
    exit 1
else
    echo -e "${GREEN}All tests PASSED${NC}"
    exit 0
fi

#############################################################################
# BASIC MATCHING TESTS
#############################################################################

log_header "BASIC PATTERN MATCHING"

test_case "Basic CIDR pattern match" \
    "$GREPNET '192.0.2.0/24' '$TESTS_DIR/sample_networks.txt'" 0

test_case "Match IPv4 address" \
    "$GREPNET '192.0.1.1' '$TESTS_DIR/sample_networks.txt'" 0

test_case "No match returns exit code 1" \
    "$GREPNET '203.0.114.0/24' '$TESTS_DIR/sample_networks.txt'" 1

test_case "Pattern file input (-f)" \
    "echo '192.0.2.0/24' > /tmp/pattern.txt && $GREPNET -f /tmp/pattern.txt '$TESTS_DIR/sample_networks.txt'" 0

test_case "Pattern via -P flag" \
    "$GREPNET -P '192.0.2.0/24' '$TESTS_DIR/sample_networks.txt'" 0

test_case "Multiple patterns (-P multiple times)" \
    "$GREPNET -P '192.0.2.0/24' -P '10.0.0.0/8' '$TESTS_DIR/sample_networks.txt'" 0

test_case "Stdin input" \
    "echo '192.0.2.0/24' | $GREPNET '192.0.2.0/24'" 0

#############################################################################
# MATCH TYPE TESTS
#############################################################################

log_header "MATCH TYPE FLAGS (-e, -s, -S, -O, -u)"

test_case "Exact match (-e)" \
    "$GREPNET -e '192.0.2.0/24' '$TESTS_DIR/match_types.txt'" 0

test_case "Subset match (-s)" \
    "$GREPNET -s '192.0.2.0/24' '$TESTS_DIR/match_types.txt'" 0

test_case "Superset match (-S)" \
    "$GREPNET -S '192.0.2.0/24' '$TESTS_DIR/match_types.txt'" 0

test_case "Overlap match (-O)" \
    "$GREPNET -O '192.0.2.0/24' '$TESTS_DIR/match_types.txt'" 0

test_case "Combined match types (-e -s)" \
    "$GREPNET -e -s '192.0.2.0/24' '$TESTS_DIR/match_types.txt'" 0

test_case "Superset and overlap (-S -O)" \
    "$GREPNET -S -O '192.0.2.0/24' '$TESTS_DIR/match_types.txt'" 0

#############################################################################
# INVERSION AND FILTERING
#############################################################################

log_header "INVERSION AND FILTERING (-v)"

test_case "Invert match (-v)" \
    "$GREPNET -v '192.0.2.0/24' '$TESTS_DIR/sample_networks.txt'" 0

test_case "Quiet mode (-q)" \
    "$GREPNET -q '192.0.2.0/24' '$TESTS_DIR/sample_networks.txt'" 0

test_case "Quiet mode no match" \
    "$GREPNET -q '203.0.114.0/24' '$TESTS_DIR/sample_networks.txt'" 1

#############################################################################
# OUTPUT CONTROL
#############################################################################

log_header "OUTPUT CONTROL (-H, -l, -L, -c)"

test_case "With filename (-H)" \
    "$GREPNET -H '192.0.2.0/24' '$TESTS_DIR/sample_networks.txt'" 0

test_case "List files only (-l)" \
    "$GREPNET -l '192.0.2.0/24' '$TESTS_DIR/file1.txt' '$TESTS_DIR/file2.txt'" 0

test_case "Files without matches (-L)" \
    "$GREPNET -L '192.0.2.0/24' '$TESTS_DIR/file1.txt' '$TESTS_DIR/file2.txt' '$TESTS_DIR/file3.txt'" 0

test_case "Count matches (-c)" \
    "$GREPNET -c '192.168.0.0/16' '$TESTS_DIR/file1.txt'" 0

test_case "Multiple files count" \
    "$GREPNET -c '192.0.2.0/24' '$TESTS_DIR/file1.txt' '$TESTS_DIR/file2.txt'" 0

#############################################################################
# LINE PREFIXES
#############################################################################

log_header "LINE PREFIXES (-n, -b, -T, -Z)"

test_case "Line numbers (-n)" \
    "$GREPNET -n '192.0.2.0/24' '$TESTS_DIR/sample_networks.txt'" 0

test_case "Byte offset (-b)" \
    "$GREPNET -b '192.0.2.0/24' '$TESTS_DIR/sample_networks.txt'" 0

test_case "Line number and byte offset (-n -b)" \
    "$GREPNET -n -b '192.0.2.0/24' '$TESTS_DIR/sample_networks.txt'" 0

test_case "Initial tab (-T)" \
    "$GREPNET -n -T '192.0.2.0/24' '$TESTS_DIR/sample_networks.txt'" 0

#############################################################################
# CONTEXT LINES
#############################################################################

log_header "CONTEXT LINES (-A, -B, -C)"

test_case "After context (-A 2)" \
    "$GREPNET -A 2 '192.168.0.0/16' '$TESTS_DIR/context_test.txt'" 0

test_case "Before context (-B 2)" \
    "$GREPNET -B 2 '192.168.0.0/16' '$TESTS_DIR/context_test.txt'" 0

test_case "Both before and after (-B 1 -A 1)" \
    "$GREPNET -B 1 -A 1 '192.168.0.0/16' '$TESTS_DIR/context_test.txt'" 0

test_case "Context shorthand (-C 1)" \
    "$GREPNET -C 1 '192.168.0.0/16' '$TESTS_DIR/context_test.txt'" 0

test_case "No group separator" \
    "$GREPNET --no-group-separator -B 1 '192.168.0.0/16' '$TESTS_DIR/context_test.txt'" 0

#############################################################################
# OUTPUT FORMATS
#############################################################################

log_header "OUTPUT FORMATS (--output-format)"

test_case "JSON output" \
    "$GREPNET --output-format json '192.0.2.0/24' '$TESTS_DIR/sample_networks.txt'" 0

test_case "Table output" \
    "$GREPNET --output-format table '192.0.2.0/24' '$TESTS_DIR/sample_networks.txt'" 0

test_case "Only matching (-o)" \
    "$GREPNET -o '192.0.2.0/24' '$TESTS_DIR/sample_networks.txt'" 0

#############################################################################
# PARSING OPTIONS
#############################################################################

log_header "PARSING OPTIONS"

test_case "Parse ranges (--parse-ranges)" \
    "$GREPNET --parse-ranges '192.0.2.0-192.0.2.255' '$TESTS_DIR/sample_networks.txt'" 0

test_case "Parse long-form ranges only" \
    "$GREPNET --parse-ranges-long '192.0.2.0-192.0.2.255' '$TESTS_DIR/sample_networks.txt'" 0

test_case "Disable CIDR parsing" \
    "$GREPNET --no-parse-cidr '192.168.1.0/24' '$TESTS_DIR/sample_networks.txt'" 1

test_case "Parse netmask format" \
    "$GREPNET --parse-netmask '192.168.1.0 255.255.255.0' '$TESTS_DIR/sample_networks.txt'" 0

test_case "Parse hostmask format" \
    "$GREPNET --parse-hostmask '192.0.2.0 0.0.0.255' '$TESTS_DIR/sample_networks.txt'" 0

#############################################################################
# STRICT CIDR MODE
#############################################################################

log_header "STRICT CIDR MODE"

test_case "Non-strict mode (default, normalizes)" \
    "$GREPNET '192.0.2.5/24' '$TESTS_DIR/match_types.txt'" 0

test_case "Strict CIDR pattern mode" \
    "$GREPNET --strict-cidrs-pattern --no-strict-cidrs-error '192.0.2.5/24' '$TESTS_DIR/match_types.txt'" 0

test_case "Strict input mode" \
    "$GREPNET --strict-cidrs-input --no-strict-cidrs-error '192.0.2.0/24' '$TESTS_DIR/match_types.txt'" 0

#############################################################################
# COMMENTS
#############################################################################

log_header "COMMENT HANDLING"

test_case "Find networks ignoring comments" \
    "$GREPNET '192.168.1.0/24' '$TESTS_DIR/comments_test.txt'" 0

test_case "Include comment lines (--no-filter-comments)" \
    "$GREPNET --no-filter-comments '10.1.0.0/16' '$TESTS_DIR/comments_test.txt'" 0

#############################################################################
# IPv6
#############################################################################

log_header "IPv6 SUPPORT"

test_case "IPv6 CIDR match" \
    "$GREPNET '2001:db8::/32' '$TESTS_DIR/ipv6_test.txt'" 0

test_case "IPv6 single address" \
    "$GREPNET '::1' '$TESTS_DIR/ipv6_test.txt'" 0

test_case "IPv6 range format" \
    "$GREPNET --parse-ranges '2001:db8::1-2001:db8::ff' '$TESTS_DIR/ipv6_test.txt'" 0

#############################################################################
# MULTIPLE FILES
#############################################################################

log_header "MULTIPLE FILES"

test_case "Search multiple files" \
    "$GREPNET '192.0.2.0/24' '$TESTS_DIR/file1.txt' '$TESTS_DIR/file2.txt'" 0

test_case "No filename prefix for single file" \
    "$GREPNET '192.0.2.0/24' '$TESTS_DIR/file1.txt'" 0

test_case "Filename prefix for multiple files" \
    "$GREPNET '192.0.2.0/24' '$TESTS_DIR/file1.txt' '$TESTS_DIR/file2.txt' | grep -q ':'" 0

test_case "Suppress filename (--no-filename)" \
    "$GREPNET --no-filename '192.0.2.0/24' '$TESTS_DIR/file1.txt' '$TESTS_DIR/file2.txt'" 0

#############################################################################
# EXTRACTION AND CONSOLIDATION
#############################################################################

log_header "EXTRACTION AND CONSOLIDATION"

test_case "Extract all networks (--extract)" \
    "$GREPNET --extract '$TESTS_DIR/sample_networks.txt'" 0

test_case "Consolidate networks (--consolidate)" \
    "$GREPNET --consolidate '$TESTS_DIR/sample_networks.txt'" 0

test_case "Consolidate with pattern filter" \
    "$GREPNET --consolidate '192.0.0.0/16' '$TESTS_DIR/sample_networks.txt'" 0

#############################################################################
# EXCLUSION FILTERING
#############################################################################

log_header "EXCLUSION FILTERING"

test_case "Exclude network (--exclude-string)" \
    "$GREPNET --exclude-string '192.0.2.0/24' '192.0.0.0/16' '$TESTS_DIR/sample_networks.txt'" 0

test_case "Exclude multiple patterns" \
    "$GREPNET --exclude-string '192.0.2.0/24' --exclude-string '10.0.0.0/8' '192.0.0.0/16' '$TESTS_DIR/sample_networks.txt'" 0

#############################################################################
# MAX COUNT
#############################################################################

log_header "MAX COUNT"

test_case "Max count limit (-m 1)" \
    "$GREPNET -m 1 '192.' '$TESTS_DIR/file1.txt' '$TESTS_DIR/file2.txt'" 0

test_case "Max count with multiple files" \
    "$GREPNET -m 3 '192.' '$TESTS_DIR/file1.txt' '$TESTS_DIR/file2.txt'" 0

#############################################################################
# HELP AND VERSION
#############################################################################

log_header "HELP AND VERSION"

test_case "Help flag (-h)" \
    "$GREPNET -h" 0

test_case "Full help (--help)" \
    "$GREPNET --help" 0

test_case "Version flag (--version)" \
    "$GREPNET --version" 0

#############################################################################
# ERROR HANDLING
#############################################################################

log_header "ERROR HANDLING"

test_case "File not found returns error" \
    "$GREPNET '192.0.2.0/24' /nonexistent/file.txt" 2

test_case "No pattern error" \
    "$GREPNET '' '$TESTS_DIR/sample_networks.txt'" 2

test_case "Invalid flag handling" \
    "$GREPNET --invalid-flag '192.0.2.0/24' '$TESTS_DIR/sample_networks.txt'" 2

#############################################################################
# RESULTS SUMMARY
#############################################################################

log_header "TEST RESULTS SUMMARY"

TOTAL_TESTS=$((PASSED_TESTS + FAILED_TESTS))
PASS_RATE=$((PASSED_TESTS * 100 / TOTAL_TESTS))

echo -e "\n${BLUE}Total Tests: $TOTAL_TESTS${NC}" | tee -a "$RESULTS_FILE"
echo -e "${GREEN}Passed: $PASSED_TESTS${NC}" | tee -a "$RESULTS_FILE"
echo -e "${RED}Failed: $FAILED_TESTS${NC}" | tee -a "$RESULTS_FILE"
echo -e "${YELLOW}Pass Rate: $PASS_RATE%${NC}" | tee -a "$RESULTS_FILE"

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "\n${GREEN}✓ ALL TESTS PASSED!${NC}\n" | tee -a "$RESULTS_FILE"
    exit 0
else
    echo -e "\n${RED}✗ SOME TESTS FAILED${NC}\n" | tee -a "$RESULTS_FILE"
    exit 1
fi
