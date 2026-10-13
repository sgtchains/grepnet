# Test Data Quick Reference

This document provides quick reference for all test data files and their contents.

## File Descriptions

### sample_networks.txt
**Purpose**: Basic network format testing

**Contents**:
```
192.0.2.0/24                          # CIDR notation
10.0.0.0/8                            # CIDR notation
172.16.0.0/12                         # CIDR notation
2001:db8::/32                         # IPv6 CIDR
192.168.1.0 255.255.255.0             # Subnet mask format
10.0.0.0 255.0.0.0                    # Subnet mask format
172.31.0.0 255.255.0.0                # Subnet mask format
192.0.2.0 0.0.0.255                   # Cisco hostmask format
10.0.0.0 0.255.255.255                # Cisco hostmask format
192.0.2.0-192.0.2.255                 # IP range (long form)
10.1.1.0-10.1.1.50                    # IP range (long form)
172.16.0.0-172.16.255.255             # IP range (long form)
192.0.1.1                             # Plain IPv4 (/32)
198.51.100.5                          # Plain IPv4 (/32)
203.0.113.42                          # Plain IPv4 (/32)
Route to 192.0.2.0/24 via 10.0.0.0/8  # Multiple on one line
```

**Use Cases**:
- Testing all CIDR formats
- Testing IPv4 and IPv6
- Testing multiple formats on one line
- General pattern matching

### context_test.txt
**Purpose**: Testing context options (-A, -B, -C)

**Contents**: 16 lines with known line numbers and matches
- Line 1: candidate (empty line in actual file)
- Line 3: context line (before)
- Line 5: context line (before)
- Line 7: MATCH - 192.168.0.0/16
- Line 9: context line (after)
- Line 11: context line (after)
- Line 13: MATCH - 10.0.0.0/8
- Line 15: context line (after)

**Use Cases**:
- Testing -A (after context)
- Testing -B (before context)
- Testing -C (both contexts)
- Testing group separators

### ipv6_test.txt
**Purpose**: IPv6 address and network testing

**Contents**:
```
2001:db8::/32                         # IPv6 CIDR (/32)
2001:db8:85a3::8a2e:370:7334          # IPv6 address (full form)
2001:db8:85a3::/48                    # IPv6 CIDR (/48)
fc00::/7                              # Unique local addresses
fe80::/10                             # Link-local addresses
2001:db8:1234::/48                    # Example CIDR
2001:db8:1234:5678::/64               # Example CIDR (/64)
::1                                   # Loopback
fe80::1                               # Link-local
2001:db8::1-2001:db8::ff              # IPv6 range
```

**Use Cases**:
- IPv6 pattern matching
- IPv6 CIDR parsing
- IPv6 address parsing
- IPv6 range parsing (with --parse-ranges)

### comments_test.txt
**Purpose**: Comment handling across multiple language styles

**Contents**:
```
# Python comment line
... Python inline comment

// C-style comment
... C-style inline comment

/* Block comment */
... no comments

-- SQL comment
... SQL inline comment

! Cisco comment
... Cisco inline comment

; Lisp comment
... Lisp inline comment
```

**Use Cases**:
- Testing comment filtering (default)
- Testing --no-filter-comments flag
- Testing inline vs. full-line comments
- Testing multiple comment styles

### match_types.txt
**Purpose**: Testing network comparison logic

**Contents**:
```
192.0.2.0/24                          # Exact match candidate
192.0.0.0/16                          # Superset candidate (contains pattern)
192.0.2.0/25                          # Subset candidate (contained by pattern)
192.0.2.0-192.0.2.255                 # Range (equal to CIDR above)
192.0.2.5/24                          # Malformed CIDR (normalizes to 192.0.2.0/24)
0.0.0.0/0                             # Edge case: all IPs
255.255.255.255/32                    # Edge case: single IP broadcast
192.0.2.1/32                          # Edge case: single host
10.0.0.0-10.0.100.255                 # Overlap candidate
```

**Test Pattern**: 192.0.2.0/24

**Expected Matches**:
- Equals: line 1 (exact), line 4 (range equal to CIDR), line 5 (normalized)
- Subset: line 3 (192.0.2.0/25 is smaller)
- Superset: line 2 (192.0.0.0/16 contains it)
- Overlap: line 8 (10.0.0.0-10.0.100.255 may overlap in some scenarios)

**Use Cases**:
- Testing -e (equals)
- Testing -s (subset)
- Testing -S (superset)
- Testing -O (overlap)
- Testing malformed CIDR handling
- Testing edge cases

### file1.txt
**Purpose**: Multi-file testing - file with matches

**Contents**:
```
192.168.1.0/24
192.168.2.0/24
10.0.0.0/8
```

