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
from .mask_format_detector import MaskFormatDetector
from .extractors import (
    CIDRExtractor,
    SubnetMaskExtractor,
    InverseMaskExtractor,
    IPRangeExtractor,
    IPv6Extractor,
    IPOnlyExtractor,
)
from ..core import ParsedExtraction, _RawExtraction


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
        self.skip_range = False
        self.skip_bare_ip = False
    
    def should_skip(self, extractor_index: int) -> bool:
        """
        Check if a specific extractor should be skipped.
        
        Args:
            extractor_index: Index of extractor (0=CIDR, 1=netmask, 2=hostmask, 3=range, 4=bare_ip)
        
        Returns:
            True if this extractor should be skipped
        """
        skip_flags = [self.skip_cidr, self.skip_netmask, self.skip_hostmask, self.skip_range, self.skip_bare_ip]
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
        parse_ranges: str = 'both',
        parse_bare_ip: str = 'both',
        scan_mask: str = 'both',
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
            parse_ranges: Where to accept IP ranges ('pattern', 'input', 'both', 'none')
            parse_bare_ip: Where to accept bare IPs ('pattern', 'input', 'both', 'none')
            scan_mask: Where to scan for format hints ('pattern', 'input', 'both', 'none')
            range_format: Range format preference ('long', 'short', 'both', 'none')
        """
        self.filter_comments = filter_comments
        self.strict_mode = strict_mode
        self.parse_cidr = parse_cidr
        self.parse_netmask = parse_netmask
        self.parse_hostmask = parse_hostmask
        self.parse_ranges = parse_ranges
        self.parse_bare_ip = parse_bare_ip
        self.scan_mask = scan_mask
        self.range_format = range_format
        
        # Initialize comment handler
        self.comment_handler = CommentHandler()
        
        # Initialize extractors in priority order
        self.extractors = [
            CIDRExtractor(strict=strict_mode),
            SubnetMaskExtractor(
                reject_zero_mask=parse_hostmask != 'none',
                enabled=parse_netmask != 'none'
            ),
            InverseMaskExtractor(enabled=parse_hostmask != 'none'),
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
            mask_format_hint: Format hint from peek buffer analysis
        
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
            'range',      # 3: IPRangeExtractor
            'ip_only',    # 4: IPOnlyExtractor
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
                # Pass mask_format_hint to extractor for special case gating
                if hasattr(extractor, 'extract') and 'mask_format_hint' in extractor.extract.__code__.co_varnames:
                    extraction = extractor.extract(working_line, mask_format_hint=mask_format_hint)
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
