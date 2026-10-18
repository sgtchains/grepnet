# Feature: Support Wildcard Mask Notation (Cisco ACL Syntax)

**Version**: 1.0  
**Status**: Design Phase  
**Objective**: Enable grepnet to recognize, parse, and match wildcard mask notation (e.g., `10.4.0.0 0.0.127.252`) as used in Cisco ACLs and network configurations.

---

## Feature Overview

### Problem Statement
Cisco ACLs and network configurations use **wildcard mask** notation to specify network ranges:
```
deny 10.4.0.0 0.0.127.252 any
```

**Wildcard masks** follow Cisco conventions where:
- **0 bits** = "must match exactly"
- **1 bits** = "don't care" (can be 0 or 1)

This is different from CIDR notation and standard subnet masks. The mask `0.0.127.252` is non-CIDR-aligned because the 1-bits are not contiguous from the MSB.

grepnet's current parser does not recognize wildcard mask syntax. Users cannot search for or match against Cisco ACL configurations using this notation.

### Solution
Extend the network parser to recognize wildcard mask notation when explicitly enabled via a new `--non-cidr-mask` flag. The parser will:
1. Detect whether to look for wildcard masks (hostmask-style) or standard netmasks based on the MSB of the address in the flag
2. Recognize the new format when scanning files and patterns
3. Expand wildcard masks into their constituent CIDRs internally using standard wildcard mask computation
4. Store original text for display/hints
5. Support matching via set operations on expanded CIDRs

---

## CLI Interface

### New Flag: `--non-cidr-mask`

**Syntax**:
```bash
--non-cidr-mask "address/prefix"
```

