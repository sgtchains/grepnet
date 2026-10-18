# GREPNET-SPEC.md: Required Changes for Wildcard Mask Support

**Status**: Reflects actual implementation (Phases 1-6 complete)

This document details all modifications required to the existing GREPNET-SPEC.md to integrate Cisco ACL wildcard mask support.

---

## 1. Data Structures Section

### Location
Section: **"Data Structures"** (around line 300)

### Change 1.1: Add WildcardMaskRange Object (NEW)

**After the IPRange Object section, insert:**

```markdown
### 2. WildcardMaskRange Object

Represents Cisco ACL wildcard mask notation using network address and wildcard mask (non-CIDR-aligned).

**Fields**:
- `original_text`: String representation of the wildcard mask notation (e.g., `"10.4.0.0 0.0.127.252"`)
  - Stored as-is from input for display purposes
  - Format: "{base_ip} {wildcard_mask}"
- `expanded_cidrs`: List of IPv4Network objects representing the constituent CIDR blocks that exactly cover the IP range specified by the wildcard mask
  - Already aggregated into minimal set using `ipaddress.collapse_addresses()`
  - Example: `"10.4.0.0 0.0.127.252"` expands to multiple /24, /25 blocks covering 10.4.0.0-10.4.127.252

**Purpose**: Support Cisco ACL wildcard mask notation (e.g., `10.4.0.0 0.0.127.252`). Internally expanded into constituent CIDRs using standard wildcard mask computation for matching, but preserves original format for display.

**Key property**: Two WildcardMaskRange objects are equal if their original_text and expanded_cidrs are identical. The expanded_cidrs set represents the exact IP space covered.

**Wildcard Mask Computation**: Based on standard Cisco ACL algorithm:
- Range: [network_address & ~wildcard_mask, (network_address & ~wildcard_mask) | wildcard_mask]
- Valid IPs: Only those where (ip & ~wildcard_mask) == (network_address & ~wildcard_mask)
  - 1-bits in wildcard mask = "don't care" (can be 0 or 1)
  - 0-bits in wildcard mask = "must match exactly"

**Example**:
```
Input: 10.4.0.0 0.0.127.252
Interpretation:
  - Base: 10.4.0.0
  - Wildcard: 0.0.127.252 (binary: ...01111111.11111100)
  - 1-bits at positions allow variation, 0-bits must match
Valid IP range: 10.4.0.0 through 10.4.127.252 (constrained by 0-bits)
Valid count: ~32K addresses matching (ip & ~mask) == (base & ~mask)
expanded_cidrs: [10.4.0.0/25, 10.4.1.0/25, ..., 10.4.127.0/25] (aggregated)
```
```

### Change 1.2: Update ParsedExtraction Tuple

**Find and replace the ParsedExtraction section (around line 333):**

**OLD**:
```python
- `format_type`: String indicating how it was found:
  - `'cidr_notation'` (e.g., `192.0.2.0/24`)
  - `'subnet_mask'` (IPv4 only, e.g., `192.0.2.0 255.255.255.0`)
  - `'inverse_mask'` (IPv4 only, Cisco hostmask, e.g., `192.0.2.0 0.0.0.255`)
  - `'ipv4_range'` (e.g., `192.0.2.0-192.0.2.255`)
  - `'ipv6_range'` (e.g., `2001:db8::0-2001:db8::255`)
  - `'ip_only'` (single IP, treated as /32 or /128)
```

**NEW**:
```python
- `format_type`: String indicating how it was found:
  - `'cidr_notation'` (e.g., `192.0.2.0/24`)
  - `'subnet_mask'` (IPv4 only, e.g., `192.0.2.0 255.255.255.0`)
  - `'inverse_mask'` (IPv4 only, Cisco hostmask, e.g., `192.0.2.0 0.0.0.255`)
  - `'wildcard_mask'` (IPv4 only, Cisco wildcard mask, e.g., `10.4.0.0 0.0.127.252`; requires `--parse-wildcard {pattern|input|both}` and `--wildcard-search` to enable parsing)
  - `'ipv4_range'` (e.g., `192.0.2.0-192.0.2.255`)
  - `'ipv6_range'` (e.g., `2001:db8::0-2001:db8::255`)
  - `'ip_only'` (single IP, treated as /32 or /128)
```

