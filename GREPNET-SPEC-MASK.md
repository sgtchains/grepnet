# GREPNET Mask Parsing Specification

This document contains the complete specification for subnet mask (netmask) and hostmask (inverse mask) parsing in grepnet.

---

### Subnet Mask Parsing

**Format**: Two values separated by one or more horizontal whitespace characters (spaces, tabs, or other horizontal space): a valid IPv4 address (not CIDR, not range) followed by a subnet mask.

**Separator**: One or more horizontal whitespace characters (ASCII space, tab, or Unicode horizontal space). Not newlines or vertical whitespace.

**Subnet mask binary structure**: All ones from MSB, followed by all zeros (contiguous 1s then 0s).

**Examples**:
- `192.0.2.0 255.255.255.0` (mask binary: 11111111.11111111.11111111.00000000)
- `10.0.0.0 255.0.0.0` (mask binary: 11111111.00000000.00000000.00000000)

**IPv4-only**: Subnet masks are not supported for IPv6 addresses.

**Validation steps**:
1. Parse both parts as IPv4 addresses
2. Verify the second part is a valid contiguous netmask (all 1s from MSB, all 0s from first 0 bit onward; no interleaved bits)
3. Calculate prefix length by counting the number of 1-bits in the mask
4. Create IPv4Network object using the first IP and derived prefix

**Special case - 255.255.255.255**: This represents a host mask (single IP). If second value is 255.255.255.255, treat as a /32 (host address).

**Reject patterns**:
- Non-contiguous masks (e.g., `255.255.254.1`) – bits are not in "all 1s then all 0s" order
- Invalid netmask values (e.g., `192.0.2.0 192.0.2.1`) – second part is not a valid netmask
- Second value is 0.0.0.0 (use inverse mask parsing instead)
- IPv6 addresses in either position

### Parsing Strategy for Space-Separated Two-Value Patterns

When a line contains two IPv4 addresses separated by one or more horizontal whitespace characters (spaces, tabs, or other horizontal space), the parser must determine if this is a subnet mask, inverse mask, or two separate IPs.

**Whitespace handling**: The separator must be one or more horizontal whitespace characters (horizontal space: ASCII space, tab, or Unicode horizontal whitespace). Do NOT split on vertical whitespace (newlines, carriage returns).

**Pattern prerequisites**:
1. Use a regex or parser that splits on one or more horizontal space characters
2. Check if exactly two parts are produced (no dashes, no extra values)
3. Check if first part is a valid IPv4 address (not CIDR, not containing `-`)
4. Check if second part is a valid IPv4 address (not CIDR, not containing `-`)

#### Special Cases for Two-Value Patterns

These special cases must be checked BEFORE normal parsing logic. They represent edge cases where the standard MSB-based detection would produce unintuitive or conflicting results.

**Special Case 1: `0.0.0.0 255.255.255.255` (Entire IPv4 Space)**
- **Condition**: Pattern is exactly `0.0.0.0 255.255.255.255` AND `--parse-hostmask` is enabled for this context
- **Normal parsing would produce**: `0.0.0.0/32` (subnet mask: 255.255.255.255 is a /32 netmask)
- **Special result**: `0.0.0.0/0` (entire IPv4 address space, all 4.3 billion addresses)
- **Rationale**: This pattern appears in network configurations to represent "match all networks"
- **Gating conditions** (ALL must be true):
  1. `--parse-hostmask` is NOT `none` AND matches current context (pattern or input)
     - `pattern` context: Must have `--parse-hostmask` set to `pattern` or `both`
     - `input` context: Must have `--parse-hostmask` set to `input` or `both`
  2. **AND** mask format hint is `'mixed'` or `'unknown'` (not a conclusive format hint)
     - If format hint is `'netmask_dominant'` or `'hostmask_dominant'`: Don't apply special case, use standard parsing
     - If format hint is `'mixed'` or `'unknown'`: Apply special case
- **Implementation order**: Check this BEFORE normal two-value parsing

