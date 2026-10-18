# GREPNET-SPEC.md: Required Changes for Wildcard Mask Support

This document details all modifications required to the existing GREPNET-SPEC.md to integrate Cisco ACL wildcard mask support (also known as non-CIDR-aligned mask notation).

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
- `network_address`: IP address representing the network base (e.g., `10.4.0.0`)
- `wildcard_mask`: IP address representing the "don't care" bits (e.g., `0.0.127.252`)
  - **1-bits** = "don't care" (can be 0 or 1)
  - **0-bits** = "must match exactly"
- `expanded_cidrs`: List of Network objects representing the constituent CIDR blocks that fit this wildcard mask profile
- `family`: Address family (4 for IPv4, 6 for IPv6)

**Purpose**: Support Cisco ACL wildcard mask notation (e.g., `10.4.0.0 0.0.127.252`). Internally expanded into constituent CIDRs using standard wildcard mask computation for matching, but preserves original format for display.

**Key property**: Two WildcardMaskRange objects are equal if their expanded_cidrs sets are equal (regardless of whether the wildcard mask bytes align with CIDR boundaries).

**Wildcard Mask Computation**: Based on standard Cisco ACL algorithm:
- Range: [network_address, network_address | wildcard_mask]
- Valid IPs: Only those where (ip & ~wildcard_mask) == (network_address & ~wildcard_mask)

**Example**:
```
Input: 10.4.0.0 0.0.127.252
network_address: 10.4.0.0
wildcard_mask: 0.0.127.252 (binary: 00000000.00000000.01111111.11111100)
Interpretation: 1-bits allow variation, 0-bits must match exactly
Valid range: 10.4.0.0 through 10.4.127.252 (with constraint that last 2 bits are 0)
Valid IPs: ~8,192 addresses matching the constraint
expanded_cidrs: (minimal CIDR set covering exactly these IPs)
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
  - `'non_cidr_mask'` (IPv4 only, Cisco wildcard mask, e.g., `10.4.0.0 0.0.127.252`; requires `--non-cidr-mask` flag to enable parsing)
  - `'ipv4_range'` (e.g., `192.0.2.0-192.0.2.255`)
  - `'ipv6_range'` (e.g., `2001:db8::0-2001:db8::255`)
  - `'ip_only'` (single IP, treated as /32 or /128)
```

### Change 1.3: Update ParsedExtraction matched_texts structure

**In the ParsedExtraction section, after the matched_texts list example, add:**

```python
**Note on non_cidr_mask format**: When format_type is 'non_cidr_mask', the matched_texts list contains the original space-separated Cisco wildcard mask notation (e.g., `"10.4.0.0 0.0.127.252"`). No normalization occurs for wildcard mask format; `was_normalized` is always False for this format type.
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
'was_normalized': (boolean - True if ANY matched text was normalized),
'original_text': (original format string for display; primarily used for 'non_cidr_mask' format, e.g., "10.4.0.0 0.0.127.252")
}
```

### Change 1.5: Update MatchResult Object

**Find and replace the MatchResult section (around line 400), updating the 'discovered' object:**

**OLD**:
```python
'format_type': (format_type string: 'cidr_notation', 'subnet_mask', 'inverse_mask', 'ipv4_range', 'ipv6_range', 'ip_only'),
```

**NEW**:
```python
'format_type': (format_type string: 'cidr_notation', 'subnet_mask', 'inverse_mask', 'non_cidr_mask', 'ipv4_range', 'ipv6_range', 'ip_only'),
```

---

## 2. Color and Output System Section

### Location
Section: **"Color and Output System"** (around line 430)

### Change 2.1: Update Color Code Categories

**Find the OBJ values section in the Color Rendering Process and update:**

**OLD**:
```
OBJ values: CIDR, BARE_IP, RANGE, SUBNET_MASK, INVERSE_MASK
```

**NEW**:
```
OBJ values: CIDR, BARE_IP, RANGE, SUBNET_MASK, INVERSE_MASK, NON_CIDR_MASK
```

### Change 2.2: Add Environment Variable Documentation

**Add a new subsection after "Color Rendering Process":**

```markdown
### Color Codes for Wildcard Mask Format

The `non_cidr_mask` format uses a single unified color code for Cisco ACL wildcard mask notation (both hostmask-style and netmask-style, though primarily hostmask-style with MSB=0).

**Color variable**:
- `GREPNET_COLORS`: When extended, includes color code for 'non_cidr_mask' format (wildcard mask notation)
  - Default: `export GREPNET_COLORS='... non_cidr_mask=01;36 ...'` (bright cyan)
  - The single color code applies to all wildcard mask matches regardless of MSB mode

**Example customization**:
```bash
export GREPNET_COLORS='me=01;32 mb=01;34 mS=01;33 mo=00 mu=00 mn=04 fn=01;35 ln=01;31 bn=01;32 se=37 non_cidr_mask=01;36'
```
```

