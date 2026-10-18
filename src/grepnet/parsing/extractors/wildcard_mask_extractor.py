"""
Wildcard mask extractor for Cisco ACL notation.

Cisco ACL wildcard masks use the inverse of netmask notation:
- 1-bits in the mask = "don't care" (can be 0 or 1)
- 0-bits in the mask = "must match exactly"

Example: "10.4.0.0 0.0.127.252" represents a range where the wildcard
positions can vary across the specified addresses.

This extractor implements the combinatorial bit generation algorithm:
1. Convert base IP and wildcard mask to 32-bit integers
2. Clean base IP (force wildcard positions to 0)
3. Identify wildcard bit positions
4. Generate all 2^N combinations (where N = wildcard bit count)
5. Collapse contiguous IPs into minimal CIDR blocks using ipaddress library

Note: Memory/CPU DoS protection is handled at a higher level in the pipeline.
"""

import re
from typing import Optional
from ipaddress import IPv4Address, IPv4Network, collapse_addresses
from . import NetworkExtractor
from ...core.network_objects import WildcardMaskRange, _RawExtraction


def _wildcard_to_cidrs(base_ip_str: str, wildcard_mask_str: str) -> list:
    """
    Convert a Cisco ACL wildcard mask to a list of minimal CIDR blocks.
    
    Algorithm:
    1. Convert both IP strings to 32-bit unsigned integers
    2. Clean base IP: force all wildcard bit positions to 0 using (base_ip & ~wildcard)
    3. Find all bit positions where wildcard has a 1 (the "don't care" positions)
    4. Generate all 2^N combinations (N = wildcard bit count)
    5. For each combination, overlay the bits onto the cleaned base IP
    6. Collapse the resulting IP addresses into minimal CIDR blocks
    
    Note: Caller is responsible for resource (memory/CPU) limits.
    
    Args:
        base_ip_str: IP address string (e.g., "10.4.0.0")
        wildcard_mask_str: Wildcard mask string (e.g., "0.0.127.252")
    
    Returns:
        list[IPv4Network]: Aggregated CIDR blocks covering all addresses
    
    Raises:
        ValueError: If IP/mask strings are invalid
    """
    # Step 1: Convert to 32-bit integers
    base_ip = int(IPv4Address(base_ip_str))
    wildcard = int(IPv4Address(wildcard_mask_str))
    
    # Step 2: Clean base IP (force wildcard positions to 0)
    base_ip &= ~wildcard
    
    # Step 3: Find all bit positions where wildcard has a 1
    wildcard_bit_positions = [i for i in range(32) if (wildcard >> i) & 1]
    num_wildcard_bits = len(wildcard_bit_positions)
    
    # Step 4 & 5: Generate all combinations
    raw_ips = []
    for i in range(2 ** num_wildcard_bits):
        current_ip = base_ip
        for bit_index in range(num_wildcard_bits):
            # If bit is set in our counter, set it in the current IP
            if (i >> bit_index) & 1:
                pos = wildcard_bit_positions[bit_index]
                current_ip |= (1 << pos)
        raw_ips.append(IPv4Address(current_ip))
    
    # Step 6: Collapse contiguous IPs into minimal CIDR blocks
    cidr_blocks = list(collapse_addresses(raw_ips))
    
    return cidr_blocks


class WildcardMaskExtractor(NetworkExtractor):
    """
    Extractor for Cisco ACL wildcard mask notation.
    
    Recognizes patterns like: "10.4.0.0 0.0.127.252"
    
    Only processes wildcard masks that fall within the search scope.
    If a mask falls outside the scope, returns None and lets other extractors handle it.
    
    Attributes:
        wildcard_mode_enabled: When True, this extractor is active. When False, skipped.
        wildcard_search_scope: IPv4Network scope boundary. Only masks within this scope are processed.
                              If None, all masks are processed (no scope filtering).
    """
    
    # Pattern: two dotted-quad IP addresses separated by whitespace
    # Matches: "10.4.0.0 0.0.127.252" or "192.168.1.0  0.0.0.255" (multiple spaces OK)
    PATTERN = re.compile(
        r'\b'
        r'(?:(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])\.){3}'  # First IP
        r'(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])'
        r'\s+'
        r'(?:(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])\.){3}'  # Second IP (mask)
        r'(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])'
        r'\b'
    )
    
    def __init__(self, wildcard_mode_enabled: bool = False, wildcard_search_scope=None):
        """
        Initialize the wildcard mask extractor.
        
        Args:
            wildcard_mode_enabled: When False, extraction is skipped (extractor is inactive).
            wildcard_search_scope: IPv4Network scope boundary. If provided, only wildcard masks
                                  within this scope are processed. If None, all masks are processed.
        """
        self.wildcard_mode_enabled = wildcard_mode_enabled
        self.wildcard_search_scope = wildcard_search_scope
    
    def extract(self, text: str) -> Optional[_RawExtraction]:
        """
        Extract first wildcard mask range from text.
        
        If wildcard_mode_enabled is False, returns None (extractor is skipped).
        If wildcard_search_scope is set, only processes masks within that scope.
        
        Args:
            text: Text to search for wildcard masks
        
        Returns:
            _RawExtraction if match found and passes scope validation, None otherwise
        """
        if not self.wildcard_mode_enabled:
            return None
        
        match = self.PATTERN.search(text)
        if not match:
            return None
        
        matched_text = match.group(0)
        parts = matched_text.split()
        
        if len(parts) != 2:
            return None
        
        base_ip_str, wildcard_mask_str = parts
        
        try:
            # Validate scope if provided
            if self.wildcard_search_scope is not None:
                # Check if the wildcard mask (as IP) falls within the search scope
                wildcard_mask_ip = IPv4Address(wildcard_mask_str)
                if wildcard_mask_ip not in self.wildcard_search_scope:
                    # Mask is outside scope - return None, let other extractors handle it
                    return None
            
            # Expand the wildcard mask to CIDR blocks
            expanded_cidrs = _wildcard_to_cidrs(base_ip_str, wildcard_mask_str)
            
            # Create WildcardMaskRange with original text and expanded CIDRs
            wildcard_range = WildcardMaskRange(
                original_text=matched_text,
                expanded_cidrs=expanded_cidrs
            )
            
            # Return extraction
            return _RawExtraction(
                network=wildcard_range,
                format_type='wildcard_mask',
                matched_text=matched_text,
                was_normalized=False
            )
            
        except (ValueError, WildcardMaskTooLargeError):
            # Invalid IP/mask format or too many bits - return None
            return None
    
    def get_format_type(self) -> str:
        """Return the format type this extractor produces."""
        return 'wildcard_mask'