**Behavior**:
- Can be specified multiple times (flags accumulate)
- Each flag can contain space-separated mask expressions
- The `address` component's MSB determines parsing mode:
  - MSB = `0` (e.g., `0.0.0.0`, `0.255.255.255`): Enable **wildcard hostmask mode** (0 bits = must match, 1 bits = don't care)
  - MSB = `1` (e.g., `255.255.255.255`, `128.0.0.0`): Enable **netmask mode** (traditional 1 bits = network, 0 bits = host)

**Examples**:
```bash
# Enable wildcard hostmask mode: look for Cisco ACL wildcard masks like "10.4.0.0 0.0.127.252"
grepnet --non-cidr-mask "0.0.0.0/17" pattern file.txt

# Enable netmask mode: look for traditional netmasks like "10.4.0.0 255.255.128.0"
grepnet --non-cidr-mask "255.255.128.0/17" pattern file.txt

# Multiple expressions in one flag
grepnet --non-cidr-mask "0.0.0.0/16 0.0.0.0/24" pattern file.txt

# Multiple flags (accumulate)
grepnet --non-cidr-mask "0.0.0.0/17" --non-cidr-mask "255.255.128.0/17" pattern file.txt
```

---

## Parser Extension

### Current Parser Behavior
The current parser recognizes:
- CIDR notation: `192.0.2.0/24`
- Subnet mask: `192.0.2.0 255.255.255.0`
- Inverse mask (Cisco hostmask): `192.0.2.0 0.0.0.255`
- IP ranges: `192.0.2.0-192.0.2.255`
- Single IPs: `192.0.2.1`

### New Parser Behavior
When `--non-cidr-mask` is active, the parser additionally recognizes:
- **Wildcard masks (hostmask-style, MSB of address = 0)**: `10.4.0.0 0.0.127.252` (Cisco ACL notation where 1-bits are "don't care")
- **Netmask notation (MSB of address = 1)**: `10.4.0.0 255.255.128.0` (if not already parsed as standard subnet mask)

### Parsing Logic

```
Input: "10.4.0.0 0.0.127.252"

1. Attempt to parse as standard formats (CIDR, subnet mask, etc.)
   → Not recognized by existing parsers

2. Check if --non-cidr-mask is active
   → Yes (e.g., mode determined by "0.0.0.0/17" → wildcard hostmask mode)

3. Check wildcard mask compatibility
   → Does "0.0.127.252" match wildcard mask criteria?
   → Is mode set to wildcard hostmask (MSB=0)?
   → If mode is wildcard hostmask and mask is valid wildcard → proceed

4. Parse as wildcard mask (Cisco ACL convention):
   → Network address: 10.4.0.0
   → Wildcard mask: 0.0.127.252 (1-bits = "don't care", 0-bits = "must match")
   → Expand to constituent CIDRs using standard wildcard mask computation

5. Store ParsedExtraction:
   → network_object: (CIDRs or IPRange representation)
   → format_type: 'non_cidr_mask'
   → matched_texts: ["10.4.0.0 0.0.127.252"]
   → original_text: "10.4.0.0 0.0.127.252" (for hints/display)
```

### Wildcard Mask Expansion Algorithm (Combinatorial Bit Generation)

Based on standard Cisco ACL wildcard mask computation. Uses combinatorial bit generation to produce all valid IP configurations, then collapses them into minimal CIDR blocks.

**Algorithm Steps**:

1. **Convert to integers**: Convert both base IP and wildcard mask from dot-decimal to 32-bit unsigned integers
2. **Force clean base**: Zero out all wildcard bit positions in the base IP: `base_ip = base_ip & ~wildcard_mask`
3. **Identify wildcard bits**: Find all bit positions where wildcard has a 1-bit
4. **Generate combinations**: Loop from 0 to (2^N - 1), where N = count of 1-bits in wildcard
   - For each iteration, map the binary counter onto the wildcard bit positions
   - Overlay each combination onto the cleaned base IP to create valid network addresses
5. **Collapse to CIDRs**: Use standard CIDR aggregation (e.g., `ipaddress.collapse_addresses()`) to merge contiguous IPs into minimal block set

**Python Implementation** (standard approach):

```python
import ipaddress

def wildcard_to_cidrs(ip_str: str, wildcard_str: str) -> list:
    """
    Convert Cisco wildcard mask to minimal CIDR block list.
    
    Args:
        ip_str: Base IP (e.g., "10.4.0.0")
        wildcard_str: Wildcard mask (e.g., "0.0.127.252")
    
    Returns:
        List of CIDR blocks covering the wildcard range
    
    Raises:
        ValueError: If wildcard has >20 bits set (too many combinations)
    """
    # 1. Convert strings to 32-bit integers
    base_ip = int(ipaddress.IPv4Address(ip_str))
    wildcard = int(ipaddress.IPv4Address(wildcard_str))
    
    # 2. Force base IP bits to 0 where wildcard bits are 1
    base_ip &= ~wildcard
    
    # 3. Find the index positions of all '1' bits in the wildcard
    wildcard_bit_positions = [i for i in range(32) if (wildcard >> i) & 1]
    num_wildcard_bits = len(wildcard_bit_positions)
    
    # Guard: Prevent memory/CPU explosion on massive masks
    if num_wildcard_bits > 20:
        raise ValueError(f"Too many wildcard bits ({num_wildcard_bits}). "
                         "This would generate over 1 million CIDRs.")
    
    raw_ips = []
    
    # 4. Generate all combinations of the wildcard bits
    for i in range(2 ** num_wildcard_bits):
        current_ip = base_ip
        for bit_index in range(num_wildcard_bits):
            # If the bit is set in our counter, set it in the current IP
            if (i >> bit_index) & 1:
                pos = wildcard_bit_positions[bit_index]
                current_ip |= (1 << pos)
        
        raw_ips.append(ipaddress.IPv4Address(current_ip))
    
    # 5. Automatically collapse contiguous IPs into standard CIDR blocks
    cidr_blocks = ipaddress.collapse_addresses(raw_ips)
    
    return [str(cidr) for cidr in cidr_blocks]
```

**Example for `10.4.0.0 0.0.127.252`**:
- Base IP: `10.4.0.0` = 167838720 (binary)
- Wildcard: `0.0.127.252` = 32764 (binary: 0000...01111111.11111100)
- Wildcard bit positions: 13 positions (2, 3, 4, 5, 6, 7 in octet 4; 0-6 in octet 3)
- Number of combinations: 2^13 = 8,192
- Loop iterations: 8,192 valid IPs generated
- Result: Collapsed CIDR set (e.g., mix of /17, /18, /24 blocks depending on alignment)

**Time Complexity**: O(2^N) where N = number of 1-bits in wildcard
- N ≤ 7: Instantaneous (≤ 128 iterations)
- N ≤ 15: Milliseconds (≤ 32,768 iterations)
- N > 20: **Guard against** (over 1 million iterations; risk of CPU/memory exhaustion)

**Guard Rail**: Implement a check to prevent user-provided masks from causing DoS:
```python
if num_wildcard_bits > 20:
    raise ValueError(f"Wildcard mask has {num_wildcard_bits} variable bits. "
                     "Maximum allowed is 20 (1,048,576 IPs).")
```

### MSB Detection Logic

For IPv4 addresses:
```
address_bytes = [10, 4, 0, 0]
msb = address_bytes[0] & 0x80  # Check bit 7 of first octet
if msb == 0:
    mode = "hostmask"  # Accept hostmasks, reject netmasks
else:
    mode = "netmask"   # Accept netmasks, reject hostmasks
```

---

## Data Structure Changes

### ParsedExtraction (Extended)

Add support for new format type:
```python
ParsedExtraction = (
    network_object,           # Network, IPRange, or new HostmaskRange object
    format_type,              # 'cidr_notation' | 'subnet_mask' | 'inverse_mask' |
                              # 'ipv4_range' | 'ipv6_range' | 'ip_only' |
                              # 'non_cidr_mask'  [NEW]
    was_normalized,           # Boolean
    matched_texts,            # List of {"text": str, "was_normalized": bool}
    original_text             # For hints: "10.4.0.0 0.0.127.252" [NEW]
)
```

### New HostmaskRange Object

Represents wildcard mask notation similar to IPRange:
```python
class WildcardMaskRange:
    network_address: IPAddress      # e.g., 10.4.0.0
    wildcard_mask: IPAddress        # e.g., 0.0.127.252
    expanded_cidrs: List[Network]   # Constituent CIDRs computed from wildcard mask
    family: int                     # 4 or 6
    
    # Convert to integer range for matching
    def to_ip_range(self) -> IPRange:
        # Compute start and end IP integers from wildcard mask using standard Cisco algorithm
    
    # Recognize this is a wildcard mask (non-CIDR-aligned)
    def is_wildcard_mask(self) -> bool:
        return True
```

### FileEntry (Extended)

```python
FileEntry = {
    'network': (Network | IPRange | WildcardMaskRange),
    'format_type': str,  # Includes 'non_cidr_mask' for wildcard masks
    'line_number': int,
    'line_content': str,
    'matched_texts': List[{"text": str, "was_normalized": bool}],
    'was_normalized': bool,
    'original_text': str  # [NEW] For display in hints (e.g., "10.4.0.0 0.0.127.252")
}
```

---

## Impact Areas

### 1. Hint Scanning
- Extend regex patterns to detect hostmask notation: `IP SPACE non-CIDR-aligned-mask`
- Respect `--non-cidr-mask` mode (hostmask vs netmask)
- Return `format_type: 'non_cidr_hostmask'` or `'non_cidr_netmask'`

### 2. Matching Logic
- Expand HostmaskRange to IPRange for set operations
- Apply existing subset/superset/overlap logic on expanded ranges
- Result: hostmask `10.4.0.0 0.0.127.252` matches CIDR `10.4.0.0/17` correctly

### 3. GREPNET_COLORS
Add new color code:
```python
GREPNET_COLORS = {
    'cidr_notation': '\033[38;5;33m',      # Existing
    'subnet_mask': '\033[38;5;34m',        # Existing
    'inverse_mask': '\033[38;5;35m',       # Existing
    'non_cidr_mask': '\033[38;5;100m',     # [NEW] - covers wildcard mask format (Cisco ACL)
    # ... other colors
}
```

### 4. Argument Processing
- Add `--non-cidr-mask` to CLI parser
- Validate flag format (must be `address/prefix`)
- Extract MSB from address to determine mode
- Store mode globally or per-parser-instance

### 5. Parser Initialization
- Create two parser instances (pattern parser, input parser) as usual
- **Extend both** to accept `--non-cidr-mask` configuration
- Each can have different modes enabled independently

---

## Implementation Strategy

### Phase 1: Core Parser Extension
1. Create `HostmaskRange` class (or equivalent for target language)
2. Add hostmask parsing logic to network parser
3. Add `--non-cidr-mask` flag to CLI
4. Detect and validate flag format (address/prefix + MSB extraction)

### Phase 2: Integration
1. Extend hint scanning regex to detect hostmask syntax
2. Update `ParsedExtraction` and `FileEntry` data structures
3. Add format types to GREPNET_COLORS
4. Test matching logic with expanded ranges

### Phase 3: Testing & Documentation
1. Unit tests for hostmask parsing
2. Integration tests (matching, hints, colors)
3. Update CLI help and documentation
4. Add spec amendments

---

## Edge Cases & Considerations

### 1. Non-CIDR-Aligned vs CIDR-Aligned
- `10.4.0.0 0.0.0.255` → CIDR-aligned (can be expressed as `10.4.0.0/24`), but still recognized as hostmask format if mode is active
- `10.4.0.0 0.0.127.252` → Non-CIDR-aligned (cannot be expressed as single CIDR)
- Both should be parsed when hostmask mode is active

### 2. Mode Stacking
- Multiple `--non-cidr-mask` flags can specify different modes
  - `--non-cidr-mask "0.0.0.0/17"` (hostmask mode)
  - `--non-cidr-mask "255.255.128.0/17"` (netmask mode)
  - Parser should accept both

### 3. Normalization
- Hostmask notation doesn't have "host bits" in the same sense as CIDR
- No normalization needed; accept as-is
- `was_normalized` = False for hostmask format

### 4. IPv6 Support
- Hostmask notation is primarily IPv4; support if needed, but IPv6 more commonly uses prefix length
- Consider future enhancement

---

## Testing Strategy

### 1. Hostmask parsing: `10.4.0.0 0.0.127.252` → expanded CIDRs
2. MSB detection: various addresses (0.x, 127.x, 128.x, 255.x)
3. Mode filtering: only parse wildcard masks in hostmask mode, etc.
4. Edge cases: CIDR-aligned wildcard masks, all-wildcard masks, etc.

### Integration Tests
1. Pattern matching: wildcard mask pattern vs CIDR input
2. File scanning: detect wildcard mask in Cisco ACL content
3. Hints: generate correct hints for wildcard mask format
4. Colors: apply correct color codes

---

## Backward Compatibility

- **No breaking changes**: Flag is opt-in
- Parser unchanged when flag not provided
- Existing functionality unaffected
- Safe to add without version bump (minor version increment recommended)

