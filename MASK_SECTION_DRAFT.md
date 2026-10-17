# Consolidated Mask Parsing Section (Draft)

## Two-Value Mask Formats

When a line contains two IPv4 addresses separated by one or more horizontal whitespace characters (spaces, tabs), the parser must determine if this is a mask notation pattern (either subnet mask or hostmask) or two separate IPs.

### Format Definitions

**Both formats** follow this pattern:
- First value: An IPv4 address (network address, or any address within the network)
- Separator: One or more horizontal whitespace characters
- Second value: An IPv4 mask (interpretation depends on MSB)

**Whitespace handling**: Separator must be horizontal space (ASCII space, tab, or Unicode horizontal whitespace). Do NOT split on vertical whitespace (newlines, carriage returns).

**Pattern prerequisites**:
1. Exactly two parts produced (no dashes, no extra values)
2. Both parts parse as valid IPv4 addresses (not CIDR, not containing `-`)
3. Neither part contains `/` or `-` (these indicate CIDR or range formats, not mask formats)

### Subnet Mask Format (Netmask)

**Recognition**: MSB of second value is 1 (starts with binary 1)

**Binary structure**: All ones from MSB, followed by all zeros (contiguous 1s then 0s)
- Example: `11111111.11111111.11111111.00000000` = 255.255.255.0

**Parsing**:
1. Verify second value is contiguous 1s-then-0s (no interleaved bits)
2. Calculate prefix length by counting 1-bits: e.g., 24 ones = /24
3. Create IPv4Network(first_ip, prefix_length)

**Examples**:
- `192.0.2.0 255.255.255.0` → 192.0.2.0/24
- `10.0.0.0 255.0.0.0` → 10.0.0.0/8
- `192.0.2.5 255.255.255.255` → 192.0.2.5/32

**Reject patterns**:
- Non-contiguous (e.g., 255.255.254.1)
- Invalid as netmask (e.g., second value is not a valid netmask)
- Second value is 0.0.0.0 (reserved for hostmask format)
- IPv6 addresses

### Hostmask Format (Inverse Mask / Cisco Format)

**Recognition**: MSB of second value is 0 (starts with binary 0)

**Binary structure**: All zeros from MSB, followed by all ones (contiguous 0s then 1s)
- Example: `00000000.00000000.00000000.11111111` = 0.0.0.255

**Parsing**:
1. Verify second value is contiguous 0s-then-1s (no interleaved bits)
2. Invert hostmask to get netmask: XOR with 0xFFFFFFFF
3. Calculate prefix length from inverted netmask
4. Create IPv4Network(first_ip, prefix_length)

**Examples**:
- `192.0.2.0 0.0.0.255` → invert(0.0.0.255) = 255.255.255.0 → 192.0.2.0/24
- `10.0.0.0 0.255.255.255` → invert(0.255.255.255) = 255.0.0.0 → 10.0.0.0/8
- `192.0.2.1 0.0.0.0` → invert(0.0.0.0) = 255.255.255.255 → 192.0.2.1/32

**Reject patterns**:
- Non-contiguous hostmask (e.g., after inversion, has interleaved bits)
- Invalid hostmask (e.g., second value is not contiguous 0s-then-1s)
- Second value is 255.255.255.255 (reserved for netmask format)
- IPv6 addresses

### Key Distinction

| Aspect | Subnet Mask (Netmask) | Hostmask (Inverse Mask) |
|--------|----------------------|-------------------------|
| MSB of second value | 1 (starts with binary 1) | 0 (starts with binary 0) |
| Binary pattern | 1s from MSB, then 0s | 0s from MSB, then 1s |
| Common notation | 255.255.255.0 | 0.0.0.255 |
| Interpretation | "Number of 1-bits" | "Number of 0-bits inverted" |
| Standard | RFC 791 standard notation | Cisco IOS notation |

### Reserved Values (CRITICAL)

Two special mask values have reserved interpretations that CANNOT be overridden by format hints:

**0.0.0.0** - ALWAYS treated as hostmask format
- MSB = 0 (fundamental property)
- Inverted: 0.0.0.0 XOR 0xFFFFFFFF = 255.255.255.255 = /32
- Example: `192.0.2.1 0.0.0.0` → 192.0.2.1/32
- NEVER attempted as netmask, even with netmask_dominant hint

**255.255.255.255** - ALWAYS treated as netmask format
- MSB = 1 (fundamental property)
- Represents: /32 (single host)
- Example: `192.0.2.5 255.255.255.255` → 192.0.2.5/32
- NEVER attempted as hostmask, even with hostmask_dominant hint

These reservations exist because they have ambiguous MSB interpretations but are fundamental to correct parsing semantics.

---

## Two-Value Pattern Parsing Algorithm

When processing a two-IP-address pattern:

### Step 0: Check Prerequisites
1. Verify exactly two whitespace-separated IPv4 values
2. Neither contains `/` or `-` (not CIDR or range)
3. Both parse as valid IPv4 addresses
4. If any prerequisite fails → treat as two separate IPs

### Step 1: Determine Parsing Availability
- Check if `--parse-netmask` is enabled in this context (pattern or input)
- Check if `--parse-hostmask` is enabled in this context
- If both disabled → extract both values as separate /32 IPs

### Step 2: Determine MSB and Apply Reserved Value Rules

Examine MSB of second value:

**If second value is 0.0.0.0 (RESERVED):**
- ALWAYS use hostmask format
- Skip all tie-breaking logic
- Go directly to Step 4

**If second value is 255.255.255.255 (RESERVED):**
- ALWAYS use netmask format
- Skip all tie-breaking logic
- Go directly to Step 3

