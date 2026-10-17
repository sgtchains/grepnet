# Bitwise CIDR Discussion

## Algorithm Overview

## Bitshift Grouping

### Sweeping Group
A **sweeping_group** is a group of CIDRs that can all be contained within a specific container CIDR.

Example: The following CIDRs all fit within 192.0.2.0/24:
- 192.0.2.1/32, 192.0.2.2/31, 192.0.2.4/30, 192.0.2.8/29, 192.0.2.16/28, 192.0.2.32/27, 192.0.2.64/26, 192.0.2.128/26, 192.0.2.192/27, 192.0.2.224/28, 192.0.2.240/29, 192.0.2.248/30, 192.0.2.252/31, 192.0.2.254/32

We only know:
- Which CIDRs are in the group
- The container CIDR they fit within
- Nothing about gaps, boundaries, or consolidation potential yet

### Algorithm: Grouping CIDRs into Sweeping Groups

**Required Parameters:**
- `min_prefix_length` (integer, 0-32): The shortest prefix length we will consider. Once expanding the hostmask would require a prefix shorter than this, we stop consolidating that sweeping_group.
- `max_prefix_length` (integer, 0-32): The longest prefix length we will consider. Bare IP inference and disaggregation will not exceed this prefix.
- **Constraint:** `min_prefix_length < max_prefix_length`

**Bare IP Inference:**
For any bare IP address (no explicit prefix), infer the shortest prefix by bitwise alignment:
- Treat the IP as a binary number
- Find the longest run of matching trailing bits with adjacent IPs
- Infer the prefix that naturally pairs this IP with its bitwise neighbor
- Do not infer a prefix longer than `max_prefix_length`

Example: 254 (binary 11111110) pairs with 255 (11111111) → infer /31, not /32.

```
Initialize:
  current_hostmask = 0
  current_group = []

For each CIDR in sorted_cidrs:
  0. Load and parse CIDR
     - If bare IP: Infer prefix using bitwise alignment, capped at max_prefix_length
     - Determine CIDR prefix_length
     - If prefix_length <= min_prefix_length:
       * If current_group is not empty:
         - Finalize current_group as a sweeping_group
         - Output the sweeping_group (all original CIDRs)
       * Start new_group with this CIDR only
       * Reset current_hostmask to 0
       * Continue to next CIDR
  
  1. Check: Does this CIDR fit within current_hostmask?
     (Using: cidr_start_ip & ~current_hostmask)
  
  2. If YES:
     - Add CIDR to current_group
     - Continue to next CIDR
  
  3. If NO:
     - Compute next_hostmask: (current_hostmask << 1) | current_hostmask
     - Determine prefix_length from next_hostmask (32 - popcount(next_hostmask))
     
     3a. If prefix_length < min_prefix_length:
         - Finalize current_group as a sweeping_group
         - Output the sweeping_group (all original CIDRs)
         - Start new_group with this unmatched CIDR
         - Reset current_hostmask to 0
         - Prime hostmask: current_hostmask = (0 << 1) | 1
         - Restart checking with new hostmask
     
     3b. Else (prefix_length >= min_prefix_length):
         - current_hostmask = next_hostmask
         - Check again if CIDR fits

Key Insight: When a CIDR doesn't fit even after expanding hostmask, or when 
expanding further would violate min_prefix_length, the networks are at their 
consolidation boundary. This signals the end of the current sweeping_group.
```

### Hostmask Formula
To compute the next hostmask (expanding to a broader prefix):
```
next_hostmask = (current_hostmask << 1) | current_hostmask
```

Examples:
- /32 hostmask: 0 → /31: 1 → /30: 3 → /29: 7 → /28: 15 → /27: 31 → /26: 63 → /25: 127 → /24: 255

### Example Walkthrough

CIDRs (from 192.0.2.0/24 block):
1. 192.0.2.1/32 - load, prime hostmask to 1 (/31)
2. 192.0.2.2/31 - doesn't fit in /31, expand to /30 (hostmask 3), fits
3. 192.0.2.4/30 - doesn't fit in /30, expand to /29 (hostmask 7), fits
4. 192.0.2.8/29 - fits in /29
5. 192.0.2.16/28 - doesn't fit, expand to /28 (hostmask 15), fits
... continuing ...
14. 192.0.2.254/32 - fits in /24 (hostmask 255)
15. 198.51.100.1/32 - NEW ADDRESS SPACE - doesn't fit in /24, keeps not fitting as hostmask expands

Result: Finalize sweeping_group of all 192.0.2.x CIDRs → Start new group with 198.51.100.1/32


## Gap Analysis

## Consolidation Criteria

## Implementation Notes

## Working Example Networks with Binary Representations

192.0.2.1/32      = 11000000.00000000.00000010.00000001 /32
192.0.2.2/31      = 11000000.00000000.00000010.00000010 /31
192.0.2.4/30      = 11000000.00000000.00000010.00000100 /30
192.0.2.8/29      = 11000000.00000000.00000010.00001000 /29
192.0.2.16/28     = 11000000.00000000.00000010.00010000 /28
192.0.2.32/27     = 11000000.00000000.00000010.00100000 /27
192.0.2.64/26     = 11000000.00000000.00000010.01000000 /26
192.0.2.128/26    = 11000000.00000000.00000010.10000000 /26
192.0.2.192/27    = 11000000.00000000.00000010.11000000 /27
192.0.2.224/28    = 11000000.00000000.00000010.11100000 /28
192.0.2.240/29    = 11000000.00000000.00000010.11110000 /29
192.0.2.248/30    = 11000000.00000000.00000010.11111000 /30
192.0.2.252/31    = 11000000.00000000.00000010.11111100 /31
192.0.2.254/32    = 11000000.00000000.00000010.11111110 /32
198.51.100.1/32   = 11000110.00110011.01100100.00000001 /32
198.51.100.2/31   = 11000110.00110011.01100100.00000010 /31
198.51.100.4/30   = 11000110.00110011.01100100.00000100 /30
198.51.100.8/29   = 11000110.00110011.01100100.00001000 /29
198.51.100.16/28  = 11000110.00110011.01100100.00010000 /28
198.51.100.32/27  = 11000110.00110011.01100100.00100000 /27
198.51.100.64/26  = 11000110.00110011.01100100.01000000 /26
203.0.113.0/32    = 11001011.00000000.01110001.00000000 /32

## Examples

## Testing