**Special Case 2: `255.255.255.255 0.0.0.0` (Broadcast Address as Single Host)**
- **Condition**: Pattern is exactly `255.255.255.255 0.0.0.0` AND `--parse-hostmask` is enabled for this context
- **Normal parsing would produce**: `255.255.255.255/32` (inverse mask: hostmask 0.0.0.0 inverts to /32)
- **Special result**: `255.255.255.255/32` (same as normal parsing - this is documented for clarity)
- **Rationale**: This pattern appears in network configurations; special case check clarifies the behavior
- **Gating conditions** (ALL must be true):
  1. `--parse-hostmask` is NOT `none` AND matches current context (pattern or input)
  2. **AND** mask format hint is `'mixed'` or `'unknown'` (not a conclusive format hint)
- **Implementation order**: Check alongside Special Case 1

#### Normal Two-Value Parsing Algorithm

After checking special cases above, apply this algorithm:

**Step 1: Parse flag checks**
- Determine if netmask parsing is enabled in this context (check `--parse-netmask` against context)
- Determine if hostmask parsing is enabled in this context (check `--parse-hostmask` against context)
- If both are disabled: Extract both values as separate IPs

**Step 2: MSB analysis and format hint tie-breaking**
- Determine MSB of second value: Is it 1 (netmask format) or 0 (hostmask format)?
- **CRITICAL RESERVED VALUES - NOT subject to tie-breaking**:
  - `0.0.0.0` is ALWAYS treated as hostmask format (reserved interpretation for inverse mask)
    - Reason: 0.0.0.0 has MSB=0 and must use hostmask parsing for correct semantics
    - Even with `netmask_dominant` hint, 0.0.0.0 skips netmask attempt and goes directly to hostmask
  - `255.255.255.255` is ALWAYS treated as netmask format (reserved interpretation for subnet mask)
    - Reason: 255.255.255.255 has MSB=1 and must use netmask parsing for correct semantics
    - Even with `hostmask_dominant` hint, 255.255.255.255 skips hostmask attempt and goes directly to netmask
- **Format hint tie-breaking for all other values**:
  - Only applies when format hint is conclusive (`'netmask_dominant'` or `'hostmask_dominant'`) AND both `--parse-netmask` and `--parse-hostmask` are enabled
  - If hint is `'netmask_dominant'`: Prefer netmask format when possible (e.g., for ambiguous boundary cases)
  - If hint is `'hostmask_dominant'`: Prefer hostmask format when possible (e.g., for ambiguous boundary cases)
  - If hint is `'mixed'` or `'unknown'`: Use standard MSB-based logic (MSB=1 → netmask, MSB=0 → hostmask)

**Step 3: Try netmask format (MSB=1 or hint=netmask_dominant, with reserved value exclusion)**
- If (MSB is 1 OR (hint is `'netmask_dominant'` AND mask is NOT `0.0.0.0`)) AND netmask parsing is enabled:
  - Check if second value is contiguous 1s-then-0s (valid netmask)
  - If yes: Parse as subnet mask, mark format as `'subnet_mask'`, done
  - If no (non-contiguous): Extraction fails, skip this pattern
- If MSB is 1 but netmask parsing is disabled: Continue to Step 4

**Step 4: Try hostmask format (MSB=0 or hint=hostmask_dominant, with reserved value exclusion)**
- If (MSB is 0 OR (hint is `'hostmask_dominant'` AND mask is NOT `255.255.255.255`)) AND hostmask parsing is enabled:
  - Check if second value inverted is contiguous 0s-then-1s (valid hostmask inverted)
  - If yes: Parse as inverse mask, mark format as `'inverse_mask'`, done
  - If no (non-contiguous): Extraction fails, skip this pattern
- If MSB is 0 but hostmask parsing is disabled: Continue to Step 5

**Step 5: Neither format matched**
- Extract both values as separate plain IPv4 addresses (each /32)

