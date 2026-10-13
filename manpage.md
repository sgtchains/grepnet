% GREPNET(1) grepnet 5.0.0 | User Commands
% Network-aware grep for CIDR blocks and IP ranges
% 2026

# NAME

grepnet - Network-aware grep for CIDR blocks, IP ranges, and network addresses

# SYNOPSIS

**grepnet** [*OPTION*...] *PATTERN* [*FILE*...]

**grepnet** [*OPTION*...] **-f** *PATTERN_FILE* [*FILE*...]

# DESCRIPTION

grepnet searches for network addresses in text files using network algebra instead of substring matching. A pattern like `192.0.2.0/24` will match any IP address, CIDR block, subnet mask, or IP range that falls within that network—regardless of format.

This makes grepnet ideal for:

- **Network auditing**: Find all references to a network across multiple files and formats
- **Configuration review**: Locate which systems/applications reference specific networks
- **Security analysis**: Identify networks referenced in logs, configs, and documentation
- **Network extraction**: Extract and consolidate all networks mentioned in files

## Core Concept: Network Matching

Unlike grep which does text matching, grepnet understands network topology. These all represent the same /24 network:

```
192.0.2.0/24             (CIDR)
192.0.2.0 255.255.255.0  (Subnet mask)
192.0.2.0 0.0.0.255      (Inverse mask)
192.0.2.0-192.0.2.255    (IP range)
192.0.2.1                (Single IP within the network)
```

A single `grepnet '192.0.2.0/24'` command finds all of these.

# QUICK START

```bash
# Find any reference to a network
grepnet '192.0.2.0/24' config.txt

# Search from stdin
echo "server 192.0.2.1" | grepnet '192.0.2.0/24'

# Search multiple files recursively
grepnet -r '10.0.0.0/8' /etc/

# Show line numbers and only matching networks
grepnet -n -o '192.0.2.0/24' data.txt

# Extract all networks from a file
grepnet --extract config.txt

# Consolidate overlapping networks
grepnet --consolidate networks.txt
```

# PATTERN AND FILE INPUT

*PATTERN*
: Network pattern to search for (CIDR, IP range, subnet mask, bare IP, or file glob with `-f`)

*FILE*...
: Files to search. If omitted, reads from stdin.

**-P**, **--pattern** *PATTERN*
: Specify additional patterns (repeatable: `-P net1 -P net2`)

**-f**, **--patterns-file** *PATTERN_FILE*
: Read patterns from file, one per line (repeatable)

**-F**, **--input-file** *FILE*
: Specify input file explicitly (alternative to positional FILE arguments)

# MATCH TYPES

By default, grepnet finds all matches. Use these flags to filter by relationship type:

**-e**, **--equal**
: Match only networks that are exactly equal

**-s**, **--subset**
: Match only when file network is smaller than pattern (contained within)

**-S**, **--superset**
: Match only when file network is larger than pattern (contains pattern)

**-O**, **--overlap**
: Match only when networks partially overlap

**-v**, **--invert-match**
: Show lines that do NOT match (inverse logic)

**Example**: `grepnet -s '192.0.0.0/16' data.txt` finds all /24 or /25 networks within 192.0.0.0/16

# OUTPUT OPTIONS

**-o**, **--only-matching**
: Print only the matched networks, not the entire line

**-n**, **--line-number**
: Prefix output with 1-based line numbers

**-b**, **--byte-offset**
: Prefix output with 0-based byte offsets

**-H**, **--with-filename**
: Include filename in output (default when multiple files)

**--no-filename**
: Suppress filename in output

**-T**, **--initial-tab**
: Insert tab after line number/byte offset for alignment

**-c**, **--count**
: Print count of matching lines instead of lines

**-l**, **--files-with-matches**
: Print only filenames containing matches (useful for scripting)

**-L**, **--files-without-matches**
: Print only filenames without matches

**-q**, **--quiet**, **--silent**
: Suppress output (exit code only)

**--label** *LABEL*
: Display stdin as *LABEL* instead of "(standard input)"

**-m** *NUM*, **--max-count** *NUM*
: Stop searching after *NUM* matches

# CONTEXT OPTIONS

**-A** *NUM*, **--after-context** *NUM*
: Print *NUM* lines after each match

**-B** *NUM*, **--before-context** *NUM*
: Print *NUM* lines before each match

**-C** *NUM*, **--context** *NUM*
: Print *NUM* lines before and after each match

**--group-separator** *SEP*
: Print *SEP* between match groups (default: "--")

**--no-group-separator**
: Suppress group separator

**Example**: `grepnet -C 2 '192.0.2.0/24' config.txt` shows each match with 2 lines of context

# EXTRACTION AND CONSOLIDATION

**--extract**
: Extract all unique networks found in input (deduplicated)

**--consolidate**
: Consolidate overlapping and adjacent networks into larger blocks

**--show-content**
: Include original line content in extract/consolidate output

**--format** {**cidr**|**range**|**short-range**|**original**}
: Output format for networks (default: **cidr**)

