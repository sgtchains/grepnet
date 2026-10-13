"""
Main GrepNet orchestrator.

Coordinates the entire pipeline:
1. Initialize colorizer at startup
2. Parse pattern(s)
3. Read and parse input sources
4. Match networks
5. Format and output results
"""

import re
from typing import List, Iterator, Tuple, Optional, Union, Dict
from ipaddress import IPv4Network, IPv6Network

from .core import ParsedExtraction, MatchResult, MatchType, Colorizer, BinaryDetector
from .parsing import NetworkParser
from .input import InputSource, InputDiscovery
from .matching import CIDRMatcher, RangeMatcher


class GrepNet:
    """
    Main grepnet orchestrator.
    
    Workflow:
    1. Initialize with options and color settings
    2. Parse pattern(s) to extract networks
    3. For each input source:
       a. Read lines
       b. Parse networks from each line
       c. Match against patterns
       d. Yield MatchResult for output
    """
    
    # Configuration: Controls whether networks that were normalized
    # (had host bits set, corrected to network address) receive styling
    # markup even when they do not match the search pattern.
    # Set to False to disable this behavior.
    CONFIG_MARK_NORMALIZED_NETWORKS = False
    
    # Configuration: If True, --format flag is only allowed with --extract or --consolidate.
    # Set to False to disable this restriction (allows --format in all modes).
    CONFIG_FORMAT_ONLY_WITH_EXTRACT_CONSOLIDATE = True
    
    # Format type to markup OBJ type mapping (used for colorization)
    FORMAT_TYPE_MAP = {
        'cidr_notation': 'CIDR',
        'subnet_mask_notation': 'SUBNET_MASK',
        'inverse_mask_notation': 'INVERSE_MASK',
        'ip_range_notation': 'RANGE',
        'ipv4_range': 'RANGE',
        'ipv6_range': 'RANGE',
        'ip_only': 'BARE_IP',
    }
    
    # Match type priority map (lower number = higher priority for colorization)
    MATCH_TYPE_PRIORITY = {
        MatchType.EQUALS: 0,
        MatchType.SUBSET: 1,
        MatchType.SUPERSET: 2,
        MatchType.OVERLAP: 3,
        MatchType.UNMATCHED: 4,
    }
    
    def __init__(
        self,
        patterns: List[str],
        filter_comments: bool = True,
        strict_mode: bool = False,
        strict_cidr_action: str = 'normalize',
        strict_cidr_mode: str = 'none',
        parse_cidr: str = 'both',
        parse_netmask: str = 'both',
        parse_hostmask: str = 'both',
        parse_ranges: str = 'both',
        parse_bare_ip: str = 'both',
        range_format: str = 'both',
        enable_colors: bool = True,
        match_type_filter: Optional[List[MatchType]] = None,
        invert_match: bool = False,
        show_unmatched: bool = False,
        mark_normalized: Optional[bool] = None,
        debug: Optional[str] = None,
        exclude_strings: Optional[List[str]] = None,
        exclude_cidrs: Optional[List] = None,
        exclude_cidr_behaviour: str = 'subset',
        output_format: str = 'cidr',
        binary_files: str = 'binary',
    ):
        """
        Initialize GrepNet.
        
        Args:
            patterns: List of pattern strings to search for
            filter_comments: If True, remove comments before extraction
            strict_mode: If True, reject malformed CIDR
            strict_cidr_action: Action on strict CIDR validation error ('fail', 'normalize', 'ignore', 'warn')
            strict_cidr_mode: Strict CIDR validation mode ('pattern', 'input', 'both', 'none')
            enable_colors: If True, use ANSI colors
            match_type_filter: List of MatchType to include (default: all except UNMATCHED)
            invert_match: If True, invert match logic
            show_unmatched: If True, include unmatched networks (with -u flag)
            mark_normalized: If True, style networks that were normalized (non-strict CIDR)
            debug: Debug mode ('markup' to show internal markup, None to disable)
            exclude_strings: List of substrings to exclude from results
            exclude_cidrs: List of network objects (IPv4Network/IPv6Network or ranges) to exclude
            exclude_cidr_behaviour: CIDR exclusion behavior ('subset', 'superset', 'equals', 'related', 'cut')
            output_format: Network output format for --extract/--consolidate ('cidr', 'range', 'short-range')
        """
        self.patterns = patterns
        self.filter_comments = filter_comments
        self.strict_mode = strict_mode
        self.strict_cidr_action = strict_cidr_action
        self.strict_cidr_mode = strict_cidr_mode
        self.enable_colors = enable_colors
        self.match_type_filter = match_type_filter or [
            MatchType.EQUALS,
            MatchType.SUBSET,
            MatchType.SUPERSET,
            MatchType.OVERLAP,
        ]
        self.invert_match = invert_match
        self.show_unmatched = show_unmatched
        # Use CONFIG value if mark_normalized not explicitly specified
        self.mark_normalized = mark_normalized if mark_normalized is not None else self.CONFIG_MARK_NORMALIZED_NETWORKS
        self.debug = debug
        self.exclude_strings = exclude_strings or []
        self.exclude_cidrs = exclude_cidrs or []
        self.exclude_cidr_behaviour = exclude_cidr_behaviour
        self.output_format = output_format
        self.binary_files = binary_files
        
        # Store parse control parameters
        self.parse_cidr = parse_cidr
        self.parse_netmask = parse_netmask
        self.parse_hostmask = parse_hostmask
        self.parse_ranges = parse_ranges
        self.parse_bare_ip = parse_bare_ip
        self.range_format = range_format
        
        # Initialize colorizer at startup (before any matching)
        self.colorizer = Colorizer(enable_colors=enable_colors)
        
        # Parse patterns
        self.parser = NetworkParser(
            filter_comments=filter_comments,
            strict_mode=strict_mode,
            parse_cidr=parse_cidr,
            parse_netmask=parse_netmask,
            parse_hostmask=parse_hostmask,
            parse_ranges=parse_ranges,
            parse_bare_ip=parse_bare_ip,
            range_format=range_format,
        )
        self.parsed_patterns = self._parse_patterns()
    
    def validate_format_usage(self, use_extract: bool = False, use_consolidate: bool = False) -> None:
        """
        Validate that --format is only used with --extract or --consolidate.
        
        Args:
            use_extract: True if --extract mode is active
            use_consolidate: True if --consolidate mode is active
        
        Raises:
            ValueError: If --format is used without --extract or --consolidate
                       (and CONFIG_FORMAT_ONLY_WITH_EXTRACT_CONSOLIDATE is True)
        """
        if not self.CONFIG_FORMAT_ONLY_WITH_EXTRACT_CONSOLIDATE:
            return  # Validation disabled
        
        # Check if output_format was explicitly set (not default)
        if self.output_format != 'cidr':
            if not (use_extract or use_consolidate):
                raise ValueError(
                    f"--format '{self.output_format}' can only be used with --extract or --consolidate"
                )
    
    def _range_to_cidrs(self, start_int: int, end_int: int, version: int = 4) -> List[str]:
        """
        Convert a range (start_int, end_int) to a list of CIDR blocks.
        
        Algorithm: Iteratively find the largest CIDR block that fits at the current position,
        emit it, and advance to the next position.
        
        Args:
            start_int: Start IP as integer
            end_int: End IP as integer  
            version: IP version (4 or 6)
        
        Returns:
            List of CIDR strings (e.g., ['192.0.2.0/30', '192.0.2.4/32'])
        """
        from ipaddress import ip_network
        
        max_bits = 32 if version == 4 else 128
        cidrs = []
        current = start_int
        
        while current <= end_int:
            # Find the largest block size (smallest prefix length) that:
            # 1. Starts at an aligned boundary
            # 2. Doesn't exceed our range
            
            # Start with the maximum possible prefix length (most specific: /32 or /128)
            prefix_len = max_bits
            
            # Try each prefix length from 0 (largest block /0 or /0) down to max
            for pl in range(max_bits):
                # Block size for this prefix: 2^(max_bits - prefix_length)
                block_size = 1 << (max_bits - pl)
                
                # Check alignment: current must be divisible by block_size
                # i.e., (current % block_size) == 0
                if (current % block_size) == 0:
                    # Check that block doesn't exceed range
                    block_end = current + block_size - 1
                    if block_end <= end_int:
                        # This block fits - use it
                        prefix_len = pl
                        break
            
            # Emit the CIDR block
            cidr_str = str(ip_network((current, prefix_len)))
            cidrs.append(cidr_str)
            
            # Advance to next block
            block_size = 1 << (max_bits - prefix_len)
            current += block_size
        
        return cidrs
    
    def format_network(self, parsed_extraction) -> str:
        """
        Format a network object according to self.output_format.
        
        Args:
            parsed_extraction: ParsedExtraction object containing network, format_type, matched_texts
        
        Returns:
            Formatted network string based on output_format setting
        """
        network = parsed_extraction.network
        is_cidr = isinstance(network, (IPv4Network, IPv6Network))
        
        # Handle 'original' format: output in the format it was parsed
        if self.output_format == 'original':
            # Use the original matched text
            if parsed_extraction.matched_texts:
                return parsed_extraction.matched_texts[0]['text']
            # Fallback to CIDR if no matched text available
            return str(network) if is_cidr else self._format_range_default(network)
        
        if self.output_format == 'cidr':
            if is_cidr:
                return str(network)
            else:
                # Convert range to CIDR blocks
                start_int, end_int = network
                
                # Determine IP version from range
                if start_int > 0xFFFFFFFF:
                    version = 6
                else:
                    version = 4
                
                # Convert range to CIDR blocks
                cidrs = self._range_to_cidrs(start_int, end_int, version)
                return '\n'.join(cidrs)
        
        elif self.output_format == 'range':
            if is_cidr:
                # Convert CIDR to range
                start_int = int(network.network_address)
                end_int = int(network.broadcast_address)
                if start_int == end_int:
                    from ipaddress import ip_address
                    return str(ip_address(start_int))
                else:
                    from ipaddress import ip_address
                    return f"{ip_address(start_int)}-{ip_address(end_int)}"
            else:
                # Already a range
                start_int, end_int = network
                from ipaddress import ip_address
                if start_int == end_int:
                    return str(ip_address(start_int))
                return f"{ip_address(start_int)}-{ip_address(end_int)}"
        
        elif self.output_format == 'short-range':
            if is_cidr:
                # Convert CIDR to short-range
                start_int = int(network.network_address)
                end_int = int(network.broadcast_address)
                network_obj = network
            else:
                start_int, end_int = network
                # Determine if IPv4 or IPv6 by address size
                from ipaddress import ip_address
                network_obj = None  # We only know the range
            
            from ipaddress import ip_address
            start_addr = ip_address(start_int)
            end_addr = ip_address(end_int)
            
            # IPv4 short-range: abbreviate last octet
            if start_addr.version == 4:
                start_parts = str(start_addr).split('.')
                end_parts = str(end_addr).split('.')
                
                if start_parts[0:3] == end_parts[0:3]:  # Same first 3 octets
                    # Can abbreviate
                    return f"{'.'.join(start_parts[0:3])}.{start_parts[3]}-{end_parts[3]}"
                else:
                    # Can't abbreviate, use full range
                    return f"{start_addr}-{end_addr}"
            else:
                # IPv6: use full range notation
                return f"{start_addr}-{end_addr}"
        
        else:
            raise ValueError(f"Unknown output format: {self.output_format}")
    
    def _format_range_default(self, network_range) -> str:
        """Format a range tuple as IP-IP."""
        from ipaddress import ip_address
        start_int, end_int = network_range
        if start_int == end_int:
            return str(ip_address(start_int))
        return f"{ip_address(start_int)}-{ip_address(end_int)}"
    
    def _parse_patterns(self) -> List[ParsedExtraction]:
        """
        Parse all pattern strings into network objects.
        
        Returns:
            List of ParsedExtraction objects
        """
        all_patterns = []
        for pattern_str in self.patterns:
            extractions = self.parser.parse_line(pattern_str, context='pattern')
            all_patterns.extend(extractions)
        return all_patterns
    
    def _is_match_in_filter(self, match_type: MatchType) -> bool:
        """
        Check if a match type passes the active filter.
        
        Args:
            match_type: MatchType to check
        
        Returns:
            True if match should be included in output
        """
        if match_type in self.match_type_filter:
            return True
        if match_type == MatchType.UNMATCHED and self.show_unmatched:
            return True
        return False
    
    def _is_excluded(self, result: 'MatchResult') -> bool:
        """
        Check if a result should be excluded based on exclusion filters.
        
        Args:
            result: MatchResult to check
        
        Returns:
            True if the result should be excluded
        """
        return self._check_extraction_excluded(result.file_extraction) if result.file_extraction else False
    
    def _check_extraction_excluded(self, extraction: 'ParsedExtraction') -> bool:
        """
        Check if a ParsedExtraction should be excluded based on exclusion filters.
        This is used by both search mode (via _is_excluded) and extract mode.
        
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
                    # Invalid regex pattern - skip this pattern
                    pass
        
        # Check exclude-cidr filter (network-based exclusions with behavior support)
        if self.exclude_cidrs:
            file_network = extraction.network
            for exclude_net in self.exclude_cidrs:
                if self._check_cidr_exclusion(file_network, exclude_net, behavior=self.exclude_cidr_behaviour):
                    return True
        
        return False
    
    
    def _check_cidr_exclusion(self, file_network, exclude_net, behavior='subset') -> bool:
        """
        Check if a file network should be excluded based on CIDR exclusion behavior.
        
        Args:
            file_network: Network from file (CIDR or Range tuple)
            exclude_net: Network to exclude (CIDR or Range tuple)
            behavior: Exclusion behavior ('subset', 'superset', 'equals', 'related', 'cut')
                     Default 'subset': exclude if file_network is subset of exclude_net
        
        Returns:
            True if file network should be excluded based on behavior
        """
        file_is_cidr = isinstance(file_network, (IPv4Network, IPv6Network))
        exclude_is_cidr = isinstance(exclude_net, (IPv4Network, IPv6Network))
        
        try:
            if behavior == 'subset':
                # Exclude if file network is a subset of (or equal to) exclude network
                if file_is_cidr and exclude_is_cidr:
                    # Both CIDR - check subset relationship
                    return file_network.subnet_of(exclude_net) or file_network == exclude_net
                elif not file_is_cidr and not exclude_is_cidr:
                    # Both ranges - check if file range is within exclude range
                    file_start, file_end = file_network
                    exclude_start, exclude_end = exclude_net
                    return file_start >= exclude_start and file_end <= exclude_end
                else:
                    # Cross-type: convert to ranges and check subset
                    if file_is_cidr:
                        file_start = int(file_network.network_address)
                        file_end = int(file_network.broadcast_address)
                        exclude_start, exclude_end = exclude_net
                    else:
                        file_start, file_end = file_network
                        exclude_start = int(exclude_net.network_address)
                        exclude_end = int(exclude_net.broadcast_address)
                    return file_start >= exclude_start and file_end <= exclude_end
            
            elif behavior == 'superset':
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
            
            elif behavior == 'equals':
                # Exclude if networks are equal
                if file_is_cidr and exclude_is_cidr:
                    return file_network == exclude_net
                else:
                    # Convert to ranges and compare
                    if file_is_cidr:
                        file_start = int(file_network.network_address)
                        file_end = int(file_network.broadcast_address)
                        exclude_start, exclude_end = exclude_net
                    else:
                        file_start, file_end = file_network
                        exclude_start = int(exclude_net.network_address)
                        exclude_end = int(exclude_net.broadcast_address)
                    return file_start == exclude_start and file_end == exclude_end
            
            elif behavior == 'related':
                # Exclude if networks overlap or have subset/superset relationship
                if file_is_cidr and exclude_is_cidr:
                    return (file_network.overlaps(exclude_net) or 
                            exclude_net.overlaps(file_network) or
                            file_network.subnet_of(exclude_net) or
                            exclude_net.subnet_of(file_network) or
                            file_network == exclude_net)
                else:
                    # Convert to ranges and check overlap
                    if file_is_cidr:
                        file_start = int(file_network.network_address)
                        file_end = int(file_network.broadcast_address)
                        exclude_start, exclude_end = exclude_net
                    else:
                        file_start, file_end = file_network
                        exclude_start = int(exclude_net.network_address)
                        exclude_end = int(exclude_net.broadcast_address)
                    # Check overlap
                    return not (file_end < exclude_start or exclude_end < file_start)
            
            else:
                # Unknown behavior - default to no exclusion
                return False
                
        except (TypeError, ValueError, AttributeError):
            # Skip if comparison fails
            return False
    
    def _cut_network(self, network, exclude_net) -> List[Union[IPv4Network, IPv6Network]]:
        """
        Carve out exclude_net from network and return remaining CIDRs.
        
        Args:
            network: Network to cut from (IPv4Network or IPv6Network)
            exclude_net: Network to remove (IPv4Network or IPv6Network)
        
        Returns:
            List of networks that remain after cutting out exclude_net
        """
        if not isinstance(network, (IPv4Network, IPv6Network)):
            # Ranges not yet supported for cut
            return [network]
        
        if not isinstance(exclude_net, (IPv4Network, IPv6Network)):
            # Exclude is a range, convert to CIDR
            return [network]
        
        # If exclude_net is not within network, return network unchanged
        if not exclude_net.subnet_of(network) and exclude_net != network:
            return [network]
        
        # If they're equal, return nothing
        if exclude_net == network:
            return []
        
        # Use supernet_of/subnets to compute complement
        result = []
        current = [network]
        
        while current:
            subnet = current.pop(0)
            
            # If exclude_net doesn't overlap with subnet, keep subnet
            if not subnet.overlaps(exclude_net):
                result.append(subnet)
                continue
            
            # If exclude_net equals subnet, skip it
            if exclude_net == subnet:
                continue
            
            # If exclude_net contains subnet, skip it
            if exclude_net.supernet_of(subnet):
                continue
            
            # If subnet is not the parent of exclude_net, split and recurse
            if not exclude_net.subnet_of(subnet):
                # Partial overlap - shouldn't happen if exclude_net.subnet_of(network)
                # but handle anyway
                result.append(subnet)
                continue
            
            # Split the subnet in half
            subnets = list(subnet.subnets(prefixlen_diff=1))
            current.extend(subnets)
        
        return result
    
    def _apply_cut_exclusion(self, networks: Dict) -> Dict:
        """
        Apply cut exclusion behavior to extracted networks.
        
        For each exclude CIDR, remove it from all networks and expand results.
        
        Args:
            networks: Dictionary from extract mode {network: (ParsedExtraction, line_content)}
        
        Returns:
            Modified dictionary with cut-out networks
        """
        if not self.exclude_cidrs:
            return networks
        
        result = {}
        
        for network, (parsed_ext, line_content) in networks.items():
            if not isinstance(network, (IPv4Network, IPv6Network)):
                # Skip ranges for now
                result[network] = (parsed_ext, line_content)
                continue
            
            remaining = [network]
            
            # Apply each exclude CIDR
            for exclude_net in self.exclude_cidrs:
                if not isinstance(exclude_net, (IPv4Network, IPv6Network)):
                    continue
                
                new_remaining = []
                for net in remaining:
                    cutout = self._cut_network(net, exclude_net)
                    new_remaining.extend(cutout)
                remaining = new_remaining
            
            # Add remaining networks to result
            for net in remaining:
                # Create a new ParsedExtraction for the cut network
                temp_extraction = ParsedExtraction(
                    network=net,
                    format_type='cidr_notation',
                    was_normalized=False,
                    matched_texts=parsed_ext.matched_texts if parsed_ext else []
                )
                result[net] = (temp_extraction, line_content)
        
        return result
    
    def _check_match_type_against_pattern(self, matcher, pattern_start_or_net, pattern_end=None) -> MatchType:
        """
        Check matcher against pattern in priority order.
        
        Args:
            matcher: CIDRMatcher or RangeMatcher instance
            pattern_start_or_net: Pattern network (CIDR) or start int (Range)
            pattern_end: End int (only for Range matcher)
        
        Returns:
            MatchType (EQUALS, SUBSET, SUPERSET, OVERLAP, or UNMATCHED)
        """
        if pattern_end is None:
            # CIDR matching
            if matcher.find_equal_matches(pattern_start_or_net):
                return MatchType.EQUALS
            if matcher.find_subset_matches(pattern_start_or_net):
                return MatchType.SUBSET
            if matcher.find_superset_matches(pattern_start_or_net):
                return MatchType.SUPERSET
            if matcher.find_overlap_matches(pattern_start_or_net):
                return MatchType.OVERLAP
        else:
            # Range matching
            if matcher.find_equal_matches(pattern_start_or_net, pattern_end):
                return MatchType.EQUALS
            if matcher.find_subset_matches(pattern_start_or_net, pattern_end):
                return MatchType.SUBSET
            if matcher.find_superset_matches(pattern_start_or_net, pattern_end):
                return MatchType.SUPERSET
            if matcher.find_overlap_matches(pattern_start_or_net, pattern_end):
                return MatchType.OVERLAP
        
        return MatchType.UNMATCHED
    
    def search(self, input_sources: List[InputSource], yield_all_lines: bool = False, mode: str = 'normal') -> Union[Iterator[MatchResult], dict]:
        """
        Search input sources for matching networks.
        
        Unified entry point for all output modes (normal, extract, consolidate).
        Implements "All Input Is Input" principle: single processing path for all modes.
        
        Args:
            input_sources: List of InputSource instances
            yield_all_lines: If True, yield ALL lines (both matches and non-matches).
                            Use for context line support (-A, -B, -C flags).
                            Non-match lines have is_match=False.
            mode: Output mode ('normal', 'extract', 'consolidate')
                 - 'normal': Yield MatchResult stream (standard mode)
                 - 'extract': Return dict of deduplicated networks (for extract mode)
                 - 'consolidate': Return dict of consolidated networks (for consolidate mode)
        
        Returns:
            - 'normal' mode: Iterator[MatchResult] objects
            - 'extract' mode: dict {network_object -> (ParsedExtraction, line_content)}
            - 'consolidate' mode: dict {network_object -> (ParsedExtraction, line_content)}
        """
        if mode == 'extract':
            # Extract mode: return deduplicated networks dict
            return self.extract_networks(input_sources)
        elif mode == 'consolidate':
            # Consolidate mode: return consolidated networks dict
            return self.consolidate_networks(input_sources)
        else:  # mode == 'normal'
            # Standard mode: stream MatchResult objects
            return self._search_generator(input_sources, yield_all_lines)
    
    def _search_generator(self, input_sources: List[InputSource], yield_all_lines: bool = False) -> Iterator[MatchResult]:
        """
        Generator for normal search mode.
        Returns MatchResult objects for each line.
        """
        for source in input_sources:
            yield from self._search_source(source, yield_all_lines=yield_all_lines)
    
    def _search_source(self, source: InputSource, yield_all_lines: bool = False) -> Iterator[MatchResult]:
        """
        Search single input source.
        
        Args:
            source: InputSource instance
            yield_all_lines: If True, yield ALL lines (including non-matches)
        
        Yields:
            MatchResult objects (all lines if yield_all_lines=True, only matches otherwise)
        """
        # Reset comment handler state for this new file
        self.parser.comment_handler.reset()
        filename = source.display_name
        file_type = source.file_type
        is_binary = source.get_binary_status()
        
        # Note: Do NOT skip binary files here. Let the search proceed normally.
        # The caller (CLI) will handle binary file suppression based on binary_files mode and output type.
        # This allows modes like -l, -L, -c to work with binary files, and allows
        # the default 'binary' mode to report "Binary file X matches" for content output.
        
        # For 'text' mode, treat binary files as text (is_binary stays False for output)
        if is_binary and self.binary_files == 'text':
            is_binary = False
        
        # Iterate over lines
        for line_number, line_content, byte_offset in source.lines():
            # Parse networks from this line
            file_extractions = self.parser.parse_line(line_content, context='input')
            
            # Validate strict CIDR in input if requested
            if self.strict_cidr_mode in ['input', 'both'] and file_extractions:
                for file_extraction in file_extractions:
                    if file_extraction.was_normalized:
                        # Get original text from matched_texts (should be present)
                        original_text = file_extraction.matched_texts[0]['text'] if file_extraction.matched_texts else str(file_extraction.network)
                        error_msg = f"{filename}:{line_number}: Malformed CIDR: {original_text} (normalized to {file_extraction.network})"
                        if self.strict_cidr_action == 'fail':
                            raise ValueError(error_msg)
                        elif self.strict_cidr_action == 'warn':
                            import sys
                            print(f'grepnet warning: {error_msg}', file=sys.stderr)
                        # 'ignore' and 'normalize' don't need special handling
            
            if not file_extractions:
                # No networks on this line
                if yield_all_lines:
                    # Yield non-match for context support
                    yield MatchResult(
                        line_number=line_number,
                        line_content=line_content,
                        content_colored=line_content,
                        file_extraction=None,
                        pattern_extraction=None,
                        match_type=None,
                        match_index=-1,
                        filename=filename,
                        is_binary_file=is_binary,
                        content_marked="",
                        is_match=False,
                        byte_offset=byte_offset,
                    )
                continue
            
            # Step 1: Determine match type for each file network against all patterns
            # Store: network → list of (pattern, match_type) pairs
            network_matches = {}  # file_extraction → list of (pattern, match_type)
            
            for match_idx, file_extraction in enumerate(file_extractions):
                network_key = str(file_extraction.network)
                if network_key not in network_matches:
                    network_matches[network_key] = []
                
                for pattern_extraction in self.parsed_patterns:
                    match_type = self._find_match_type(
                        file_extraction,
                        pattern_extraction,
                    )
                    network_matches[network_key].append((pattern_extraction, match_type))
            
            # Step 2: Determine if line should be output and which networks to mark
            # First: check if ANY network matches the filter (determines line output)
            any_match_on_line = False
            all_file_extractions_with_type = []  # All networks with their match types
            networks_to_mark = set()  # Networks that should get markup (for styling)
            
            for match_idx, file_extraction in enumerate(file_extractions):
                network_key = str(file_extraction.network)
                
                for pattern_extraction, match_type in network_matches[network_key]:
                    all_file_extractions_with_type.append({
                        'file_extraction': file_extraction,
                        'pattern_extraction': pattern_extraction,
                        'match_type': match_type,
                        'match_idx': match_idx,
                    })
                    
                    # Check if this match is in the active filter
                    if self._is_match_in_filter(match_type):
                        any_match_on_line = True
                        # Mark this network for styling
                        networks_to_mark.add(network_key)
                
                # ALSO mark networks for styling if they were normalized
                # (even if they don't match any pattern)
                # Only if mark_normalized is enabled
                if self.mark_normalized and file_extraction.was_normalized:
                    networks_to_mark.add(network_key)
            
            # Determine if line should be output based on inversion
            # Normal mode: output if ANY_MATCH_ON_LINE
            # Inverted mode: output if NO_MATCH_ON_LINE
            if self.invert_match:
                line_should_output = not any_match_on_line
            else:
                line_should_output = any_match_on_line
            
            if not line_should_output:
                if yield_all_lines:
                    # Yield non-match for context support
                    yield MatchResult(
                        line_number=line_number,
                        line_content=line_content,
                        content_colored=line_content,
                        file_extraction=None,
                        pattern_extraction=None,
                        match_type=None,
                        match_index=-1,
                        filename=filename,
                        is_binary_file=is_binary,
                        content_marked="",
                        is_match=False,
                        byte_offset=byte_offset,
                        file_type=file_type,
                    )
                continue
            
            # Build matches_on_line for output
            # Normal mode: only networks that matched the filter
            # Inverted mode: all networks (since no networks matched the filter)
            if self.invert_match:
                # For inverted mode, create result for each network that didn't match
                matches_on_line = []
                seen_networks = set()
                for entry in all_file_extractions_with_type:
                    network_key = str(entry['file_extraction'].network)
                    # Only include each network once, using the first pattern pair
                    if network_key not in seen_networks:
                        matches_on_line.append(entry)
                        seen_networks.add(network_key)
            else:
                # For normal mode, only include networks that matched
                matches_on_line = []
                for entry in all_file_extractions_with_type:
                    if self._is_match_in_filter(entry['match_type']):
                        matches_on_line.append(entry)

            
            # Step 3: Generate markup for networks to be styled
            # Mark by format_type priority to avoid bare IPs mixing with other formats
            # Priority order: CIDR > subnet mask > inverse mask > ranges > bare IP (last)
            # For each network, mark ALL text variations (matched_texts)
            
            content_marked = line_content
            marked_texts = set()  # Track which unique texts have been marked (to avoid double-marking duplicates)
            
            # Group extractions by format_type for ordered processing
            format_priority = ['cidr_notation', 'subnet_mask', 'inverse_mask', 'ipv4_range', 'ipv6_range', 'ip_only']
            
            for format_type_name in format_priority:
                for file_extraction in file_extractions:
                    # Process only extractions of this format type
                    if file_extraction.format_type != format_type_name:
                        continue
                    
                    network_key = str(file_extraction.network)
                    if network_key not in networks_to_mark:
                        continue
                    
                    # Determine the match type for markup (use highest priority)
                    match_types = [mt for _, mt in network_matches[network_key]]
                    match_type = min(match_types, key=lambda mt: self.MATCH_TYPE_PRIORITY.get(mt, 5))
                    
                    obj_type = self.FORMAT_TYPE_MAP.get(file_extraction.format_type, 'UNKNOWN')
                    
                    # Mark each unique text variation once (duplicate texts in matched_texts are marked only once for display)
                    for text_entry in file_extraction.matched_texts:
                        matched_text = text_entry['text']
                        
                        # Skip if this text was already marked (handles duplicates in matched_texts)
                        if matched_text in marked_texts:
                            continue
                        marked_texts.add(matched_text)
                        
                        text_was_normalized = text_entry['was_normalized']
                        
                        # Build markup with per-text normalization status
                        match_type_name = match_type.name
                        markup_start = f'\uE000TYPE:{match_type_name}|OBJ:{obj_type}|NORM:{str(text_was_normalized).lower()}\uE001'
                        markup_end = '\uE000/TYPE\uE001'
                        
                        # For bare IPs, check that no markup precedes it
                        if format_type_name == 'ip_only':
                            # Build a safe replacement that checks for preceding markup
                            import re
                            # Pattern: match network text that is NOT preceded by \uE000 or \uE001
                            safe_pattern = re.compile(
                                r'(?<!\uE000)(?<!\uE001)' + re.escape(matched_text) + r'(?![/\d])',
                                re.MULTILINE
                            )
                            content_marked = safe_pattern.sub(
                                f'{markup_start}{matched_text}{markup_end}',
                                content_marked
                            )
                        else:
                            # For non-bare-IP networks, simple global replace (marks ALL occurrences)
                            content_marked = content_marked.replace(
                                matched_text,
                                f'{markup_start}{matched_text}{markup_end}'
                            )
            
            # Finalize markup to ANSI codes (or strip if colors disabled)
            content_colored = self.colorizer.finalize_markup(
                content_marked,
                enable_colors=self.enable_colors,
            )
            
            # Create one MatchResult per match, all sharing the same content_colored
            for match in matches_on_line:
                result = MatchResult(
                    line_number=line_number,
                    line_content=line_content,
                    content_colored=content_colored,
                    file_extraction=match['file_extraction'],
                    pattern_extraction=match['pattern_extraction'],
                    match_type=match['match_type'],
                    match_index=match['match_idx'],
                    filename=filename,
                    is_binary_file=is_binary,
                    content_marked=content_marked,  # Always include marked content for -o mode ordering
                    is_match=True,
                    byte_offset=byte_offset,
                    file_type=file_type,
                )
                
                # Apply exclusion filters
                if self._is_excluded(result):
                    continue
                
                yield result
    
    def _find_match_type(
        self,
        file_extraction: ParsedExtraction,
        pattern_extraction: ParsedExtraction,
    ) -> MatchType:
        """
        Determine match type between file network and pattern.
        
        Supports cross-type matching: CIDR ↔ Range
        
        Priority order (first match wins):
        1. EQUALS
        2. SUBSET
        3. SUPERSET
        4. OVERLAP
        5. UNMATCHED (if no match above)
        
        Args:
            file_extraction: Network from file
            pattern_extraction: Network from pattern
        
        Returns:
            MatchType
        """
        file_net = file_extraction.network
        pattern_net = pattern_extraction.network
        
        # Check if both are CIDR or both are ranges
        file_is_cidr = isinstance(file_net, (IPv4Network, IPv6Network))
        pattern_is_cidr = isinstance(pattern_net, (IPv4Network, IPv6Network))
        
        # Handle same-type matching first
        if file_is_cidr == pattern_is_cidr:
            if file_is_cidr:
                # CIDR vs CIDR matching
                matcher = CIDRMatcher([file_net])
                return self._check_match_type_against_pattern(matcher, pattern_net)
            else:
                # Range vs Range matching
                matcher = RangeMatcher([file_net])
                pattern_start, pattern_end = pattern_net
                return self._check_match_type_against_pattern(matcher, pattern_start, pattern_end)
        else:
            # Cross-type matching: convert both to ranges and compare
            # CIDR networks have int() conversion that gives network address
            file_start, file_end = self._cidr_to_range(file_net) if file_is_cidr else file_net
            pattern_start, pattern_end = self._cidr_to_range(pattern_net) if pattern_is_cidr else pattern_net
            
            # Now both are (start_int, end_int) tuples, use range matcher
            matcher = RangeMatcher([(file_start, file_end)])
            return self._check_match_type_against_pattern(matcher, pattern_start, pattern_end)
    
    def _cidr_to_range(self, network: Union[IPv4Network, IPv6Network]) -> tuple:
        """
        Convert CIDR network to (start_int, end_int) range.
        
        Args:
            network: IPv4Network or IPv6Network
        
        Returns:
            Tuple of (network_address_as_int, broadcast_address_as_int)
        """
        return (int(network.network_address), int(network.broadcast_address))
    
    def extract_networks(self, input_sources: List[InputSource]) -> dict:
        """
        Extract and deduplicate networks from input sources.
        
        This is the foundation for both --extract and --consolidate modes.
        It applies pattern filtering at the network level (not line level).
        
        Returns:
            dict: {network_object -> (ParsedExtraction, line_content)}
            
            Keys are network objects (IPv4Network/IPv6Network, or range tuples)
            Values are tuples of (ParsedExtraction object, original line content)
            
            Same network appearing in multiple formats/lines is deduplicated.
            ParsedExtraction preserves format_type and matched_texts for output.
        """
        from ipaddress import ip_network
        
        networks_dict = {}  # network_obj -> (parsed_extraction, line_content)
        
        for input_source in input_sources:
            for line_number, line_content, byte_offset in input_source.lines():
                line = line_content.rstrip('\n\r')
                
                # Extract networks from this line
                parsed_extractions = self.parser.parse_line(line)
                
                for parsed_ext in parsed_extractions:
                    network_obj = parsed_ext.network
                    
                    # Apply pattern filtering at network level
                    match_found = False
                    for pattern in self.parsed_patterns:
                        match_type = self._find_match_type(parsed_ext, pattern)
                        if match_type in self.match_type_filter:
                            match_found = True
                            break
                    
                    # Handle invert_match
                    if self.invert_match:
                        match_found = not match_found
                    
                    if not match_found:
                        continue
                    
                    # Deduplication: Keep ranges as ranges, CIDR as CIDR
                    # (don't convert - this preserves the original format)
                    dedup_network = network_obj
                    
                    # Store deduplicated (only first occurrence of each network is kept)
                    if dedup_network not in networks_dict:
                        networks_dict[dedup_network] = (parsed_ext, line)
        
        return networks_dict
    
    def consolidate_networks(self, input_sources: List[InputSource]) -> dict:
        """
        Consolidate (merge overlapping/adjacent) networks.
        
        Implementation note: This function uses extract_networks() as its foundation,
        maintaining the "Consolidate = Extract + Merge" architectural relationship.
        
        Process:
        1. Extract deduplicated networks using extract_networks()
        2. Convert ranges to CIDR blocks
        3. Use RFC-compliant CIDR supernetting (collapse_addresses) to merge
        4. Return consolidated network dictionary
        
        Returns:
            dict: {consolidated_network_object -> (ParsedExtraction, line_content)}
            
            Keys are consolidated network objects (merged/supernets)
            Values are ParsedExtraction + line_content from the first network in each supernet
        """
        from ipaddress import ip_network, collapse_addresses, IPv4Network, IPv6Network
        
        # Step 1: Extract unique networks
        networks_dict = self.extract_networks(input_sources)
        
        if not networks_dict:
            return {}
        
        # Step 2: Convert ranges to CIDR blocks and track metadata
        # (ranges cannot be directly consolidated, must expand to CIDR)
        expanded_networks = {}
        network_metadata = {}  # Maps network object to (ParsedExtraction, line_content)
        
        for net_obj, (parsed_ext, line_content) in networks_dict.items():
            if isinstance(net_obj, tuple):
                # Range: convert to CIDR blocks
                start_int, end_int = net_obj
                version = 6 if start_int > 0xFFFFFFFF else 4
                cidr_strings = self._range_to_cidrs(start_int, end_int, version)
                # Add each CIDR block (using same ParsedExtraction/line)
                for cidr_str in cidr_strings:
                    cidr_net = ip_network(cidr_str)
                    expanded_networks[cidr_net] = cidr_str
                    network_metadata[cidr_net] = (parsed_ext, line_content)
            else:
                # Already CIDR - keep as-is
                expanded_networks[net_obj] = str(net_obj)
                network_metadata[net_obj] = (parsed_ext, line_content)
        
        # Step 3: Use RFC-compliant collapse_addresses for proper CIDR supernetting
        # Separate IPv4 and IPv6 networks
        ipv4_networks = [net for net in expanded_networks.keys() if isinstance(net, IPv4Network)]
        ipv6_networks = [net for net in expanded_networks.keys() if isinstance(net, IPv6Network)]
        
        consolidated_list = []
        
        # Consolidate IPv4 networks
        if ipv4_networks:
            consolidated_list.extend(collapse_addresses(ipv4_networks))
        
        # Consolidate IPv6 networks
        if ipv6_networks:
            consolidated_list.extend(collapse_addresses(ipv6_networks))
        
        # Step 4: Map consolidated networks back to their metadata
        # For each consolidated network, find the first original network that it contains/equals
        consolidated_dict = {}
        for consolidated_net in consolidated_list:
            # Find the first original network that maps to this consolidated result
            for original_net, (parsed_ext, line_content) in network_metadata.items():
                if (isinstance(consolidated_net, type(original_net)) and
                    (consolidated_net == original_net or 
                     original_net.subnet_of(consolidated_net))):
                    consolidated_dict[consolidated_net] = (parsed_ext, line_content)
                    break
            else:
                # Fallback: shouldn't happen, but assign a dummy value
                consolidated_dict[consolidated_net] = (None, None)
        
        return consolidated_dict
    
    def _range_to_cidrs(self, start_int: int, end_int: int, version: int = 4) -> List[str]:
        """
        Convert a range (start_int, end_int) to a list of CIDR blocks.
        
        Algorithm: Iteratively find the largest CIDR block that fits at the current position,
        emit it, and advance to the next position.
        
        Args:
            start_int: Start IP as integer
            end_int: End IP as integer  
            version: IP version (4 or 6)
        
        Returns:
            List of CIDR strings (e.g., ['192.0.2.0/30', '192.0.2.4/32'])
        """
        from ipaddress import ip_network
        
        max_bits = 32 if version == 4 else 128
        cidrs = []
        current = start_int
        
        while current <= end_int:
            # Find the largest block size (smallest prefix length) that:
            # 1. Starts at an aligned boundary
            # 2. Doesn't exceed our range
            
            prefix_len = max_bits
            
            # Try each prefix length from 0 (largest block) to max
            for pl in range(max_bits):
                # Block size for this prefix: 2^(max_bits - prefix_length)
                block_size = 1 << (max_bits - pl)
                
                # Check alignment: current must be divisible by block_size
                if (current % block_size) == 0:
                    # Check that block doesn't exceed range
                    block_end = current + block_size - 1
                    if block_end <= end_int:
                        # This block fits - use it
                        prefix_len = pl
                        break
            
            # Emit the CIDR block
            cidr_str = str(ip_network((current, prefix_len)))
            cidrs.append(cidr_str)
            
            # Advance to next block
            block_size = 1 << (max_bits - prefix_len)
            current += block_size
        
        return cidrs
