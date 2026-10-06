"""
CIDR notation extractor.

Extracts IPv4 and IPv6 CIDR blocks (e.g., 192.0.2.0/24, 2001:db8::/32).
Normalizes host bits in non-strict mode (e.g., 192.0.2.5/24 → 192.0.2.0/24).
"""

import re
from typing import Optional
from ipaddress import IPv4Network, IPv6Network, AddressValueError

from . import NetworkExtractor
from ...core import _RawExtraction


class CIDRExtractor(NetworkExtractor):
    """
    Extract CIDR notation networks.
    
    Regex matches:
    - IPv4: 0.0.0.0/0 to 255.255.255.255/32
    - IPv6: ::1/128, 2001:db8::/32, etc.
    
    Handles host bits by normalizing in non-strict mode (strict=False).
    """
    
    # Match IPv4 and IPv6 CIDR notations
    # IPv4: standard dotted decimal with /0-32
    # IPv6: handles all forms including ::, full address, mixed notation
    # Use negative lookbehind (?<!\.) to prevent matching IP fragments
    # (e.g., prevents 0.2.1.232/24 from matching in 192.0.2.1.232/24)
    CIDR_PATTERN = re.compile(
        r'(?<!\.)(?:'
        # IPv4 CIDR: 0-255.0-255.0-255.0-255/0-32
        r'(?:(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])\.){3}(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])'
        r'/(?:3[0-2]|[1-2]?[0-9])'
        r'|'
        # IPv6 CIDR: 
        # Handles: 2001:db8::/32, ::1/128, fe80::1/64, 2001:db8::1/128, etc.
        r'(?:'
        r'(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|'  # 1:2:3:4:5:6:7:8
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
        r'(?:25[0-5]|(?:2[0-4]|1{0,1}[0-9]){0,1}[0-9])'
        r')'
        r'/(?:12[0-8]|1[01]?[0-9]|[0-9]{1,2})'
        r')\b'
    )
    
    def __init__(self, strict: bool = False):
        """
        Initialize extractor.
        
        Args:
            strict: If True, reject CIDR with host bits set.
                   If False, normalize host bits.
        """
        self.strict = strict
    
    def extract(self, text: str) -> Optional[_RawExtraction]:
        """
        Extract first CIDR from text.
        
        Args:
            text: Text to search
        
        Returns:
            _RawExtraction if found, None otherwise
        """
        match = self.CIDR_PATTERN.search(text)
        if not match:
            return None
        
        cidr_text = match.group(0)
        
        try:
            # strict=False normalizes host bits (e.g., 192.0.2.5/24 → 192.0.2.0/24)
            network = IPv4Network(cidr_text, strict=False)
            was_normalized = str(network) != cidr_text
            
            return _RawExtraction(
                network=network,
                format_type='cidr_notation',
                matched_text=cidr_text,
                was_normalized=was_normalized,
            )
        except (AddressValueError, ValueError):
            pass
        
        try:
            network = IPv6Network(cidr_text, strict=False)
            was_normalized = str(network) != cidr_text
            
            return _RawExtraction(
                network=network,
                format_type='cidr_notation',
                matched_text=cidr_text,
                was_normalized=was_normalized,
            )
        except (AddressValueError, ValueError):
            pass
        
        return None
    
    def get_format_type(self) -> str:
        return 'cidr_notation'
