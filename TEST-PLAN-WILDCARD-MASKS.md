# Test Plan: Wildcard Mask Support (--non-cidr-mask)

**Version**: 1.0  
**Scope**: Comprehensive testing for Cisco ACL wildcard mask notation parsing, expansion, and matching  
**Status**: Planning Phase

---

## Test Organization

Tests are organized into:
1. **Unit Tests** — Algorithm correctness (wildcard expansion, bit generation, CIDR aggregation)
2. **Parser Tests** — Parsing logic (mode detection, mask recognition, format type assignment)
3. **Integration Tests** — End-to-end workflows (file scanning, matching, output)
4. **Edge Case Tests** — Boundary conditions, error handling, guard rails
5. **Performance Tests** — Complexity validation, guard rail enforcement
6. **CLI Tests** — Command-line flag handling and validation
7. **Output Tests** — Colorization, format preservation, hint generation

---

## 1. Unit Tests: Wildcard Mask Expansion Algorithm

### 1.1 Basic Wildcard Expansion

**Test Case: Simple Contiguous Wildcard**
```
Input: 10.4.0.0 0.0.0.255
Expected: [10.4.0.0/24]
Reason: Wildcard covers all 256 addresses in final octet; contiguous; collapses to single /24
```

**Test Case: Non-Contiguous Wildcard (Even IPs)**
```
Input: 192.168.1.0 0.0.0.254
Expected: 128 individual /32 blocks (192.168.1.0/32, 192.168.1.2/32, ..., 192.168.1.254/32)
Reason: 7 wildcard bits, but they represent even addresses only (not contiguous); each is /32
Verify: Exactly 128 blocks, all are /32, covers all even addresses from .0 to .254
```

**Test Case: CIDR-Aligned Wildcard**
```
Input: 10.0.0.0 0.0.255.255
Expected: [10.0.0.0/16]
Reason: Wildcard masks exactly a /16 network; collapses to single CIDR block
```

**Test Case: High Wildcard Bits**
```
Input: 10.4.0.0 0.0.127.252
Expected: Minimal CIDR set covering ~8,192 addresses
Verify:
  - Exactly 8,192 addresses in collapsed result
  - No address outside 10.4.0.0 - 10.4.127.252
  - Last 2 bits of final octet are always 0 (per mask constraint)
  - CIDR blocks are properly aggregated
```

**Test Case: Full Wildcard (All 1s)**
```
Input: 0.0.0.0 255.255.255.255
Expected: [0.0.0.0/0] (the entire IPv4 space)
Reason: All bits are "don't care"; covers all possible IPs
Guard: Should trigger guard rail (24 wildcard bits > 20 limit)
```

### 1.2 Wildcard Bit Isolation

**Test Case: Verify Bit Position Detection**
```
Input wildcard: 0.0.0.255
Expected bit positions: [0, 1, 2, 3, 4, 5, 6, 7] (final octet)
Verify: Exactly 8 positions; all are contiguous from bit 0 to 7
```

**Test Case: Non-Contiguous Bit Positions**
```
Input wildcard: 0.0.127.252
Expected bit positions: [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14] (13 total, split across octets)
Verify: Bit positions correctly identified; count = 13; includes bits from octets 3 and 4
```

**Test Case: Single Bit Wildcard**
```
Input wildcard: 0.0.0.1
Expected: 2 addresses (base and base | 1)
```

### 1.3 Base IP Cleaning

**Test Case: Wildcard Bits Set in Base IP**
```
Input: 10.4.5.3 0.0.127.252
Process:
  - Clean base IP: 10.4.5.3 & ~(0.0.127.252) = 10.4.4.0 (clear wildcard bits)
  - Expected first IP: 10.4.4.0 (not 10.4.5.3)
Verify: Results start from cleaned base, not the provided base
```

### 1.4 CIDR Aggregation

