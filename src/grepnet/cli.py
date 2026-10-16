"""GrepNet command-line interface."""

import sys
import argparse
import re
import signal
from collections import deque

# Version string - same in bundled and packaged versions
__version__ = '5.0.0'

# Handle CTRL-C gracefully without error output
def _handle_sigint(signum, frame):
    """Exit cleanly on CTRL-C without traceback."""
    sys.exit(130)

signal.signal(signal.SIGINT, _handle_sigint)

# In bundled version, these classes are already defined in current namespace
# In packaged version, import from grepnet
try:
    import grepnet as grepnet_module
    from grepnet import GrepNet, InputDiscovery, MatchType
    from grepnet.input import InputSource
except ImportError:
    # Running as bundled single file - everything is in current namespace
    # Classes will be defined later in the same file
    grepnet_module = None


def error(message, exit_code=2):
    """Standard error handler - prints message to stderr and exits."""
    print(f"grepnet: error: {message}", file=sys.stderr)
    sys.exit(exit_code)


class GrepNetArgumentParser(argparse.ArgumentParser):
    """Custom ArgumentParser that adds help hint to all error messages."""
    
    def error(self, message):
        """Print error message with usage and help hint, matching grep format."""
        self.exit(2, f"{self.prog}: error: {message}\nUsage: {self.format_usage().split('usage: ')[1]}Try '{self.prog} --help' for more information.\n")


class FilterCommentsValidator:
    """Validator for --no-filter-comments values."""
    VALID_CHOICES = {'pattern', 'input', 'both', 'none'}
    
    def __call__(self, value):
        if value not in self.VALID_CHOICES:
            msg = f'invalid choice: {value!r} (choose from {", ".join(sorted(self.VALID_CHOICES))})'
            raise argparse.ArgumentTypeError(msg)
        return value


class NoFilterCommentsAction(argparse.Action):
    """Custom action for --no-filter-comments that handles optional values."""
    def __init__(self, option_strings, dest, const='both', **kwargs):
        super().__init__(option_strings, dest, nargs='?', const=const, **kwargs)
    
    def __call__(self, parser, namespace, values, option_string=None):
        if values is None:
            setattr(namespace, self.dest, self.const)
        else:
            validator = FilterCommentsValidator()
            try:
                setattr(namespace, self.dest, validator(values))
            except argparse.ArgumentTypeError as e:
                raise argparse.ArgumentError(self, str(e))