---

## 3. Network Parsing Pipeline Section

### Location
Section: **"Network Parsing Pipeline"** (check line numbers, typically around line 800+)

### Change 3.1: Add Wildcard Mask Parsing Documentation

**After the CIDR Notation Parsing subsection, add a new subsection:**

```markdown
### Wildcard Mask Notation Parsing (Cisco ACL)

**Format**: IP address followed by space and a wildcard mask (IPv4 only).

**Pattern Examples** (Cisco ACL notation):
- Wildcard mask (MSB=0): `10.4.0.0 0.0.127.252` (1-bits = "don't care", 0-bits = "must match exactly")
- Netmask (MSB=1): `10.4.0.0 255.255.128.0` (if not already parsed as standard netmask; 1-bits = network, 0-bits = host)

**Enabled By**: The `--non-cidr-mask` flag determines whether and what type of mask to recognize.

**Parsing Logic**:

1. **Mode Detection** (at startup, from `--non-cidr-mask` flag):
   - Extract address component of flag (e.g., `0.0.0.0` from `0.0.0.0/17`)
   - Compute MSB of address first octet: `(address[0] & 0x80)`
   - If MSB = 0 → **Wildcard hostmask mode**: Look for wildcard masks where 1-bits = "don't care"
   - If MSB = 1 → **Netmask mode**: Look for traditional netmasks where 1-bits = network bits

2. **Runtime Parsing** (when scanning patterns or input):
   - After standard parsers (CIDR, subnet mask, inverse mask, etc.) fail to match
   - Check if `--non-cidr-mask` mode is active
   - Attempt to match pattern: `ADDRESS SPACE MASK_VALUE` where:
     - `ADDRESS` is a valid IPv4 address (e.g., `10.4.0.0`)
     - `MASK_VALUE` is a valid IPv4 address not already recognized as standard subnet/inverse mask
   - If match found, validate mask alignment:
     - **Wildcard hostmask mode** (MSB=0): Accept any mask pattern (1-bits indicate "don't care" positions)
     - **Netmask mode** (MSB=1): Validate bits are contiguous from MSB (standard netmask constraint)
   - If validation passes:
     - Expand into constituent CIDR blocks using standard Cisco wildcard mask algorithm
     - Create WildcardMaskRange object with original text
     - Return ParsedExtraction with format_type='non_cidr_mask'
   - If validation fails: Skip this format (move to next parser)

3. **Expansion to CIDR Blocks (Combinatorial Bit Generation - Standard Cisco Algorithm)**:
   - **Wildcard mask convention**: 1-bits = "don't care", 0-bits = "must match exactly"
   - **Algorithm** (5 steps):
     1. Convert base IP and wildcard mask to 32-bit unsigned integers
     2. Zero out all wildcard bit positions in base IP: `base_ip & ~wildcard_mask`
     3. Find all bit positions where wildcard has a 1-bit
     4. Generate all combinations: Loop from 0 to (2^N - 1), where N = count of 1-bits
        - For each iteration, overlay the binary counter onto wildcard bit positions
        - Combine with the cleaned base IP to create a valid network address
     5. Use standard CIDR aggregation (e.g., `ipaddress.collapse_addresses()`) to collapse contiguous IPs into minimal CIDR block set
   - **Time complexity**: O(2^N) where N = number of 1-bits in wildcard
     - Guard: Warn or reject if N > 20 (over 1 million combinations, risk of DoS)

**Examples**:

- Input: `10.4.0.0 0.0.127.252` (wildcard hostmask mode active via `--non-cidr-mask "0.0.0.0/17"`)
  - Network: `10.4.0.0`
  - Wildcard mask: `0.0.127.252` (binary: 00000000.00000000.01111111.11111100)
  - Wildcard interpretation: Last 2 bits of octet 4 must be 0; octets 1-2 must be 10.4; bits 0-6 of octet 3 can vary
  - Valid IP count: 8,192 (2^13 combinations within constraint)
  - Expanded CIDRs: (minimal CIDR set covering exactly these valid IPs)
  - Format type: `'non_cidr_mask'`

- Input: `10.4.0.0 255.255.128.0` (netmask mode active via `--non-cidr-mask "255.255.128.0/17"`)
  - Network: `10.4.0.0`
  - Netmask: `255.255.128.0` (binary: 11111111.11111111.10000000.00000000)
  - Netmask interpretation: Network is 10.4.0.0/17 (standard)
  - Expanded CIDRs: [IPv4Network('10.4.0.0/17')]
  - Format type: `'non_cidr_mask'`

**Non-matching examples**:
- Input: `10.4.0.0 0.0.127.252`, mode is netmask (MSB=1) → Skipped (wildcard mask rejected in netmask mode)
- Input: `10.4.0.0 255.255.128.0`, mode is wildcard hostmask (MSB=0) → Skipped (netmask rejected in wildcard mode)
- Input: `10.4.0.0 255.255.128.0`, no `--non-cidr-mask` flag → Treated as two separate values or single standard subnet mask (existing parser behavior)

**Key Invariant**: WildcardMaskRange objects maintain both the original text (e.g., "10.4.0.0 0.0.127.252") and the expanded CIDR representation. For matching operations, the expanded CIDRs are used. For display/hints, the original text is shown.
```