**Test Case: Mergeable Consecutive Blocks**
```
Input: 10.0.0.0 0.0.1.255
Generates: All IPs from 10.0.0.0 to 10.0.1.255 (512 addresses)
Expected: Collapses to [10.0.0.0/23]
Verify: Aggregation is optimal; single /23 block covers all
```

**Test Case: Mixed Aggregatable Ranges**
```
Input: 10.4.0.0 0.0.127.252
Expected: Multiple CIDR blocks (/17, /18, /24, or mix)
Verify: Every generated IP is in the result; no duplicates; minimal block count
```

### 1.5 Guard Rail: Wildcard Bit Limit

**Test Case: Exactly 20 Wildcard Bits (Boundary)**
```
Input: 0.0.0.0 0.15.255.255 (20 wildcard bits)
Expected: Success; generate 2^20 = 1,048,576 addresses
Verify: No guard rail triggered; result is complete
```

**Test Case: 21 Wildcard Bits (Over Limit)**
```
Input: 0.0.0.0 0.31.255.255 (21 wildcard bits)
Expected: ValueError raised with message about exceeding 20-bit limit
Verify: Guard rail prevents computation; error is logged/reported
```

**Test Case: Massive Wildcard (24 Bits)**
```
Input: 0.0.0.0 0.255.255.255 (24 wildcard bits)
Expected: ValueError raised; computation not attempted
Verify: Guard rail prevents DoS; error message is clear
```

---

## 2. Parser Tests: Mode Detection and Recognition

### 2.1 MSB-Based Mode Detection

**Test Case: Hostmask Mode Detection (MSB = 0)**
```
Flag: --non-cidr-mask 0.0.0.0/17
Mode extracted: Hostmask
Parser behavior: Accept wildcard masks (1-bits = "don't care"); reject netmasks
```

**Test Case: Netmask Mode Detection (MSB = 1)**
```
Flag: --non-cidr-mask 255.255.128.0/17
Mode extracted: Netmask
Parser behavior: Accept traditional netmasks; reject wildcard/hostmask formats
```

**Test Case: Edge MSB Values**
```
Flag: --non-cidr-mask 128.0.0.0/1
Mode: Netmask (128 = 10000000 binary; MSB = 1)

Flag: --non-cidr-mask 127.255.255.255/25
Mode: Hostmask (127 = 01111111 binary; MSB = 0)
```

### 2.2 Wildcard Mask Recognition

**Test Case: Valid Wildcard Syntax**
```
Input line: "access-list 101 permit 10.4.0.0 0.0.127.252 any"
Mode: Hostmask (active)
Expected: Wildcard "10.4.0.0 0.0.127.252" recognized
Format type: 'non_cidr_mask'
Matched text: "10.4.0.0 0.0.127.252"
```

**Test Case: Wildcard with Extra Whitespace**
```
Input: "10.4.0.0  0.0.127.252" (double space)
Expected: Recognized as single wildcard (parser normalizes whitespace)
```

**Test Case: Rejected Wildcard in Wrong Mode**
```
Input: "10.4.0.0 0.0.127.252"
Mode: Netmask (via --non-cidr-mask 255.255.128.0/17)
Expected: Not recognized as wildcard; skipped; may be parsed as other format
```

**Test Case: Standard Subnet Mask Not Affected**
```
Input: "10.4.0.0 255.255.255.0"
Mode: Hostmask
Expected: Recognized as standard subnet mask (existing parser), not as wildcard
Format type: 'subnet_mask'
```

**Test Case: Inverse Mask Not Affected**
```
Input: "10.4.0.0 0.0.0.255"
Mode: Hostmask
Expected: Recognized as inverse mask (existing parser, contiguous 1-bits from right), not wildcard
Format type: 'inverse_mask'
```

### 2.3 Format Type Assignment

**Test Case: Format Type = 'non_cidr_mask'**
```
Input: "10.4.0.0 0.0.127.252" (wildcard mode, non-aligned)
Expected ParsedExtraction:
  - format_type: 'non_cidr_mask'
  - was_normalized: False
  - matched_texts: [{"text": "10.4.0.0 0.0.127.252", "was_normalized": False}]
```

