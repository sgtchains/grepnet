"""
Network objects and match result data structures.

ParsedExtraction: Represents an extracted network object before matching.
MatchResult: Represents the result of matching a pattern against file data.
MatchType: Enumeration of match relationship types.
"""

from enum import Enum, auto
from typing import NamedTuple, Optional
from ipaddress import IPv4Network, IPv6Network, IPv4Address, IPv6Address


class MatchType(Enum):
    """
    Match relationship types between pattern and file data.
    
    Comparison priority (when multiple match types apply to a single line):
    1. EQUALS - identical networks
    2. SUBSET - pattern is subset of file data
    3. SUPERSET - pattern is superset of file data
    4. OVERLAP - partial overlap (only ranges, impossible with CIDR)
    5. UNMATCHED - no relationship (when using -u flag)
    """
    EQUALS = auto()
    SUBSET = auto()
    SUPERSET = auto()
    OVERLAP = auto()
    UNMATCHED = auto()


class _RawExtraction(NamedTuple):
    """
    Internal extraction format used by extractors.
    
    This intermediate type allows extractors to work independently of the
    matched_texts architecture. The parser converts these to ParsedExtraction.
    """
    network: object  # IPv4Network | IPv6Network | tuple[int, int]
    format_type: str
    matched_text: str  # Single matched text (aggregated by parser)
    was_normalized: bool


class ParsedExtraction(NamedTuple):
    """
    Result of parsing a single network expression from text.
    
    Attributes:
        network: IPv4Network, IPv6Network, or tuple (start_int, end_int) for ranges
        format_type: One of: 'cidr_notation', 'subnet_mask', 'inverse_mask', 
                     'ipv4_range', 'ipv6_range', 'ip_only'
        was_normalized: True if ANY matched text required normalization
        matched_texts: List of dicts with text and per-text normalization info
                       [{"text": "192.0.2.2/24", "was_normalized": true}, ...]
    """
    network: object  # IPv4Network | IPv6Network | tuple[int, int]
    format_type: str
    was_normalized: bool  # True if ANY text in matched_texts was normalized
    matched_texts: list  # List[dict] with {"text": str, "was_normalized": bool}


class MatchResult(NamedTuple):
    """
    Result of matching a single pattern against a single extracted file network.
    
    When yield_all_lines is enabled, also represents non-match lines (for context).
    
    Created at match time with pre-rendered colored content. Output formatters
    consume the pre-rendered content_colored to prevent re-coloring during output.
    
    Attributes:
        line_number: 1-based line number from input source
        line_content: Original line text (uncolored)
        content_colored: Pre-rendered colored content (at match time, not output time)
        file_extraction: ParsedExtraction from the matched line (None for non-matches)
        pattern_extraction: ParsedExtraction of the pattern being matched (None for non-matches)
        match_type: MatchType (EQUALS, SUBSET, SUPERSET, OVERLAP, UNMATCHED) (None for non-matches)
        match_index: Index into the extracted networks on this line (0-based) (-1 for non-matches)
        filename: Name of input file or '<stdin>'
        is_binary_file: True if this match is from a binary file
        content_marked: Internal markup content (U+E000/U+E001 encoded) for debugging
        is_match: True if this line contains an actual match (False for context lines)
        byte_offset: 0-based byte offset of line start in file (or 0 for stdin)
    """
    line_number: int
    line_content: str
    content_colored: str
    file_extraction: Optional[ParsedExtraction]
    pattern_extraction: Optional[ParsedExtraction]
    match_type: Optional[MatchType]
    match_index: int
    filename: Optional[str] = None  # Display name from InputSource, or None for stdin without --label
    is_binary_file: bool = False
    content_marked: str = ""
    is_match: bool = True
    byte_offset: int = 0
    file_type: str = 'stdin'  # 'file', 'stdin', or 'fd'
