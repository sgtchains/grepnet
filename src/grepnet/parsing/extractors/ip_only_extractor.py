"""
IP-only extractor.

Extracts bare IP addresses (IPv4 and IPv6).
Converts single IPs to /32 (IPv4) or /128 (IPv6) networks for matching.
"""

import re
from typing import Optional
from ipaddress import IPv4Address, IPv6Address, IPv4Network, IPv6Network, AddressValueError

from . import NetworkExtractor
from ...core import _RawExtraction


class IPOnlyExtractor(NetworkExtractor):
    """
    Extract bare IP addresses.
    
    Formats:
    - IPv4: 192.0.2.1, 10.0.0.1
    - IPv6: 2001:db8::1, ::1
    
    Converts to /32 or /128 networks internally for matching.
    """
    
    # IPv4 address
    IPV4_PATTERN = r'\b(?:(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])\.){3}(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])\b'
    
    # IPv6 address - comprehensive RFC 4291 pattern handling all valid formats
    # Matches: ::1, 2001:db8::, 2001:db8::1, ::ffff:192.0.2.1, etc.
    # NOTE: Uses negative lookahead to prevent partial matches of compressed addresses
    # NOTE: Zone IDs (e.g., fe80::1%eth0) are NOT supported per spec
    IPV6_PATTERN = (
        r'(?:(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|'  # 1:2:3:4:5:6:7:8
        r'(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|'  # 1::8, 1:2:3:4:5:6::8
        r'(?:[0-9a-fA-F]{1,4}:){1,5}(?::[0-9a-fA-F]{1,4}){1,2}|'  # 1::7:8, 1:2:3:4:5::7:8
        r'(?:[0-9a-fA-F]{1,4}:){1,4}(?::[0-9a-fA-F]{1,4}){1,3}|'  # 1::6:7:8, 1:2:3:4::6:7:8
        r'(?:[0-9a-fA-F]{1,4}:){1,3}(?::[0-9a-fA-F]{1,4}){1,4}|'  # 1::5:6:7:8, 1:2:3::5:6:7:8
        r'(?:[0-9a-fA-F]{1,4}:){1,2}(?::[0-9a-fA-F]{1,4}){1,5}|'  # 1::4:5:6:7:8, 1:2::4:5:6:7:8
        r'[0-9a-fA-F]{1,4}:(?:(?::[0-9a-fA-F]{1,4}){1,6})|'  # 1::3:4:5:6:7:8
        r'::(?:ffff(?::0{1,4})?:)?(?:(?:25[0-5]|(?:2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3}'  # ::ffff:192.0.2.1
        r'(?:25[0-5]|(?:2[0-4]|1{0,1}[0-9]){0,1}[0-9])|'
        r'(?:[0-9a-fA-F]{1,4}:){1,4}:(?:(?:25[0-5]|(?:2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3}'
        r'(?:25[0-5]|(?:2[0-4]|1{0,1}[0-9]){0,1}[0-9])|'
        r'(?:[0-9a-fA-F]{1,4}:){1,7}:|'  # 1:: (trailing :: - must come AFTER more specific patterns)
        r':(?:(?::[0-9a-fA-F]{1,4}){1,7}|:)'  # ::2:3:4:5:6:7:8, ::1, ::
        r')(?![0-9a-fA-F:])'  # Negative lookahead: no hex digit or colon after
    )
    
    IPV4_ONLY_PATTERN = re.compile(IPV4_PATTERN)
    IPV6_ONLY_PATTERN = re.compile(IPV6_PATTERN)
    
    def extract(self, text: str) -> Optional[_RawExtraction]:
        """
        Extract first bare IP address from text.
        
        Args:
            text: Text to search
        
        Returns:
            _RawExtraction if found, None otherwise
        """
        # Try IPv4 first
        match = self.IPV4_ONLY_PATTERN.search(text)
        if match:
            ip_str = match.group(0)
            try:
                addr = IPv4Address(ip_str)
                network = IPv4Network(f'{ip_str}/32', strict=True)
                return _RawExtraction(
                    network=network,
                    format_type='ip_only',
                    matched_text=ip_str,
                    was_normalized=False,
                )
            except (AddressValueError, ValueError):
                pass
        
        # Then IPv6
        match = self.IPV6_ONLY_PATTERN.search(text)
        if match:
            ip_str = match.group(0)
            try:
                addr = IPv6Address(ip_str)
                network = IPv6Network(f'{ip_str}/128', strict=True)
                return _RawExtraction(
                    network=network,
                    format_type='ip_only',
                    matched_text=ip_str,
                    was_normalized=False,
                )
            except (AddressValueError, ValueError):
                pass
        
        return None
    
    def get_format_type(self) -> str:
        return 'ip_only'
