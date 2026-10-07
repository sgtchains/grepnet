"""
Network parser: orchestrates extraction from text.

Handles:
- Comment filtering
- Extraction in priority order (CIDR → subnet mask → inverse mask → ranges → IP only)
- Deduplication
- Validation
"""

from typing import List, Optional, Set
import re
from ipaddress import IPv4Address
from .comment_handler import CommentHandler
from .extractors import (
    CIDRExtractor,
    SubnetMaskExtractor,
    InverseMaskExtractor,
    IPRangeExtractor,
    IPv6Extractor,
    IPOnlyExtractor,
)
from ..core import ParsedExtraction, _RawExtraction


class NetworkParser:
    """
    Main parsing orchestrator.
    
    Extraction priority (prevents false positives from overlapping patterns):
    1. CIDR notation (IPv4 and IPv6, most specific, least ambiguous)
    2. Subnet mask notation (IPv4 only: IP + netmask)
    3. Inverse mask notation (IPv4 only: IP + hostmask)
    4. IP ranges (IPv4 and IPv6: start-end)
    5. Bare IP addresses (IPv4 and IPv6, least specific, most ambiguous)
    
    Strategy: Extract all networks from each line, deduplicate by network value.
    """
    
    def __init__(
        self,
        filter_comments: bool = True,
        strict_mode: bool = False,
        parse_cidr: str = 'both',
        parse_netmask: str = 'both',
        parse_hostmask: str = 'both',
        parse_ranges: str = 'both',
        range_format: str = 'both',
    ):
        """
        Initialize parser.
        
        Args:
            filter_comments: If True, remove comments before extraction
            strict_mode: If True, reject malformed CIDR (host bits set)
            parse_cidr: Where to accept CIDR ('pattern', 'input', 'both', 'none')
            parse_netmask: Where to accept subnet masks ('pattern', 'input', 'both', 'none')
            parse_hostmask: Where to accept hostmasks ('pattern', 'input', 'both', 'none')
            range_format: Range format preference ('long', 'short', 'both', 'none')
        """
        self.filter_comments = filter_comments
        self.strict_mode = strict_mode
        self.parse_cidr = parse_cidr
        self.parse_netmask = parse_netmask
        self.parse_hostmask = parse_hostmask
        self.parse_ranges = parse_ranges
        self.range_format = range_format
        
        # Initialize comment handler
        self.comment_handler = CommentHandler()
        
        # Initialize extractors in priority order
        self.extractors = [
            CIDRExtractor(strict=strict_mode),
            SubnetMaskExtractor(),
            InverseMaskExtractor(),
            IPRangeExtractor(),
            IPOnlyExtractor(),
        ]
    
    def _is_snmp_oid_line(self, line: str) -> bool:
        """
        Detect if line contains SNMP OID patterns or malformed MIB-like patterns.
        
        SNMP OIDs have 4+ dots (5+ octets), e.g., 1.3.6.1.2.1.1.0
        IPv4 addresses have 3 dots (4 octets), e.g., 192.0.2.1
        Malformed patterns have 4+ dots before CIDR/mask, e.g., 192.0.2.1.232/24
        
        Args:
            line: Line text
        
        Returns:
            True if SNMP OID or malformed MIB-like pattern detected
        """
        # Pattern 1: 4+ dots separated by digits (SNMP OID or 5+ octet pattern)
        # Matches: 1.3.6.1.2.1.1.0 (4 dots = 5 octets), 192.0.2.1.232 (4 dots), etc.
        # This catches both pure SNMP OIDs and malformed IP patterns
        multiple_dots_pattern = r'\d{1,4}(?:\.\d{1,4}){4,}'
        if re.search(multiple_dots_pattern, line):
            return True
        
        return False
    
    def _should_use_extractor(self, extractor_type: str, context: str) -> bool:
        """
        Determine if an extractor should be used based on parse control flags.
        
        Args:
            extractor_type: Type of extractor ('cidr', 'netmask', 'hostmask', 'range')
            context: Context ('pattern' or 'input')
        
        Returns:
            True if extractor should be used, False otherwise
        """
        if extractor_type == 'cidr':
            if self.parse_cidr == 'none':
                return False
            if self.parse_cidr == 'pattern' and context != 'pattern':
                return False
            if self.parse_cidr == 'input' and context != 'input':
                return False
        elif extractor_type == 'netmask':
            if self.parse_netmask == 'none':
                return False
            if self.parse_netmask == 'pattern' and context != 'pattern':
                return False
            if self.parse_netmask == 'input' and context != 'input':
                return False
        elif extractor_type == 'hostmask':
            if self.parse_hostmask == 'none':
                return False
            if self.parse_hostmask == 'pattern' and context != 'pattern':
                return False
            if self.parse_hostmask == 'input' and context != 'input':
                return False
        elif extractor_type == 'range':
            if self.parse_ranges == 'none':
                return False
            if self.parse_ranges == 'pattern' and context != 'pattern':
                return False
            if self.parse_ranges == 'input' and context != 'input':
                return False
        
        return True
    
    def parse_line(self, line: str, line_number: int = 0, context: str = 'input') -> List[ParsedExtraction]:
        """
        Extract all networks from a line.
        
        Args:
            line: Line text
            line_number: Line number (1-based, for reference)
            context: Context for parsing ('pattern' for search patterns, 'input' for file input)
        
        Returns:
            List of ParsedExtraction objects, deduplicated by network value
        """
        # Filter comments if enabled
        filtered_line, _ = self.comment_handler.filter_comments(
            line,
            filter_enabled=self.filter_comments,
        )
        
        # Skip empty lines after comment removal
        if not filtered_line.strip():
            return []
        
        # Check if line contains SNMP OID patterns (skip plain IP extraction if true)
        has_snmp_oid = self._is_snmp_oid_line(filtered_line)
        
        # Map extractor indices to types for parse control checking
        extractor_types = [
            'cidr',       # 0: CIDRExtractor
            'netmask',    # 1: SubnetMaskExtractor
            'hostmask',   # 2: InverseMaskExtractor
            'range',      # 3: IPRangeExtractor
            'ip_only',    # 4: IPOnlyExtractor
        ]
        
        # Extract networks using each extractor
        # Collect raw extractions from extractors with their positions in original line
        raw_extractions: List[_RawExtraction] = []
        working_line = filtered_line
        original_line = filtered_line  # Keep original for position tracking
        
        for idx, extractor in enumerate(self.extractors):
            # Skip IPOnlyExtractor if SNMP OID detected (IPOnlyExtractor is at index 4)
            if idx == 4 and has_snmp_oid:
                continue
            
            # Check parse control flags
            if idx < len(extractor_types):
                extractor_type = extractor_types[idx]
                if not self._should_use_extractor(extractor_type, context):
                    continue
            
            # Keep calling each extractor until no more networks found
            while True:
                extraction = extractor.extract(working_line)
                if extraction is None:
                    break
                
                # Helper functions for mask detection
                def _is_valid_netmask(ip_str: str) -> bool:
                    """Check if IP is a valid netmask (contiguous 1s followed by 0s)"""
                    try:
                        ip_addr = IPv4Address(ip_str)
                        binary = bin(int(ip_addr))[2:].zfill(32)
                        return bool(re.match(r'^1+0*$', binary))
                    except:
                        return False
                
                def _is_valid_hostmask(ip_str: str) -> bool:
                    """Check if IP is a valid hostmask (contiguous 0s followed by 1s)"""
                    try:
                        ip_addr = IPv4Address(ip_str)
                        binary = bin(int(ip_addr))[2:].zfill(32)
                        return bool(re.match(r'^0+1*$', binary))
                    except:
                        return False
                
                # Validate extraction against parse control settings
                skip_extraction = False
                
                if extraction.format_type == 'ip_only' and idx == 4:
                    # Find position in ORIGINAL line to detect format context
                    orig_pos = original_line.find(extraction.matched_text)
                    
                    if orig_pos >= 0:
                        match_end_pos = orig_pos + len(extraction.matched_text)
                        if match_end_pos < len(original_line):
                            next_char = original_line[match_end_pos]
                            
                            # If followed by /, validate CIDR parse control
                            if next_char == '/':
                                if self.parse_cidr == 'none':
                                    skip_extraction = True
                                elif self.parse_cidr == 'pattern' and context != 'pattern':
                                    skip_extraction = True
                                elif self.parse_cidr == 'input' and context == 'pattern':
                                    skip_extraction = True
                            
                            # If followed by -, validate range parse control
                            elif next_char == '-':
                                if self.parse_ranges == 'none':
                                    skip_extraction = True
                                elif self.parse_ranges == 'pattern' and context != 'pattern':
                                    skip_extraction = True
                                elif self.parse_ranges == 'input' and context == 'pattern':
                                    skip_extraction = True
                            
                            # If followed by space, check for space-separated pair formats (netmask/hostmask)
                            elif next_char == ' ':
                                lookahead = original_line[match_end_pos:]
                                space_match = re.match(r' +([0-9.]+|[\da-fA-F:]+)(?:\s|$)', lookahead)
                                if space_match:
                                    second_ip = space_match.group(1)
                                    # Determine if it's a netmask or hostmask
                                    is_netmask = _is_valid_netmask(second_ip)
                                    is_hostmask = _is_valid_hostmask(second_ip)
                                    
                                    if is_netmask:
                                        # It's netmask format (space-separated pair)
                                        if self.parse_netmask == 'none':
                                            skip_extraction = True
                                        elif self.parse_netmask == 'pattern' and context != 'pattern':
                                            skip_extraction = True
                                        elif self.parse_netmask == 'input' and context == 'pattern':
                                            skip_extraction = True
                                    elif is_hostmask:
                                        # It's hostmask format (space-separated pair)
                                        if self.parse_hostmask == 'none':
                                            skip_extraction = True
                                        elif self.parse_hostmask == 'pattern' and context != 'pattern':
                                            skip_extraction = True
                                        elif self.parse_hostmask == 'input' and context == 'pattern':
                                            skip_extraction = True
                        
                        # Check what comes BEFORE the matched IP (for 2nd part of space-separated pairs)
                        if not skip_extraction and orig_pos > 0:
                            before_context = original_line[:orig_pos]
                            
                            # Check for "IP space" pattern before (2nd part of space-separated pair)
                            before_match = re.search(r'(\d+\.\d+\.\d+\.\d+)\s+$', before_context)
                            if before_match:
                                # This IP appears to be the 2nd part of a space-separated pair
                                is_netmask = _is_valid_netmask(extraction.matched_text)
                                is_hostmask = _is_valid_hostmask(extraction.matched_text)
                                
                                if is_netmask:
                                    # It's the netmask part (space-separated pair)
                                    if self.parse_netmask == 'none':
                                        skip_extraction = True
                                    elif self.parse_netmask == 'pattern' and context != 'pattern':
                                        skip_extraction = True
                                    elif self.parse_netmask == 'input' and context == 'pattern':
                                        skip_extraction = True
                                elif is_hostmask:
                                    # It's the hostmask part (space-separated pair)
                                    if self.parse_hostmask == 'none':
                                        skip_extraction = True
                                    elif self.parse_hostmask == 'pattern' and context != 'pattern':
                                        skip_extraction = True
                                    elif self.parse_hostmask == 'input' and context == 'pattern':
                                        skip_extraction = True
                
                if skip_extraction:
                    # Remove the matched text to prevent re-extraction by other extractors
                    working_line = working_line.replace(extraction.matched_text, '', 1)
                    continue
                
                raw_extractions.append(extraction)
                # Remove the matched text to prevent re-extraction by lower-priority extractors
                working_line = working_line.replace(extraction.matched_text, '', 1)
        
        # Determine position of each extraction in the original line for ordering
        # Track positions sequentially to handle duplicates correctly
        positions_map = {}  # Map extraction to its position
        position_search_start = 0
        
        for extraction in raw_extractions:
            pos = original_line.find(extraction.matched_text, position_search_start)
            if pos >= 0:
                positions_map[id(extraction)] = pos
                position_search_start = pos + 1  # Next search starts after this match
            else:
                positions_map[id(extraction)] = float('inf')
        
        # Sort raw_extractions by position in original_line
        raw_extractions.sort(key=lambda e: positions_map[id(e)])
        
        # Group extractions by network value, collecting all text variations with per-text normalization
        # Networks are already ordered by position in original_line (from raw_extractions sort above)
        network_groups: dict = {}
        
        for extraction in raw_extractions:
            network_key = str(extraction.network)
            
            if network_key not in network_groups:
                network_groups[network_key] = {
                    'network': extraction.network,
                    'format_type': extraction.format_type,
                    'matched_texts': [],  # List of {"text": str, "was_normalized": bool}
                    'any_normalized': False  # Track if ANY text was normalized
                }
            
            # Add this matched text with its normalization status
            text_entry = {
                'text': extraction.matched_text,
                'was_normalized': extraction.was_normalized,
            }
            
            # Preserve all occurrences (no deduplication at parse time)
            network_groups[network_key]['matched_texts'].append(text_entry)
            if extraction.was_normalized:
                network_groups[network_key]['any_normalized'] = True
        
        # Convert to ParsedExtraction with all matched texts aggregated
        deduped = []
        for network_key, group_data in network_groups.items():
            extraction_with_texts = ParsedExtraction(
                network=group_data['network'],
                format_type=group_data['format_type'],
                was_normalized=group_data['any_normalized'],
                matched_texts=group_data['matched_texts'],
            )
            deduped.append(extraction_with_texts)
        
        return deduped
    
    def parse_text(self, text: str) -> List[tuple]:
        """
        Parse multi-line text.
        
        Args:
            text: Multi-line text
        
        Returns:
            List of (line_number, line_text, extractions) tuples
        """
        results = []
        for line_num, line in enumerate(text.split('\n'), start=1):
            extractions = self.parse_line(line, line_num)
            if extractions:
                results.append((line_num, line, extractions))
        return results
