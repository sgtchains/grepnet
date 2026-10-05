% GREPNET(1) grepnet 3.0.0 | User Commands
% Network-aware grep for CIDR blocks and IP ranges
% 2026

# NAME

grepnet - Network-aware grep for CIDR blocks, IP ranges, and network addresses

# SYNOPSIS

**grepnet** [*OPTION*...] *PATTERN* [*FILE*...]

**grepnet** [*OPTION*...] **-f** *PATTERN_FILE* [*FILE*...]

# DESCRIPTION

grepnet searches for network addresses (CIDR blocks, IP ranges, subnet masks, and bare IPs) in text files. Unlike traditional text grep, grepnet uses network algebra to match addresses: a bare IP `192.0.2.1` will match a CIDR pattern `192.0.2.0/24` because the IP is within that network.

Network addresses can be expressed in multiple formats:
- CIDR notation: `192.0.2.0/24`, `2001:db8::/32`
- Subnet mask: `192.0.2.0 255.255.255.0`
- Inverse mask: `192.0.2.0 0.0.0.255`
- IP ranges: `192.0.2.0-192.0.2.255`
- Bare IPs: `192.0.2.1`, `2001:db8::1`

Patterns are parsed through the same extraction process as input files, ensuring consistency: a network expressed in a pattern will be recognized identically when found in a file.

# PATTERN AND FILE INPUT

## Positional Arguments

*PATTERN*
: Network pattern to search for (CIDR, range, subnet mask, IP, or bare address)

*FILE*...
: Files to search (repeatable; if omitted, reads from stdin)

## Pattern and File Options

**-P**, **--pattern** *PATTERN*
: Specify pattern (repeatable: `-P pattern1 -P pattern2`)

**-f**, **--file-patterns** *PATTERN_FILE*
: Read patterns from file (one per line; repeatable)

**-F**, **--file** *INPUT_FILE*
: Specify input file explicitly (repeatable; alternative to positional FILE)

# MATCH TYPE FLAGS

By default, all four match types are searched. Specify combinations to filter:

**-e**, **--equals**
: Match only networks that are exactly equal to pattern

**-s**, **--subset**
: Match only networks that are subsets of pattern (file is smaller)

**-S**, **--superset**
: Match only networks that are supersets of pattern (file is larger)

**-O**, **--overlap**
: Match only networks that partially overlap with pattern

**-u**, **--unmatched**
: Include networks that don't match any pattern (requires `-u` flag or disabled by default)

**-v**, **--invert-match**
: Invert match logic: show lines that do NOT match the current filter set

Default if none specified: EQUALS, SUBSET, SUPERSET, and OVERLAP

# OUTPUT FORMAT OPTIONS

**-o**, **--only-matching**
: Print only matched networks, not entire line

**-n**, **--line-number**
: Print 1-based line number prefix

**-b**, **--byte-offset**
: Print 0-based byte offset prefix

**-H**, **--with-filename**
: Print filename prefix (default when multiple files)

**--no-filename**
: Suppress filename in output

**-l**, **--files-with-matches**
: Print only filenames with matches (exit 1 if none found)

**-L**, **--files-without-matches**
: Print only filenames without matches (exit 1 if all found)

**-c**, **--count**
: Print count of matching lines instead of lines

**-m** *NUM*, **--max-count** *NUM*
: Stop after *NUM* matches

**-q**, **--quiet**, **--silent**
: Suppress output (exit code only)

**-T**, **--initial-tab**
: Insert tab after line number and byte offset prefixes

**-Z**, **--null**
: Use NUL character after filename instead of colon

**--label** *LABEL*
: Display stdin as *LABEL* instead of "(standard input)"

# CONTEXT AND GROUPING

**-A** *NUM*, **--after-context** *NUM*
: Print *NUM* lines after each match

**-B** *NUM*, **--before-context** *NUM*
: Print *NUM* lines before each match

**-C** *NUM*, **--context** *NUM*
: Print *NUM* lines before and after each match (equivalent to `-B NUM -A NUM`)

**--group-separator** *SEP*
: Print *SEP* between groups of matches when using context (default: "--")

**--no-group-separator**
: Suppress group separator output

# EXTRACTION AND CONSOLIDATION

**--extract**
: Extract all unique networks from input (deduplicated)

**--consolidate**
: Consolidate overlapping and adjacent networks into larger blocks

**--show-content**
: Show original line content in extract/consolidate output

**--format** {**cidr**|**range**|**short-range**|**original**}
: Network output format for extract/consolidate modes (default: **cidr**)

- **cidr**: Output as CIDR notation (e.g., `192.0.2.0/24`)
- **range**: Output as IP ranges (e.g., `192.0.2.0-192.0.2.255`)
- **short-range**: Abbreviated ranges for IPv4 (e.g., `192.0.2.0-255`)
- **original**: Output in original parsed format (cannot be used with `--consolidate`)

