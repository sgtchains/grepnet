"""GrepNet command-line interface."""

import sys
import argparse
import re
from collections import deque

import grepnet as grepnet_module
from grepnet import GrepNet, InputDiscovery, MatchType


def run():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog='grepnet',
        description='Network-aware grep for CIDR blocks and IP ranges',
        usage='%(prog)s [OPTION...] PATTERN [FILE...]  OR  %(prog)s [OPTION...] -f PATTERNS_FILE [FILE...]',
        allow_abbrev=False,
    )
    
    # Version
    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {grepnet_module.__version__}',
    )
    
    # Patterns
    parser.add_argument(
        'positional_args',
        nargs='*',
        help='PATTERN [FILE...] or FILE... (with -f)',
    )
    parser.add_argument(
        '-P',
        '--pattern',
        action='append',
        dest='pattern_flags',
        help='Specify pattern (can be used multiple times)',
    )
    parser.add_argument(
        '-f',
        '--file-patterns',
        action='store',
        dest='pattern_file',
        help='Read patterns from file (one per line)',
    )
    
    # Matching options
    parser.add_argument(
        '-e',
        '--equals',
        action='store_true',
        help='Match only EQUALS',
    )
    parser.add_argument(
        '-s',
        '--subset',
        action='store_true',
        help='Match only SUBSET',
    )
    parser.add_argument(
        '-S',
        '--superset',
        action='store_true',
        help='Match only SUPERSET',
    )
    parser.add_argument(
        '-O',
        '--overlap',
        action='store_true',
        help='Match only OVERLAP',
    )
    parser.add_argument(
        '-v',
        '--invert-match',
        action='store_true',
        help='Invert match logic',
    )
    parser.add_argument(
        '-u',
        '--unmatched',
        action='store_true',
        help='Include unmatched networks',
    )
    parser.add_argument(
        '-q',
        '--quiet',
        action='store_true',
        help='Suppress output (exit code only)',
    )
    parser.add_argument(
        '--no-messages',
        action='store_true',
        help='Suppress error/warning messages',
    )
    
    # Output formatting
    parser.add_argument(
        '-o',
        '--only-matching',
        action='store_true',
        help='Print only matched networks (original text as found)',
    )
    parser.add_argument(
        '-n',
        '--line-number',
        action='store_true',
        help='Print 1-based line number',
    )
    parser.add_argument(
        '-b',
        '--byte-offset',
        action='store_true',
        help='Print 0-based byte offset',
    )
    parser.add_argument(
        '-c',
        '--count',
        action='store_true',
        help='Print count of matching lines',
    )
    parser.add_argument(
        '-m',
        '--max-count',
        type=int,
        default=0,
        metavar='NUM',
        help='Stop after NUM matches',
    )
    parser.add_argument(
        '-H', '--with-filename',
        action='store_true',
        help='Print filename with output',
    )
    parser.add_argument(
        '--no-filename',
        action='store_true',
        help='Suppress filename in output',
    )
    parser.add_argument(
        '--label',
        action='store',
        dest='label',
        help='Display stdin as LABEL instead of (standard input)',
    )
    parser.add_argument(
        '-T',
        '--tab',
        action='store_true',
        dest='tab_prefix',
        help='Prepend tab character to each output line',
    )
    parser.add_argument(
        '-l',
        '--files-with-matches',
        action='store_true',
        help='Print only files with matches',
    )
    parser.add_argument(
        '-L',
        '--files-without-matches',
        action='store_true',
        help='Print only files without matches',
    )
    
    # Comment handling
    parser.add_argument(
        '--no-filter-comments',
        action='store_true',
        help='Do not remove comments before parsing',
    )
    
    # Parse control flags
    parser.add_argument(
        '--parse-cidr',
        choices=['pattern', 'input', 'both', 'none'],
        default='both',
        help='Where to accept CIDR notation (default: both)',
    )
    parser.add_argument(
        '--parse-netmask',
        choices=['pattern', 'input', 'both', 'none'],
        default='both',
        help='Where to accept subnet masks (default: both)',
    )
    parser.add_argument(
        '--parse-hostmask',
        choices=['pattern', 'input', 'both', 'none'],
        default='both',
        help='Where to accept hostmasks (default: both)',
    )
    parser.add_argument(
        '--parse-ranges',
        choices=['pattern', 'input', 'both', 'none'],
        default='both',
        help='Where to accept IP ranges (default: both)',
    )
    parser.add_argument(
        '--range-format',
        choices=['long', 'short', 'both', 'none'],
        default='both',
        help='Range output format preference (default: both)',
    )
    
    # Network extraction/consolidation
    parser.add_argument(
        '--extract',
        action='store_true',
        help='Extract all networks from files (deduplicated)',
    )
    parser.add_argument(
        '--consolidate',
        action='store_true',
        help='Consolidate overlapping and adjacent networks',
    )
    parser.add_argument(
        '--show-content',
        action='store_true',
        help='Show line content in extract/consolidate mode',
    )
    parser.add_argument(
        '--format',
        choices=['cidr', 'range', 'short-range', 'original'],
        default=None,  # None means not provided; will validate before using
        help='Network output format for extract/consolidate (default: cidr)',
    )
    
    # Context lines
    parser.add_argument(
        '-A',
        '--after-context',
        type=int,
        default=0,
        metavar='NUM',
        help='Print NUM lines after each match',
    )
    parser.add_argument(
        '-B',
        '--before-context',
        type=int,
        default=0,
        metavar='NUM',
        help='Print NUM lines before each match',
    )
    parser.add_argument(
        '-C',
        '--context',
        type=int,
        default=0,
        metavar='NUM',
        help='Print NUM lines before and after each match',
    )
    parser.add_argument(
        '--group-separator',
        action='store',
        dest='group_separator',
        default='--',
        help='Print SEP between match groups (default: "--")',
    )
    parser.add_argument(
        '--no-group-separator',
        action='store_true',
        help='Don\'t print group separator',
    )
    
    # CIDR validation
    parser.add_argument(
        '--strict-cidr',
        choices=['pattern', 'input', 'both', 'none'],
        default='none',
        help='Strict CIDR validation mode',
    )
    
    parser.add_argument(
        '--strict-cidr-action',
        choices=['fail', 'normalize', 'ignore', 'warn'],
        default='normalize',
        help='Action on CIDR validation error: fail (exit 2), normalize (default), ignore (skip), warn (stderr+skip)',
    )
    
    # File discovery
    parser.add_argument(
        '-r',
        '--recursive',
        action='store_true',
        help='Recursively search directories (do not follow symlinks)',
    )
    parser.add_argument(
        '-R',
        '--dereference-recursive',
        action='store_true',
        help='Recursively search directories (follow symlinks)',
    )
    parser.add_argument(
        '-F',
        '--file',
        action='append',
        dest='input_files_explicit',
        help='Specify input file explicitly (can be used multiple times)',
    )
    
    # Exclusion filters
    parser.add_argument(
        '--exclude-string',
        action='append',
        dest='exclude_strings',
        help='Exclude lines matching substring (can be used multiple times)',
    )
    parser.add_argument(
        '--exclude-cidr',
        action='append',
        dest='exclude_cidrs',
        help='Exclude networks matching CIDR/range (can be used multiple times)',
    )
    parser.add_argument(
        '--exclude-strings-file',
        action='store',
        dest='exclude_strings_file',
        help='Load text patterns to exclude from file (one regex per line)',
    )
    parser.add_argument(
        '--exclude-cidrs-file',
        action='store',
        dest='exclude_cidrs_file',
        help='Load networks to exclude from file (one network per line)',
    )
    
    # File filtering options
    parser.add_argument(
        '--include',
        action='append',
        dest='include_patterns',
        help='Include only files matching glob (repeatable)',
    )
    parser.add_argument(
        '--exclude',
        action='append',
        dest='exclude_patterns',
        help='Exclude files matching glob (repeatable)',
    )
    parser.add_argument(
        '--exclude-from',
        action='store',
        dest='exclude_from_file',
        help='Load exclude glob patterns from file (one pattern per line)',
    )
    parser.add_argument(
        '--exclude-dir',
        action='append',
        dest='exclude_dirs',
        help='Exclude directories matching glob (repeatable)',
    )
    parser.add_argument(
        '--binary-files',
        choices=['binary', 'text', 'without-match'],
        default='binary',
        help='How to handle binary files (default: binary)',
    )
    
    # Output options
    parser.add_argument(
        '--color',
        choices=['always', 'auto', 'never'],
        default='auto',
        help='Use colored output',
    )
    
    # Debug options
    parser.add_argument(
        '--debug',
        choices=['markup'],
        default=None,
        help='Debug mode (markup: show internal Unicode markup)',
    )
    
    args = parser.parse_args()
    
    # Handle -C (context) flag which sets both -A and -B
    if args.context > 0:
        args.after_context = args.context
        args.before_context = args.context
    
    # Parse positional arguments
    patterns = []
    files = []
    
    # From -P flags
    if args.pattern_flags:
        patterns.extend(args.pattern_flags)
    
    # From -f file
    if args.pattern_file:
        try:
            # Handle special case: -f - means read from stdin
            if args.pattern_file == '-':
                f = sys.stdin
            else:
                f = open(args.pattern_file, 'r')
            
            for line in f:
                line = line.rstrip('\n\r')
                # Add all non-empty lines to patterns list (without pre-filtering)
                # Comment handling is done by the extraction pipeline in GrepNet.parser
                if line:
                    patterns.append(line)
            
            # Close file if we opened it (not stdin)
            if args.pattern_file != '-':
                f.close()
            
            # Empty pattern file is allowed - will match nothing (or extract all in extract mode)
        except IOError as e:
            if not args.no_messages:
                print(f'grepnet: Cannot read pattern file {args.pattern_file}: {e}', file=sys.stderr)
            sys.exit(2)
        # All positional args are files when using -f
        files = args.positional_args
    elif args.pattern_flags:
        # When using -P, all positional args are files
        files = args.positional_args
    else:
        # If no -f or -P, first positional is pattern, rest are files
        if args.positional_args:
            patterns.append(args.positional_args[0])
            files = args.positional_args[1:]
    
    # Merge explicit files from -F flags (Issue 9)
    # The -F flag can be used multiple times to specify input files explicitly
    # These are merged into the files list regardless of whether files came from positional args or -f
    if args.input_files_explicit:
        files.extend(args.input_files_explicit)
    
    # Validate incompatible flag combinations (Issue 5)
    # Context flags cannot be used with -l, -L, --extract, or --consolidate
    # Check if any context flags were explicitly provided (even if value is 0)
    # Handle short flags (-A0, -A 0), long flags (--after-context, --after-context=0)
    context_flags_provided = any(
        arg.startswith('-A') or arg.startswith('-B') or arg.startswith('-C') or
        arg.startswith('--after-context') or arg.startswith('--before-context') or arg.startswith('--context')
        for arg in sys.argv[1:]  # Skip program name
    )
    if context_flags_provided and (args.files_with_matches or args.files_without_matches or args.extract or args.consolidate):
        if not args.no_messages:
            print('grepnet: error: context flags (-B/-A/-C) cannot be used with -l, -L, --extract, or --consolidate', file=sys.stderr)
        sys.exit(2)
    
    # If no patterns found from any source (args.pattern_flags or positional), error
    # But allow it if pattern file was provided (even if empty), or if --extract/--consolidate
    # Only error if user provided NO pattern source at all in normal grep mode
    has_pattern_source = args.pattern_file or args.pattern_flags or (args.positional_args and not args.extract and not args.consolidate and not (args.files_with_matches or args.files_without_matches))
    
    if not patterns and not has_pattern_source and not args.extract and not args.consolidate:
        if not args.no_messages:
            print('grepnet: error: no patterns to search for', file=sys.stderr)
        sys.exit(2)
    
    # Determine match type filter based on -e, -s, -S, -O, -u flags
    match_type_filter = []
    has_explicit_match_type = False
    
    if args.equals:
        match_type_filter.append(MatchType.EQUALS)
        has_explicit_match_type = True
    if args.subset:
        match_type_filter.append(MatchType.SUBSET)
        has_explicit_match_type = True
    if args.superset:
        match_type_filter.append(MatchType.SUPERSET)
        has_explicit_match_type = True
    if args.overlap:
        match_type_filter.append(MatchType.OVERLAP)
        has_explicit_match_type = True
    
    # If no match type flags specified, use default (unless -u is the only one)
    if not has_explicit_match_type and not args.unmatched:
        match_type_filter = [
            MatchType.EQUALS,
            MatchType.SUBSET,
            MatchType.SUPERSET,
            MatchType.OVERLAP,
        ]
    
    # Add UNMATCHED if -u flag specified
    if args.unmatched:
        match_type_filter.append(MatchType.UNMATCHED)
    
    # Determine enable_colors
    if args.color == 'always':
        enable_colors = True
    elif args.color == 'never':
        enable_colors = False
    else:  # auto
        enable_colors = sys.stdout.isatty()
    
    # Load exclude strings from file if provided (BEFORE creating GrepNet instance)
    if args.exclude_strings_file:
        try:
            with open(args.exclude_strings_file, 'r') as f:
                for line in f:
                    line = line.rstrip('\n\r')
                    if line and not line.lstrip().startswith('#'):
                        if args.exclude_strings is None:
                            args.exclude_strings = []
                        args.exclude_strings.append(line)
        except IOError as e:
            if not args.no_messages:
                print(f'grepnet: Cannot read exclude strings file {args.exclude_strings_file}: {e}', file=sys.stderr)
            sys.exit(2)
    
    # Load exclude CIDR patterns from file if provided (BEFORE creating GrepNet instance)
    if args.exclude_cidrs_file:
        try:
            with open(args.exclude_cidrs_file, 'r') as f:
                for line in f:
                    line = line.rstrip('\n\r')
                    if line and not line.lstrip().startswith('#'):
                        if args.exclude_cidrs is None:
                            args.exclude_cidrs = []
                        args.exclude_cidrs.append(line)
        except IOError as e:
            if not args.no_messages:
                print(f'grepnet: Cannot read exclude CIDR file {args.exclude_cidrs_file}: {e}', file=sys.stderr)
            sys.exit(2)
    
    # Create GrepNet instance
    try:
        # For extract/consolidate, use default patterns if none provided
        # BUT: Don't add defaults if pattern file was explicitly provided (even if empty)
        pattern_file_explicitly_provided = bool(args.pattern_file)
        if args.extract or args.consolidate:
            # Only use default patterns if no explicit pattern file was provided
            if not pattern_file_explicitly_provided and not patterns:
                grepnet_patterns = ['0.0.0.0/0', '::0/0']
            else:
                grepnet_patterns = patterns
        else:
            grepnet_patterns = patterns
        
        grepnet = GrepNet(
            patterns=grepnet_patterns,
            filter_comments=not args.no_filter_comments,
            strict_mode=(args.strict_cidr in ['pattern', 'both']),
            strict_cidr_action=args.strict_cidr_action,
            strict_cidr_mode=args.strict_cidr,
            parse_cidr=args.parse_cidr,
            parse_netmask=args.parse_netmask,
            parse_hostmask=args.parse_hostmask,
            parse_ranges=args.parse_ranges,
            range_format=args.range_format,
            enable_colors=enable_colors,
            match_type_filter=match_type_filter,
            invert_match=args.invert_match,
            show_unmatched=args.unmatched,
            debug=args.debug,
            exclude_strings=args.exclude_strings,
            exclude_cidrs=None,  # Will be set after parsing
            output_format=args.format if args.format else 'cidr',  # Default to 'cidr' if not provided
            binary_files=args.binary_files,
        )
        
        # Validate strict CIDR in patterns if requested
        if args.strict_cidr in ['pattern', 'both']:
            for pattern_extraction in grepnet.parsed_patterns:
                if pattern_extraction.was_normalized:
                    # Get original text from matched_texts (should be present)
                    original_text = pattern_extraction.matched_texts[0]['text'] if pattern_extraction.matched_texts else str(pattern_extraction.network)
                    error_msg = f"Malformed CIDR in pattern: {original_text} (normalized to {pattern_extraction.network})"
                    if args.strict_cidr_action == 'fail':
                        raise ValueError(error_msg)
                    elif args.strict_cidr_action == 'warn' and not args.no_messages:
                        print(f'grepnet warning: {error_msg}', file=sys.stderr)
        
        # Load exclude patterns from file if provided (for --exclude-from)
        if args.exclude_from_file:
            try:
                with open(args.exclude_from_file, 'r') as f:
                    for line in f:
                        line = line.rstrip('\n\r')
                        if line and not line.lstrip().startswith('#'):
                            if args.exclude_patterns is None:
                                args.exclude_patterns = []
                            args.exclude_patterns.append(line)
            except IOError as e:
                if not args.no_messages:
                    print(f'grepnet: Cannot read exclude patterns file {args.exclude_from_file}: {e}', file=sys.stderr)
                sys.exit(2)
        
        # Parse exclude CIDR patterns
        if args.exclude_cidrs:
            exclude_cidrs = []
            for cidr_str in args.exclude_cidrs:
                exclude_extractions = grepnet.parser.parse_line(cidr_str)
                exclude_cidrs.extend([e.network for e in exclude_extractions])
            grepnet.exclude_cidrs = exclude_cidrs
    except Exception as e:
        if not args.no_messages:
            import traceback
            print(f'grepnet: {e}', file=sys.stderr)
            print('=== TRACEBACK ===', file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
        sys.exit(2)
    
    # Get input sources
    use_stdin = not sys.stdin.isatty() and not files
    input_sources = InputDiscovery.get_sources(
        files=files if files else None,
        use_stdin=use_stdin,
        recursive=args.recursive,
        dereference_recursive=args.dereference_recursive,
        include_patterns=args.include_patterns,
        exclude_patterns=args.exclude_patterns,
        exclude_dirs=args.exclude_dirs,
        stdin_label=args.label,
    )
    
    if not input_sources:
        parser.error('No input files specified and stdin is a terminal')
    
    # Auto-enable filename prefix for multiple files (unless --no-filename is set)
    # Count non-stdin files in input_sources
    file_count = len([s for s in input_sources if s.display_name is not None])
    if file_count > 1 and not args.files_without_matches and not args.no_filename:
        args.with_filename = True
    
    if not input_sources:
        parser.error('No input files specified and stdin is a terminal')
    
    # Validate --format usage early (before search)
    # Only validate if --format was explicitly provided (args.format is not None)
    if args.format is not None:
        if not (args.extract or args.consolidate):
            if not args.no_messages:
                print(f'grepnet: error: --format \'{args.format}\' can only be used with --extract or --consolidate', file=sys.stderr)
            sys.exit(2)
        if args.format == 'original' and args.consolidate:
            if not args.no_messages:
                print(f'grepnet: error: --format original cannot be used with --consolidate', file=sys.stderr)
            sys.exit(2)
    
    # Validate that patterns were actually extracted (not just empty strings)
    # This catches the case where user passes '' or whitespace-only patterns
    # 
    # IMPORTANT: Different rules for different modes:
    # - Normal search mode: patterns REQUIRED (empty = error, exit 2)
    # - Extract/consolidate modes: patterns OPTIONAL (empty = OK, exit 1 if no networks)
    
    if not args.extract and not args.consolidate and not grepnet.parsed_patterns:
        # Normal search mode: empty patterns is an ERROR
        if not args.no_messages:
            print('grepnet: error: no patterns to search for', file=sys.stderr)
        sys.exit(2)
    
    # Run search
    try:
        if args.extract or args.consolidate:
            from ipaddress import IPv4Network, IPv6Network, ip_network
            
            # Internal validation: patterns must exist (CLI should have provided defaults or user patterns)
            # For extract/consolidate: allow empty patterns (will extract nothing, exit 1)
            # This is belt & suspenders - CLI layer should have validated, but check here too
            if not grepnet.parsed_patterns:
                # In extract/consolidate mode with empty patterns: exit 1 (no matches)
                # not error (which would be 2)
                if not args.no_messages:
                    # Silently return 1 - no patterns means no networks to extract
                    pass
                sys.exit(1)
            
            # For extract/consolidate modes: iterate through ALL lines and extract networks
            # Then apply pattern filtering at NETWORK level (not line level)
            
            # ============================================================================
            # DATA STRUCTURE: networks_dict
            # ============================================================================
            # Type: dict[IPv4Network | IPv6Network, tuple[ParsedExtraction, str]]
            # 
            # Key Design Decisions:
            # =====================
            # 
            # 1. KEYS ARE NETWORK OBJECTS (not strings):
            #    - Keys must be IPv4Network/IPv6Network objects (from ipaddress module)
            #    - NOT string representations (e.g., not "192.0.2.0/24" strings)
            #    - Reason: Network objects have proper __eq__() and __hash__() for dict lookup
            #    - Reason: Consolidate mode needs to call .supernet_of(), .subnet_of(), 
            #              .version, .network_address, etc.
            #
            # 2. RANGE TUPLES CONVERTED TO CIDR OBJECTS:
            #    - Ranges are parsed as tuples: (start_int, end_int)
            #    - Tuples are NOT added to dict directly
            #    - Instead: Convert to CIDR via _range_to_cidrs(), use first CIDR as key
            #    - Reason: Ensures all dict keys are compatible IPv4Network/IPv6Network
            #    - Reason: Deduplication works correctly (same network in different formats)
            #
            # 3. VALUES CONTAIN METADATA:
            #    - value[0] = ParsedExtraction object
            #      Contains: network_obj, format_type, was_normalized, matched_texts
            #    - value[1] = Original line content (string)
            #    - Reason: Preserves format info for output (can show "subnet mask" vs "CIDR")
            #    - Reason: Consolidate mode can access line-level context
            #
            # Architectural Dependency:
            # ==========================
            # This structure is specifically designed to support CONSOLIDATE MODE:
            # - Consolidate merges overlapping/adjacent networks into supernets
            # - It must call network_obj.supernet_of() and .subnet_of() methods
            # - String keys would break this (can't call methods on strings)
            # - Previous bug: Used string keys, broke consolidate's merge logic
            # - Current fix: Use network objects, consolidate can access all methods
            #
            # Example:
            # --------
            # Input lines:
            #   192.0.2.0/24 (CIDR format)
            #   192.0.2.0 255.255.255.0 (subnet mask format)
            #   192.0.2.0-192.0.2.255 (range format)
            #
            # All three parse to same network: IPv4Network('192.0.2.0/24')
            # All three convert to same dedup key: IPv4Network('192.0.2.0/24')
            # Dict contains single entry (deduplicated), preserves all original texts
            # ============================================================================
            
            networks_dict = {}  # network_obj -> (parsed_extraction, line_content)
            
            try:
                # Iterate through all input lines
                for input_source in input_sources:
                    try:
                        for line_number, line_content, byte_offset in input_source.lines():
                            line = line_content.rstrip('\n\r')
                            
                            # Extract networks from this line
                            parsed_extractions = grepnet.parser.parse_line(line)
                            
                            for parsed_ext in parsed_extractions:
                                network_obj = parsed_ext.network
                                
                                # Apply pattern filtering at network level
                                # Check if this network matches any pattern
                                match_found = False
                                for pattern in grepnet.parsed_patterns:
                                    match_type = grepnet._find_match_type(parsed_ext, pattern)
                                    if match_type in grepnet.match_type_filter:
                                        match_found = True
                                        break
                                
                                # Handle invert_match
                                if grepnet.invert_match:
                                    match_found = not match_found
                                
                                # Only include if it matches the pattern filter
                                if match_found:
                                    # =========================================================================
                                    # DEDUP
                                    # DEDUPLICATION LOGIC: Convert all network types to canonical form
                                    # =========================================================================
                                    # Problem: Networks extracted from different formats need deduplication
                                    # - CIDR: "192.0.2.0/24" -> IPv4Network object
                                    # - Subnet mask: "192.0.2.0 255.255.255.0" -> IPv4Network object  
                                    # - Range: "192.0.2.0-192.0.2.255" -> tuple (start_int, end_int)
                                    # - IP only: "192.0.2.0" -> IPv4Network object (/32)
                                    #
                                    # All the above represent the SAME NETWORK, but:
                                    # - IPv4Network objects compare equal (correct behavior)
                                    # - Tuples are a different type, so tuple != IPv4Network (bug!)
                                    #
                                    # Fix: Convert range tuples to IPv4Network/IPv6Network objects
                                    # This way all dict keys are compatible, with proper equality checking
                                    # =========================================================================
                                    
                                    dedup_network = network_obj
                                    if isinstance(network_obj, tuple):
                                        # Range tuple: (start_int, end_int)
                                        # Must convert to CIDR to get IPv4Network/IPv6Network object
                                        start_int, end_int = network_obj
                                        
                                        # Determine IP version based on address size
                                        if start_int > 0xFFFFFFFF:
                                            version = 6
                                        else:
                                            version = 4
                                        
                                        # Convert range to CIDR blocks
                                        # _range_to_cidrs() returns list of CIDR STRINGS
                                        cidr_strings = grepnet._range_to_cidrs(start_int, end_int, version)
                                        if cidr_strings:
                                            # Convert string CIDR to network object
                                            cidr_str = cidr_strings[0]  # Use first CIDR block
                                            dedup_network = ip_network(cidr_str)  # Convert string to network object
                                        # else: keep original tuple if conversion fails (edge case - shouldn't happen)
                                    
                                    # Store in networks_dict with network object as key
                                    # Value is tuple: (ParsedExtraction object, original line content string)
                                    # - ParsedExtraction contains format_type, matched_texts for output formatting
                                    # - Line content string provides context for consolidate mode
                                    # CRITICAL: Do NOT use string keys (breaks consolidate mode's .supernet_of() calls)
                                    if dedup_network not in networks_dict:
                                        try:
                                            networks_dict[dedup_network] = (parsed_ext, line)
                                        except Exception as e:
                                            if not args.no_messages:
                                                print(f'grepnet: error storing in networks_dict: {e}', file=sys.stderr)
                                                print(f'  dedup_network type: {type(dedup_network).__name__}, value: {dedup_network}', file=sys.stderr)
                                                print(f'  parsed_ext type: {type(parsed_ext).__name__}', file=sys.stderr)
                                                print(f'  line type: {type(line).__name__}, length: {len(line) if isinstance(line, str) else "N/A"}', file=sys.stderr)
                                            raise
                    except IOError as e:
                        if not args.no_messages:
                            print(f'grepnet: Cannot read {input_source.display_name or "stdin"}: {e}', file=sys.stderr)
                        continue
            except Exception as e:
                if not args.no_messages:
                    import traceback
                    print(f'grepnet: error during extract/consolidate processing: {e}', file=sys.stderr)
                    traceback.print_exc(file=sys.stderr)
                sys.exit(2)
            
            if not networks_dict:
                sys.exit(1)
            
            # Step 2: For extract mode, output and exit
            if args.extract:
                for parsed_extraction, line_content in networks_dict.values():
                    # Apply exclusion filters in extract mode
                    if grepnet._check_extraction_excluded(parsed_extraction):
                        continue
                    
                    formatted_net = grepnet.format_network(parsed_extraction)
                    if args.show_content and line_content:
                        print(f'{formatted_net} {line_content}')
                    else:
                        print(formatted_net)
                sys.exit(0)
            
            # Step 3: For consolidate mode, consolidate the extracted networks
            # ========================================================================
            # CONSOLIDATE MODE: Merge overlapping and adjacent networks into supernets
            # ========================================================================
            # Purpose: Take extracted networks and merge them:
            # - Overlapping networks: Keep the superset (largest network)
            # - Adjacent networks: Merge into single supernet if possible
            # - Example: 192.0.2.0/25 + 192.0.2.128/25 -> 192.0.2.0/24
            #
            # Why networks_dict keys must be IPv4Network/IPv6Network objects:
            # - Need to call .subnet_of(), .supernet_of(), .version properties
            # - String keys can't call methods (this was the Issue 1 bug that broke consolidate)
            # - Issue 1 fix ensures all keys are network objects (not strings, not tuples)
            #
            # Algorithm:
            # 1. Sort networks by version and start address (ensures consistent merge order)
            # 2. Iterate through sorted networks
            # 3. For each network: check if it overlaps/is-adjacent-to previous
            # 4. If yes: merge into supernet and replace last entry
            # 5. If no: append as new entry
            # 6. Output merged networks
            # ========================================================================
            
            if args.consolidate:
                # Sort extracted networks for consolidation
                # networks_dict.items() returns: [(network_obj, (parsed_ext, line)), ...]
                # where network_obj is guaranteed to be IPv4Network/IPv6Network (Issue 1 ensures this)
                
                # Debug: Check networks_dict contents
                if args.debug:
                    print(f'DEBUG: networks_dict has {len(networks_dict)} entries', file=sys.stderr)
                    for i, (k, v) in enumerate(list(networks_dict.items())[:3]):  # Show first 3
                        print(f'  [{i}] key={k} (type={type(k).__name__}), value={type(v).__name__} with {len(v)} items', file=sys.stderr)
                
                networks_list = list(networks_dict.items())  # [(network_obj, (parsed_ext, line)), ...]
                
                def _sort_key(item):
                    # Sort networks by: (ip_version, start_address)
                    # This ensures:
                    # - IPv4 networks come before IPv6 networks
                    # - Within same version, sorted by start address (ascending)
                    # - Consolidation algorithm can safely merge adjacent networks
                    # 
                    # Note: By Issue 1 fix, all network_obj should be IPv4Network/IPv6Network
                    # (no tuples), so the hasattr check should always return True
                    network_obj, _ = item
                    if hasattr(network_obj, 'version'):
                        # CIDR: IPv4Network or IPv6Network object
                        # Can directly access .version and .network_address properties
                        version = network_obj.version
                        start_addr = int(network_obj.network_address)
                    else:
                        # Range tuple: (start_int, end_int)
                        start_addr, _ = network_obj
                        # IPv4 ranges are 32-bit, IPv6 are 128-bit
                        version = 4 if start_addr <= 0xFFFFFFFF else 6
                    return (version, start_addr)
                
                networks_list.sort(key=_sort_key)
                
                # Debug: Check what's in networks_list
                if not networks_list:
                    sys.exit(1)
                
                # Merge overlapping and adjacent networks
                consolidated = []
                for network_obj, value_tuple in networks_list:
                    # Unpack value tuple - should be (parsed_ext, content)
                    try:
                        parsed_ext, content = value_tuple
                    except (TypeError, ValueError) as e:
                        if not args.no_messages:
                            print(f'grepnet: error: failed to unpack value from networks_dict: {e}', file=sys.stderr)
                            print(f'  network_obj: {network_obj}', file=sys.stderr)
                            print(f'  value_tuple type: {type(value_tuple)}, len: {len(value_tuple) if isinstance(value_tuple, (list, tuple)) else "N/A"}', file=sys.stderr)
                            if isinstance(value_tuple, (list, tuple)):
                                for i, item in enumerate(value_tuple):
                                    print(f'    [{i}]: {type(item)} = {item}', file=sys.stderr)
                        sys.exit(2)
                    
                    net = network_obj
                    net = network_obj
                    if not consolidated:
                        # First network - always add
                        consolidated.append(net)
                    else:
                        last = consolidated[-1]
                        
                        # Check if networks are both CIDR or both tuples
                        # (By Issue 1 fix, should always be CIDR IPv4Network/IPv6Network)
                        is_cidr_net = isinstance(net, (IPv4Network, IPv6Network))
                        is_cidr_last = isinstance(last, (IPv4Network, IPv6Network))
                        
                        if is_cidr_net and is_cidr_last:
                            # Both are CIDR network objects - try to merge
                            try:
                                # Check if networks overlap or one is subset of other
                                if net.subnet_of(last) or last.subnet_of(net):
                                    # One is contained in the other
                                    # Keep the superset (largest network)
                                    if net.version == last.version:
                                        # Same IP version: keep whichever is larger
                                        consolidated[-1] = last if last.supernet_of(net) else net
                                elif net.network_address == last.broadcast_address + 1:
                                    # Adjacent networks - next network starts where previous ends
                                    # Merge into single supernet
                                    supernet_addr = last.network_address
                                    supernet_mask = last.prefixlen - 1
                                    consolidated[-1] = ip_network((supernet_addr, supernet_mask))
                                else:
                                    # Networks don't overlap or touch - keep both
                                    consolidated.append(net)
                            except:
                                # If merge logic fails for any reason, keep the network
                                consolidated.append(net)
                        else:
                            # Can't easily merge ranges, just append as-is
                            # (This case shouldn't happen due to Issue 1 fix)
                            consolidated.append(net)
                
                # Output consolidated networks in requested format
                # ===================================================
                # For consolidate mode, networks came from the original extraction pipeline
                # and may have original format_type (subnet_mask, cidr_notation, etc.)
                # However, after consolidation, we need to output in target format
                # 
                # Create temporary ParsedExtraction wrappers to provide metadata
                # to the formatting function. The network object is what matters most.
                from grepnet.core.network_objects import ParsedExtraction
                for net in consolidated:
                    # Create temporary ParsedExtraction wrapper for consolidated networks
                    # Note: format_type is 'cidr_notation' for all consolidated output
                    # (consolidation produces standard CIDR form)
                    temp_extraction = ParsedExtraction(
                        network=net,
                        format_type='cidr_notation' if isinstance(net, (IPv4Network, IPv6Network)) else 'ipv4_range',
                        was_normalized=False,
                        matched_texts=[]
                    )
                    # format_network() handles output format conversion (--format cidr/range/etc.)
                    formatted_net = grepnet.format_network(temp_extraction)
                    print(formatted_net)
                
                sys.exit(0)

        
        match_count = 0
        file_matches = {}  # Map filename -> set of line numbers with matches
        seen_output = set()  # Track output to avoid duplication
        results_by_line = {}  # Map line_number -> list of (filename, result) tuples
        
        # Track binary files with matches for "without-match" mode
        binary_files_matched = {}  # filename -> bool (whether it had matches)
        
        # Determine if context is needed
        # Context is needed if ANY context flags were explicitly provided (even with value 0)
        # Handle short flags (-A0, -A 0), long flags (--after-context, --after-context=0)
        context_flags_provided = any(
            arg.startswith('-A') or arg.startswith('-B') or arg.startswith('-C') or
            arg.startswith('--after-context') or arg.startswith('--before-context') or arg.startswith('--context')
            for arg in sys.argv[1:]  # Skip program name
        )
        use_context = context_flags_provided or args.before_context > 0 or args.after_context > 0
        
        if use_context:
            # Streaming context mode with gap detection
            before_buf = deque(maxlen=args.before_context)  # Last N lines
            after_count = 0  # Number of lines to output after next match
            last_match_line = None  # Track previous match line for gap detection
            lines_output = set()  # Track which line numbers we've already output (to avoid dupes)
            
            for result in grepnet.search(input_sources, yield_all_lines=True):
                current_line = result.line_number
                
                if result.is_match:
                    # Skip if we've already output this line (handles multiple matches per line)
                    if current_line in lines_output:
                        continue
                    
                    # Check for gap between previous after-context and current before-context
                    if last_match_line is not None:
                        prev_context_end = last_match_line + args.after_context
                        curr_context_start = current_line - args.before_context
                        
                        # Gap exists if there's space between them (ranges don't overlap)
                        if prev_context_end < curr_context_start and not args.quiet and not args.no_group_separator:
                            print(args.group_separator)
                    
                    # Output before-context buffer
                    for ctx_filename, ctx_line_num, ctx_content in before_buf:
                        prefix_parts = []
                        if args.with_filename and ctx_filename:
                            if enable_colors:
                                prefix_parts.append(grepnet.colorizer.colorize_filename(ctx_filename))
                            else:
                                prefix_parts.append(ctx_filename)
                        if args.line_number:
                            if enable_colors:
                                prefix_parts.append(grepnet.colorizer.colorize_line_number(str(ctx_line_num)))
                            else:
                                prefix_parts.append(str(ctx_line_num))
                        
                        # Choose separator: tab for -T, colon for normal
                        if args.tab_prefix and prefix_parts:
                            sep = '\t'
                        elif enable_colors:
                            sep = grepnet.colorizer.colorize_separator(':')
                        else:
                            sep = ':'
                        
                        prefix = sep.join(prefix_parts)
                        
                        if prefix:
                            # Use tab as separator if -T and single prefix, colon if multiple
                            ctx_prefix_count = 0
                            if args.with_filename and ctx_filename:
                                ctx_prefix_count += 1
                            if args.line_number:
                                ctx_prefix_count += 1
                            if args.tab_prefix and ctx_prefix_count == 1:
                                output = f'{prefix}\t{ctx_content}'
                            else:
                                output = f'{prefix}:{ctx_content}'
                        else:
                            output = ctx_content
                        if not args.quiet:
                            print(output)
                    
                    before_buf.clear()
                    
                    # Output the match itself
                    if args.max_count > 0 and match_count >= args.max_count:
                        break
                    
                    filename = result.filename
                    if filename not in file_matches:
                        file_matches[filename] = set()
                    file_matches[filename].add(current_line)
                    if current_line not in results_by_line:
                        results_by_line[current_line] = []
                    results_by_line[current_line].append((filename, result))
                    
                    prefix_parts = []
                    byte_offset_str = None
                    line_num_str = None
                    filename_str = None
                    
                    if args.with_filename and filename:
                        filename_str = filename if not enable_colors else filename
                    if args.line_number:
                        line_num_str = (grepnet.colorizer.colorize_line_number(str(current_line))
                                      if enable_colors else str(current_line))
                    if args.byte_offset:
                        byte_offset_str = (grepnet.colorizer.colorize_byte_offset(str(result.byte_offset))
                                         if enable_colors else str(result.byte_offset))
                    
                    # Build prefix in the correct order for -T or normal mode
                    if args.tab_prefix:
                        # For -T mode: byte, line, filename order with tab separators
                        if byte_offset_str:
                            prefix_parts.append(byte_offset_str)
                        if line_num_str:
                            prefix_parts.append(line_num_str)
                        if filename_str:
                            prefix_parts.append(filename_str)
                        sep = '\t'
                    else:
                        # For normal mode: filename, line, byte order with colon separators
                        if filename_str:
                            prefix_parts.append(filename_str)
                        if line_num_str:
                            prefix_parts.append(line_num_str)
                        if byte_offset_str:
                            prefix_parts.append(byte_offset_str)
                        if enable_colors:
                            sep = grepnet.colorizer.colorize_separator(':')
                        else:
                            sep = ':'
                    
                    prefix = sep.join(prefix_parts)
                    
                    if args.only_matching:
                        # Extract networks in order
                        marked_content = result.content_marked
                        pattern = r'\uE000TYPE:[A-Z_]+\|OBJ:[A-Z_]+\|NORM:\w+\uE001(.*?)\uE000/TYPE\uE001'
                        networks_in_order = re.findall(pattern, marked_content)
                        for network_text in networks_in_order:
                            output_text = network_text
                            if enable_colors:
                                markup_pattern = r'\uE000TYPE:[A-Z_]+\|OBJ:[A-Z_]+\|NORM:\w+\uE001' + re.escape(network_text) + r'\uE000/TYPE\uE001'
                                marked_block = re.search(markup_pattern, marked_content)
                                if marked_block:
                                    output_text = grepnet.colorizer.finalize_markup(marked_block.group(0), enable_colors=True)
                            if prefix:
                                # Use tab as separator if -T and single prefix, colon if multiple
                                if args.tab_prefix and len(prefix_parts) == 1:
                                    output = f'{prefix}\t{output_text}'
                                else:
                                    output = f'{prefix}:{output_text}'
                            else:
                                output = output_text
                            if not args.quiet:
                                print(output)
                            match_count += 1
                            if args.max_count > 0 and match_count >= args.max_count:
                                break
                    else:
                        # Full line output
                        line_output = result.content_colored if enable_colors else result.line_content
                        if prefix:
                            # Use tab as separator if -T and single prefix, colon if multiple
                            if args.tab_prefix and len(prefix_parts) == 1:
                                output = f'{prefix}\t{line_output}'
                            else:
                                output = f'{prefix}:{line_output}'
                        else:
                            output = line_output
                        if not args.quiet:
                            print(output)
                        match_count += 1
                    
                    # Track this line and match for next iteration's gap check
                    lines_output.add(current_line)
                    last_match_line = current_line
                    after_count = args.after_context
                
                elif after_count > 0:
                    # After-context: output non-match line following a match
                    prefix_parts = []
                    if args.with_filename and result.filename:
                        prefix_parts.append(result.filename)
                    if args.line_number:
                        prefix_parts.append(str(current_line))
                    
                    # Choose separator: tab for -T, colon for normal
                    if args.tab_prefix and prefix_parts:
                        sep = '\t'
                    else:
                        sep = ':'
                    
                    prefix = sep.join(prefix_parts)
                    
                    line_output = result.line_content.rstrip('\n')
                    if prefix:
                        # Use tab as separator if -T and single prefix, colon if multiple
                        if args.tab_prefix and len(prefix_parts) == 1:
                            output = f'{prefix}\t{line_output}'
                        else:
                            output = f'{prefix}:{line_output}'
                    else:
                        output = line_output
                    if not args.quiet:
                        print(output)
                    
                    after_count -= 1
                
                else:
                    # Before-context: add to buffer for next match
                    before_buf.append((result.filename, current_line, result.line_content.rstrip('\n')))
        
        else:
            # No context: original simple approach
            for result in grepnet.search(input_sources):
                if not result.is_match:
                    continue
                    
                filename = result.filename
                if filename not in file_matches:
                    file_matches[filename] = set()
                file_matches[filename].add(result.line_number)
                
                # Track if this file is binary (already detected in search)
                if result.is_binary_file:
                    binary_files_matched[filename] = True
                
                if result.line_number not in results_by_line:
                    results_by_line[result.line_number] = []
                results_by_line[result.line_number].append((filename, result))
        
        # Skip output phase if context mode already output all results
        if not use_context:
            # For "without-match" mode, output binary file messages instead of normal output
            if args.binary_files == 'without-match' and binary_files_matched:
                for filename in sorted(binary_files_matched.keys()):
                    if not args.quiet:
                        print(f'Binary file {filename} matches')
                # Still set match_count for -c (count) mode
                for lines in file_matches.values():
                    match_count += len(lines)
            
            # Output normal results (only if NOT in without-match mode or no binary matches)
            elif not (args.binary_files == 'without-match' and binary_files_matched):
                for line_number in sorted(results_by_line.keys()):
                    # Check max_count before outputting this line
                    if args.max_count > 0 and match_count >= args.max_count:
                        break
                        
                    line_results = results_by_line[line_number]
                    filename, first_result = line_results[0]
                    
                    # Skip output for -l and -L (handled at end)
                    if args.files_with_matches or args.files_without_matches:
                        continue
                    
                    # For -c (count), just count and skip output
                    if args.count:
                        match_count += len(line_results)
                        continue
                    
                    # Build prefix parts (used by all output modes)
                    prefix_parts = []
                    byte_offset_str = None
                    line_num_str = None
                    filename_str = None
                    
                    if args.with_filename and filename:
                        filename_str = (grepnet.colorizer.colorize_filename(filename)
                                      if enable_colors else filename)
                    if args.line_number:
                        line_num_str = (grepnet.colorizer.colorize_line_number(str(line_number))
                                      if enable_colors else str(line_number))
                    if args.byte_offset:
                        byte_offset_str = (grepnet.colorizer.colorize_byte_offset(str(first_result.byte_offset))
                                         if enable_colors else str(first_result.byte_offset))
                    
                    # Build prefix in the correct order for -T or normal mode
                    if args.tab_prefix:
                        # For -T mode: byte, line, filename order with tab separators
                        if byte_offset_str:
                            prefix_parts.append(byte_offset_str)
                        if line_num_str:
                            prefix_parts.append(line_num_str)
                        if filename_str:
                            prefix_parts.append(filename_str)
                        sep = '\t'
                    else:
                        # For normal mode: filename, line, byte order with colon separators
                        if filename_str:
                            prefix_parts.append(filename_str)
                        if line_num_str:
                            prefix_parts.append(line_num_str)
                        if byte_offset_str:
                            prefix_parts.append(byte_offset_str)
                        if enable_colors:
                            sep = grepnet.colorizer.colorize_separator(':')
                        else:
                            sep = ':'
                    
                    prefix = sep.join(prefix_parts)
                    
                    # Output phase: -o mode (only matched texts)
                    if args.only_matching:
                        # Extract networks in order from the marked content
                        marked_content = line_results[0][1].content_marked
                        pattern = r'\uE000TYPE:[A-Z_]+\|OBJ:[A-Z_]+\|NORM:\w+\uE001(.*?)\uE000/TYPE\uE001'
                        networks_in_order = re.findall(pattern, marked_content)
                        
                        for network_text in networks_in_order:
                            output_text = network_text
                            
                            # Colorize if enabled (find markup block and colorize just that)
                            if enable_colors:
                                markup_pattern = r'\uE000TYPE:[A-Z_]+\|OBJ:[A-Z_]+\|NORM:\w+\uE001' + re.escape(network_text) + r'\uE000/TYPE\uE001'
                                marked_block = re.search(markup_pattern, marked_content)
                                if marked_block:
                                    output_text = grepnet.colorizer.finalize_markup(marked_block.group(0), enable_colors=True)
                            
                            # Add prefix
                            if prefix:
                                # Use tab as separator if -T and single prefix, colon if multiple
                                if args.tab_prefix and len(prefix_parts) == 1:
                                    output = f'{prefix}\t{output_text}'
                                else:
                                    output = f'{prefix}:{output_text}'
                            else:
                                output = output_text
                            
                            if not args.quiet:
                                print(output)
                            match_count += 1
                            
                            # Check max_count after each match in -o mode
                            if args.max_count > 0 and match_count >= args.max_count:
                                break
                    
                    # Normal mode (full line output)
                    else:
                        output_key = line_number
                        if output_key not in seen_output:
                            line_output = first_result.content_colored if enable_colors else first_result.line_content
                            
                            if prefix:
                                # Use tab as separator if -T and single prefix, colon if multiple
                                if args.tab_prefix and len(prefix_parts) == 1:
                                    output = f'{prefix}\t{line_output}'
                                else:
                                    output = f'{prefix}:{line_output}'
                            else:
                                output = line_output
                            
                            # Debug output if requested
                            if args.debug == 'markup':
                                print('=== MARKUP ===', file=sys.stderr)
                                print(repr(first_result.content_marked), file=sys.stderr)
                                print('=== OUTPUT ===', file=sys.stderr)
                            
                            if not args.quiet:
                                print(output)
                            
                            seen_output.add(output_key)
                            match_count += 1
                            
                            # Check max_count
                            if args.max_count > 0 and match_count >= args.max_count:
                                break
        
        # Handle -l (files-with-matches): print only filenames with matches
        if args.files_with_matches:
            for filename in sorted(file_matches.keys()):
                if file_matches[filename]:  # Has matches
                    if enable_colors:
                        output = grepnet.colorizer.colorize_filename(filename)
                    else:
                        output = filename
                    print(output)
            if not file_matches or not any(file_matches.values()):
                sys.exit(1)
        # Handle -L (files-without-matches): print only filenames without matches
        elif args.files_without_matches:
            matched_files = set(f for f, lines in file_matches.items() if lines)
            # Extract filenames from input_sources (display_name is None for stdin without --label)
            all_files = set()
            for source in input_sources:
                all_files.add(source.display_name)
            unmatched = all_files - matched_files
            # Filter out None (stdin without --label) from output
            unmatched = {f for f in unmatched if f is not None}
            for filename in sorted(unmatched):
                if enable_colors:
                    output = grepnet.colorizer.colorize_filename(filename)
                else:
                    output = filename
                print(output)
            if not unmatched:
                sys.exit(1)
        # Handle -c (count): print count
        elif args.count:
            if not args.quiet:
                # Check if we have multiple files or need to show filenames
                has_multiple_files = len([s for s in input_sources if s.display_name is not None]) > 1
                
                if has_multiple_files or (file_matches and len(file_matches) > 1):
                    # Output per-file counts for multiple files
                    for filename in sorted(file_matches.keys()):
                        if file_matches[filename]:  # Only show files with matches
                            count = len(file_matches[filename])
                            if enable_colors:
                                colored_filename = grepnet.colorizer.colorize_filename(filename)
                                print(f"{colored_filename}:{count}")
                            else:
                                print(f"{filename}:{count}")
                else:
                    # Single file or stdin - just print count
                    print(match_count)
            if match_count == 0:
                sys.exit(1)
        else:
            # Normal mode
            if match_count == 0:
                sys.exit(1)
    except BrokenPipeError:
        # Handle pipe closure gracefully
        sys.exit(0)
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        if not args.no_messages:
            print(f'grepnet: {e}', file=sys.stderr)
        sys.exit(2)


if __name__ == '__main__':
    run()