**For all other values:**
- Determine MSB: 1 = netmask format, 0 = hostmask format
- If format hint is conclusive (`netmask_dominant` or `hostmask_dominant`) AND both parsing modes enabled:
  - Use hint as tie-breaker (override standard MSB logic)
  - `netmask_dominant`: Try netmask first
  - `hostmask_dominant`: Try hostmask first
- Otherwise: Follow standard MSB-based logic

### Step 3: Try Netmask Format (if MSB=1 or netmask_dominant hint)

**Condition**: (MSB is 1 OR (hint is netmask_dominant AND mask ≠ 0.0.0.0)) AND netmask parsing enabled

1. Verify second value is contiguous 1s-then-0s
2. If yes → Parse as subnet mask, done
3. If no → Extraction fails, continue to Step 4

### Step 4: Try Hostmask Format (if MSB=0 or hostmask_dominant hint)

**Condition**: (MSB is 0 OR (hint is hostmask_dominant AND mask ≠ 255.255.255.255)) AND hostmask parsing enabled

1. Verify second value is contiguous 0s-then-1s
2. Invert to get netmask
3. If inversion is valid → Parse as hostmask, done
4. If no → Extraction fails, continue to Step 5

### Step 5: Fallback to Two Separate IPs

If neither netmask nor hostmask format succeeded, extract both values as separate /32 addresses.

---

## Special Cases for Two-Value Patterns

These patterns are checked BEFORE normal parsing to handle edge cases:

**Special Case 1: `0.0.0.0 255.255.255.255` (Entire IPv4 Space)**
- Condition: Exact pattern AND `--parse-hostmask` enabled
- Gating: Format hint must be `mixed` or `unknown` (not conclusive)
- Result: `0.0.0.0/0` instead of normal `0.0.0.0/32`
- Rationale: Represents "all networks" in some configs

**Special Case 2: `255.255.255.255 0.0.0.0` (Broadcast + Hostmask All-Zeros)**
- Condition: Exact pattern AND `--parse-hostmask` enabled
- Gating: Format hint must be `mixed` or `unknown` (not conclusive)
- Result: `255.255.255.255/32` (same as normal parsing, documented for clarity)
- Rationale: Common in some configurations

---

## Format Hint Detection

**What are hints?** When parsing input files, grepnet analyzes the first 8KB to detect if two-value patterns prefer netmask or hostmask format. This hint improves heuristics for ambiguous values.

**Four hint values**:
- `netmask_dominant`: ≥66% of clear two-value patterns are netmask format
- `hostmask_dominant`: ≥66% of clear two-value patterns are hostmask format
- `mixed`: Roughly equal netmask and hostmask patterns detected
- `unknown`: Too few patterns or all ambiguous to determine

**Detection process**:
1. Scan first 8KB of input for two-value patterns
2. Skip ambiguous values (0.0.0.0, 255.255.255.255)
3. Classify each pattern by MSB and contiguity
4. Calculate percentages
5. Assign hint value

**Scope**: Hints apply to all lines from an input source, NOT to patterns (CLI arguments)

**Gating**:
- `--scan-mask=both` (default): Detect from both patterns and input
- `--scan-mask=input`: Detect from input files only
- `--scan-mask=pattern`: Detect from patterns only
- `--scan-mask=none`: Disable detection (always use MSB-based logic)

**Critical limitation**: Hints are advisory, not directive. Reserved values (0.0.0.0, 255.255.255.255) are NEVER subject to hint-based tie-breaking. Format hints only improve heuristics for non-reserved values when both parsing modes are enabled.

---

## Examples

### Example 1: Basic Netmask Pattern
```
Input: "192.0.2.0 255.255.255.0"
MSB of 255.255.255.0 = 1 (netmask format)
Contiguous? Yes (24 ones, 8 zeros)
Result: 192.0.2.0/24
```

### Example 2: Basic Hostmask Pattern
```
Input: "192.0.2.0 0.0.0.255"
MSB of 0.0.0.255 = 0 (hostmask format)
Contiguous? Yes (0 zeros, 8 ones)
Inverted: 0.0.0.255 XOR 0xFFFFFFFF = 255.255.255.0
Result: 192.0.2.0/24
```

### Example 3: Reserved Value 0.0.0.0
```
Input: "192.0.2.1 0.0.0.0"
MSB of 0.0.0.0 = 0 (RESERVED for hostmask)
Even if netmask_dominant hint present: Skip netmask, go to hostmask
Inverted: 0.0.0.0 XOR 0xFFFFFFFF = 255.255.255.255
Result: 192.0.2.1/32
```

### Example 4: Reserved Value 255.255.255.255
```
Input: "192.0.2.5 255.255.255.255"
MSB of 255.255.255.255 = 1 (RESERVED for netmask)
Even if hostmask_dominant hint present: Skip hostmask, go to netmask
Result: 192.0.2.5/32
```

### Example 5: Format Hint Tie-Breaking
```
File contains: "192.0.2.0 255.255.255.0" and "192.0.2.0 255.255.255.255"
Detected as: netmask_dominant

Line 1: "192.0.2.0 255.255.255.0"
  MSB = 1, hint = netmask_dominant
  Try netmask → Success → 192.0.2.0/24

Line 2: "192.0.2.0 255.255.255.255"
  MSB = 1, hint = netmask_dominant
  Try netmask → Success → 192.0.2.0/0
```

### Example 6: Parsing Flags Control Format Choice
```
Input: "192.0.2.1 0.0.0.255"
MSB = 0 (hostmask format)

--parse-hostmask=both → Try hostmask first → Success → 192.0.2.0/24
--parse-hostmask=none → Hostmask disabled → Try netmask → Fail → Two IPs: 192.0.2.1/32, 0.0.0.255/32
```

