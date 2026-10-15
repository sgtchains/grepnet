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
192.0.2.0-1              (Short-range: first and last address)
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

**-u**, **--unmatched**
: Include networks that don't match any pattern (for use with other match type flags)

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

**-L**, **--files-without-match**
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

**--fill-pct** *N*
: Allow consolidation to fill gaps up to N% of network size (only with `--consolidate`; range 0-100)

- Finds the smallest supernet for each network where gap_ratio ≤ N%
- Single-pass: fill-pct applies once per extracted network, then networks merge via `collapse_addresses()`
- Examples: `--fill-pct=50` allows up to 50% gap filling; `--fill-pct=0` disallows any gap

**--show-content**
: Include original line content in extract/consolidate output

**--format** {**cidr**|**range**|**short-range**|**ips**|**original**}
: Output format for networks (default: **cidr**)

- **cidr** - CIDR notation: `192.0.2.0/24`
- **range** - Full ranges: `192.0.2.0-192.0.2.255`
- **short-range** - Abbreviated ranges: `192.0.2.0-255` (IPv4 only, last octet)
- **ips** - Individual IP addresses, one per line (only with `--consolidate`)
- **original** - Original format as found (not available with `--consolidate`)

**Examples**:

```bash
# Extract all unique networks
grepnet --extract network_logs.txt

# Consolidate overlapping networks into larger blocks
grepnet --consolidate all_networks.txt

# Consolidate with gap filling (up to 50%)
grepnet --consolidate --fill-pct=50 network_ranges.txt

# Extract networks matching a pattern, output as ranges
grepnet --extract '10.0.0.0/8' systems.txt --format range

# Consolidate and output individual IPs
grepnet --consolidate --format ips networks.txt

# Consolidate and show which lines contained each network
grepnet --consolidate --show-content config.txt

# Combine fill-pct with IP list output
grepnet --consolidate --fill-pct=50 --format ips network_ranges.txt
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

**--exclude-cidr-behaviour** {**subset**|**subset-strict**|**superset**|**superset-strict**|**equals**|**related**|**cut**}
: How to match excluded networks (default: **subset**)

Control how excluded networks are matched:

- **subset** (⊆): Exclude networks contained within excluded CIDR, including exact matches (default)
- **subset-strict** (⊂): Exclude networks strictly contained within excluded CIDR, excluding exact matches
- **superset** (⊇): Exclude networks that contain excluded CIDR, including exact matches
- **superset-strict** (⊃): Exclude networks strictly containing excluded CIDR, excluding exact matches
- **equals**: Exclude only exact matches
- **related**: Exclude any network that touches, contains, or is contained by excluded CIDR
- **cut**: Remove excluded network and return non-overlapping remainder blocks

**Examples**:
- `--exclude-cidr-behaviour=subset --exclude-cidr 192.0.0.0/16` excludes `192.0.2.0/24` and `192.0.0.0/16` but not `10.0.0.0/8`
- `--exclude-cidr-behaviour=subset-strict --exclude-cidr 192.0.0.0/16` excludes `192.0.2.0/24` but NOT `192.0.0.0/16` or `10.0.0.0/8`
- `--exclude-cidr-behaviour=superset --exclude-cidr 192.0.2.0/24` excludes `192.0.0.0/16` and `192.0.2.0/24` but not `10.0.0.0/8`
- `--exclude-cidr-behaviour=superset-strict --exclude-cidr 192.0.2.0/24` excludes `192.0.0.0/16` but NOT `192.0.2.0/24` or `10.0.0.0/8`
- `--exclude-cidr-behaviour=cut --exclude-cidr 192.0.2.4/30 --exclude-cidr 192.0.2.0/24` returns gap-fill blocks

**--exclude-string** example: `grepnet '192.0.0.0/16' data.txt --exclude-string 'deprecated'` finds all matches except lines marked deprecated

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

**--parse-bare-ip** {**pattern**|**input**|**both**|**none**}
: Accept single IP addresses without CIDR notation (default: **both**)

**--range-format** {**long**|**short**|**both**|**none**}
: Accept long/short range formats (default: **both**)

Use these to restrict which network formats are recognized. For example:
- `--parse-ranges none` ignores range notation entirely
- `--parse-bare-ip input` only accepts bare IPs in input files (not in patterns)
- `--parse-bare-ip none` requires explicit CIDR notation (e.g., `192.0.2.0/32` instead of `192.0.2.0`)

# PREFIX LENGTH FILTERING

**--ipv4-shorter-than** *N*
: Include only IPv4 networks with prefix length < N

**--ipv4-longer-than** *N*
: Include only IPv4 networks with prefix length > N

**--ipv6-shorter-than** *N*
: Include only IPv6 networks with prefix length < N

**--ipv6-longer-than** *N*
: Include only IPv6 networks with prefix length > N

Filter extracted or consolidated networks by prefix length (CIDR mask size). Useful for finding smaller subnets or larger aggregates.

**Examples**:
- `--ipv4-longer-than=24` - Only networks with /25 or smaller (more specific)
- `--ipv4-shorter-than=16` - Only networks with /0 to /15 (less specific)
- `--ipv4-longer-than=24 --ipv4-shorter-than=32` - Networks between /25 and /31
- `--ipv6-longer-than=64` - Only IPv6 with /65 or longer

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

## Exclusion with Strict Behavior

```bash
# Default subset: Exclude 192.0.2.0/24 AND 192.0.0.0/16, but not 10.0.0.0/8
grepnet --exclude-cidr '192.0.0.0/16' '0.0.0.0/0' networks.txt