**Test Case: Multiple Formats on Same Line**
```
Input: "match 192.0.2.0/24 or 10.4.0.0 0.0.127.252"
Expected: Two ParsedExtractions
  1. format_type: 'cidr_notation'
  2. format_type: 'non_cidr_mask'
```

---

## 3. Integration Tests: File Scanning and Matching

### 3.1 File Scanning with Wildcard Masks

**Test Case: Detect Wildcard in File Content**
```
File content:
  "deny 10.4.0.0 0.0.127.252 any"
  "permit 10.5.0.0/24 any"

Flag: --non-cidr-mask "0.0.0.0/16"

Expected extractions:
  Line 1: "10.4.0.0 0.0.127.252" (format: 'non_cidr_mask')
  Line 2: "10.5.0.0/24" (format: 'cidr_notation')
```

**Test Case: Comment Handling with Wildcard**
```
File:
  "10.4.0.0 0.0.127.252 # allow this range"

Expected:
  - Extract: "10.4.0.0 0.0.127.252"
  - Comment: "# allow this range" (not scanned)
  - Format type: 'non_cidr_mask'
  - Output: full line with comment preserved (uncolorized)
```

### 3.2 Pattern Matching: Wildcard vs Input

**Test Case: Wildcard Pattern Matches CIDR Input**
```
Pattern: "10.4.0.0 0.0.127.252" (wildcard mode)
Input line: "Found network: 10.4.64.0/25"

Expected:
  - Pattern expands to ~8,192 IPs
  - 10.4.64.0/25 matches EQUALS (exact set match)
  - Output: line matched
```

**Test Case: Wildcard Pattern Subset of Input**
```
Pattern: "10.4.0.0 0.0.0.255" (256 IPs, /24-equivalent)
Input: "10.4.0.0/16" (65,536 IPs)

Expected:
  - Match type: SUBSET (pattern is subset of input)
  - Output: line matched (if -s flag or default behavior)
```

**Test Case: Wildcard Pattern Superset of Input**
```
Pattern: "10.0.0.0 0.255.255.255" (all of 10.0.0.0/8)
Input: "10.4.0.0/24"

Expected:
  - Match type: SUPERSET (pattern contains input)
  - Output: line matched (if -S flag or default behavior)
```

**Test Case: Wildcard No Match**
```
Pattern: "10.0.0.0 0.0.0.255"
Input: "192.168.0.0/24"

Expected:
  - No match (ranges don't overlap)
  - Output: no line (unless -v or -u flags)
```

### 3.3 Matching with --equal, --subset, --superset Flags

**Test Case: -e (equals) with Wildcard**
```
Pattern: "10.4.0.0 0.0.0.255" (256 addresses)
Input 1: "10.4.0.0/24" → EQUALS → matched
Input 2: "10.4.0.0/23" → SUPERSET → not matched
Input 3: "10.4.0.100/32" → SUBSET → not matched
```

**Test Case: -s (subset) with Wildcard**
```
Pattern: "10.4.0.0 0.0.127.252" (~8,192 addresses)
Input 1: "10.4.0.0/16" → SUPERSET → not matched
Input 2: "10.4.1.0/24" → SUBSET → matched
Input 3: "10.0.0.0/8" → SUPERSET → not matched
```

### 3.4 Multiple Wildcard Masks

**Test Case: Multiple --non-cidr-mask Flags**
```
Flags:
  --non-cidr-mask "0.0.0.0/16" (hostmask mode)
  --non-cidr-mask "255.255.128.0/17" (netmask mode)

File:
  "10.0.0.0 0.0.255.255" (wildcard, hostmask mode active)
  "10.0.0.0 255.255.0.0" (netmask, netmask mode active)

Expected: Both lines recognized with format 'non_cidr_mask'
```

