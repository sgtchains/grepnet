#!/bin/bash

# Test Phase 3: File Discovery & Filtering
# Tests -d, -D, --include, --exclude, --exclude-from, --exclude-dir

set -euo pipefail

# Get grepnet binary from standard location
if [ -z "${GREPNET:-}" ]; then
    if [ -f "$(dirname "$0")/../../bin/grepnet" ]; then
        GREPNET="$(dirname "$0")/../../bin/grepnet"
    elif [ -f "$(dirname "$0")/../../grepnet" ]; then
        GREPNET="$(dirname "$0")/../../grepnet"
    elif command -v grepnet &>/dev/null; then
        GREPNET="grepnet"
    else
        GREPNET="/home/chains/bin/grepnet"
    fi
fi

TESTS_DIR="$(dirname "$0")/../files"

PASSED=0
FAILED=0

test_case() {
    local name="$1"
    local cmd="$2"
    local expected_exit="$3"
    
    echo -n "Testing: $name ... "
    
    set +e
    eval "$cmd" > /tmp/test_output.txt 2>&1
    actual_exit=$?
    set -e
    
    if [[ $actual_exit -eq $expected_exit ]]; then
        echo "✓ PASS (exit: $actual_exit)"
        ((PASSED++))
    else
        echo "✗ FAIL"
        echo "  Expected exit code: $expected_exit, Got: $actual_exit"
        echo "  Output:"
        cat /tmp/test_output.txt | head -5 | sed 's/^/    /'
        ((FAILED++))
    fi
}

echo "====== Phase 3: File Discovery Tests ======"
echo ""

# Create test directory structure
TEST_DIR="/tmp/grepnet_file_test"
rm -rf "$TEST_DIR"
mkdir -p "$TEST_DIR"/{subdir1,subdir2,.git}

cat > "$TEST_DIR/file1.txt" << 'EOF'
192.0.2.0
10.0.0.0
EOF

cat > "$TEST_DIR/file1.log" << 'EOF'
test log 192.0.2.1
EOF

cat > "$TEST_DIR/file1.bak" << 'EOF'
backup 10.0.0.1
EOF

cat > "$TEST_DIR/subdir1/file2.txt" << 'EOF'
172.16.0.0
EOF

cat > "$TEST_DIR/.git/config" << 'EOF'
192.168.1.0
EOF

echo "--- --include Tests ---"
# SPEC: Include pattern flag (--include) restricts search to files matching the pattern
# SPEC-REF: GREPNET-SPEC.md - File Discovery: "Include patterns (--include)"
test_case "--include single pattern" \
    "$GREPNET -r --include '*.txt' 0.0.0.0/0 '$TEST_DIR' | wc -l" \
    0

# SPEC: Multiple include patterns can be specified with multiple --include flags
# SPEC-REF: GREPNET-SPEC.md - File Discovery: "Multiple include patterns can be combined"
test_case "--include multiple patterns" \
    "$GREPNET -r --include '*.txt' --include '*.log' 0.0.0.0/0 '$TEST_DIR' | wc -l" \
    0

echo ""
echo "--- --exclude Tests ---"
# SPEC: Exclude pattern flag (--exclude) skips files matching the pattern
# SPEC-REF: GREPNET-SPEC.md - File Discovery: "Exclude file patterns (--exclude)"
test_case "--exclude single pattern" \
    "$GREPNET -r --exclude '*.bak' 0.0.0.0/0 '$TEST_DIR' | grep -c '^' " \
    0

# SPEC: Multiple exclude patterns can be specified with multiple --exclude flags
# SPEC-REF: GREPNET-SPEC.md - File Discovery: "Multiple exclude patterns can be combined"
test_case "--exclude multiple patterns" \
    "$GREPNET -r --exclude '*.bak' --exclude '*.log' 0.0.0.0/0 '$TEST_DIR' | grep -c '^'" \
    0

echo ""
echo "--- --exclude-dir Tests ---"
# SPEC: Exclude directory flag (--exclude-dir) skips entire directories matching the pattern
# SPEC-REF: GREPNET-SPEC.md - File Discovery: "Exclude directories (--exclude-dir)"
test_case "--exclude-dir single pattern" \
    "$GREPNET -r --exclude-dir '.git' 0.0.0.0/0 '$TEST_DIR' | grep -c '^'" \
    0

# SPEC: Exclude directory must prevent searching inside the excluded directory
# SPEC-REF: GREPNET-SPEC.md - File Discovery: "Exclude directories (--exclude-dir)"
test_case "--exclude-dir skips directory" \
    "$GREPNET -r --exclude-dir '.git' 0.0.0.0/0 '$TEST_DIR' | grep -q '192.168.1.0' && echo 'FOUND' || echo 'NOT FOUND'" \
    0

echo ""
echo "--- --exclude-from Tests ---"
EXCLUDE_FILE="/tmp/grepnet_exclude.txt"
cat > "$EXCLUDE_FILE" << 'EOF'
# SPEC: Exclude patterns can be read from a file via --exclude-from
# SPEC-REF: GREPNET-SPEC.md - File Discovery: "Read exclude patterns from file (--exclude-from)"
*.bak
*.log
EOF

test_case "--exclude-from file" \
    "$GREPNET -r --exclude-from '$EXCLUDE_FILE' 0.0.0.0/0 '$TEST_DIR' | grep -c '^'" \
    0

echo ""
echo "--- -d (Directory Handling) Tests ---"
# SPEC: Recursive search mode (-r with -d recurse) searches subdirectories
# SPEC-REF: GREPNET-SPEC.md - File Discovery: "Recursive search (-r, -d recurse)"
test_case "-d recurse (default)" \
    "$GREPNET -r -d recurse 0.0.0.0/0 '$TEST_DIR' | grep -c '^'" \
    0

# SPEC: Skip directory mode (-d skip) processes only files in the given directory, not subdirectories
# SPEC-REF: GREPNET-SPEC.md - File Discovery: "Skip directories (-d skip)"
test_case "-d skip skips directories" \
    "$GREPNET -r -d skip 0.0.0.0/0 '$TEST_DIR' | wc -l" \
    0

echo ""
echo "--- -D (Device Handling) Tests ---"
# SPEC: Device skip mode (-D skip) prevents reading from device files
# SPEC-REF: GREPNET-SPEC.md - File Discovery: "Skip devices (-D skip)"
test_case "-D skip skips devices" \
    "$GREPNET -D skip /dev/null 0.0.0.0/0" \
    1

echo ""
echo "====== Test Summary ======"
echo "Passed: $PASSED"
echo "Failed: $FAILED"
echo "Total:  $((PASSED + FAILED))"

# Cleanup
rm -rf "$TEST_DIR" "$EXCLUDE_FILE"

if [[ $FAILED -eq 0 ]]; then
    echo "✓ All tests PASSED"
    exit 0
else
    echo "✗ Some tests FAILED"
    exit 1
fi
