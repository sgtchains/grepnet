"""
IPv6 address and CIDR extractor.

Extracts IPv6 addresses in all valid formats:
- Full format: 2001:0db8:0000:0000:0000:0000:0000:0001
- Compressed: 2001:db8::1
- Link-local: fe80::1%eth0
- Loopback: ::1
- All zeros: ::
- IPv4-mapped: ::ffff:192.0.2.1
- CIDR notation: 2001:db8::/32
"""

import re
from typing import Optional
from ipaddress import IPv6Address, IPv6Network, AddressValueError

from . import NetworkExtractor
from ...core import _RawExtraction


class IPv6Extractor(NetworkExtractor):
    """
    Extract IPv6 addresses and CIDR notation.
    
    Supports:
    - Full addresses: 2001:0db8::0001/128
    - Compressed: 2001:db8::1/128, ::1/128, ::/0
    - Link-local: fe80::1%eth0/64
    - IPv4-mapped: ::ffff:192.0.2.1/128
    - All standard IPv6 formats per RFC 4291
    """
    
    # Comprehensive IPv6 regex pattern covering all valid formats
    # Based on https://stackoverflow.com/questions/53497/regular-expression-that-matches-valid-ipv6-addresses
    IPV6_PATTERN = re.compile(
        r'(?:(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|'  # 1:2:3:4:5:6:7:8
        r'(?:[0-9a-fA-F]{1,4}:){1,7}:|'  # 1::, 1:2:3:4:5:6:7::
        r'(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|'  # 1::8, 1:2:3:4:5:6::8
        r'(?:[0-9a-fA-F]{1,4}:){1,5}(?::[0-9a-fA-F]{1,4}){1,2}|'  # 1::7:8, 1:2:3:4:5::7:8
        r'(?:[0-9a-fA-F]{1,4}:){1,4}(?::[0-9a-fA-F]{1,4}){1,3}|'  # 1::6:7:8
        r'(?:[0-9a-fA-F]{1,4}:){1,3}(?::[0-9a-fA-F]{1,4}){1,4}|'  # 1::5:6:7:8
        r'(?:[0-9a-fA-F]{1,4}:){1,2}(?::[0-9a-fA-F]{1,4}){1,5}|'  # 1::4:5:6:7:8
        r'[0-9a-fA-F]{1,4}:(?::[0-9a-fA-F]{1,4}){1,6}|'  # 1::3:4:5:6:7:8
        r':(?:(?::[0-9a-fA-F]{1,4}){1,7}|:)|'  # ::2:3:4:5:6:7:8, ::1, ::
        r'fe80:(?::[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|'  # fe80::, fe80::1, fe80::1%eth0
        r'::(?:ffff(?::0{1,4})?:)?(?:(?:25[0-5]|(?:2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3}'  # ::ffff:192.0.2.1
        r'(?:25[0-5]|(?:2[0-4]|1{0,1}[0-9]){0,1}[0-9])|'
        r'(?:[0-9a-fA-F]{1,4}:){1,4}:(?:(?:25[0-5]|(?:2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3}'
        r'(?:25[0-5]|(?:2[0-4]|1{0,1}[0-9]){0,1}[0-9]))\b'
    )
    
    def extract(self, text: str) -> Optional[_RawExtraction]:
        """
        Extract first IPv6 address or CIDR from text.
        
        Args:
            text: Text to search
        
        Returns:
            _RawExtraction if found, None otherwise
        """
        match = self.IPV6_PATTERN.search(text)
        if not match:
            return None
        
        matched_text = match.group(0)
        remaining_text = text[match.end():]
        
        # Check for optional CIDR prefix (/0-128)
        cidr_match = re.match(r'^/(\d{1,3})', remaining_text)
        if cidr_match:
            prefix_len = int(cidr_match.group(1))
            if 0 <= prefix_len <= 128:
                matched_text += '/' + cidr_match.group(1)
                remaining_text = remaining_text[cidr_match.end():]
        
        # Parse to IPv6Network
        try:
            if '/' in matched_text:
                # CIDR notation
                network = IPv6Network(matched_text, strict=False)
                format_type = 'ipv6_cidr'
            else:
                # Plain address - convert to /128 network
                address = IPv6Address(matched_text)
                network = IPv6Network(f'{address}/128', strict=True)
                format_type = 'ip_only'
        except (AddressValueError, ValueError):
            # Invalid IPv6 format - skip
            return None
        
        return _RawExtraction(
            network=network,
            format_type=format_type,
            matched_text=matched_text,
            was_normalized=False,
        )
    
    def get_format_type(self) -> str:
        """Return the format type this extractor produces."""
        return 'ipv6'