# PARSING CONTROL

**--parse-cidr** {**pattern**|**input**|**both**|**none**}
: Where to accept CIDR notation (default: **both**)

**--parse-netmask** {**pattern**|**input**|**both**|**none**}
: Where to accept subnet masks (default: **both**)

**--parse-hostmask** {**pattern**|**input**|**both**|**none**}
: Where to accept hostmasks/inverse masks (default: **both**)

**--parse-ranges** {**pattern**|**input**|**both**|**none**}
: Where to accept IP ranges (default: **both**)

**--range-format** {**long**|**short**|**both**|**none**}
: Range format acceptance: long-form, short-form, both, or none (default: **both**)

Options:
- **pattern** - Accept this format in patterns only
- **input** - Accept this format in input files only
- **both** - Accept this format in both patterns and input (default)
- **none** - Don't accept this format anywhere

# STRICT CIDR VALIDATION

**--strict-cidr** {**pattern**|**input**|**both**|**none**}
: Where to apply strict CIDR validation (default: **none**)

**--strict-cidr-action** {**fail**|**normalize**|**ignore**|**warn**}
: Action on CIDR validation error (default: **normalize**)

Strict mode rejects malformed CIDRs (e.g., `192.0.2.1/24` where host bits are set).

Actions:
- **fail** - Exit immediately with code 2
- **normalize** - Silently correct to network address (default: `192.0.2.1/24` → `192.0.2.0/24`)
- **ignore** - Skip malformed CIDR without processing
- **warn** - Print warning to stderr, then skip

# EXCLUSION FILTERING

**--exclude-string** *PATTERN*
: Exclude lines matching text pattern (PCRE regex; repeatable)

**--exclude-strings-file** *FILE*
: Load text patterns to exclude from file (one regex per line)

**--exclude-cidr** *NETWORK*
: Exclude networks matching CIDR/range/subnet (repeatable)

**--exclude-cidrs-file** *FILE*
: Load network patterns to exclude from file (one network per line)

Results are excluded if they match ANY text pattern OR ANY network pattern.

# FILE DISCOVERY

**-r**, **--recursive**
: Recursively search directories (do not follow symlinks)

**-R**, **--dereference-recursive**
: Recursively search directories (follow symlinks)

**--include** *GLOB*
: Include only files matching glob pattern (repeatable)

**--exclude** *GLOB*
: Exclude files matching glob pattern (repeatable)

**--exclude-from** *FILE*
: Load exclude patterns from file (one glob per line)

**--exclude-dir** *PATTERN*
: Exclude directories matching glob (repeatable)

# BINARY FILE HANDLING

**-a**, **--text**
: Process all files as text (ignore binary detection)

**-I**
: Treat binary files as non-matching

**--binary-files** {**binary**|**text**|**without-match**}
: How to handle binary files (default: **binary**)

- **binary** - Treat as binary data (no output, but counted as non-matching)
- **text** - Treat as text files
- **without-match** - Report "Binary file *FILE* matches" if matches found

# COMMENTS