**Test Case: Space-Separated Masks in Single Flag**
```
Flag: --non-cidr-mask "0.0.0.0/16 0.0.0.0/24"

Expected: Both mode specifications apply (both hostmask mode)
Parser recognizes wildcards in both modes from same flag
```

---

## 4. Edge Cases and Boundary Conditions

### 4.1 Malformed Input

**Test Case: Invalid Wildcard Syntax**
```
Input: "10.4.0.0 0.0.127" (incomplete mask)
Expected: Not recognized as wildcard; skipped or parsed as other format
```

**Test Case: Missing Space**
```
Input: "10.4.0.00.0.127.252" (no space)
Expected: Not recognized as wildcard
```

**Test Case: Invalid IP Address in Wildcard**
```
Input: "10.4.256.0 0.0.127.252" (256 out of range)
Expected: Parse error or skipped
```

### 4.2 Boundary Wildcard Values

**Test Case: All-Zero Wildcard**
```
Input: "10.4.0.0 0.0.0.0"
Expected: Single IP only: 10.4.0.0/32
Reason: No wildcard bits; address is fully specified
```

**Test Case: All-One Wildcard**
```
Input: "0.0.0.0 255.255.255.255"
Expected: Guard rail triggered (24 bits > 20 limit)
Error: Computation refused
```

**Test Case: Single Octet Wildcard**
```
Input: "10.4.0.0 0.0.0.255"
Expected: [10.4.0.0/24] (single CIDR block)
```

### 4.3 Normalization Behavior

**Test Case: No Normalization for Wildcard Masks**
```
Input: "10.4.5.3 0.0.127.252"
Expected:
  - Base IP cleaned during expansion (5.3 bits cleared if they overlap with wildcard)
  - was_normalized: False (no normalization flag)
  - matched_texts shows original: "10.4.5.3 0.0.127.252"
Reason: Wildcard masks are always valid as-is; no "host bits" concept
```

---

## 5. Performance and Complexity Tests

### 5.1 Acceptable Performance

**Test Case: Small Wildcard (7 bits) Performance**
```
Input: "192.168.1.0 0.0.0.254"
Expected: Completes in <1ms
Iterations: 128
```

**Test Case: Medium Wildcard (15 bits) Performance**
```
Input: "10.0.0.0 0.0.127.254"
Expected: Completes in <100ms
Iterations: 32,768
```

**Test Case: Large Wildcard (20 bits) Performance**
```
Input: "0.0.0.0 0.15.255.255"
Expected: Completes in <5 seconds
Iterations: 1,048,576
Verify: No memory exhaustion; result is complete
```

### 5.2 Guard Rail Enforcement

**Test Case: 21 Bits Rejected**
```
Input: "0.0.0.0 0.31.255.255"
Expected: ValueError raised before computation
Verify: No delay; error immediate
```

**Test Case: 24 Bits Rejected**
```
Input: "0.0.0.0 0.255.255.255"
Expected: ValueError raised immediately
```

### 5.3 CIDR Aggregation Efficiency

**Test Case: Verify Minimal Block Count**
```
Input: "10.4.0.0 0.0.127.252"
Generate: 8,192 individual IPs
Collapse: Result should be minimal CIDR blocks (typically 10-50 blocks)
Verify: No unnecessary blocks; aggregation is optimal
```

---

## 6. CLI Tests

### 6.1 Flag Parsing

**Test Case: Valid Flag Format**
```
Command: grepnet --non-cidr-mask "0.0.0.0/17" pattern file.txt
Expected: Flag parsed; mode set; pattern and file processed
```

**Test Case: Multiple Flags**
```
Command: grepnet --non-cidr-mask "0.0.0.0/17" --non-cidr-mask "255.255.128.0/17" pattern file.txt
Expected: Both modes accumulated; both parsers respect their mode
```

**Test Case: Invalid Flag Format**
```
Command: grepnet --non-cidr-mask "0.0.0.0-17" pattern file.txt (dash instead of slash)
Expected: Error; exit code 2
Message: Clear error about invalid format
```

