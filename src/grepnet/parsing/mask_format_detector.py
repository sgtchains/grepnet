"""
Mask format detector for analyzing peek buffer contents.

Detects whether a text sample uses netmask or hostmask format predominantly,
to provide hints for more intelligent parsing.
"""

import re
from ipaddress import IPv4Address, AddressValueError


class MaskFormatDetector:
    """
    Analyze text to detect netmask vs hostmask format preferences.
    
    Returns format hints: 'netmask_dominant', 'hostmask_dominant', 'mixed', 'unknown'
    """
    
    # Pattern to match two space-separated IPv4 addresses
    IP_PATTERN = r'(?:(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])\.){3}(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])'
    # Two-value pattern: IP followed by spaces/tabs (not newlines), then another IP
    TWO_VALUE_PATTERN = re.compile(f'\\b({IP_PATTERN})[ \t]+({IP_PATTERN})\\b')
    
    @staticmethod
    def detect_format(text: str) -> str:
        """
        Detect dominant mask format in text.
        
        Args:
            text: Text to analyze (typically first 8KB of file)
        
        Returns:
            Format hint: 'netmask_dominant', 'hostmask_dominant', 'mixed', or 'unknown'
        """
        if not text or not text.strip():
            return 'unknown'
        
        netmask_count = 0
        hostmask_count = 0
        
        # Find all two-value patterns
        for match in MaskFormatDetector.TWO_VALUE_PATTERN.finditer(text):
            second_value_str = match.group(2)
            
            try:
                second_value = IPv4Address(second_value_str)
                second_value_int = int(second_value)
                
                # Check MSB to determine format
                has_msb_one = bool(second_value_int & 0x80000000)
                
                if has_msb_one:
                    # MSB=1 indicates netmask format
                    netmask_count += 1
                else:
                    # MSB=0 indicates hostmask format
                    hostmask_count += 1
            except (AddressValueError, ValueError):
                # Invalid IP, skip
                continue
        
        # Determine result based on counts
        total = netmask_count + hostmask_count
        
        if total == 0:
            return 'unknown'
        
        # Calculate ratio
        netmask_ratio = netmask_count / total if total > 0 else 0
        hostmask_ratio = hostmask_count / total if total > 0 else 0
        
        # Threshold: >66% for dominance (at least 2:1 ratio)
        threshold = 0.66
        
        if netmask_ratio >= threshold:
            return 'netmask_dominant'
        elif hostmask_ratio >= threshold:
            return 'hostmask_dominant'
        else:
            # Mixed format detected
            return 'mixed'
    
    @staticmethod
    def is_conclusive(hint: str) -> bool:
        """
        Check if a format hint is conclusive enough to use.
        
        Args:
            hint: Format hint from detect_format()
        
        Returns:
            True if hint should be used, False if should fallback to standard algorithm
        """
        return hint in ('netmask_dominant', 'hostmask_dominant')