**--no-filter-comments**
: Include commented lines in search (by default, lines starting with # are ignored)

# COLOR OUTPUT

**--color** {**auto**|**always**|**never**}
: Use colored output (default: **auto** - colors on terminal, none when piped)

Colors can be customized via **GREPNET_COLORS** environment variable.

# ENVIRONMENT VARIABLES

**GREPNET_COLORS**
: Customize output colors (space-separated `KEY=ANSI_CODE` pairs)

Available keys:
- `me=` - Match type equals (bright green)
- `mb=` - Match type subset (bright blue)
- `mS=` - Match type superset (bright yellow)
- `mo=` - Match type overlap (bright red)
- `mu=` - Match type unmatched (no color)
- `fn=` - Filename (magenta)
- `ln=` - Line number (green)
- `bn=` - Byte offset (green)
- `se=` - Separator (cyan)

ANSI codes: `01;32` (bright green), `01;34` (bright blue), `35` (magenta), etc.

Example: `export GREPNET_COLORS="me=01;32 mb=01;34 fn=35"`

# DEBUG AND DIAGNOSTIC

**--debug** [*FUNCTIONS*]
: Enable debug output to stderr (optional filter for specific functions)

**--no-messages**
: Suppress all error and warning messages

**-h**
: Show brief help and exit

**--help**
: Show full help text and exit

**--version**
: Show version and exit

# EXIT STATUS

0
: Matches found

1
: No matches found, or no matching files found (with `-l` / `-L`)

2
: Error occurred (invalid arguments, file not found, malformed CIDR in strict mode, etc.)

# EXAMPLES

## Basic Matching

```
# Search for a CIDR block
grepnet '192.0.2.0/24' config.txt

# Match any IP in the 10.0.0.0/8 network
grepnet '10.0.0.0/8' servers.txt

# Search from stdin
echo "server 192.0.2.1" | grepnet '192.0.2.0/24'
```

## Multiple Patterns and Match Types

```
# Search for either CIDR block
grepnet -P '192.0.2.0/24' -P '10.0.0.0/8' *.txt

# Match only exact CIDR equivalents
grepnet -e '192.0.2.0/24' networks.txt

# Match only subsets (networks smaller than pattern)
grepnet -s '192.0.0.0/16' data.txt

# Invert match: show lines NOT matching pattern
grepnet -v '192.0.2.0/24' *.txt
```

## Output Formatting

```
# Show line numbers
grepnet -n '192.0.2.0/24' config.txt

# Show only matched networks
grepnet -o '192.0.2.0/24' data.txt

# Count matches
grepnet -c '192.0.2.0/24' *.txt

# Show filenames only
grepnet -l '192.0.2.0/24' *.txt
```

## Context and Grouping

```
# Show 2 lines of context around matches
grepnet -C 2 '192.0.2.0/24' config.txt

# Show 1 line before, 3 lines after, with custom separator
grepnet -B 1 -A 3 --group-separator "---" '192.0.2.0/24' data.txt

# No group separator
grepnet -C 1 --no-group-separator '192.0.2.0/24' file.txt
```

## Extraction and Consolidation

```
# Extract all networks from file
grepnet --extract config.txt

# Extract only networks matching pattern
grepnet --extract -P '192.0.0.0/16' data.txt

# Consolidate overlapping networks
grepnet --consolidate networks.txt

# Output consolidated networks as ranges
grepnet --consolidate --format range networks.txt

# Show original format of extracted networks
grepnet --extract --format original mixed.txt
```

## Filtering and Exclusion

```
# Exclude specific network from results
grepnet --exclude-cidr '192.0.2.0/25' '192.0.2.0/24' networks.txt

# Exclude lines containing comment text
grepnet --exclude-string 'deprecated' config.txt

# Exclude networks from file
grepnet --exclude-cidrs-file excluded_nets.txt '192.0.0.0/16' data.txt
```

## File Discovery

```
# Recursively search directory
grepnet -r '192.0.2.0/24' /etc/

# Include only .conf files
grepnet -r --include '*.conf' '192.0.2.0/24' /etc/

# Exclude backup directories
grepnet -r --exclude-dir 'backup' '192.0.2.0/24' /var/
```

## Binary and Encoding Handling

```
# Treat binary files as text
grepnet -a '192.0.2.0/24' data.bin

# Show "Binary file matches" message for binary files
grepnet --binary-files without-match '192.0.2.0/24' *.bin
```

## Strict CIDR Validation

```
# Reject malformed CIDRs in patterns
grepnet --strict-cidr pattern --strict-cidr-action fail '192.0.2.1/24' data.txt

# Normalize malformed CIDRs in input files
grepnet --strict-cidr input --strict-cidr-action normalize '192.0.2.0/24' data.txt

# Warn about malformed CIDRs
grepnet --strict-cidr both --strict-cidr-action warn '192.0.2.0/24' data.txt
```

## Advanced Combinations

```
# Extract networks from pattern file, consolidate, exclude deprecated
grepnet --extract -f patterns.txt --exclude-strings-file deprecated.txt --format range data.txt

# Recursive search with context, line numbers, and color
grepnet -rn -C 1 --color always '192.0.2.0/24' /etc/

# Count matches per file, show only files with matches
grepnet -rc -l '10.0.0.0/8' *.txt
```

# SIMILAR COMMANDS

- grep(1) - Search text patterns (not network-aware)
- awk(1) - Text processing (more general-purpose)
- ipcalc(1) - IP address calculations
- whois(1) - IP address ownership lookup

# NOTES

Network comparison uses network algebra:

- **EQUALS**: Networks represent exactly the same address space
- **SUBSET**: File network is entirely contained within pattern (smaller)
- **SUPERSET**: File network entirely contains pattern (larger)
- **OVERLAP**: Networks partially overlap but neither contains the other

When multiple networks appear on the same line, they are all matched and highlighted individually.

Strict CIDR mode is off by default. Malformed CIDRs like `192.0.2.1/24` are silently normalized to `192.0.2.0/24` (permissive mode). Use `--strict-cidr` to enforce strict validation.

# AUTHOR

GrepNet Contributors

# COPYRIGHT

GrepNet is released under the MIT License.

# SEE ALSO

**grepnet-spec**(7) - Full GrepNet specification

Official documentation: https://github.com/grepnet/grepnet