**Test Case: Missing Flag Value**
```
Command: grepnet --non-cidr-mask pattern file.txt (no address/prefix)
Expected: Error; exit code 2
```

### 6.2 Flag Interaction

**Test Case: With -P (pattern) Flag**
```
Command: grepnet --non-cidr-mask "0.0.0.0/16" -P "10.4.0.0 0.0.127.252" file.txt
Expected: Wildcard pattern recognized; mode from --non-cidr-mask applied
```

**Test Case: With -e, -s, -S Flags**
```
Command: grepnet --non-cidr-mask "0.0.0.0/16" -e pattern file.txt
Expected: Match type filter applied; only EQUALS matches output
```

**Test Case: With -n (line number)**
```
Command: grepnet --non-cidr-mask "0.0.0.0/16" -n pattern file.txt
Expected: Line numbers printed correctly
```

**Test Case: With --extract and --consolidate**
```
Command: grepnet --non-cidr-mask "0.0.0.0/16" --extract pattern file.txt
Expected: Wildcard format preserved in output; displayed as "network 0.0.0.0 X..."
```

---

## 7. Output and Display Tests

### 7.1 Colorization

**Test Case: Non-CIDR-Mask Color Code Applied**
```
Pattern: "10.4.0.0 0.0.127.252"
Input line: "config: 10.4.64.0/25"
Expected output: "config: " (plain) + "10.4.64.0/25" (colored with 'non_cidr_mask' code)
```

**Test Case: GREPNET_COLORS Environment Variable**
```
Set: export GREPNET_COLORS='non_cidr_mask=01;35'
Pattern: "10.4.0.0 0.0.127.252"
Input: "10.4.64.0/25"
Expected: Match colorized with bright magenta (01;35)
```

**Test Case: Color Stacking (Normalization + Match Type)**
```
Scenario: Wildcard match (non-CIDR-mask format) with match type EQUALS
Expected: Apply both 'non_cidr_mask' color and 'me=' (equals) color
Result: Combined ANSI codes
```

### 7.2 Hint Display

**Test Case: Hint for Wildcard Mask**
```
File: "access-list 101 permit 10.4.0.0 0.0.127.252 any"
Expected hint: "10.4.0.0 0.0.127.252" highlighted in 'non_cidr_mask' color
```

**Test Case: Hint Preserves Original Format**
```
File: "10.4.0.0 0.0.127.252"
Expected: Displayed as "10.4.0.0 0.0.127.252" (exact original text), not as CIDR
```

### 7.3 Extract and Consolidate Modes

**Test Case: --extract with Wildcard**
```
Command: grepnet --non-cidr-mask "0.0.0.0/16" --extract file.txt
File: "10.4.0.0 0.0.127.252"
Expected: Output lists the wildcard mask in original format or expanded CIDRs (per --format flag)
```

**Test Case: --consolidate with Wildcard**
```
Command: grepnet --non-cidr-mask "0.0.0.0/16" --consolidate file.txt
File:
  "10.4.0.0 0.0.127.252"
  "10.4.128.0/25"
Expected: Consolidated result merges both into minimal CIDR set
```

**Test Case: --format with Wildcard**
```
Command: grepnet --non-cidr-mask "0.0.0.0/16" --extract --format cidr file.txt
File: "10.4.0.0 0.0.127.252"
Expected: Output in CIDR format, not wildcard format
```

---

## 8. Error Handling Tests

### 8.1 Invalid Configurations

**Test Case: Invalid --non-cidr-mask Value**
```
Flag: --non-cidr-mask "not-an-ip/16"
Expected: Error; exit code 2
Message: "Invalid IP address in --non-cidr-mask flag"
```

**Test Case: Invalid Prefix Length**
```
Flag: --non-cidr-mask "0.0.0.0/33"
Expected: Error; exit code 2 (prefix out of range)
```

