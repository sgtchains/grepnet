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
                
                # Convert hostmask to netmask: inverse of hostmask
                netmask_int = (~hostmask_addr._ip) & 0xffffffff
                netmask_ip = IPv4Address(netmask_int)
                
                # Create network with IP and netmask
                network = IPv4Network(f'{ip_addr}/{netmask_ip}', strict=False)
                
                # Check if this looks like an inverse mask (hostmask is non-zero)
                # Note: This is a best-effort heuristic to distinguish from subnet mask format
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