**Critical constraints**:
- Exactly two space-separated parts required (not three or more)
- Neither value can contain `/` or `-` (these indicate CIDR or range, not mask format)
- If a dash is present, range parsing handles it at the range extraction stage
- Cannot have both netmask and hostmask disabled in one context (at least one must be enabled to avoid all two-value patterns becoming two-IP fallback)

**Examples with parsing flags**:
- `192.0.2.1 255.255.255.0` with `--parse-netmask=both`: MSB=1, netmask enabled → Subnet mask: `192.0.2.0/24`
- `192.0.2.1 255.255.255.0` with `--parse-netmask=none`: MSB=1, netmask disabled → Two IPs: `192.0.2.1/32` and `255.255.255.0/32`
- `192.0.2.1 0.0.0.255` with `--parse-hostmask=both`: MSB=0, hostmask enabled → Inverse mask: `192.0.2.0/24`
- `192.0.2.1 0.0.0.255` with `--parse-hostmask=none`: MSB=0, hostmask disabled → Two IPs: `192.0.2.1/32` and `0.0.0.255/32`
- `192.0.2.1 255.255.255.255` with `--parse-netmask=none`: MSB=1, netmask disabled → Two IPs: `192.0.2.1/32` and `255.255.255.255/32`

**Examples with format hints (tie-breaking for ambiguous values)**:
- Input file: `192.0.2.0 255.255.255.0` and `192.0.2.0 255.255.255.255` (detected as `'netmask_dominant'`)
  - Line 1 `192.0.2.0 255.255.255.0`: MSB=1 → Try netmask → Success → `192.0.2.0/24`
  - Line 2 `192.0.2.0 255.255.255.255`: MSB=1 → Try netmask → Success → `192.0.2.0/0`
- Input file: `192.0.2.1 0.0.0.255` and `192.0.2.1 0.0.0.0` (detected as `'hostmask_dominant'`)
  - Line 1 `192.0.2.1 0.0.0.255`: MSB=0 → Try hostmask → Success → `192.0.2.0/24`
  - Line 2 `192.0.2.1 0.0.0.0` with hint=`'hostmask_dominant'`: MSB=0, both parsing enabled → Try hostmask first (per hint) → Check if inverted is valid → Inverted `0.0.0.0` is all 1s (valid) → `192.0.2.1/32`
- Input file: `192.0.2.0 255.255.255.0` and `192.0.2.0 0.0.0.255` with `--scan-mask=none` (no hint detected)
  - Line 1 `192.0.2.0 255.255.255.0`: MSB=1 → Try netmask → Success → `192.0.2.0/24`
  - Line 2 `192.0.2.0 0.0.0.255`: MSB=0 → Try hostmask → Success → `192.0.2.0/24`
  - Both formats handled independently by standard MSB logic

**Implementation note**: Extractors must have access to the parse flag settings (`--parse-netmask`, `--parse-hostmask`, context) and format hints so they can make context-aware decisions about which formats to try and in what order when both parsing modes are enabled.

### Inverse/Hostmask Parsing (Cisco Format)

**Format**: Two values separated by one or more horizontal whitespace characters (spaces, tabs, or other horizontal space): a valid IPv4 address (not CIDR, not range) followed by an inverse mask (hostmask).

**Separator**: One or more horizontal whitespace characters (ASCII space, tab, or Unicode horizontal space). Not newlines or vertical whitespace.

**Inverse mask (hostmask) binary structure**: All zeros from MSB, followed by all ones (contiguous 0s then 1s).

**Examples**:
- `192.0.2.0 0.0.0.255` (hostmask binary: 00000000.00000000.00000000.11111111) – represents /24
- `10.0.0.0 0.255.255.255` (hostmask binary: 00000000.11111111.11111111.11111111) – represents /8

**IPv4-only**: Inverse masks are not supported for IPv6 addresses.

**Key distinction from subnet masks**:
- Netmask: 1s from MSB (e.g., 255.255.255.0)
- Hostmask: 0s from MSB then 1s (e.g., 0.0.0.255)