### 8.2 Wildcard Expansion Errors

**Test Case: Guard Rail Exceeded**
```
Pattern: "0.0.0.0 0.255.255.255" (24 wildcard bits)
Expected: ValueError during parsing
Exit code: 2
Message: Clear explanation about wildcard bit limit
```

### 8.3 File I/O Errors

**Test Case: File Not Found (existing behavior)**
```
Command: grepnet --non-cidr-mask "0.0.0.0/16" pattern nonexistent.txt
Expected: Standard file-not-found error; exit code 2
(Wildcard feature doesn't change existing error handling)
```

---

## 9. Regression Tests (Ensure Existing Functionality Unchanged)

### 9.1 Standard Formats Still Work

**Test Case: CIDR Still Recognized**
```
Command: grepnet "10.4.0.0/24" file.txt (no --non-cidr-mask)
Expected: Matches "10.4.0.0/24" normally; no wildcard parsing attempt
```

**Test Case: Subnet Mask Still Recognized**
```
Command: grepnet "10.4.0.0 255.255.255.0" file.txt (no --non-cidr-mask)
Expected: Matches "10.4.0.0 255.255.255.0" as standard subnet mask
```

**Test Case: Inverse Mask Still Recognized**
```
Command: grepnet "10.4.0.0 0.0.0.255" file.txt (no --non-cidr-mask)
Expected: Matches as inverse mask (existing behavior); not as wildcard
```

### 9.2 Comment Filtering Unchanged

**Test Case: Comments Still Filtered**
```
Command: grepnet --non-cidr-mask "0.0.0.0/16" "10.4.0.0/24" file.txt
File: "# 10.4.0.0/24"
Expected: Comment line excluded; not matched
```

### 9.3 Output Modes Unchanged

**Test Case: -n (line number) Works**
```
Command: grepnet --non-cidr-mask "0.0.0.0/16" -n pattern file.txt
Expected: Line numbers printed as usual
```

**Test Case: -H (with filename) Works**
```
Command: grepnet --non-cidr-mask "0.0.0.0/16" -H pattern file1.txt file2.txt
Expected: Filenames printed as usual
```

---

## 10. Test Execution Plan

### Test Automation Framework

**Language**: Python (matching grepnet implementation)

**Tools**:
- `unittest` or `pytest` for unit/integration tests
- Test fixtures for sample files and patterns
- Parametrized tests for bulk case coverage

### Test Data

**Sample Wildcard Masks**:
```
10.4.0.0 0.0.127.252          # Primary example
192.168.1.0 0.0.0.254         # Even IPs only
10.0.0.0 0.255.255.255        # /16 network
0.0.0.0 255.255.255.255       # Full space (guard rail)
```

**Sample CIDR/Mask Files**:
```
Cisco ACL format:
  deny 10.4.0.0 0.0.127.252 any
  permit 10.5.0.0/24 any
  remark Allow internal networks

Mixed format:
  192.0.2.0/24
  10.4.0.0 0.0.127.252
  172.16.0.0 255.255.0.0
```

### Success Criteria

- ✅ All unit tests pass (algorithm correctness)
- ✅ All parser tests pass (mode detection, recognition)
- ✅ All integration tests pass (end-to-end workflows)
- ✅ All edge case tests pass (boundary conditions, error handling)
- ✅ Performance tests validate O(2^N) complexity
- ✅ Guard rail prevents wildcard bits > 20
- ✅ All regression tests pass (existing functionality unchanged)
- ✅ CLI tests validate flag parsing and interaction
- ✅ Output tests validate colorization and display
- ✅ No new bugs introduced; test coverage > 85%

---

## 11. Known Test Gaps (Future Enhancement)

- IPv6 wildcard masks (currently IPv4-only, documented as future)
- Stress testing with production ACL files (file size, line count)
- Memory profiling for large wildcard expansions (20-bit range)
- Parallel processing considerations (if implemented later)