**Use Cases**:
- Multiple file searches
- File listing (-l, -L)
- Count mode (-c)
- Filename prefix testing

### file2.txt
**Purpose**: Multi-file testing - file with different matches

**Contents**:
```
172.16.0.0/12
192.0.2.0/24
203.0.113.0/24
```

**Use Cases**:
- Multiple file searches
- Different patterns in different files
- File count validation

### file3.txt
**Purpose**: Multi-file testing - file with NO matches

**Contents**:
```
This file has no network addresses
Just plain text with no CIDR notation
Or subnet masks like 255.255.255.0
But no actual networks to find
```

**Use Cases**:
- Testing -L (files without matches)
- Testing file filtering
- Testing when some files have no matches

## Quick Test Commands

### Basic Commands
```bash
# Basic match
grepnet '192.0.2.0/24' sample_networks.txt

# No match
grepnet '203.0.114.0/24' sample_networks.txt

# Multiple files
grepnet '192.0.2.0/24' file1.txt file2.txt
```

### Match Types
```bash
# Test equals
grepnet -e '192.0.2.0/24' match_types.txt

# Test subset (find smaller networks in file)
grepnet -s '192.0.2.0/24' match_types.txt

# Test superset (find larger networks in file)
grepnet -S '192.0.2.0/24' match_types.txt

# Test overlap
grepnet -O '192.0.2.0/24' match_types.txt
```

### Context
```bash
# After context (2 lines)
grepnet -A 2 '192.168.0.0/16' context_test.txt

# Before context (2 lines)
grepnet -B 2 '192.168.0.0/16' context_test.txt

# Both (2 lines before and after)
grepnet -C 2 '192.168.0.0/16' context_test.txt
```

### Output Options
```bash
# With line numbers
grepnet -n '192.0.2.0/24' sample_networks.txt

# With byte offset
grepnet -b '192.0.2.0/24' sample_networks.txt

# Count only
grepnet -c '192.168.' file1.txt file2.txt

# List files only
grepnet -l '192.0.2.0/24' file1.txt file2.txt file3.txt

# Files without matches
grepnet -L '192.0.2.0/24' file1.txt file2.txt file3.txt
```

### IPv6
```bash
# IPv6 CIDR
grepnet '2001:db8::/32' ipv6_test.txt

# IPv6 single address
grepnet '::1' ipv6_test.txt

# IPv6 range (requires --parse-ranges)
grepnet --parse-ranges '2001:db8::1-2001:db8::ff' ipv6_test.txt
```

### Formats
```bash
# JSON output
grepnet --output-format json '192.0.2.0/24' sample_networks.txt

# Table output
grepnet --output-format table '192.0.2.0/24' sample_networks.txt

# Only matching (just the network text)
grepnet -o '192.0.2.0/24' sample_networks.txt
```

### Comments
```bash
# Default: filter out comments
grepnet '10.1.0.0/16' comments_test.txt

# Include comments
grepnet --no-filter-comments '10.1.0.0/16' comments_test.txt
```

## Test Data Statistics

| File | Lines | Matches (192.0.2.0/24) | Matches (192.0.0.0/16) | Matches (10.*) |
|------|-------|------------------------|------------------------|----------------|
| sample_networks.txt | 14 | 3 | 1 | 2 |
| context_test.txt | 16 | 1 (line 7) | 1 (line 7) | 1 (line 13) |
| ipv6_test.txt | 10 | 0 | 0 | 0 |
| comments_test.txt | 13 | 2 | 0 | 1 |
| match_types.txt | 9 | 3 | 1 | 1 |
| file1.txt | 3 | 0 | 0 | 1 |
| file2.txt | 3 | 1 | 0 | 0 |
| file3.txt | 4 | 0 | 0 | 0 |

## Tips for Test Development

1. **Use line numbers**: Reference specific lines in tests using `-n` flag to verify exact behavior
2. **Use byte offsets**: Check binary handling with `-b` flag
3. **Use count mode**: Quick validation without processing large outputs
4. **Use -v (invert)**: Test negative matching logic
5. **Combine flags**: Test multiple options together (e.g., `-n -b -H`)
6. **Check exit codes**: Validate proper error handling with different scenarios

## Extending the Test Suite

### Adding New Data Files

Create new files following the naming convention:
```
tests/test_name.txt
```

### Creating Test Categories

Add new sections to `run_tests.sh`:
```bash
log_header "NEW TEST CATEGORY"

test_case "Test name" \
    "command" \
    expected_exit
```

### Adding Specific Format Tests

For specialized testing:
```bash
# Create format-specific file
cat > tests/format_test.txt << 'EOF'
format examples...
EOF
```