**Detection and validation**:
1. Parse both parts as IPv4 addresses
2. Check if the second value is in hostmask format (MSB must be 0, indicating hostmask not netmask)
   - If MSB is 1, this is netmask format, not hostmask → reject (use subnet mask parsing)
3. Verify the hostmask is contiguous (all 0s from MSB, then all 1s; no interleaved bits)
4. Invert the hostmask to get the netmask (XOR with 0xFFFFFFFF to flip all bits)
5. Verify resulting netmask is contiguous
6. Calculate prefix length from the netmask
7. Create IPv4Network object

**Special case - 0.0.0.0**: When the second value is 0.0.0.0 (all zeros hostmask), invert it to get 255.255.255.255 (all ones), which represents /32 (single host). Example: `192.0.2.1 0.0.0.0` = `192.0.2.1/32`.

**Reject patterns**:
- Non-contiguous hostmasks (e.g., after inversion, netmask has interleaved 0s and 1s)
- Netmask format (MSB is 1) – must use subnet mask parsing instead
- Second value is 255.255.255.255 (this is netmask format, use subnet mask parsing)
- IPv6 addresses in either position

### Special Mask Values

**255.255.255.255 (all ones)**:
- When used as second value in subnet mask format, represents /32 (single host)
- MSB is 1, so it is netmask format (not hostmask)
- Example: `192.0.2.5 255.255.255.255` = `192.0.2.5/32`

**0.0.0.0 (all zeros)**:
- When used as second value in inverse mask format, represents /32 (single host)
- MSB is 0, so it is hostmask format (not netmask)
- Invert to get netmask: 0.0.0.0 XOR 0xFFFFFFFF = 255.255.255.255 = /32
- Example: `192.0.2.1 0.0.0.0` = `192.0.2.1/32`


---

## Format Hint Detection

**Gating with --scan-mask flag**:
- `--scan-mask=both` (default): Analyze patterns and input files
- `--scan-mask=input`: Analyze only input files
- `--scan-mask=pattern`: Analyze only patterns
- `--scan-mask=none`: Disable format detection (treat all two-value patterns with standard MSB-based logic)

**Examples**:
- File contains `0.0.0.0 0.0.0.0` and `192.0.2.1 0.0.0.255` → Skip first (all zeros), count second as hostmask → Detected as `'hostmask_dominant'`
- File contains `192.0.2.1 0.0.0.0` only → Skip (all zeros) → No clear patterns → Detected as `'unknown'` → FALLBACK
- File contains `192.0.2.0 0.0.0.255` and `192.0.2.0 255.255.255.0` → Conflicting formats → Detected as `'mixed'` → FALLBACK
- File contains `192.0.2.0 255.255.255.0` patterns → All clearly netmask → Detected as `'netmask_dominant'`

**Implementation note**: Format detection is a hint, not a directive. Ambiguous patterns (all zeros, all ones, non-contiguous) are excluded from analysis. The standard MSB-based two-value parsing algorithm (see "Normal Two-Value Parsing Algorithm" section) is always the authoritative source. Format hints improve heuristics only when both `--parse-netmask` and `--parse-hostmask` are enabled AND the hint is conclusive (`'netmask_dominant'` or `'hostmask_dominant'`). Any uncertainty triggers fallback to standard algorithm.

### Code Pattern Elimination

The InputSource abstraction eliminates these anti-patterns:

**Before** (ad-hoc type checking):
```python
if hasattr(source, 'file_path'):
    filename = source.file_path
else:
    filename = '(standard input)'

if filename != '(standard input)':
    print_with_filename(filename)

# Stream consumption bug: first 8KB lost
is_binary = BinaryDetector.is_binary_fd(fd)
for line_num, content in lines(fd):
    # First 8KB missing!
```

**After** (unified InputSource):
```python
# No type checking needed
if source.display_name:  # None for unlabeled stdin/fd
    output_header = source.display_name

# Binary detection respects streaming
is_binary = source.get_binary_status()  # Caches 8KB internally
for line_num, content, offset in source.lines():
    # All data (including first 8KB) is available!
```

### InputDiscovery Helper Class

