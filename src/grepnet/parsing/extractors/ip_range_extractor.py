"""
IP range extractor.

Extracts ranges in format: 192.0.2.0-192.0.2.255 (long), 192.0.2.0-255 (short)
"""

import re
from typing import Optional, Tuple
from ipaddress import IPv4Address, IPv6Address, AddressValueError

from . import NetworkExtractor
from ...core import _RawExtraction


class IPRangeExtractor(NetworkExtractor):
    """
    Extract IP range notation (start-end).
    
    Formats:
    - IPv4 long: 192.0.2.0-192.0.2.255
    - IPv4 short: 192.0.2.0-255 (abbreviated - end only specifies last octet)
    - IPv6: 2001:db8::1-2001:db8::100
    
    Stores as tuple (start_int, end_int) internally.
    """
    
    # IPv4 address
    IPV4_PATTERN = r'(?:(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])\.){3}(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])'
    
    # IPv6 address (simplified, allows leading zeros)
    IPV6_PATTERN = r'(?:[0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}'
    
    # IP range: IP-IP (long form)
    IPV4_RANGE_PATTERN = re.compile(f'\\b({IPV4_PATTERN})-({IPV4_PATTERN})\\b')
    IPV6_RANGE_PATTERN = re.compile(f'\\b({IPV6_PATTERN})-({IPV6_PATTERN})\\b')
    
    # IPv4 short range: IP-OCTET (e.g., 192.0.2.0-255 means 192.0.2.0-192.0.2.255)
    # Must come after long form to avoid premature matching
    IPV4_SHORT_RANGE_PATTERN = re.compile(f'\\b({IPV4_PATTERN})-([0-9]|[1-9][0-9]|1[0-9][0-9]|2[0-4][0-9]|25[0-5])\\b')
    
    def extract(self, text: str) -> Optional[_RawExtraction]:
        """
        Extract first IP range from text.
        
        Args:
            text: Text to search
        
        Returns:
            _RawExtraction if found, None otherwise
        """
        # Try IPv6 first (more specific)
        match = self.IPV6_RANGE_PATTERN.search(text)
        if match:
            return self._parse_ipv6_range(match)
        
        # Then IPv4 long form (IP-IP)
        match = self.IPV4_RANGE_PATTERN.search(text)
        if match:
            return self._parse_ipv4_range(match)
        
        # Finally IPv4 short form (IP-OCTET), but only if long form didn't match
        # This prevents 192.0.2.1-192.0.2.255 from being partially matched as 192.0.2.1-255
        match = self.IPV4_SHORT_RANGE_PATTERN.search(text)
        if match:
            return self._parse_ipv4_short_range(match)
        
        return None
        # Then IPv4
        match = self.IPV4_RANGE_PATTERN.search(text)
        if match:
            return self._parse_ipv4_range(match)
        
        return None
    
    def _parse_ipv4_range(self, match) -> Optional[_RawExtraction]:
        """Parse IPv4 range match (long form: 192.0.2.0-192.0.2.255)."""
        start_str = match.group(1)
        end_str = match.group(2)
        matched_text = match.group(0)
        
        try:
            start = IPv4Address(start_str)
            end = IPv4Address(end_str)
            
            if start > end:
                return None
            
            return _RawExtraction(
                network=(int(start), int(end)),
                format_type='ipv4_range',
                matched_text=matched_text,
                was_normalized=False,
            )
        except (AddressValueError, ValueError):
            return None
    
    def _parse_ipv4_short_range(self, match) -> Optional[_RawExtraction]:
        """
        Parse IPv4 short range match (abbreviated form: 192.0.2.0-255).
        
        Takes start IP and end octet, constructs full end IP by replacing
        the last octet of the start IP with the end octet.
        
        Args:
            match: Regex match with groups (1: start_ip, 2: end_octet)
        
        Returns:
            _RawExtraction with full range, or None if invalid
        """
        start_str = match.group(1)
        end_octet_str = match.group(2)
        matched_text = match.group(0)
        
        try:
            start = IPv4Address(start_str)
            end_octet = int(end_octet_str)
            
            # Validate octet range
            if end_octet < 0 or end_octet > 255:
                return None
            
            # Construct end IP by replacing last octet of start IP
            start_parts = str(start).split('.')
            end_ip_str = '.'.join(start_parts[:3]) + '.' + str(end_octet)
            end = IPv4Address(end_ip_str)
            
            # Validate start <= end
            if start > end:
                return None
            
            return _RawExtraction(
                network=(int(start), int(end)),
                format_type='ipv4_range',
                matched_text=matched_text,
                was_normalized=False,
            )
        except (AddressValueError, ValueError):
            return None
    
    def _parse_ipv6_range(self, match) -> Optional[_RawExtraction]:
        """Parse IPv6 range match."""
        start_str = match.group(1)
        end_str = match.group(2)
        matched_text = match.group(0)
        
        try:
            start = IPv6Address(start_str)
            end = IPv6Address(end_str)
            
            if start > end:
                return None
            
            return _RawExtraction(
                network=(int(start), int(end)),
                format_type='ipv6_range',
                matched_text=matched_text,
                was_normalized=False,
            )
        except (AddressValueError, ValueError):
            return None
    
    def get_format_type(self) -> str:
        return 'ip_range'
