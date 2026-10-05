"""
Base class for network extractors.

Extractors:
- CIDRExtractor: IPv4/IPv6 CIDR notation
- SubnetMaskExtractor: IPv4 subnet mask notation
- InverseMaskExtractor: IPv4 inverse mask notation
- IPRangeExtractor: IP range notation
- IPv6Extractor: IPv6 addresses and CIDR blocks
- IPOnlyExtractor: Bare IP addresses
"""

from abc import ABC, abstractmethod
from typing import Optional
from ...core import ParsedExtraction


class NetworkExtractor(ABC):
    """
    Abstract base class for extracting network objects from text.
    
    All extractors follow the same interface:
    - extract(text) → Optional[ParsedExtraction]
    - Returns None if no match
    - Returns ParsedExtraction if match found
    """
    
    @abstractmethod
    def extract(self, text: str) -> Optional[ParsedExtraction]:
        """
        Extract network object from text.
        
        Args:
            text: Text to search for network object
        
        Returns:
            ParsedExtraction if found, None otherwise
        """
        pass
    
    @abstractmethod
    def get_format_type(self) -> str:
        """Return the format type this extractor produces."""
        pass


from .cidr_extractor import CIDRExtractor
from .subnet_mask_extractor import SubnetMaskExtractor
from .inverse_mask_extractor import InverseMaskExtractor
from .ip_range_extractor import IPRangeExtractor
from .ipv6_extractor import IPv6Extractor
from .ip_only_extractor import IPOnlyExtractor

__all__ = [
    'NetworkExtractor',
    'CIDRExtractor',
    'SubnetMaskExtractor',
    'InverseMaskExtractor',
    'IPRangeExtractor',
    'IPOnlyExtractor',
]