def run():
    """Main CLI entry point."""
    parser = GrepNetArgumentParser(
        prog='grepnet',
        description='Network-aware grep for CIDR blocks and IP ranges',
        usage='%(prog)s [OPTION...] PATTERN [FILE...]  OR  %(prog)s [OPTION...] -f PATTERNS_FILE [FILE...]',
        allow_abbrev=False,
    )
    
    # Version
    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__}',
    )
    
    # Patterns
    parser.add_argument(
        '-P',
        '--pattern',
        action='append',
        dest='pattern_flags',
        help='Specify pattern (can be used multiple times)',
    )
    parser.add_argument(
        '-f',
        '--patterns-file',
        action='store',
        dest='pattern_file',
        help='Read patterns from file (one per line)',
    )
    
    # Matching options
    parser.add_argument(
        '-e',
        '--equal',
        action='store_true',
        help='Match equal networks',
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
        '--silent',
        action='store_true',
        dest='quiet',
        help='Alias for --quiet',
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
        '-Z',
        '--null',
        action='store_true',
        dest='null_output',
        help='Output NUL byte instead of newline after filename',
    )
    parser.add_argument(
        '-z',
        '--null-data',
        action='store_true',
        dest='null_data',
        help='Treat input/output data as NUL-terminated records',
    )
    parser.add_argument(
        '-T',
        '--initial-tab',
        action='store_true',
        dest='initial_tab',
        help='Insert tab after prefixes for alignment',
    )
    parser.add_argument(
        '-l',
        '--files-with-matches',
        action='store_true',
        help='Print only files with matches',
    )
    parser.add_argument(
        '-L',
        '--files-without-match',
        action='store_true',
        help='Print only files without matches',
    )
    parser.add_argument(
        '-a',
        '--text',
        action='store_true',
        dest='text_mode',
        help='Process binary files as text (equivalent to --binary-files=text)',
    )
    parser.add_argument(
        '-I',
        action='store_true',
        dest='no_binary_match',
        help='Binary files are treated as non-matching (equivalent to --binary-files=without-match)',
    )
    
    # Comment handling
    parser.add_argument(
        '--no-filter-comments',
        action=NoFilterCommentsAction,
        default=None,
        help='Do not filter comments (pattern, input, both, or none; default: both)',
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
        '--parse-bare-ip',
        choices=['pattern', 'input', 'both', 'none'],
        default='both',
        help='Where to accept single IP address (default: both)',
    )
    parser.add_argument(
        '--scan-mask',
        choices=['pattern', 'input', 'both', 'none'],
        default='both',
        help='Scan peek buffer for netmask vs hostmask format hints (default: both)',
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
        '--fill-pct',
        type=int,
        default=None,
        metavar='N',
        help='Allow consolidation to fill gaps up to N%% (only with --consolidate)',
    )
    parser.add_argument(
        '--fill-boundary',
        action='store_true',
        help='Allow consolidation to fill boundary addresses (only with --consolidate)',
    )
    parser.add_argument(
        '--show-content',
        action='store_true',
        help='Show line content in extract/consolidate mode',
    )
    parser.add_argument(
        '--format',
        choices=['cidr', 'range', 'short-range', 'ips', 'original'],
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
        '--input-file',
        action='append',
        dest='input_files_explicit',
        help='Specify input file explicitly (repeatable)',
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
    parser.add_argument(
        '--exclude-cidr-behavior',
        choices=['subset', 'subset-strict', 'superset', 'superset-strict', 'equals', 'related', 'cut'],
        default='subset',
        dest='exclude_cidr_behavior',
        help='CIDR exclusion behavior: subset (default), subset-strict, superset, superset-strict, equals, related, or cut',
    )
    
    # Prefix length filtering options
    parser.add_argument(
        '--ipv4-shorter-than',
        type=int,
        dest='ipv4_shorter_than',
        help='Include only IPv4 networks with prefix length < N (for --extract/--consolidate)',
    )
    parser.add_argument(
        '--ipv4-longer-than',
        type=int,
        dest='ipv4_longer_than',
        help='Include only IPv4 networks with prefix length > N (for --extract/--consolidate)',
    )
    parser.add_argument(
        '--ipv6-shorter-than',
        type=int,
        dest='ipv6_shorter_than',
        help='Include only IPv6 networks with prefix length < N (for --extract/--consolidate)',
    )
    parser.add_argument(
        '--ipv6-longer-than',
        type=int,
        dest='ipv6_longer_than',
        help='Include only IPv6 networks with prefix length > N (for --extract/--consolidate)',
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
    
    # Positional arguments
    parser.add_argument(
        'positional_args',
        nargs='*',
        help='PATTERN [FILE...] or FILE... (with -f)',
    )
    
    args = parser.parse_intermixed_args()
    
    # Handle flag precedence: if both -H and --no-filename are specified,
    # whichever came last in the command line takes precedence
    if args.with_filename and args.no_filename:
        # Check which flag came last in sys.argv
        h_index = -1
        no_filename_index = -1
        for i, arg in enumerate(sys.argv):
            if arg == '-H' or arg == '--with-filename':
                h_index = i
            elif arg == '--no-filename':
                no_filename_index = i
        # The flag that appears last in sys.argv wins
        if h_index > no_filename_index:
            args.no_filename = False  # -H wins
        else:
            args.with_filename = False  # --no-filename wins
    
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
            # Use InputSource for pattern files - exact same extraction process as input files
            # This ensures pattern files respect -z (null-delimited) and binary file handling
            if args.pattern_file == '-':
                pattern_source = InputSource('stdin', null_delimited=args.null_data)
            else:
                pattern_source = InputSource('file', file_path=args.pattern_file, null_delimited=args.null_data)
            
            for line_num, line_content, byte_offset in pattern_source.lines():
                # Add all non-empty lines to patterns list (without pre-filtering)
                # Comment handling is done by the extraction pipeline in GrepNet.parser
                if line_content:
                    patterns.append(line_content)
            
            # Empty pattern file is allowed - will match nothing (or extract all in extract mode)
        except IOError as e:
            if not args.no_messages:
                print(f'grepnet: Cannot read pattern file {args.pattern_file}: {e}', file=sys.stderr)
            sys.exit(2)
        except KeyboardInterrupt:
            sys.exit(130)
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
    if context_flags_provided and (args.files_with_matches or args.files_without_match or args.extract or args.consolidate):
        if not args.no_messages:
            print('grepnet: error: context flags (-B/-A/-C) cannot be used with -l, -L, --extract, or --consolidate', file=sys.stderr)
        sys.exit(2)
    
    # Handle binary file flags: -a (--text), -I, and --binary-files
    # Precedence: explicit binary flags override --binary-files
    if args.text_mode:
        # -a, --text: process binary files as text
        args.binary_files = 'text'
    elif args.no_binary_match:
        # -I: treat binary files as non-matching
        args.binary_files = 'without-match'
    # else: use the default or explicitly set --binary-files value
    
    # Force text mode for -z flag: NUL-delimited files are detected as binary due to NUL bytes,
    # but -z means the user explicitly wants to treat them as text records separated by NUL
    if args.null_data:
        args.binary_files = 'text'
    
    # If no patterns found from any source (args.pattern_flags or positional), error
    # But allow it if pattern file was provided (even if empty), or if --extract/--consolidate
    # Only error if user provided NO pattern source at all in normal grep mode
    has_pattern_source = args.pattern_file or args.pattern_flags or (args.positional_args and not args.extract and not args.consolidate and not (args.files_with_matches or args.files_without_match))
    
    if not patterns and not has_pattern_source and not args.extract and not args.consolidate:
        if not args.no_messages:
            parser.error('no patterns to search for')
    
    # Validate --exclude-cidr-behavior=cut: only valid with --extract or --consolidate
    if args.exclude_cidr_behavior == 'cut' and not (args.extract or args.consolidate):
        if not args.no_messages:
            print('grepnet: error: --exclude-cidr-behavior=cut requires --extract or --consolidate', file=sys.stderr)
        sys.exit(2)
    
    # Validate --fill-pct: only valid with --consolidate
    if args.fill_pct is not None and not args.consolidate:
        if not args.no_messages:
            print('grepnet: error: --fill-pct requires --consolidate', file=sys.stderr)
        sys.exit(2)
    
    # Validate --fill-boundary: only valid with --consolidate
    if args.fill_boundary and not args.consolidate:
        if not args.no_messages:
            print('grepnet: error: --fill-boundary requires --consolidate', file=sys.stderr)
        sys.exit(2)
    
    # Validate prefix length filters: only valid with --extract or --consolidate
    prefix_length_flags = [
        ('--ipv4-shorter-than', args.ipv4_shorter_than),
        ('--ipv4-longer-than', args.ipv4_longer_than),
        ('--ipv6-shorter-than', args.ipv6_shorter_than),
        ('--ipv6-longer-than', args.ipv6_longer_than),
    ]
    
    for flag_name, flag_value in prefix_length_flags:
        if flag_value is not None and not (args.extract or args.consolidate):
            if not args.no_messages:
                print(f'grepnet: error: {flag_name} requires --extract or --consolidate', file=sys.stderr)
            sys.exit(2)
        # Validate range: 0-32 for IPv4, 0-128 for IPv6
        if flag_value is not None:
            if 'ipv4' in flag_name and not (0 <= flag_value <= 32):
                if not args.no_messages:
                    print(f'grepnet: error: {flag_name} must be between 0 and 32', file=sys.stderr)
                sys.exit(2)
            elif 'ipv6' in flag_name and not (0 <= flag_value <= 128):
                if not args.no_messages:
                    print(f'grepnet: error: {flag_name} must be between 0 and 128', file=sys.stderr)
                sys.exit(2)
    
    # Determine match type filter based on -e, -s, -S, -O, -u flags
    match_type_filter = []
    has_explicit_match_type = False
    
    if args.equal:
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
    
    # Set output record delimiter based on -z flag
    output_delimiter = '\0' if args.null_data else '\n'
    
    # Load exclude strings from file if provided (BEFORE creating GrepNet instance)
    if args.exclude_strings_file:
        try:
            # Use InputSource for exclude files - exact same extraction process as input files
            exclude_source = InputSource('file', file_path=args.exclude_strings_file, null_delimited=args.null_data)
            for line_num, line_content, byte_offset in exclude_source.lines():
                if line_content and not line_content.lstrip().startswith('#'):
                    if args.exclude_strings is None:
                        args.exclude_strings = []
                    args.exclude_strings.append(line_content)
        except IOError as e:
            if not args.no_messages:
                print(f'grepnet: Cannot read exclude strings file {args.exclude_strings_file}: {e}', file=sys.stderr)
            sys.exit(2)
        except KeyboardInterrupt:
            sys.exit(130)
    
    # Load exclude CIDR patterns from file if provided (BEFORE creating GrepNet instance)
    if args.exclude_cidrs_file:
        try:
            # Use InputSource for exclude files - exact same extraction process as input files
            exclude_source = InputSource('file', file_path=args.exclude_cidrs_file, null_delimited=args.null_data)
            for line_num, line_content, byte_offset in exclude_source.lines():
                if line_content and not line_content.lstrip().startswith('#'):
                    if args.exclude_cidrs is None:
                        args.exclude_cidrs = []
                    args.exclude_cidrs.append(line_content)
        except IOError as e:
            if not args.no_messages:
                print(f'grepnet: Cannot read exclude CIDR file {args.exclude_cidrs_file}: {e}', file=sys.stderr)
            sys.exit(2)
        except KeyboardInterrupt:
            sys.exit(130)
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
        
        # Determine comment filtering behavior based on --no-filter-comments scope
        # Default (None): filter comments in both patterns and input
        # 'both': don't filter comments anywhere
        # 'input': don't filter input comments (but filter patterns)
        # 'pattern': don't filter pattern comments (but filter input)
        # 'none': filter comments everywhere (same as default)
        if args.no_filter_comments is None or args.no_filter_comments == 'none':
            # Default behavior: filter comments
            filter_comments_enabled = True
        elif args.no_filter_comments == 'both':
            # Don't filter comments anywhere
            filter_comments_enabled = False
        elif args.no_filter_comments == 'input':
            # Don't filter input comments (filter patterns instead)
            # TODO: This requires passing separate flags to GrepNet
            filter_comments_enabled = False
        elif args.no_filter_comments == 'pattern':
            # Don't filter pattern comments (filter input instead)
            # TODO: This requires passing separate flags to GrepNet
            filter_comments_enabled = True
        else:
            # Fallback to filtering enabled
            filter_comments_enabled = True
        
        grepnet = GrepNet(
            patterns=grepnet_patterns,
            filter_comments=filter_comments_enabled,
            strict_mode=(args.strict_cidr in ['pattern', 'both']),
            strict_cidr_action=args.strict_cidr_action,
            strict_cidr_mode=args.strict_cidr,
            parse_cidr=args.parse_cidr,
            parse_netmask=args.parse_netmask,
            parse_hostmask=args.parse_hostmask,
            parse_ranges=args.parse_ranges,
            parse_bare_ip=args.parse_bare_ip,
            scan_mask=args.scan_mask,
            range_format=args.range_format,
            enable_colors=enable_colors,
            match_type_filter=match_type_filter,
            invert_match=args.invert_match,
            show_unmatched=args.unmatched,
            debug=args.debug,
            exclude_strings=args.exclude_strings,
            exclude_cidrs=None,  # Will be set after parsing
            exclude_cidr_behavior=args.exclude_cidr_behavior,
            output_format=args.format if args.format else 'cidr',  # Default to 'cidr' if not provided
            binary_files=args.binary_files,
            ipv4_shorter_than=args.ipv4_shorter_than,
            ipv4_longer_than=args.ipv4_longer_than,
            ipv6_shorter_than=args.ipv6_shorter_than,
            ipv6_longer_than=args.ipv6_longer_than,
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
                # Use InputSource for exclude files - exact same extraction process as input files
                exclude_source = InputSource('file', file_path=args.exclude_from_file, null_delimited=args.null_data)
                for line_num, line_content, byte_offset in exclude_source.lines():
                    if line_content and not line_content.lstrip().startswith('#'):
                        if args.exclude_patterns is None:
                            args.exclude_patterns = []
                        args.exclude_patterns.append(line_content)
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
        null_delimited=args.null_data,
    )
    
    if not input_sources:
        parser.error('No input files specified and stdin is a terminal')
    
    # Auto-enable filename prefix for multiple files (unless --no-filename is set)
    # Count non-stdin files in input_sources
    file_count = len([s for s in input_sources if s.display_name is not None])
    if file_count > 1 and not args.files_without_match and not args.no_filename:
        args.with_filename = True
    
    if not input_sources:
        parser.error('No input files specified and stdin is a terminal')
    
    # Validate --format usage early (before search)
    # Only validate if --format was explicitly provided (args.format is not None)
    if args.format is not None:
        # Check for ips-specific constraint first
        if args.format == 'ips' and not args.consolidate:
            if not args.no_messages:
                print(f'grepnet: error: --format ips can only be used with --consolidate', file=sys.stderr)
            sys.exit(2)
        
        # General constraint: --format requires --extract or --consolidate
        if not (args.extract or args.consolidate):
            if not args.no_messages:
                print(f'grepnet: error: --format \'{args.format}\' can only be used with --extract or --consolidate', file=sys.stderr)
            sys.exit(2)
        
        # Cannot use 'original' with consolidate
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
            parser.error('no patterns to search for')
    
    # Run search
    try:
        if args.extract or args.consolidate:
            from ipaddress import IPv4Network, IPv6Network
            from grepnet.core.network_objects import ParsedExtraction
            
            # Validation: patterns must exist for extract/consolidate
            if not grepnet.parsed_patterns:
                # No patterns means no networks to extract
                sys.exit(1)
            
            # Use unified grepnet.search() interface for extraction
            # This replaces the old direct input loop pattern
            try:
                if args.extract:
                    # Extract mode: use grepnet.search(mode='extract')
                    networks_dict = grepnet.search(input_sources, mode='extract')
                    
                    if not networks_dict:
                        sys.exit(1)
                    
                    # Apply cut behavior if requested
                    if args.exclude_cidr_behavior == 'cut':
                        networks_dict = grepnet._apply_cut_exclusion(networks_dict)
                    
                    # Output extracted networks
                    for parsed_extraction, line_content in networks_dict.values():
                        # Apply exclusion filters (skip cut, as it was already applied)
                        if args.exclude_cidr_behavior != 'cut' and grepnet._check_extraction_excluded(parsed_extraction):
                            continue
                        
                        # Apply prefix length filters (after exclusion and cut)
                        if not grepnet._passes_prefix_length_filter(parsed_extraction.network):
                            continue
                        
                        formatted_net = grepnet.format_network(parsed_extraction)
                        if args.show_content and line_content:
                            print(f'{formatted_net} {line_content}', end=output_delimiter)
                        else:
                            print(formatted_net, end=output_delimiter)
                    
                    sys.exit(0)
                
                elif args.consolidate:
                    # Consolidate mode: use grepnet.search(mode='consolidate')
                    # Returns consolidated network dictionary
                    consolidated_dict = grepnet.search(input_sources, mode='consolidate', fill_pct=args.fill_pct, fill_boundary=args.fill_boundary)
                    
                    if not consolidated_dict:
                        sys.exit(1)
                    
                    # Apply cut behavior if requested
                    if args.exclude_cidr_behavior == 'cut':
                        # Convert consolidated_dict to extract format, apply cut, then convert back
                        extract_dict = {net: data for net, data in consolidated_dict.items()}
                        extract_dict = grepnet._apply_cut_exclusion(extract_dict)
                        consolidated_dict = extract_dict
                    
                    # Handle --format=ips: expand networks to individual IPs
                    if args.format == 'ips':
                        for net_obj, (parsed_ext, line_content) in consolidated_dict.items():
                            # Apply prefix length filters
                            if isinstance(net_obj, (IPv4Network, IPv6Network)):
                                if not grepnet._passes_prefix_length_filter(net_obj):
                                    continue
                            
                            # Expand network to all IPs
                            for ip_str in grepnet.expand_network_to_ips(net_obj):
                                print(ip_str, end=output_delimiter)
                        
                        sys.exit(0)
                    
                    # Output consolidated networks (standard formats)
                    for net_obj, (parsed_ext, line_content) in consolidated_dict.items():
                        # Create temporary ParsedExtraction wrapper for consolidated networks
                        if isinstance(net_obj, (IPv4Network, IPv6Network)):
                            temp_extraction = ParsedExtraction(
                                network=net_obj,
                                format_type='cidr_notation',
                                was_normalized=False,
                                matched_texts=[]
                            )
                        else:
                            # Range tuple - mark as range
                            temp_extraction = ParsedExtraction(
                                network=net_obj,
                                format_type='ipv4_range' if net_obj[0] <= 0xFFFFFFFF else 'ipv6_range',
                                was_normalized=False,
                                matched_texts=[]
                            )
                        
                        # Apply prefix length filters (after consolidation and cut)
                        if isinstance(net_obj, (IPv4Network, IPv6Network)):
                            if not grepnet._passes_prefix_length_filter(net_obj):
                                continue
                        
                        # format_network() handles output format conversion
                        formatted_net = grepnet.format_network(temp_extraction)
                        print(formatted_net, end=output_delimiter)
                    
                    sys.exit(0)
            
            except Exception as e:
                if not args.no_messages:
                    import traceback
                    print(f'grepnet: error during extract/consolidate: {e}', file=sys.stderr)
                    traceback.print_exc(file=sys.stderr)
                sys.exit(2)
        
        # Normal mode: process as standard search
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
            lines_output = set()  # Track which (filename, line_number) pairs we've already output (to avoid dupes)
            
            for result in grepnet.search(input_sources, yield_all_lines=True):
                current_line = result.line_number
                
                if result.is_match:
                    # Skip if we've already output this line in this file (handles multiple matches per line)
                    # Use (filename, line_number) as key to allow same line number in different files
                    if (result.filename, current_line) in lines_output:
                        continue
                    
                    # Check for gap between previous after-context and current before-context
                    if last_match_line is not None:
                        prev_context_end = last_match_line + args.after_context
                        curr_context_start = current_line - args.before_context
                        
                        # Gap exists if there's space between them (ranges don't overlap)
                        if prev_context_end < curr_context_start and not args.quiet and not args.no_group_separator:
                            print(args.group_separator, end=output_delimiter)
                    
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
                        
                        # Choose separator: tab for -T, null for -Z, colon for normal
                        if args.initial_tab and prefix_parts:
                            sep = '\t'
                        elif args.null_output:
                            sep = '\x00'
                        elif enable_colors:
                            sep = grepnet.colorizer.colorize_separator(':')
                        else:
                            sep = ':'
                        
                        prefix = sep.join(prefix_parts)
                        
                        if prefix:
                            # Use tab as separator if -T and single prefix, null for -Z, colon if multiple
                            ctx_prefix_count = 0
                            if args.with_filename and ctx_filename:
                                ctx_prefix_count += 1
                            if args.line_number:
                                ctx_prefix_count += 1
                            if args.initial_tab and ctx_prefix_count == 1:
                                output = f'{prefix}\t{ctx_content}'
                            elif args.null_output:
                                output = f'{prefix}\x00{ctx_content}'
                            else:
                                output = f'{prefix}:{ctx_content}'
                        else:
                            output = ctx_content
                        if not args.quiet:
                            print(output, end=output_delimiter)
                    
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
                    
                    if args.with_filename:
                        # Use default "(standard input)" label if filename is None (stdin)
                        display_name = filename if filename else "(standard input)"
                        filename_str = display_name if not enable_colors else display_name
                    if args.line_number:
                        line_num_str = (grepnet.colorizer.colorize_line_number(str(current_line))
                                      if enable_colors else str(current_line))
                    if args.byte_offset:
                        byte_offset_str = (grepnet.colorizer.colorize_byte_offset(str(result.byte_offset))
                                         if enable_colors else str(result.byte_offset))
                    
                    # Build prefix in the correct order for -T or normal mode
                    if args.initial_tab:
                        # For -T mode: byte, line, filename order with tab separators
                        if byte_offset_str:
                            prefix_parts.append(byte_offset_str)
                        if line_num_str:
                            prefix_parts.append(line_num_str)
                        if filename_str:
                            prefix_parts.append(filename_str)
                        sep = '\t'
                    else:
                        # For normal mode: filename, line, byte order with separators (null for -Z, colon for normal)
                        if filename_str:
                            prefix_parts.append(filename_str)
                        if line_num_str:
                            prefix_parts.append(line_num_str)
                        if byte_offset_str:
                            prefix_parts.append(byte_offset_str)
                        if args.null_output:
                            sep = '\x00'
                        elif enable_colors:
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
                                # Use tab as separator if -T and single prefix, null for -Z, colon if multiple
                                if args.initial_tab and len(prefix_parts) == 1:
                                    output = f'{prefix}\t{output_text}'
                                elif args.null_output:
                                    output = f'{prefix}\x00{output_text}'
                                else:
                                    output = f'{prefix}:{output_text}'
                            else:
                                output = output_text
                            if not args.quiet:
                                print(output, end=output_delimiter)
                            match_count += 1
                            if args.max_count > 0 and match_count >= args.max_count:
                                break
                    else:
                        # Full line output
                        line_output = result.content_colored if enable_colors else result.line_content
                        if prefix:
                            # Use tab as separator if -T and single prefix, null for -Z, colon if multiple
                            if args.initial_tab and len(prefix_parts) == 1:
                                output = f'{prefix}\t{line_output}'
                            elif args.null_output:
                                output = f'{prefix}\x00{line_output}'
                            else:
                                output = f'{prefix}:{line_output}'
                        else:
                            output = line_output
                        if not args.quiet:
                            print(output, end=output_delimiter)
                        match_count += 1
                    
                    # Track this (filename, line_number) pair for next iteration's gap check
                    lines_output.add((result.filename, current_line))
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
                    if args.initial_tab and prefix_parts:
                        sep = '\t'
                    else:
                        sep = ':'
                    
                    prefix = sep.join(prefix_parts)
                    
                    line_output = result.line_content.rstrip('\n')
                    if prefix:
                        # Use tab as separator if -T and single prefix, colon if multiple
                        if args.initial_tab and len(prefix_parts) == 1:
                            output = f'{prefix}\t{line_output}'
                        else:
                            output = f'{prefix}:{line_output}'
                    else:
                        output = line_output
                    if not args.quiet:
                        print(output, end=output_delimiter)
                    
                    after_count -= 1
                
                else:
                    # Before-context: add to buffer for next match
                    before_buf.append((result.filename, current_line, result.line_content.rstrip('\n')))
        
        else:
            # No context: original simple approach
            # Count results as we collect them so we can stop early with max_count
            collection_match_count = 0
            for result in grepnet.search(input_sources):
                if not result.is_match:
                    continue
                
                # Check if we've hit max_count limit BEFORE processing this result
                # This allows us to stop consuming from stdin/files early
                if args.max_count > 0 and collection_match_count >= args.max_count:
                    break
                    
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
                
                # Increment local counter to track when we've hit the limit
                collection_match_count += 1
        
        # Skip output phase if context mode already output all results
        if not use_context:
            # Handle binary files based on binary_files mode
            # For 'binary' mode (default): output "Binary file X matches" for normal output only
            # For 'without-match' mode (-I): same suppression
            # For 'text' mode (-a): output normally
            
            binary_files_with_output = set()  # Track which binary files we've already reported
            only_matching_output = set()  # Track (filename, line_number) pairs already output in -o mode
            
            # For "binary" or "without-match" mode, output binary file messages for NORMAL OUTPUT ONLY
            # (not for -c, -l, -L which have their own output handling)
            if (args.binary_files in ['binary', 'without-match']) and binary_files_matched:
                # Only output "Binary file X matches" if NOT in count/list mode
                if not (args.count or args.files_with_matches or args.files_without_match):
                    for filename in sorted(binary_files_matched.keys()):
                        if not args.quiet:
                            print(f'Binary file {filename} matches', end=output_delimiter)
                        binary_files_with_output.add(filename)
                # Count matches for all modes
                for filename in binary_files_matched.keys():
                    match_count += len(file_matches.get(filename, []))
            
            # Output normal results (skipping binary files if already handled)
            if not (args.binary_files == 'without-match' and binary_files_matched):
                for line_number in sorted(results_by_line.keys()):
                    # Check max_count before outputting this line
                    if args.max_count > 0 and match_count >= args.max_count:
                        break
                        
                    line_results = results_by_line[line_number]
                    
                    # Skip output for -l and -L (handled at end)
                    if args.files_with_matches or args.files_without_match:
                        continue
                    
                    # Process each (filename, result) pair and output it with its own prefix
                    for filename, result in line_results:
                        # In -o mode, process only the first result per (filename, line_number) pair
                        # because all results for the same line have identical marked content
                        if args.only_matching:
                            if (filename, line_number) in only_matching_output:
                                continue
                            only_matching_output.add((filename, line_number))
                        
                        # Skip line output for binary files in 'binary' mode (they were already reported as "Binary file X matches")
                        if result.is_binary_file and args.binary_files == 'binary':
                            # Only count the match, don't output line content
                            if not args.count:  # -c mode already counted above
                                match_count += 1
                            continue
                        
                        # For -c (count), just count and skip output
                        if args.count:
                            match_count += 1
                            continue
                        # Build prefix parts for this specific result
                        prefix_parts = []
                        byte_offset_str = None
                        line_num_str = None
                        filename_str = None
                        
                        if args.with_filename:
                            # Use default "(standard input)" label if filename is None (stdin)
                            display_name = filename if filename else "(standard input)"
                            filename_str = (grepnet.colorizer.colorize_filename(display_name)
                                          if enable_colors else display_name)
                        if args.line_number:
                            line_num_str = (grepnet.colorizer.colorize_line_number(str(line_number))
                                          if enable_colors else str(line_number))
                        if args.byte_offset:
                            byte_offset_str = (grepnet.colorizer.colorize_byte_offset(str(result.byte_offset))
                                             if enable_colors else str(result.byte_offset))
                        
                        # Build prefix in the correct order for -T or normal mode
                        if args.initial_tab:
                            # For -T mode: byte, line, filename order with tab separators
                            if byte_offset_str:
                                prefix_parts.append(byte_offset_str)
                            if line_num_str:
                                prefix_parts.append(line_num_str)
                            if filename_str:
                                prefix_parts.append(filename_str)
                            sep = '\t'
                        else:
                            # For normal mode: filename, line, byte order with separators (null for -Z, colon for normal)
                            if filename_str:
                                prefix_parts.append(filename_str)
                            if line_num_str:
                                prefix_parts.append(line_num_str)
                            if byte_offset_str:
                                prefix_parts.append(byte_offset_str)
                            if args.null_output:
                                sep = '\x00'
                            elif enable_colors:
                                sep = grepnet.colorizer.colorize_separator(':')
                            else:
                                sep = ':'
                        
                        prefix = sep.join(prefix_parts)
                        
                        # Output phase: -o mode (only matched texts)
                        if args.only_matching:
                            # Extract networks in order from the marked content
                            marked_content = result.content_marked
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
                                    # Use tab as separator if -T and single prefix, null for -Z, colon if multiple
                                    if args.initial_tab and len(prefix_parts) == 1:
                                        output = f'{prefix}\t{output_text}'
                                    elif args.null_output:
                                        output = f'{prefix}\x00{output_text}'
                                    else:
                                        output = f'{prefix}:{output_text}'
                                else:
                                    output = output_text
                                
                                if not args.quiet:
                                    print(output, end=output_delimiter)
                                match_count += 1
                                
                                # Check max_count after each match in -o mode
                                if args.max_count > 0 and match_count >= args.max_count:
                                    break
                        
                        # Normal mode (full line output)
                        else:
                            # Use (filename, line_number) as key to avoid dedup across files
                            output_key = (filename, line_number)
                            if output_key not in seen_output:
                                line_output = result.content_colored if enable_colors else result.line_content
                                
                                if prefix:
                                    # Use tab as separator if -T and single prefix, null for -Z, colon if multiple
                                    if args.initial_tab and len(prefix_parts) == 1:
                                        output = f'{prefix}\t{line_output}'
                                    elif args.null_output:
                                        output = f'{prefix}\x00{line_output}'
                                    else:
                                        output = f'{prefix}:{line_output}'
                                else:
                                    output = line_output
                                
                                # Debug output if requested
                                if args.debug == 'markup':
                                    print('=== MARKUP ===', file=sys.stderr)
                                    print(repr(result.content_marked), file=sys.stderr)
                                    print('=== OUTPUT ===', file=sys.stderr)
                                
                                if not args.quiet:
                                    print(output, end=output_delimiter)
                                
                                seen_output.add(output_key)
                                match_count += 1
                                
                                # Check max_count
                                if args.max_count > 0 and match_count >= args.max_count:
                                    break
        
        # Handle -l (files-with-matches): print only filenames with matches
        if args.files_with_matches:
            end_char = '\0' if args.null_output else '\n'
            for filename in sorted(file_matches.keys()):
                if file_matches[filename]:  # Has matches
                    if enable_colors:
                        output = grepnet.colorizer.colorize_filename(filename)
                    else:
                        output = filename
                    if not args.quiet:
                        print(output, end=end_char)
            if not file_matches or not any(file_matches.values()):
                sys.exit(1)
        # Handle -L (files-without-matches): print only filenames without matches
        elif args.files_without_match:
            matched_files = set(f for f, lines in file_matches.items() if lines)
            # Extract filenames from input_sources (display_name is None for stdin without --label)
            all_files = set()
            for source in input_sources:
                all_files.add(source.display_name)
            unmatched = all_files - matched_files
            # Filter out None (stdin without --label) from output
            unmatched = {f for f in unmatched if f is not None}
            end_char = '\0' if args.null_output else '\n'
            for filename in sorted(unmatched):
                if enable_colors:
                    output = grepnet.colorizer.colorize_filename(filename)
                else:
                    output = filename
                if not args.quiet:
                    print(output, end=end_char)
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
                                print(f"{colored_filename}:{count}", end=output_delimiter)
                            else:
                                print(f"{filename}:{count}", end=output_delimiter)
                else:
                    # Single file or stdin - just print count
                    print(match_count, end=output_delimiter)
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
            error(str(e))


if __name__ == '__main__':
    run()
