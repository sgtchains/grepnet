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
from ipaddress import IPv4Address, IPv4Network, IPv6Network
from .comment_handler import CommentHandler
from .mask_format_detector import MaskFormatDetector
from .extractors import (
    CIDRExtractor,
    SubnetMaskExtractor,
    InverseMaskExtractor,
    WildcardMaskExtractor,
    IPRangeExtractor,
    IPv6Extractor,
    IPOnlyExtractor,
)
from ..core import ParsedExtraction, _RawExtraction, MatchType


class ExtractorDecisions:
    """
    Tracks per-extractor decisions for skip/run logic.
    
    ARCHITECTURAL PRINCIPLE: This class makes it impossible to reject a line
    at line-level. It only tracks which extractors to skip, not whether to
    skip the entire line. This enforces the spec requirement: lines are only
    skipped if they produce zero networks, not based on line metadata.
    
    This prevents the anti-pattern:
        if condition:
            return None  # ❌ WRONG: Rejects entire line
    
    And enforces the correct pattern:
        if condition:
            skip_bare_ip_extraction = True  # ✅ CORRECT: Only affects one extractor
    """
    
    def __init__(self):
        """Initialize all extractors as enabled (no skips)."""
        # Note: The order here corresponds to extractors in NetworkParser.__init__
        self.skip_cidr = False
        self.skip_netmask = False
        self.skip_hostmask = False
        self.skip_wildcard = False
        self.skip_range = False
        self.skip_bare_ip = False
    
    def should_skip(self, extractor_index: int) -> bool:
        """
        Check if a specific extractor should be skipped.
        
        Args:
            extractor_index: Index of extractor (0=CIDR, 1=netmask, 2=hostmask, 3=wildcard, 4=range, 5=bare_ip)
        
        Returns:
            True if this extractor should be skipped
        """
        skip_flags = [self.skip_cidr, self.skip_netmask, self.skip_hostmask, self.skip_wildcard, self.skip_range, self.skip_bare_ip]
        if extractor_index < len(skip_flags):
            return skip_flags[extractor_index]
        return False
    
    def set_skip_bare_ip_extraction(self):
        """Mark bare IP extractor to be skipped. Used when SNMP OID patterns detected."""
        self.skip_bare_ip = True


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
        parse_wildcard: str = 'none',
        wildcard_search_scope=None,
        parse_ranges: str = 'both',
        parse_bare_ip: str = 'both',
        scan_mask: str = 'both',
        range_format: str = 'both',
        parsed_patterns: Optional[List] = None,
        exclude_strings: Optional[List[str]] = None,
        exclude_cidrs: Optional[List] = None,
        exclude_cidr_behavior: str = 'subset',
        exclude_cidr_behavior_strict: bool = False,
        match_type_filter: Optional[Set] = None,
        invert_match: bool = False,
    ):
        """
        Initialize parser.
        
        Args:
            filter_comments: If True, remove comments before extraction
            strict_mode: If True, reject malformed CIDR (host bits set)
            parse_cidr: Where to accept CIDR ('pattern', 'input', 'both', 'none')
            parse_netmask: Where to accept subnet masks ('pattern', 'input', 'both', 'none')
            parse_hostmask: Where to accept hostmasks ('pattern', 'input', 'both', 'none')
            parse_wildcard: Where to accept wildcard masks ('pattern', 'input', 'both', 'none')
            wildcard_search_scope: IPv4Network scope boundary for wildcard mask filtering (optional)
            parse_ranges: Where to accept IP ranges ('pattern', 'input', 'both', 'none')
            parse_bare_ip: Where to accept bare IPs ('pattern', 'input', 'both', 'none')
            scan_mask: Where to scan for format hints ('pattern', 'input', 'both', 'none')
            range_format: Range format preference ('long', 'short', 'both', 'none')
            parsed_patterns: List of ParsedExtraction pattern objects (for pattern matching in extract/consolidate)
            exclude_strings: List of regex patterns to exclude (--exclude-string)
            exclude_cidrs: List of network objects to exclude (--exclude-cidr)
            exclude_cidr_behavior: Exclusion behavior ('subset', 'subset-strict', 'superset', etc.)
            exclude_cidr_behavior_strict: Whether to use strict matching
            match_type_filter: Set of match types to filter on (for extract/consolidate pattern matching)
            invert_match: Whether to invert match results
        """
        self.filter_comments = filter_comments
        self.strict_mode = strict_mode
        self.parse_cidr = parse_cidr
        self.parse_netmask = parse_netmask
        self.parse_hostmask = parse_hostmask
        self.parse_wildcard = parse_wildcard
        self.wildcard_search_scope = wildcard_search_scope
        self.parse_ranges = parse_ranges
        self.parse_bare_ip = parse_bare_ip
        self.scan_mask = scan_mask
        self.range_format = range_format
        self.parsed_patterns = parsed_patterns or []
        self.exclude_strings = exclude_strings or []
        self.exclude_cidrs = exclude_cidrs or []
        self.exclude_cidr_behavior = exclude_cidr_behavior
        self.exclude_cidr_behavior_strict = exclude_cidr_behavior_strict
        self.match_type_filter = match_type_filter or set()
        self.invert_match = invert_match
        
        # Initialize comment handler
        self.comment_handler = CommentHandler()
        
        # Initialize extractors in priority order
        # Priority: CIDR → Subnet Mask → Inverse Mask → Wildcard Mask → Ranges → Bare IP
        self.extractors = [
            CIDRExtractor(strict=strict_mode),
            SubnetMaskExtractor(
                reject_zero_mask=parse_hostmask != 'none',
                enabled=parse_netmask != 'none'
            ),
            InverseMaskExtractor(
                enabled=parse_hostmask != 'none',
                netmask_enabled=parse_netmask != 'none'
            ),
            WildcardMaskExtractor(
                wildcard_mode_enabled=parse_wildcard != 'none',
                wildcard_search_scope=wildcard_search_scope
            ),
            IPRangeExtractor(),
            IPOnlyExtractor(),
        ]
    
    def _contains_snmp_oid_pattern(self, line: str) -> bool:
        """
        Detect if line contains SNMP OID patterns or malformed MIB-like patterns.
        
        IMPORTANT: This check only affects which EXTRACTORS are skipped (e.g., bare IP
        extraction). It does NOT cause the entire line to be rejected. The line is only
        rejected if it produces zero networks after all extractors run.
        
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
    
    def _detect_mask_format(self, text: str) -> Optional[str]:
        """
        Detect mask format hints from text using peek buffer analysis.
        
        Args:
            text: Text to analyze (typically first 8KB)
        
        Returns:
            Format hint: 'netmask_dominant', 'hostmask_dominant', 'mixed', 'unknown'
            or None if scan_mask is disabled
        """
        if self.scan_mask == 'none':
            return None
        
        return MaskFormatDetector.detect_format(text)
    
    def _should_use_extractor(self, extractor_type: str, context: str) -> bool:
        """
        Determine if an extractor should be used based on parse control flags.
        
        Args:
            extractor_type: Type of extractor ('cidr', 'netmask', 'hostmask', 'wildcard', 'range', 'ip_only')
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
        elif extractor_type == 'wildcard':
            if self.parse_wildcard == 'none':
                return False
            if self.parse_wildcard == 'pattern' and context != 'pattern':
                return False
            if self.parse_wildcard == 'input' and context != 'input':
                return False
        elif extractor_type == 'range':
            if self.parse_ranges == 'none':
                return False
            if self.parse_ranges == 'pattern' and context != 'pattern':
                return False
            if self.parse_ranges == 'input' and context != 'input':
                return False
        elif extractor_type == 'ip_only':
            if self.parse_bare_ip == 'none':
                return False
            if self.parse_bare_ip == 'pattern' and context != 'pattern':
                return False
            if self.parse_bare_ip == 'input' and context != 'input':
                return False
        
        return True
    
    def parse_line(self, line: str, line_number: int = 0, context: str = 'input', mask_format_hint: Optional[str] = None) -> List[ParsedExtraction]:
        """
        Extract ALL networks from a line (never rejects line wholesale).
        
        CRITICAL ARCHITECTURAL REQUIREMENT (per GREPNET-SPEC):
        This method NEVER rejects a line based on line-level metadata. It returns
        an empty list ONLY if the line produces zero networks after all processing.
        
        Individual extractors may be skipped (e.g., skip bare IP extraction when
        SNMP OID patterns are detected), but the line processing continues with
        remaining extractors. This ensures networks in mixed-content lines are
        still extracted.
        
        Examples of correct behavior:
        - Line "1.3.6.1.2.1.1.0 192.0.2.0/24" → Extracts CIDR (skips bare IP)
        - Line "1.3.6.1.2.1.1.0 192.0.2.1" → No output (bare IP suppressed, no CIDR)
        - Line "192.0.2.0/24" → Extracts CIDR
        
        Args:
            line: Line text
            line_number: Line number (1-based, for reference)
            context: Context for parsing ('pattern' for search patterns, 'input' for file input)
            mask_format_hint: Format hint from peek buffer analysis (used for Special Cases 1 & 2)
        
        Returns:
            List of ParsedExtraction objects, deduplicated by network value.
            Empty list only if no networks were extracted.
        """
        # Filter comments if enabled
        filtered_line, _ = self.comment_handler.filter_comments(
            line,
            filter_enabled=self.filter_comments,
        )
        
        # Skip empty lines after comment removal
        if not filtered_line.strip():
            return []
        
        # Determine which extractors to skip based on line content/settings
        decisions = ExtractorDecisions()
        
        # Check if line contains SNMP OID patterns (skip bare IP extraction if true)
        if self._contains_snmp_oid_pattern(filtered_line):
            decisions.set_skip_bare_ip_extraction()
        
        # Map extractor indices to types for parse control checking
        extractor_types = [
            'cidr',       # 0: CIDRExtractor
            'netmask',    # 1: SubnetMaskExtractor
            'hostmask',   # 2: InverseMaskExtractor
            'wildcard',   # 3: WildcardMaskExtractor
            'range',      # 4: IPRangeExtractor
            'ip_only',    # 5: IPOnlyExtractor
        ]
        
        # Extract networks using each extractor
        # Collect raw extractions from extractors with their positions in original line
        raw_extractions: List[_RawExtraction] = []
        working_line = filtered_line
        original_line = filtered_line  # Keep original for position tracking
        
        # SPECIAL CASE: 0.0.0.0 255.255.255.255 (entire IPv4 space)
        # Per spec: Represents 0.0.0.0/0 (entire IPv4 space)
        # Gating: Only apply if:
        #   1. Format hint is 'mixed' or 'unknown' (not conclusively netmask or hostmask)
        #   2. AND hostmask parsing is enabled in this context
        special_case_0_0_pattern = re.compile(r'\b0\.0\.0\.0\s+255\.255\.255\.255\b')
        should_apply_0_0_special = (
            special_case_0_0_pattern.search(original_line) and
            mask_format_hint in ('mixed', 'unknown') and
            self._should_use_extractor('hostmask', context)
        )
        if should_apply_0_0_special:
            match = special_case_0_0_pattern.search(original_line)
            if match:
                from ipaddress import ip_network
                network = ip_network('0.0.0.0/0')
                raw_extractions.append(_RawExtraction(
                    network=network,
                    format_type='inverse_mask',
                    matched_text=match.group(0),
                    was_normalized=False,
                ))
                working_line = working_line.replace(match.group(0), '', 1)
        
        # SPECIAL CASE: 255.255.255.255 0.0.0.0 (broadcast as single host)
        # Per spec: Represents 255.255.255.255/32
        # Gating: Only apply if:
        #   1. Format hint is 'mixed' or 'unknown' (not conclusively netmask or hostmask)
        #   2. AND hostmask parsing is enabled
        special_case_bcast_pattern = re.compile(r'\b255\.255\.255\.255\s+0\.0\.0\.0\b')
        should_apply_bcast_special = (
            special_case_bcast_pattern.search(original_line) and
            mask_format_hint in ('mixed', 'unknown') and
            self._should_use_extractor('hostmask', context)
        )
        if should_apply_bcast_special:
            match = special_case_bcast_pattern.search(original_line)
            if match:
                from ipaddress import ip_network
                network = ip_network('255.255.255.255/32')
                raw_extractions.append(_RawExtraction(
                    network=network,
                    format_type='inverse_mask',
                    matched_text=match.group(0),
                    was_normalized=False,
                ))
                working_line = working_line.replace(match.group(0), '', 1)
        
        for idx, extractor in enumerate(self.extractors):
            # Check extractor-level skip decisions (never line-level rejection)
            if decisions.should_skip(idx):
                continue
            
            # Check parse control flags
            if idx < len(extractor_types):
                extractor_type = extractor_types[idx]
                if not self._should_use_extractor(extractor_type, context):
                    continue
            
            # Keep calling each extractor until no more networks found
            while True:
                # Pass format hint only to SubnetMaskExtractor and InverseMaskExtractor
                # Others don't use it
                if idx == 1 or idx == 2:  # SubnetMaskExtractor or InverseMaskExtractor
                    extraction = extractor.extract(working_line, mask_format_hint)
                else:
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
                        is_bare_ip = True  # Assume bare IP unless proven otherwise
                        
                        if match_end_pos < len(original_line):
                            next_char = original_line[match_end_pos]
                            
                            # If followed by /, validate CIDR parse control
                            if next_char == '/':
                                is_bare_ip = False
                                if self.parse_cidr == 'none':
                                    skip_extraction = True
                                elif self.parse_cidr == 'pattern' and context != 'pattern':
                                    skip_extraction = True
                                elif self.parse_cidr == 'input' and context == 'pattern':
                                    skip_extraction = True
                            
                            # If followed by -, validate range parse control
                            elif next_char == '-':
                                is_bare_ip = False
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
                                    
                                    # Only mark as not-bare-ip if:
                                    # 1. Second value is actually a valid netmask/hostmask
                                    # 2. AND that parsing mode is enabled in this context
                                    netmask_enabled = self._should_use_extractor('netmask', context)
                                    hostmask_enabled = self._should_use_extractor('hostmask', context)
                                    
                                    if (is_netmask and netmask_enabled) or (is_hostmask and hostmask_enabled):
                                        is_bare_ip = False
                        
                        # Check what comes BEFORE the matched IP (for 2nd part of space-separated pairs)
                        if not skip_extraction and orig_pos > 0:
                            before_context = original_line[:orig_pos]
                            
                            # Check for "IP space" pattern before (2nd part of space-separated pair)
                            before_match = re.search(r'(\d+\.\d+\.\d+\.\d+)\s+$', before_context)
                            if before_match:
                                first_ip = before_match.group(1)
                                # This IP appears to be the 2nd part of a space-separated pair
                                is_netmask = _is_valid_netmask(extraction.matched_text)
                                is_hostmask = _is_valid_hostmask(extraction.matched_text)
                                
                                # Only mark as not-bare-ip if:
                                # 1. This value is actually a valid netmask/hostmask
                                # 2. AND that parsing mode is enabled in this context
                                netmask_enabled = self._should_use_extractor('netmask', context)
                                hostmask_enabled = self._should_use_extractor('hostmask', context)
                                
                                if (is_netmask and netmask_enabled) or (is_hostmask and hostmask_enabled):
                                    is_bare_ip = False
                        
                        # If it's a bare IP (not part of another format), validate parse_bare_ip control
                        if not skip_extraction and is_bare_ip:
                            if self.parse_bare_ip == 'none':
                                skip_extraction = True
                            elif self.parse_bare_ip == 'pattern' and context != 'pattern':
                                skip_extraction = True
                            elif self.parse_bare_ip == 'input' and context == 'pattern':
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
        
        # Apply filtering (pattern matching and exclusion filters)
        filtered = []
        for extraction in deduped:
            # 1. Check pattern matching (if patterns provided)
            if self.parsed_patterns:
                match_found = False
                for pattern in self.parsed_patterns:
                    match_type = self._find_match_type(extraction, pattern)
                    if match_type in self.match_type_filter:
                        match_found = True
                        break
                if self.invert_match:
                    match_found = not match_found
                if not match_found:
                    continue
            
            # 2. Check exclusion filters (if provided)
            if self._is_excluded(extraction):
                continue
            
            # Network passed all filters
            filtered.append(extraction)
        
        return filtered
    
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
    
    def _find_match_type(self, file_extraction: 'ParsedExtraction', pattern_extraction: 'ParsedExtraction'):
        """
        Determine the type of match between a file network and a pattern network.
        
        This is used by parse_line() for pattern filtering in extract/consolidate modes.
        
        Returns MatchType: EQUALS, SUBSET, SUPERSET, OVERLAP, or None
        """
        file_net = file_extraction.network
        pattern_net = pattern_extraction.network
        
        # Determine if each is a range or CIDR
        file_is_range = isinstance(file_net, tuple)
        pattern_is_range = isinstance(pattern_net, tuple)
        
        # Both are range tuples
        if file_is_range and pattern_is_range:
            file_start, file_end = file_net
            pattern_start, pattern_end = pattern_net
            if file_start == pattern_start and file_end == pattern_end:
                return MatchType.EQUALS
            elif file_start >= pattern_start and file_end <= pattern_end:
                return MatchType.SUBSET
            elif file_start <= pattern_start and file_end >= pattern_end:
                return MatchType.SUPERSET
            else:
                # Check for overlap
                if not (file_end < pattern_start or file_start > pattern_end):
                    return MatchType.OVERLAP
            return None
        
        # Both are CIDR networks
        if not file_is_range and not pattern_is_range:
            try:
                if file_net == pattern_net:
                    return MatchType.EQUALS
                elif file_net.subnet_of(pattern_net):
                    return MatchType.SUBSET
                elif pattern_net.subnet_of(file_net):
                    return MatchType.SUPERSET
                elif file_net.overlaps(pattern_net):
                    return MatchType.OVERLAP
            except (AttributeError, TypeError):
                pass
            return None
        
        # Cross-type: convert to ranges and compare
        try:
            if file_is_range:
                file_start, file_end = file_net
                pattern_start = int(pattern_net.network_address)
                pattern_end = int(pattern_net.broadcast_address)
            else:
                file_start = int(file_net.network_address)
                file_end = int(file_net.broadcast_address)
                pattern_start, pattern_end = pattern_net
            
            # Compare as ranges
            if file_start == pattern_start and file_end == pattern_end:
                return MatchType.EQUALS
            elif file_start >= pattern_start and file_end <= pattern_end:
                return MatchType.SUBSET
            elif file_start <= pattern_start and file_end >= pattern_end:
                return MatchType.SUPERSET
            else:
                # Check for overlap
                if not (file_end < pattern_start or file_start > pattern_end):
                    return MatchType.OVERLAP
        except (AttributeError, TypeError):
            pass
        
        return None
    
    def _is_excluded(self, extraction: 'ParsedExtraction') -> bool:
        """
        Check if a ParsedExtraction should be excluded based on exclusion filters.
        
        Args:
            extraction: ParsedExtraction to check
        
        Returns:
            True if the extraction should be excluded
        """
        if not extraction:
            return False
        
        # Check exclude-string filter (PCRE regex matching against matched_texts)
        if self.exclude_strings:
            for exclude_pattern_str in self.exclude_strings:
                try:
                    exclude_regex = re.compile(exclude_pattern_str)
                    # Check each original text variation in matched_texts
                    for text_entry in extraction.matched_texts:
                        matched_text = text_entry['text']
                        if exclude_regex.search(matched_text):
                            return True
                except re.error:
                    pass
        
        # Check exclude-cidr filter (network-based exclusions)
        if self.exclude_cidrs:
            file_network = extraction.network
            for exclude_net in self.exclude_cidrs:
                if self._check_cidr_exclusion(file_network, exclude_net):
                    return True
        
        return False
    
    def _check_cidr_exclusion(self, file_network, exclude_net) -> bool:
        """
        Check if a file network should be excluded based on CIDR exclusion behavior.
        Supports: 'subset', 'subset-strict', 'superset', 'superset-strict', 'equals', 'related', 'cut'
        """
        file_is_cidr = isinstance(file_network, (IPv4Network, IPv6Network))
        exclude_is_cidr = isinstance(exclude_net, (IPv4Network, IPv6Network))
        
        try:
            if self.exclude_cidr_behavior == 'subset':
                # Exclude if file network is a subset of (or equal to) exclude network
                if file_is_cidr and exclude_is_cidr:
                    return file_network.subnet_of(exclude_net) or file_network == exclude_net
                elif not file_is_cidr and not exclude_is_cidr:
                    file_start, file_end = file_network
                    exclude_start, exclude_end = exclude_net
                    return file_start >= exclude_start and file_end <= exclude_end
                else:
                    if file_is_cidr:
                        file_start = int(file_network.network_address)
                        file_end = int(file_network.broadcast_address)
                        exclude_start, exclude_end = exclude_net
                    else:
                        file_start, file_end = file_network
                        exclude_start = int(exclude_net.network_address)
                        exclude_end = int(exclude_net.broadcast_address)
                    return file_start >= exclude_start and file_end <= exclude_end
            
            elif self.exclude_cidr_behavior == 'subset-strict':
                # Exclude if file network is a STRICT subset of exclude network (no equality)
                if file_is_cidr and exclude_is_cidr:
                    return file_network.subnet_of(exclude_net) and file_network != exclude_net
                elif not file_is_cidr and not exclude_is_cidr:
                    file_start, file_end = file_network
                    exclude_start, exclude_end = exclude_net
                    return (file_start >= exclude_start and file_end <= exclude_end and
                            not (file_start == exclude_start and file_end == exclude_end))
                else:
                    if file_is_cidr:
                        file_start = int(file_network.network_address)
                        file_end = int(file_network.broadcast_address)
                        exclude_start, exclude_end = exclude_net
                    else:
                        file_start, file_end = file_network
                        exclude_start = int(exclude_net.network_address)
                        exclude_end = int(exclude_net.broadcast_address)
                    return (file_start >= exclude_start and file_end <= exclude_end and
                            not (file_start == exclude_start and file_end == exclude_end))
            
            elif self.exclude_cidr_behavior == 'superset':
                # Exclude if file network is a superset of (or equal to) exclude network
                if file_is_cidr and exclude_is_cidr:
                    return exclude_net.subnet_of(file_network) or file_network == exclude_net
                elif not file_is_cidr and not exclude_is_cidr:
                    file_start, file_end = file_network
                    exclude_start, exclude_end = exclude_net
                    return exclude_start >= file_start and exclude_end <= file_end
                else:
                    if file_is_cidr:
                        file_start = int(file_network.network_address)
                        file_end = int(file_network.broadcast_address)
                        exclude_start, exclude_end = exclude_net
                    else:
                        file_start, file_end = file_network
                        exclude_start = int(exclude_net.network_address)
                        exclude_end = int(exclude_net.broadcast_address)
                    return exclude_start >= file_start and exclude_end <= file_end
            
            elif self.exclude_cidr_behavior == 'superset-strict':
                # Exclude if file network is a STRICT superset of exclude network (no equality)
                if file_is_cidr and exclude_is_cidr:
                    return exclude_net.subnet_of(file_network) and file_network != exclude_net
                elif not file_is_cidr and not exclude_is_cidr:
                    file_start, file_end = file_network
                    exclude_start, exclude_end = exclude_net
                    return (exclude_start >= file_start and exclude_end <= file_end and
                            not (file_start == exclude_start and file_end == exclude_end))
                else:
                    if file_is_cidr:
                        file_start = int(file_network.network_address)
                        file_end = int(file_network.broadcast_address)
                        exclude_start, exclude_end = exclude_net
                    else:
                        file_start, file_end = file_network
                        exclude_start = int(exclude_net.network_address)
                        exclude_end = int(exclude_net.broadcast_address)
                    return (exclude_start >= file_start and exclude_end <= file_end and
                            not (file_start == exclude_start and file_end == exclude_end))
            
            elif self.exclude_cidr_behavior == 'equals':
                # Exclude if networks are equal
                if file_is_cidr and exclude_is_cidr:
                    return file_network == exclude_net
                else:
                    if file_is_cidr:
                        file_start = int(file_network.network_address)
                        file_end = int(file_network.broadcast_address)
                        exclude_start, exclude_end = exclude_net
                    else:
                        file_start, file_end = file_network
                        exclude_start = int(exclude_net.network_address)
                        exclude_end = int(exclude_net.broadcast_address)
                    return file_start == exclude_start and file_end == exclude_end
            
            elif self.exclude_cidr_behavior == 'related':
                # Exclude if networks overlap or have subset/superset relationship
                if file_is_cidr and exclude_is_cidr:
                    return (file_network.overlaps(exclude_net) or 
                            exclude_net.overlaps(file_network) or
                            file_network.subnet_of(exclude_net) or
                            exclude_net.subnet_of(file_network) or
                            file_network == exclude_net)
                elif not file_is_cidr and not exclude_is_cidr:
                    file_start, file_end = file_network
                    exclude_start, exclude_end = exclude_net
                    # Ranges overlap if: file_start <= exclude_end AND file_end >= exclude_start
                    return file_start <= exclude_end and file_end >= exclude_start
                else:
                    if file_is_cidr:
                        file_start = int(file_network.network_address)
                        file_end = int(file_network.broadcast_address)
                        exclude_start, exclude_end = exclude_net
                    else:
                        file_start, file_end = file_network
                        exclude_start = int(exclude_net.network_address)
                        exclude_end = int(exclude_net.broadcast_address)
                    return file_start <= exclude_end and file_end >= exclude_start
            
            elif self.exclude_cidr_behavior == 'cut':
                # 'cut' behavior: same as 'subset' (for now, actual cutting happens elsewhere)
                if file_is_cidr and exclude_is_cidr:
                    return file_network.subnet_of(exclude_net) or file_network == exclude_net
                elif not file_is_cidr and not exclude_is_cidr:
                    file_start, file_end = file_network
                    exclude_start, exclude_end = exclude_net
                    return file_start >= exclude_start and file_end <= exclude_end
                else:
                    if file_is_cidr:
                        file_start = int(file_network.network_address)
                        file_end = int(file_network.broadcast_address)
                        exclude_start, exclude_end = exclude_net
                    else:
                        file_start, file_end = file_network
                        exclude_start = int(exclude_net.network_address)
                        exclude_end = int(exclude_net.broadcast_address)
                    return file_start >= exclude_start and file_end <= exclude_end
        except (AttributeError, TypeError, ValueError):
            pass
        
        return False
