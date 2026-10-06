"""
Subnet mask notation extractor.

Extracts networks in IP mask format (e.g., 192.0.2.0 255.255.255.0).
Converts to CIDR internally for matching.
"""

import re
from typing import Optional
from ipaddress import IPv4Address, IPv4Network, AddressValueError

from . import NetworkExtractor
from ...core import _RawExtraction


class SubnetMaskExtractor(NetworkExtractor):
    """
    Extract subnet mask notation (IP with decimal mask).
    
    Format: 192.0.2.0 255.255.255.0
    Pattern: IP space mask (both must be valid IPv4)
    
    Converts to CIDR network internally.
    """
    
    # IP address: 0-255.0-255.0-255.0-255
    IP_PATTERN = r'(?:(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])\.){3}(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])'
    
    # Subnet mask notation: IP space IP
    SUBNET_MASK_PATTERN = re.compile(
        f'\\b({IP_PATTERN})\\s+({IP_PATTERN})\\b'
    )
    
    def extract(self, text: str) -> Optional[_RawExtraction]:
        """
        Extract first valid subnet mask notation from text.
        
        Searches through all IP-space-IP patterns and returns the first one
        that has a valid subnet mask (contiguous 1-bits from left).
        Handles overlapping patterns by manually advancing search position.
        
        Args:
            text: Text to search
        
        Returns:
            _RawExtraction if found, None otherwise
        """
        pos = 0
        while pos < len(text):
            # Search for next potential subnet mask from current position
            match = self.SUBNET_MASK_PATTERN.search(text, pos)
            if not match:
                return None
            
            ip_str = match.group(1)
            mask_str = match.group(2)
            matched_text = match.group(0)
            
            try:
                # Validate that the mask is a valid subnet mask (contiguous 1-bits from left)
                mask_addr = IPv4Address(mask_str)
                mask_int = int(mask_addr)
                
                # A valid netmask has contiguous 1-bits from the left
                # Count leading 1s, then all remaining bits should be 0
                ones_count = bin(mask_int).count('1')
                # Reconstruct what a valid mask with that many 1s should look like
                valid_mask = (0xffffffff << (32 - ones_count)) & 0xffffffff
                
                if mask_int != valid_mask:
                    # Not a valid subnet mask, advance past the first IP in this match
                    # to allow the second IP to be the start of the next pattern
                    pos = match.start(2)  # Start searching from the second IP
                    continue
                
                # Create network from IP and mask
                network = IPv4Network(f'{ip_str}/{mask_str}', strict=False)
                
                # Check if host bits were set in original
                was_normalized = f'{network.network_address} {network.netmask}' != matched_text
                
                return _RawExtraction(
                    network=network,
                    format_type='subnet_mask',
                    matched_text=matched_text,
                    was_normalized=was_normalized,
                )
            except (AddressValueError, ValueError):
                # Invalid IP addresses, advance to second IP to allow retrying
                pos = match.start(2)
                continue
        
        return None
    
    def get_format_type(self) -> str:
        return 'subnet_mask'
