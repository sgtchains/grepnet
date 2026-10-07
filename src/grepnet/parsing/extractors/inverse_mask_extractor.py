"""
Inverse mask (hostmask) notation extractor.

Extracts networks in hostmask format (e.g., 192.0.2.0 0.0.0.255).
The second IP is the inverse of the subnet mask (hostmask).
"""

import re
from typing import Optional
from ipaddress import IPv4Address, IPv4Network, AddressValueError

from . import NetworkExtractor
from ...core import _RawExtraction


class InverseMaskExtractor(NetworkExtractor):
    """
    Extract inverse mask (hostmask) notation.
    
    Format: 192.0.2.0 0.0.0.255
    The second IP is the hostmask (inverse of netmask).
    
    Converts to CIDR network internally.
    """
    
    # IP address: 0-255.0-255.0-255.0-255
    IP_PATTERN = r'(?:(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])\.){3}(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])'
    
    # Inverse mask notation: IP space hostmask
    INVERSE_MASK_PATTERN = re.compile(
        f'\\b({IP_PATTERN})\\s+({IP_PATTERN})\\b'
    )
    
    def extract(self, text: str) -> Optional[_RawExtraction]:
        """
        Extract first valid inverse mask notation from text.
        
        Searches through all IP-space-IP patterns and returns the first one
        that has a valid hostmask. Handles overlapping patterns by manually
        advancing search position.
        
        Args:
            text: Text to search
        
        Returns:
            _RawExtraction if found, None otherwise
        """
        pos = 0
        while pos < len(text):
            # Search for next potential inverse mask from current position
            match = self.INVERSE_MASK_PATTERN.search(text, pos)
            if not match:
                return None
            
            ip_str = match.group(1)
            hostmask_str = match.group(2)
            matched_text = match.group(0)
            
            try:
                # Parse IP and hostmask
                ip_addr = IPv4Address(ip_str)
                hostmask_addr = IPv4Address(hostmask_str)
                
                # SPEC REQUIREMENT: Inverse mask MUST have MSB=0 (leading zero bit)
                # This distinguishes hostmask (0s from MSB) from netmask (1s from MSB)
                hostmask_int = int(hostmask_addr)
                if hostmask_int & 0x80000000:  # Check if MSB is 1
                    # MSB=1 means this is netmask format, not hostmask
                    # Reject and try next pattern
                    pos = match.start(2)  # Advance to second IP
                    continue
                
                # SPEC REQUIREMENT: Hostmask must be contiguous (all 0s from MSB, then all 1s)
                # Check if it matches pattern: 0+1* (zero or more 0s, then zero or more 1s)
                binary = bin(hostmask_int)[2:].zfill(32)
                if not (binary == '0' * 32 or bool(re.match(r'^0+1+$', binary))):
                    # Not a contiguous hostmask
                    pos = match.start(2)
                    continue
                
                # Convert hostmask to netmask: inverse of hostmask
                netmask_int = (~hostmask_addr._ip) & 0xffffffff
                netmask_ip = IPv4Address(netmask_int)
                
                # Create network with IP and netmask
                network = IPv4Network(f'{ip_addr}/{netmask_ip}', strict=False)
                
                was_normalized = False
                
                return _RawExtraction(
                    network=network,
                    format_type='inverse_mask',
                    matched_text=matched_text,
                    was_normalized=was_normalized,
                )
            except (AddressValueError, ValueError):
                # Invalid conversion, advance to second IP to allow retrying
                pos = match.start(2)
                continue
        
        return None
    
    def get_format_type(self) -> str:
        return 'inverse_mask'