---

## 4. Command-Line Interface Specification Section

### Location
Section: **"Command-Line Interface Specification"** (around line 2462)

### Change 4.1: Add Non-CIDR-Mask Flag

**In the "Pattern/File Input" subsection, after the `-f, --patterns-file` entry, add:**

```markdown
--non-cidr-mask SPEC             Enable non-CIDR-aligned mask parsing (repeatable)
                                 SPEC format: "address/prefix" where address MSB determines mode:
                                   MSB=0 (e.g., 0.0.0.0/17): hostmask mode
                                   MSB=1 (e.g., 255.255.128.0/17): netmask mode
                                 Multiple flags accumulate.
```

### Change 4.2: Expand Non-CIDR-Mask Documentation

**After the Complete Argument List section, add a new subsection:**

```markdown
#### Non-CIDR-Aligned Mask Support

**Flag**: `--non-cidr-mask`

**Purpose**: Enable recognition and parsing of non-CIDR-aligned mask notation (e.g., Cisco ACL syntax: `10.4.0.0 0.0.127.252`).

**Syntax**:
```bash
--non-cidr-mask ADDRESS/PREFIX
```

**Behavior**:
- Can be specified multiple times (flags accumulate)
- Each flag contains one or more space-separated expressions
- The `ADDRESS` component's MSB determines parsing mode:
  - **MSB = 0** (e.g., `0.0.0.0`, `0.255.255.255`): Enable **hostmask mode**
    - Parser looks for hostmask notation in patterns and input
    - Netmasks are skipped
  - **MSB = 1** (e.g., `255.255.255.255`, `128.0.0.0`): Enable **netmask mode**
    - Parser looks for netmask notation in patterns and input
    - Hostmasks are skipped

**Examples**:
```bash
# Enable hostmask mode: search for hostmasks like "10.4.0.0 0.0.127.252"
grepnet --non-cidr-mask "0.0.0.0/17" pattern file.txt

# Enable netmask mode: search for netmasks like "10.4.0.0 255.255.128.0"
grepnet --non-cidr-mask "255.255.128.0/17" pattern file.txt

# Multiple expressions in one flag
grepnet --non-cidr-mask "0.0.0.0/16 0.0.0.0/24" pattern file.txt

# Multiple flags (both modes active)
grepnet --non-cidr-mask "0.0.0.0/17" --non-cidr-mask "255.255.128.0/17" pattern file.txt
```

**Interaction with Pattern/Input Parsers**:
- The parser automatically applies the mode to both pattern patterns (via pattern parser) and input lines (via input parser)
- Each mode operates independently; activating hostmask mode does not affect netmask detection and vice versa
- When multiple modes are active, the parser attempts to match each in its respective mode

**Matching Behavior**:
- Non-CIDR-aligned masks are internally expanded into constituent CIDR blocks
- Matching uses set operations (subset, superset, overlap) on the expanded CIDR ranges
- Example: hostmask `10.4.0.0 0.0.127.252` matching against pattern `10.4.0.0/17` → EQUALS (same set of IPs)

**Format Type in Output**:
- Matched networks retain their `format_type: 'non_cidr_mask'` designation
- Color codes: Uses the unified `non_cidr_mask` color code (set via GREPNET_COLORS or default)
```

---

## 5. Environment Variables Section

### Location
Section: **"Environment Variables"** (check for existing section; if not present, add before "Command-Line Interface Specification")

### Change 5.1: Add GREPNET_COLORS Documentation (if not already present) or Update

**If GREPNET_COLORS is already documented, update the color codes list to include:**

```markdown
- `non_cidr_mask=ANSI_CODE`: Color for non-CIDR-aligned masks (hostmask/netmask notation) — default: bright cyan (01;36)
```