### Change 1.3: Update ParsedExtraction matched_texts structure

**In the ParsedExtraction section, after the matched_texts list example, add:**

```python
**Note on wildcard_mask format**: When format_type is 'wildcard_mask', the matched_texts list contains the original space-separated Cisco wildcard mask notation (e.g., `"10.4.0.0 0.0.127.252"`). No normalization occurs for wildcard mask format; `was_normalized` is always False for this format type.
```

### Change 1.4: Update FileEntry Object

**Find and replace the FileEntry section (around line 380):**

**OLD**:
```python
FileEntry = {
  'network': (Network or IPRange object),
  'format_type': (format_type string from ParsedExtraction),
  'line_number': (1-based line number),
  'line_content': (raw line text, newline stripped),
  'matched_texts': (list of {"text": str, "was_normalized": bool} dicts),
  'was_normalized': (boolean - True if ANY matched text was normalized)
}
```

**NEW**:
```python
FileEntry = {
  'network': (Network or IPRange or WildcardMaskRange object),
  'format_type': (format_type string from ParsedExtraction),
  'line_number': (1-based line number),
  'line_content': (raw line text, newline stripped),
  'matched_texts': (list of {"text": str, "was_normalized": bool} dicts),
  'was_normalized': (boolean - True if ANY matched text was normalized)
}
```

### Change 1.5: Update MatchResult Object

**In the MatchResult section, update the network field note:**

**OLD**:
```
- `file_extraction.network`: IPv4Network, IPv6Network, or tuple(start_int, end_int) for ranges
```

**NEW**:
```
- `file_extraction.network`: IPv4Network, IPv6Network, WildcardMaskRange, or tuple(start_int, end_int) for ranges
  - WildcardMaskRange.original_text is used for display
  - WildcardMaskRange.expanded_cidrs is used for matching (see Matching Logic)
```

---

## 2. Color and Output System Section

### Location
Section: **"Color Codes"** (around line 450)

### Change 2.1: Update Color Code Categories

**Find the GREPNET_COLORS reference and add:**

```markdown
## Color Codes for Wildcard Mask Format

When `--parse-wildcard` is enabled and wildcard masks are found:

- **Color code name**: `'wildcard_mask'`
- **Color code value**: (customizable via environment variable, default: bright cyan/magenta)
- **Markup encoding**: `OBJ:WILDCARD_MASK`
- **Applies to**: Cisco ACL wildcard mask notation in both original format and expanded CIDR display modes
- **Example output**: 
  ```
  deny [COLORED: 10.4.0.0 0.0.127.252] any
  ```
  where `10.4.0.0 0.0.127.252` is colored with the wildcard_mask color code
```

### Change 2.2: Add Environment Variable Documentation

**In the GREPNET_COLORS environment variable section, add:**