- **cidr** - CIDR notation: `192.0.2.0/24`
- **range** - Full ranges: `192.0.2.0-192.0.2.255`
- **short-range** - Abbreviated ranges: `192.0.2.0-255`
- **original** - Original format as found (not available with `--consolidate`)

**Examples**:

```bash
# Extract all unique networks
grepnet --extract network_logs.txt

# Consolidate overlapping networks into larger blocks
grepnet --consolidate all_networks.txt

# Extract networks matching a pattern, output as ranges
grepnet --extract '10.0.0.0/8' systems.txt --format range

# Consolidate and show which lines contained each network
grepnet --consolidate --show-content config.txt
```

# FILTERING

**--exclude-string** *PATTERN*
: Exclude lines matching text pattern (regex; repeatable)

**--exclude-strings-file** *FILE*
: Load text patterns to exclude from file

**--exclude-cidr** *NETWORK*
: Exclude specific networks (repeatable)

**--exclude-cidrs-file** *FILE*
: Load networks to exclude from file

**Example**: `grepnet '192.0.0.0/16' data.txt --exclude-string 'deprecated'` finds all matches except lines marked deprecated

# FILE DISCOVERY

**-r**, **--recursive**
: Search directories recursively (don't follow symlinks)

**-R**, **--dereference-recursive**
: Search directories recursively (follow symlinks)

**--include** *GLOB*
: Include only files matching glob (repeatable)

**--exclude** *GLOB*
: Exclude files matching glob (repeatable)

**--exclude-from** *FILE*
: Load exclude patterns from file

**--exclude-dir** *PATTERN*
: Exclude directories matching glob (repeatable)

**Examples**:

```bash
# Search all .conf files recursively
grepnet -r --include '*.conf' '192.0.0.0/16' /etc/

# Search everywhere except backups
grepnet -r --exclude-dir 'backup' '10.0.0.0/8' /var/

# Search logs excluding old archive subdirectories
grepnet -r --exclude '*/old/*' '192.0.2.0/24' /var/log/
```

# PARSING CONTROL

**--parse-cidr** {**pattern**|**input**|**both**|**none**}
: Accept CIDR notation in patterns, input, both, or neither (default: **both**)

**--parse-netmask** {**pattern**|**input**|**both**|**none**}
: Accept subnet masks (default: **both**)

**--parse-hostmask** {**pattern**|**input**|**both**|**none**}
: Accept inverse/host masks (default: **both**)

**--parse-ranges** {**pattern**|**input**|**both**|**none**}
: Accept IP ranges (default: **both**)

**--range-format** {**long**|**short**|**both**|**none**}
: Accept long/short range formats (default: **both**)

Use these to restrict which network formats are recognized. For example, `--parse-ranges none` ignores range notation entirely.

# STRICT CIDR VALIDATION

**--strict-cidr** {**pattern**|**input**|**both**|**none**}
: Apply strict CIDR validation (default: **none**)

**--strict-cidr-action** {**fail**|**normalize**|**ignore**|**warn**}
: Action on invalid CIDR (default: **normalize**)

Strict mode rejects CIDRs with host bits set (e.g., `192.0.2.1/24` should be `192.0.2.0/24`).

- **fail** - Exit with error code 2
- **normalize** - Silently correct to network address
- **ignore** - Skip invalid CIDR
- **warn** - Print warning, then skip

# BINARY FILE HANDLING

**-a**, **--text**
: Treat all files as text

**-I**
: Skip binary files

**--binary-files** {**binary**|**text**|**without-match**}
: How to handle binary files (default: **binary**)

# COMMENT FILTERING

By default, grepnet ignores commented lines and removes inline comments from processing.

**--no-filter-comments**
: Include commented lines in search

Recognized comment markers: `#`, `!`, `--`, `//`, `;`

Cisco keywords like `remark` and `description` are also recognized as comment markers.

**Example**: 

```
# Default behavior: this line is ignored
server 192.0.2.1 # production

# With --no-filter-comments: both lines included
```

# COLOR OUTPUT

**--color** {**auto**|**always**|**never**}
: Use colored output (default: **auto** - colors on terminal, none when piped)

**GREPNET_COLORS**
: Environment variable to customize colors (space-separated `KEY=ANSI_CODE` pairs)

```bash
export GREPNET_COLORS="match=01;32 filename=35"
grepnet '192.0.2.0/24' *.txt
```

# DATA FORMATS

**-z**, **--null-data**
: Treat input/output as NUL-terminated records instead of newlines

**-Z**, **--null**
: Output NUL after filename instead of colon

Useful for safe handling of filenames with special characters: `grepnet -lZ '192.0.0.0/16' *.txt | xargs -0 cat`

# DEBUGGING

**--debug** [*FUNCTIONS*]
: Enable debug output to stderr

**--no-messages**
: Suppress error and warning messages

**--version**
: Show version and exit

**-h**, **--help**
: Show help and exit

# EXIT STATUS

0
: Matches found

1
: No matches found, or no matching files found (with `-l` / `-L`)

2
: Error occurred (invalid arguments, file not found, pattern error, etc.)

# EXAMPLES

## Basic Searching

```bash
# Find all references to a network in a file
grepnet '192.0.2.0/24' config.txt

# Match a single IP against a CIDR pattern
echo "192.0.2.50" | grepnet '192.0.2.0/24'

# Search multiple files
grepnet '10.0.0.0/8' server1.txt server2.txt server3.txt
```

## Multiple Patterns

```bash
# Search for either network
grepnet -P '192.0.2.0/24' -P '10.0.0.0/8' data.txt

# Read patterns from file
grepnet -f allowed_networks.txt config.txt
```

## Match Type Filtering

```bash
# Find only exact matches
grepnet -e '192.0.2.0/24' networks.txt

# Find networks contained within the pattern
grepnet -s '192.0.0.0/16' all_networks.txt

# Find networks that contain the pattern
grepnet -S '192.0.2.1' subnets.txt
```

## Output Formatting

```bash
# Show line numbers
grepnet -n '192.0.2.0/24' config.txt

# Show only the matched networks
grepnet -o '192.0.2.0/24' data.txt

# Count matching lines
grepnet -c '192.0.2.0/24' *.txt

# Show only filenames with matches
grepnet -l '192.0.0.0/16' *.conf
```

## Context Display

```bash
# Show 2 lines of context around matches
grepnet -C 2 '192.0.2.0/24' config.txt

# Show 1 line before, 3 lines after
grepnet -B 1 -A 3 '192.0.2.0/24' audit.log

# Context without group separator
grepnet -C 1 --no-group-separator '192.0.2.0/24' file.txt
```

## Network Extraction

```bash
# Extract all unique networks from file
grepnet --extract firewall_rules.txt

# Extract networks matching a pattern
grepnet --extract -P '192.0.0.0/16' all_networks.txt

# Consolidate overlapping networks
grepnet --consolidate all_subnets.txt

# Output consolidated networks as ranges
grepnet --consolidate --format range networks.txt

# Extract and show source lines
grepnet --extract --show-content config.txt
```

## Exclusion

```bash
# Exclude deprecated networks
grepnet --exclude-string 'deprecated' '192.0.0.0/16' config.txt

# Exclude specific network from results
grepnet --exclude-cidr '192.0.2.0/25' '192.0.2.0/24' data.txt

# Exclude networks from file
grepnet --exclude-cidrs-file banned.txt '0.0.0.0/0' networks.txt
```

## Recursive Searching

```bash
# Find all references in configuration directory
grepnet -r '192.0.0.0/16' /etc/

# Include only .conf and .yaml files
grepnet -r --include '*.conf' --include '*.yaml' '10.0.0.0/8' /etc/

# Exclude backup directories
grepnet -r --exclude-dir 'backup' '192.0.2.0/24' /var/

# Search logs, exclude archived subdirectories
grepnet -r --exclude '*/archive/*' '192.0.0.0/16' /var/log/
```

## Binary File Handling

```bash
# Process binary files as text
grepnet -a '192.0.2.0/24' data.bin

# Report binary matches without displaying content
grepnet --binary-files without-match '192.0.0.0/16' *.bin
```

## Advanced Combinations

```bash
# Extract networks from pattern file, exclude deprecated, consolidate
grepnet --extract -f allowed.txt --exclude-strings-file deprecated.txt \
  --consolidate --format range config.txt

# Recursive search with context, line numbers, and colors
grepnet -rn -C 2 --color always '192.0.2.0/24' /etc/

# Find networks in logs, exclude internal, show counts per file
grepnet -rc --exclude-cidr '10.0.0.0/8' '192.0.0.0/16' /var/log/*.txt
```

# COMMON PATTERNS

**Security audits**:
```bash
# Find all external networks referenced
grepnet -r --exclude-cidr '10.0.0.0/8' --exclude-cidr '172.16.0.0/12' \
  --exclude-cidr '192.168.0.0/16' '0.0.0.0/0' /etc/
```

**Configuration extraction**:
```bash
# Extract all networks from config files and consolidate
find /etc -name '*.conf' | xargs grepnet --extract --consolidate --format range
```

**Network monitoring**:
```bash
# Check for changes to allowed networks
grepnet --extract -f current.txt config.txt > new.txt
diff allowed.txt new.txt
```

**Compliance checking**:
```bash
# Verify no systems reference banned networks
if grepnet --exclude-cidrs-file banned.txt '0.0.0.0/0' *.txt > /dev/null; then
  echo "FAIL: Banned networks found"
fi
```

# ENVIRONMENT VARIABLES

**GREPNET_COLORS**
: Customize output colors (space-separated KEY=ANSI_CODE pairs)

**Example**: `export GREPNET_COLORS="match=01;32 fn=35"`

# AUTHOR

GrepNet Contributors

# COPYRIGHT

GrepNet is released under the MIT License.

# SEE ALSO

grep(1), awk(1), ipcalc(1), cidr(1)