**If GREPNET_COLORS section doesn't exist, add:**

```markdown
### GREPNET_COLORS

Controls colorization of output. Set environment variable to override defaults.

**Format**: `export GREPNET_COLORS='key1=code1 key2=code2 ...'`

**Available Keys**:
- `me=ANSI_CODE`: Match type equals (exact network match) — default: bright green (01;32)
- `mb=ANSI_CODE`: Match type subset — default: bright blue (01;34)
- `mS=ANSI_CODE`: Match type superset — default: bright yellow (01;33)
- `mo=ANSI_CODE`: Match type overlap — default: no color (0)
- `mu=ANSI_CODE`: Match type unmatched — default: no color (0)
- `mn=ANSI_CODE`: Normalized CIDR — default: underlined (04)
- `non_cidr_mask=ANSI_CODE`: Non-CIDR-aligned mask format — default: bright cyan (01;36)
- (other keys: fn, ln, bn, se, sl, etc.)

**Example**:
```bash
export GREPNET_COLORS='me=01;32 mb=01;34 mS=01;33 non_cidr_mask=01;36'
```
```

---

## 6. Hints and Scanning Section

### Location
Section: **"Hint Scanning"** (if exists) or subsection of **"Network Parsing Pipeline"**

### Change 6.1: Add Non-CIDR-Mask Hint Detection

**Add documentation describing hint detection for non-CIDR-mask format:**

```markdown
### Hint Detection for Non-CIDR-Aligned Masks

When `--non-cidr-mask` flag is active, hint scanning extends to detect non-CIDR-aligned mask notation.

**Detection Pattern**:
- `ADDRESS SPACE MASK_VALUE` where both are valid IPv4 addresses
- Matches only if:
  - Mode is active (via `--non-cidr-mask` flag)
  - Mask does not match existing formats (CIDR, standard subnet mask, inverse mask)
  - Mask alignment matches the active mode (hostmask in hostmask mode, netmask in netmask mode)

**Example Hints Generated**:
- Input: `access-list 101 permit ip 10.4.0.0 0.0.127.252 any`
- Mode: Hostmask (active via `--non-cidr-mask "0.0.0.0/17"`)
- Hint detected: `10.4.0.0 0.0.127.252`
- Format type: `'non_cidr_mask'`
- Color applied: `non_cidr_mask` color code from GREPNET_COLORS
```

---

## 7. Exit Codes and Error Handling Section

### Location
Section: **"Exit Codes and Error Handling"** (around line 1100+)

### Change 7.1: Add Error Handling for Non-CIDR-Mask

**In the error handling subsection, add:**

```markdown
**Non-CIDR-Mask Errors**:
- **Invalid SPEC format**: If `--non-cidr-mask` receives malformed input (not `address/prefix`), return error and exit code 2
- **Mode conflict**: If `--non-cidr-mask` specifies an invalid address for MSB detection, return error and exit code 2
- **Parsing failure**: If a network cannot be parsed in non-CIDR-mask mode, the parser continues to next format (non-fatal)
```

---

## 8. Summary of New/Modified Structures

### New Elements:
1. **WildcardMaskRange object** - represents Cisco ACL wildcard mask notation
2. **Format type**: `'non_cidr_mask'` - added to ParsedExtraction and FileEntry
3. **CLI flag**: `--non-cidr-mask` - enables wildcard mask parsing
4. **Color code**: `non_cidr_mask` - unified color for wildcard mask format
5. **Field**: `original_text` - added to FileEntry for display purposes (e.g., "10.4.0.0 0.0.127.252")

### Modified Elements:
1. **ParsedExtraction** - now can contain WildcardMaskRange objects
2. **FileEntry** - network field can be WildcardMaskRange; added original_text field
3. **MatchResult.discovered** - format_type includes 'non_cidr_mask'
4. **Hint scanning** - extends to detect wildcard mask notation
5. **Color rendering** - adds NON_CIDR_MASK as OBJ value

### Unchanged Principles:
- All matching logic remains unchanged (uses expanded CIDR ranges)
- Comment handling unaffected
- Output modes (-n, -b, --extract, --consolidate, etc.) work identically
- Strict CIDR mode applies to standard formats; wildcard masks always non-strict (can be non-aligned)
- Backward compatibility maintained (flag is opt-in)

### Implementation Complexity:
- **Wildcard mask expansion**: Uses combinatorial bit generation (O(2^N) complexity where N = number of 1-bits)
- **Guard rail required**: Reject masks with >20 variable bits (would generate >1 million CIDRs)
- **CIDR aggregation**: Use standard library function (e.g., `ipaddress.collapse_addresses()`) to minimize output block count