# Strict subset: Exclude only 192.0.2.0/24, NOT 192.0.0.0/16 (exact match)
grepnet --exclude-cidr-behaviour subset-strict --exclude-cidr '192.0.0.0/16' '0.0.0.0/0' networks.txt

# Default superset: Exclude 192.0.0.0/16 AND 192.0.2.0/24, but not 10.0.0.0/8
grepnet --exclude-cidr-behaviour superset --exclude-cidr '192.0.2.0/24' '0.0.0.0/0' networks.txt

# Strict superset: Exclude only 192.0.0.0/16, NOT 192.0.2.0/24 (exact match)
grepnet --exclude-cidr-behaviour superset-strict --exclude-cidr '192.0.2.0/24' '0.0.0.0/0' networks.txt
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
: Customize output colors (space-separated `KEY=ANSI_CODE` pairs)

Supported color keys:

- `fn`: Filename (default: 35 = magenta)
- `ln`: Line number (default: 32 = green)
- `bn`: Byte offset (default: 32 = green)
- `se`: Separator (default: 36 = cyan)
- `sl`: Selected line background (default: 0 = none)
- `cx`: Context line (default: 0 = none)
- `mt`: Match text color (default: 0 = none)
- `ms`: Match separator (default: 0 = none)
- `mc`: Match colon (default: 0 = none)
- `me`: EQUALS match type (default: 01;32 = bright green)
- `mb`: SUBSET match type (default: 01;34 = bright blue)
- `mS`: SUPERSET match type (default: 01;33 = bright yellow)
- `mo`: OVERLAP match type (default: 01;31 = bright red)
- `mu`: UNMATCHED type (default: 0 = none)
- `mn`: Normalized CIDR (default: 04 = underline)

ANSI codes are SGR (Select Graphic Rendition) values. Common values:
- `0` = reset/no color
- `01` = bold
- `04` = underline
- `31-37` = foreground colors (red, green, yellow, blue, magenta, cyan, white)
- Combine with semicolons: `01;32` = bold green

**Example**:
```bash
export GREPNET_COLORS="fn=35 me=01;31 mb=01;36"
grepnet '192.0.2.0/24' *.txt
```

# AUTHOR

Larry M. Smith <sgtchains@att.com>

# SEE ALSO

grep(1), awk(1), ipcalc(1), cidr(1)

**Related tools:**
- grepcidr (Jem Berkes' version): https://www.pc-tools.net/unix/grepcidr/
- grepcidr3 (John Levine's version): https://github.com/jrlevine/grepcidr3