```markdown
#### Wildcard Mask Color Code

- **Variable**: `GREPNET_COLORS['wildcard_mask']`
- **Default**: `\033[38;5;75m` (or platform-specific equivalent)
- **Usage**: Controls color for Cisco ACL wildcard mask notation when `--parse-wildcard` is enabled
- **Example**: Set to bright magenta for high visibility:
  ```bash
  export GREPNET_COLORS='{"wildcard_mask": "\033[38;5;201m"}'
  ```
```

---

## 3. Network Parsing Pipeline Section

### Location
Section: **"Network Parsing Pipeline"** (around line 650)

### Change 3.1: Add Wildcard Mask Parsing Documentation

**After the Inverse Mask Parsing section, insert:**

```markdown
### Wildcard Mask Notation Parsing (Cisco ACL)

**Pattern**: `{base_ip} {wildcard_mask}`
- Example: `10.4.0.0 0.0.127.252`
- Base IP: Valid IPv4 address (e.g., 10.4.0.0)
- Wildcard Mask: Valid IPv4 address (e.g., 0.0.127.252)
  - 1-bits indicate "don't care" positions
  - 0-bits indicate "must match exactly"

**Activation**: Requires both flags:
1. `--parse-wildcard {pattern|input|both}` - WHERE to look for wildcard masks
2. `--wildcard-search CIDR` - WHICH scope to consider valid
   - Example: `--parse-wildcard input --wildcard-search 0.0.0.0/8`
   - Only masks falling within the scope are recognized as wildcard masks
   - Out-of-scope masks are rejected and fall back to other extractors

**Extraction Pipeline Position**: Index 3 (after Inverse Mask, before IP Range)
1. CIDR Extractor
2. Subnet Mask Extractor
3. Inverse Mask Extractor
4. **Wildcard Mask Extractor** ← HERE
5. IP Range Extractor
6. IPv6 Extractor
7. IP Only Extractor

**Processing**:
1. Detect pattern: space-separated IPv4 address pair
2. Validate both are valid IPv4 addresses
3. Check if mask falls within `--wildcard-search` scope
4. Verify mask is NOT CIDR-aligned (inverse mask extractor already caught CIDR-aligned masks)
5. Expand wildcard mask to constituent CIDR blocks:
   - Algorithm: Combinatorial bit generation (all 2^N bit combinations)
   - Aggregation: Use `ipaddress.collapse_addresses()` to minimize CIDR set
   - Result: List of minimal IPv4Network objects
6. Create WildcardMaskRange(original_text, expanded_cidrs)
7. Return as ParsedExtraction with format_type='wildcard_mask'

**IMPORTANT**: Only non-CIDR-aligned masks are processed here. CIDR-aligned masks (e.g., `0.255.255.255` matching "all zeros followed by all ones") are caught by the Inverse Mask Extractor first.

**Expansion Example**:
```
Input: "10.0.0.0 0.0.3.255"
Wildcard bits: 14 (0-13 in octet 2, bits 0-7 in octet 3)
Algorithm: Generate all 2^14 combinations = 16,384 IP addresses
Collapse: Aggregate into minimal CIDR set
Result: [10.0.0.0/22, 10.0.4.0/22, ...]
Output: WildcardMaskRange("10.0.0.0 0.0.3.255", [10.0.0.0/22, 10.0.4.0/22, ...])
```

**Scope Filtering**:
- If `--wildcard-search 10.0.0.0/8` is set:
  - Mask `10.0.0.0 0.0.1.255` → within scope → PROCESS
  - Mask `192.168.0.0 0.0.1.255` → outside scope → REJECT → fall back to other extractors
- If `--wildcard-search` is not set:
  - Wildcard parsing is disabled (CLI validates this)

**DoS Protection**:
- No hard limit on wildcard bits (removed; higher pipeline handles limits)
- Scope requirement (`--wildcard-search`) acts as explicit user consent
- Out-of-scope check is O(1) operation, prevents expensive expansion
```

---

## 4. Command-Line Interface Specification Section

### Location
Section: **"Command-Line Interface"** (around line 800)

### Change 4.1: Add Wildcard Mask Parsing Flags

**After the existing format flags, insert:**

```markdown
#### Wildcard Mask Parsing (`--parse-wildcard` and `--wildcard-search`)

**Purpose**: Detect and parse Cisco ACL wildcard mask notation (e.g., `10.4.0.0 0.0.127.252`)

**Flag 1: `--parse-wildcard`**
```
--parse-wildcard {none|pattern|input|both}
```

- **Default**: `none` (wildcard parsing disabled)
- **Values**:
  - `none`: Wildcard masks are NOT parsed (treated as two separate IPs)
  - `pattern`: Parse wildcard masks only in pattern(s), not in input files
  - `input`: Parse wildcard masks only in input file(s), not in pattern(s)
  - `both`: Parse wildcard masks in both pattern(s) and input file(s)
- **Behavior**: Specifies WHERE to look for wildcard masks
  - When set, NetworkParser uses WildcardMaskExtractor at position 3
  - Extractor checks if mask is within `--wildcard-search` scope
  - Out-of-scope masks fall back to other extractors (e.g., two separate IPs)
- **Example**:
  ```bash
  grepnet --parse-wildcard input --wildcard-search 10.0.0.0/8 pattern.txt data.conf
  # Parses wildcard masks ONLY in data.conf, treats pattern as literal
  ```

**Flag 2: `--wildcard-search`**
```
--wildcard-search CIDR
```

- **Required if**: `--parse-wildcard` is not `none`
- **Value**: Valid CIDR notation (e.g., `10.0.0.0/8`, `0.0.0.0/0`)
- **Purpose**: Defines scope boundary for wildcard mask recognition
  - Only masks whose entire range falls within this CIDR are recognized
  - Out-of-scope masks are rejected and fall back to other extractors
  - Acts as explicit user consent: "Only consider wildcard masks within this scope"
- **Behavior**:
  1. Extractor receives candidate mask pair
  2. Expands mask (potentially expensive operation)
  3. Checks if any expanded CIDR falls outside scope
  4. If outside: returns None (rejected), other extractors try it
  5. If inside: returns WildcardMaskRange
- **Example**:
  ```bash
  grepnet --parse-wildcard both --wildcard-search 192.168.0.0/16 -f pattern.txt data.conf
  # Only masks within 192.168.0.0/16 are parsed; others become two IPs
  ```

**Interaction**: Both flags work together
- `--parse-wildcard` controls WHERE to look
- `--wildcard-search` controls WHICH masks to accept
- If `--parse-wildcard=none`, `--wildcard-search` is ignored (validation warning)
- If `--parse-wildcard` is not `none`, `--wildcard-search` is REQUIRED (validation error)

---

## 5. Environment Variables Section

### Location
Section: **"Environment Variables"** (around line 950)

### Change 5.1: Update GREPNET_COLORS Documentation

**In the GREPNET_COLORS environment variable section, add 'wildcard_mask':**

```markdown
### GREPNET_COLORS

Dictionary of color codes (ANSI escape sequences) for network format types.

**Format**:
```json
{
  "cidr": "\033[38;5;33m",           // CIDR notation
  "subnet_mask": "\033[38;5;33m",    // Subnet mask notation
  "inverse_mask": "\033[38;5;51m",   // Cisco inverse mask (hostmask)
  "wildcard_mask": "\033[38;5;75m",  // Cisco wildcard mask (NEW)
  "range": "\033[38;5;220m",         // IP ranges
  "bare_ip": "\033[38;5;150m",       // Single IP addresses
  "equals": "\033[38;5;34m",         // EQUALS match type
  "subset": "\033[38;5;226m",        // SUBSET match type
  "superset": "\033[38;5;226m",      // SUPERSET match type
  "overlap": "\033[38;5;208m"        // OVERLAP match type
}
```

**New Entry: `wildcard_mask`**
- **Default**: `\033[38;5;75m` (bright cyan)
- **Purpose**: Color for Cisco ACL wildcard mask notation
- **Example**: Override to bright magenta:
  ```bash
  export GREPNET_COLORS='{"wildcard_mask": "\033[38;5;201m"}'
  ```
```

---

## 6. Hints and Scanning Section

### Location
Section: **"Hints and Scanning"** (around line 1000)

### Change 6.1: Add Wildcard Mask Hint Detection

**After the Inverse Mask Hint section, add:**

```markdown
### Hint Detection for Wildcard Masks

**Scan Pattern**: Detects space-separated IPv4 address pairs where the second address could be a wildcard mask

**Hint Format**: `"10.4.0.0 0.0.127.252"` (same as extraction pattern)

**Behavior When `--scan-mask both|input`**:
1. Scans first 8KB of file for hint
2. If found, sets `mask_format_hint='wildcard_mask'` for parser
3. Parser uses hint to prioritize wildcard mask detection
4. Reduces false positives (mask ambiguity: is it subnet mask or wildcard mask?)

**Behavior When `--scan-mask cidr|none`**:
- Wildcard mask hints are NOT scanned
- Parser must still detect them explicitly if `--parse-wildcard` is enabled

**Note**: Hint detection does NOT enable parsing; `--parse-wildcard` must still be set separately.
```

---

## 7. Exit Codes and Error Handling Section

### Location
Section: **"Exit Codes and Error Handling"** (around line 1050)

### Change 7.1: Add Error Handling for Wildcard Masks

**In the error codes section, add:**

```markdown
#### Wildcard Mask Errors

**Error Code 2: Invalid wildcard mask configuration**
- **Cause**: `--parse-wildcard` is not `none` but `--wildcard-search` is not provided
- **Message**: `"Error: --wildcard-search CIDR is required when --parse-wildcard is not 'none'"`
- **Action**: User must provide `--wildcard-search` flag with valid CIDR

**Error Code 2: Invalid wildcard search scope**
- **Cause**: `--wildcard-search` is not valid CIDR notation
- **Message**: `"Error: --wildcard-search value is not valid CIDR notation: {value}"`
- **Action**: User must provide valid CIDR (e.g., `0.0.0.0/0`, `10.0.0.0/8`)

**Note**: Malformed wildcard masks in input do NOT cause errors:
- They are simply rejected by the extractor
- Other extractors attempt to parse them (e.g., as two separate IPs)
- Processing continues normally
```

---

## 8. Matching Logic Section

### Location
Section: **"Matching Logic"** or **"Network Comparison"** (NEW or around line 1150)

### Change 8.1: Add Wildcard Mask Matching Documentation

**Insert new section:**

```markdown
### Matching: WildcardMaskRange Support

**Overview**: WildcardMaskRange objects are compared using their expanded_cidrs set against pattern networks.

**Match Type Determination**:

When comparing WildcardMaskRange (file_network) against pattern:

1. **EQUALS**: Any expanded CIDR equals the pattern exactly
   - Example: File has wildcard mask expanding to [10.0.0.0/25, 10.0.1.0/25]; pattern is 10.0.0.0/25 → EQUALS

2. **SUBSET**: Pattern is a subnet of ANY expanded CIDR
   - Example: File has [10.0.0.0/24]; pattern is 10.0.0.0/25 (subset of 10.0.0.0/24) → SUBSET

3. **SUPERSET**: Pattern is a superset that covers ALL expanded CIDRs
   - Example: File has [10.0.0.0/25, 10.0.1.0/25]; pattern is 10.0.0.0/23 (covers both) → SUPERSET

4. **OVERLAP**: Pattern shares address space with expanded CIDRs but is neither subset nor superset
   - Example: File has [10.0.0.0/24, 10.0.2.0/24]; pattern is 10.0.1.0/24 (doesn't match either, but overlaps space)
   - Note: With CIDR networks this is impossible, but wildcard masks have gaps, enabling true partial overlap

5. **UNMATCHED**: No relationship found

**Priority Order**: EQUALS > SUBSET > SUPERSET > OVERLAP > UNMATCHED

**Reverse Matching**: Same logic applies if pattern is WildcardMaskRange and file is CIDR
```

---

## 9. Summary of New/Modified Structures

### New Elements:

1. **Data Structure**:
   - `WildcardMaskRange(original_text: str, expanded_cidrs: list[IPv4Network])`

2. **Format Type**:
   - `'wildcard_mask'` (in ParsedExtraction.format_type)

3. **Color Code**:
   - `'wildcard_mask'` key in GREPNET_COLORS

4. **CLI Flags**:
   - `--parse-wildcard {none|pattern|input|both}`
   - `--wildcard-search CIDR`

5. **Extractor**:
   - `WildcardMaskExtractor` (position 3 in pipeline)

6. **Matching**:
   - Support for WildcardMaskRange in _find_match_type()

### Modified Elements:

1. **ParsedExtraction**:
   - Added `'wildcard_mask'` to format_type values
   - network field now accepts WildcardMaskRange

2. **Network Parsing Pipeline**:
   - Added WildcardMaskExtractor at index 3
   - Extraction order: CIDR → Subnet Mask → Inverse Mask → **Wildcard Mask** → Range → IPv6 → Bare IP

3. **FORMAT_TYPE_MAP**:
   - Added `'wildcard_mask': 'WILDCARD_MASK'` mapping

4. **Matching Logic** (_find_match_type):
   - Added support for WildcardMaskRange in both file and pattern positions
   - Uses OVERLAP for partial matches with wildcard masks

### Unchanged Principles:

1. **"All Input Is Input"**: Wildcard masks are parsed consistently in patterns and input
2. **CIDR Alignment**: Masks that ARE CIDR-aligned go to Inverse Mask Extractor first (unchanged)
3. **Format Priority**: CIDR > Subnet Mask > Inverse Mask > **Wildcard Mask** > Range > Bare IP
4. **Match Type Set**: Still uses EQUALS, SUBSET, SUPERSET, OVERLAP, UNMATCHED (no new types)
5. **Display**: matched_texts preserves original format for display

### Implementation Complexity:

- **Phases 1-6 complete**: Data structures, extraction, parsing, matching implemented
- **Phases 7-9 pending**: Colorization, error handling, testing
- **Total lines of code added**: ~600+ lines across 5 files
- **Backward compatibility**: Fully maintained (wildcard parsing is opt-in via flags)

