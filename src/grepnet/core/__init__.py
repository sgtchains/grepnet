"""
Core module: Data structures and fundamental abstractions.

Classes:
- _RawExtraction: Internal format used by extractors (network, format_type, matched_text, was_normalized)
- ParsedExtraction: Represents a single extracted network object with all matched text variations
- MatchResult: Represents a match between a pattern and file data
- MatchType: Enumeration of match relationship types
- WildcardMaskRange: Represents a network range specified via Cisco ACL wildcard mask notation
- Colorizer: ANSI color code generation and application
- BinaryDetector: Binary file detection for VTY protection
"""

from .network_objects import _RawExtraction, ParsedExtraction, MatchResult, MatchType, WildcardMaskRange
from .colorizer import Colorizer
from .binary_detector import BinaryDetector

__all__ = [
    '_RawExtraction',
    'ParsedExtraction',
    'MatchResult',
    'MatchType',
    'WildcardMaskRange',
    'Colorizer',
    'BinaryDetector',
]
