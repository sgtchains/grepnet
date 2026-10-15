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
192.0.2.0-255            (Short-range: octet-based notation)
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

Network extraction and consolidation are two related operations for analyzing and simplifying network data:

**Extraction** (`--extract`): Scans input and finds all unique network objects (CIDR blocks, IP ranges, subnets, individual IPs). Deduplicates by network value (same network in different formats counts as one). Useful for discovering what networks are referenced in files, configurations, or logs.

**Consolidation** (`--consolidate`): Merges overlapping and adjacent networks into larger blocks, reducing complexity. For example, `192.0.2.0/25` and `192.0.2.128/25` merge into `192.0.2.0/24`. This simplifies network inventories and highlights coverage gaps.

**Gap Filling** (`--fill-pct`): Optional consolidation enhancement. Instead of merging only adjacent networks, allows filling small gaps if the gap is ≤ N% of the combined network size. Useful for simplifying "nearly complete" network ranges. For example, with `--fill-pct=25`:
- `192.0.2.0/25` and `192.0.2.192/26` (gap of 64 IPs = 25% of /24) merge into `192.0.2.0/24`
- With `--fill-pct=10`: `192.0.2.0/25` and `192.0.2.224/26` (gap of 32 IPs = 12.5% of /24) do NOT merge (gap exceeds 10%)

**Output Formats**: Extracted/consolidated networks can be output in multiple formats (CIDR, IP ranges, short-ranges, individual IPs, or original format).

## Flags

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

Filtering allows you to narrow or refine search results by excluding networks or matches that don't meet your criteria. Two independent filtering approaches:

**Text-based filtering** (`--exclude-string`): Excludes individual network matches whose matched text contains a regex pattern. Useful for filtering by context (e.g., "deprecated", "testing", "archived"). Applied after network matching—a network match is excluded if its matched text matches the regex. If a line has no remaining matches after text filtering, the entire line is removed from output.

**Network-based filtering** (`--exclude-cidr`): Excludes network matches that have specific relationships to excluded CIDR blocks. The relationship is determined by `--exclude-cidr-behaviour`. Useful for filtering by network hierarchy (e.g., exclude all internal networks, keep only external references).

**Combining filters**: Text and network filters are independent and stackable:
- `--exclude-string 'deprecated' --exclude-cidr '192.168.0.0/16'` excludes matches where the text contains "deprecated" OR the network is in 192.168.0.0/16
- Multiple `--exclude-string` or `--exclude-cidr` flags accumulate (any match causes exclusion)

## Text Filtering

**--exclude-string** *PATTERN*
: Exclude network matches whose matched text matches regex PATTERN (repeatable)

**--exclude-strings-file** *FILE*
: Load text patterns to exclude from file

**Behavior**: For each network match found, test the matched text against each regex pattern. If any match, exclude that result. If a line's last network match is excluded by text filtering, the entire line is removed from output.

## Network Filtering

**--exclude-cidr** *NETWORK*
: Exclude specific networks (repeatable)

**--exclude-cidrs-file** *FILE*
: Load networks to exclude from file

**--exclude-cidr-behaviour** {**subset**|**subset-strict**|**superset**|**superset-strict**|**equals**|**related**|**cut**}
: How to match excluded networks (default: **subset**)

### Exclusion Behaviors

Control how excluded networks are matched:

- **subset** (⊆): Exclude networks contained within excluded CIDR, including exact matches (default)
  - Use when: Filtering by network hierarchy ("exclude this network and anything inside it")
  
- **subset-strict** (⊂): Exclude networks strictly contained within excluded CIDR, excluding exact matches
  - Use when: Filtering all subnets of a network but keeping the parent network itself
  
- **superset** (⊇): Exclude networks that contain excluded CIDR, including exact matches
  - Use when: Filtering broader networks ("exclude networks that encompass this range")
  
- **superset-strict** (⊃): Exclude networks strictly containing excluded CIDR, excluding exact matches
  - Use when: Filtering broader networks but keeping networks at the same level
  
- **equals**: Exclude only exact matches
  - Use when: Blacklisting specific networks
  
- **related**: Exclude any network that touches, contains, or is contained by excluded CIDR
  - Use when: Filtering all networks touching a specific range (strictest exclusion)
  
- **cut**: Remove excluded network and return non-overlapping remainder blocks
  - Use when: Carving out excluded ranges and returning only the gaps (e.g., whitelist by exclusion)

### Exclusion Examples

**Scenario 1: Filter internal networks from results**
```bash
# Exclude all private networks (default subset behavior)
grepnet --exclude-cidr '10.0.0.0/8' --exclude-cidr '172.16.0.0/12' \
  --exclude-cidr '192.168.0.0/16' '0.0.0.0/0' all_networks.txt
```

**Scenario 2: Keep only subnets of a network, not parent networks**
```bash
# Find subnets of 192.0.0.0/16, but exclude 192.0.0.0/16 itself
grepnet --extract --exclude-cidr-behaviour subset-strict \
  --exclude-cidr '192.0.0.0/16' networks.txt
```

**Scenario 3: Whitelist by exclusion (find only gaps)**
```bash
# Find networks NOT in allowed ranges (carve out allowed space)
grepnet --extract --consolidate --exclude-cidr-behaviour cut \
  --exclude-cidr '10.0.0.0/8' --exclude-cidr '192.168.0.0/16' all_networks.txt
```

### Cut Behavior Details

The `cut` behavior is unique: instead of filtering out matched networks, it returns the complement—the "gaps" left after removing excluded networks. Useful for:
- Finding unaccounted network space
- Whitelist-based filtering (define what's allowed, get everything else)
- Network carving (subdivide networks by removing sections)

Example:
```bash
# Input networks: 10.0.0.0/8
# Exclude: 10.10.0.0/16
# Result: 10.0.0.0/22, 10.0.4.0/22, ..., 10.10.0.0/16 (gap), ..., 10.255.0.0/22
grepnet --extract --exclude-cidr-behaviour cut --exclude-cidr '10.10.0.0/16' \
  --format cidr networks.txt
```

# FILE DISCOVERY

File discovery controls which files are scanned when searching directories. This is critical for large directory trees where you need to focus on specific file types or exclude large backup/archive sections.

**Default behavior**: When no include/exclude filters specified, all files in the directory tree are scanned.

**Include patterns** (`--include`): Whitelist files matching glob patterns. Only files matching at least one include pattern are scanned. Can be specified multiple times (OR'd together).

**Exclude patterns** (`--exclude`): Blacklist files matching glob patterns. Files matching any exclude pattern are skipped. Can be specified multiple times. Applied after include filtering.

**Directory-level exclusion** (`--exclude-dir`): Faster alternative to `--exclude`. Skips entire directories without traversing them. More efficient than glob patterns on deep directory trees.

**Symlink handling**:
- `-r` (default): Don't follow symlinks (safer, faster)
- `-R`: Follow symlinks (can cause infinite loops if circular links exist)

**Glob pattern syntax**: Uses standard glob wildcards:
- `*` matches anything except `/` (doesn't cross directory boundaries)
- `?` matches single character
- `[abc]` matches character class
- `**` matches any path including `/` (if supported)

**Example precedence**: 
```
Input: /var/log/2024/archived/app.log
--include '*.log' → Matches ✓
--exclude '*/archived/*' → Excluded ✗
Result: File NOT scanned
```

## Flags

**-r**, **--recursive**
: Search directories recursively (don't follow symlinks; faster, safer)

**-R**, **--dereference-recursive**
: Search directories recursively (follow symlinks; can cause infinite loops)

**--include** *GLOB*
: Include only files matching glob pattern (repeatable; patterns OR'd together)

**--exclude** *GLOB*
: Exclude files matching glob pattern (repeatable; patterns OR'd together)

**--exclude-from** *FILE*
: Load exclude patterns from file, one per line

**--exclude-dir** *PATTERN*
: Exclude directories matching glob pattern (repeatable; doesn't traverse excluded dirs)

## Common Patterns

**Configuration auditing**:
```bash
# Search only .conf and .yaml files
grepnet -r --include '*.conf' --include '*.yaml' '192.0.0.0/16' /etc/
```

**Log analysis**:
```bash
# Search logs excluding old archives and backups
grepnet -r --exclude-dir 'archive' --exclude-dir 'backup' \
  --exclude '*.gz' --exclude '*.zip' '192.0.2.0/24' /var/log/
```

**Backup exclusion**:
```bash
# Search everywhere except backups and cache
grepnet -r --exclude-dir '.git' --exclude-dir '__pycache__' \
  --exclude-dir 'node_modules' '10.0.0.0/8' /home/
```

**Whitelist-based scanning**:
```bash
# Only scan source code files
grepnet -r --include '*.py' --include '*.js' --include '*.go' \
  '192.0.0.0/16' src/
```

**Performance tip**: Use `--exclude-dir` instead of `--exclude` for large directories—it skips traversal entirely instead of checking each file.

# PARSING CONTROL

Parsing control allows you to restrict which network formats grepnet accepts. This is useful for:

- **Enforcing consistency**: Require all networks in a specific format (e.g., only CIDR)
- **Reducing false positives**: Disable formats that might be ambiguous or commonly mistyped
- **Validation**: Ensure input conforms to expected structure before processing
- **Format migration**: Accept input in old format, require output in new format

**Key concept**: Each format type can be enabled/disabled independently for patterns (search terms) and input (data being searched). This allows asymmetric rules like "accept any format in input, but only CIDR in patterns."

**Default behavior**: All formats accepted everywhere (`both`). This provides maximum flexibility but may catch unintended matches.

## Format Options

Each format flag accepts one of four modes:

- **pattern**: Accept format only in search patterns (via `-P`, `-f`, or arguments)
- **input**: Accept format only in data files being searched
- **both**: Accept format in both patterns and input (default)
- **none**: Disable format entirely

## Flags

**--parse-cidr** {**pattern**|**input**|**both**|**none**}
: Accept CIDR notation (e.g., `192.0.2.0/24`; default: **both**)

**--parse-netmask** {**pattern**|**input**|**both**|**none**}
: Accept subnet mask notation (e.g., `192.0.2.0 255.255.255.0`; default: **both**)

**--parse-hostmask** {**pattern**|**input**|**both**|**none**}
: Accept inverse/host mask notation (e.g., `192.0.2.0 0.0.0.255`; default: **both**)

**--parse-ranges** {**pattern**|**input**|**both**|**none**}
: Accept IP range notation (e.g., `192.0.2.0-192.0.2.255`; default: **both**)

**--parse-bare-ip** {**pattern**|**input**|**both**|**none**}
: Accept single IP addresses without CIDR notation (e.g., `192.0.2.1`; default: **both**)

**--range-format** {**long**|**short**|**both**|**none**}
: Accept long/short range formats (default: **both**)
- **long**: `192.0.2.0-192.0.2.255`
- **short**: `192.0.2.0-255`

## Common Use Cases

**Enforce CIDR-only patterns**:
```bash
# Only allow CIDR in search patterns; accept any format in data
grepnet --parse-cidr both --parse-netmask input \
  --parse-hostmask input --parse-ranges input \
  --parse-bare-ip input '192.0.2.0/24' data.txt
```

**Strict format validation**:
```bash
# Accept only CIDR everywhere; reject all other formats
grepnet --parse-cidr both --parse-netmask none \
  --parse-hostmask none --parse-ranges none \
  --parse-bare-ip none '192.0.2.0/24' data.txt
```

**Accept flexible input, output CIDR only**:
```bash
# Extract networks in any format from input, output as standardized CIDR
grepnet --extract --format cidr data.txt
# (No parsing flags needed; extraction normalizes everything to CIDR)
```

**Bare IP only (no CIDR interpretation)**:
```bash
# Find exact IPs only; don't interpret as /32 networks
grepnet --parse-bare-ip both --parse-cidr none \
  --parse-netmask none --parse-hostmask none \
  --parse-ranges none 192.0.2.1 data.txt
```

**Disable potentially ambiguous formats**:
```bash
# Turn off bare IPs (often ambiguous in mixed data) and hostmask (rarely used)
grepnet --parse-bare-ip none --parse-hostmask none '192.0.2.0/24' data.txt
```

## Asymmetric Parsing Example

**Scenario**: Accept subnet masks in configuration files (old format), but patterns must use CIDR (modern standard).

```bash
grepnet --parse-cidr both \
        --parse-netmask input \
        --parse-ranges none \
        --parse-bare-ip none \
        '192.0.2.0/24' config.txt
```

**Result**:
- Pattern `192.0.2.0/24` accepted ✓ (CIDR in pattern)
- File line `server 192.0.2.0 255.255.255.0` matches ✓ (netmask in input)
- File line `range 192.0.2.0-192.0.2.255` does NOT match ✗ (ranges disabled)

# PREFIX LENGTH FILTERING

Prefix length (also called CIDR mask size or network mask bits) determines how many IP addresses a network block contains. Lower numbers = larger networks, higher numbers = smaller networks.

**Prefix length basics**:
- IPv4: `/0` to `/32` (0 = entire internet, 32 = single IP)
- IPv6: `/0` to `/128` (0 = entire IPv6 space, 128 = single IP)
- Each increment halves the network size: `/24` has 256 IPs, `/25` has 128 IPs

**Why filter by prefix length**:
- **Audit subnetting**: Find networks larger/smaller than policy allows
- **Simplify output**: Extract only top-level aggregates or leaf subnets
- **Validate consistency**: Ensure all networks are within expected size range
- **Find anomalies**: Detect over-aggressive subnetting or under-utilized aggregates

**Terminology clarification**:
- **Shorter** prefix = fewer bits = LARGER network (more IPs)
  - `/8` is "shorter" than `/24` (contains 65,536x more IPs)
- **Longer** prefix = more bits = SMALLER network (fewer IPs)
  - `/24` is "longer" than `/8` (contains fewer IPs)

## Flags

**--ipv4-shorter-than** *N*
: Include only IPv4 networks with prefix length < N (larger networks)

**--ipv4-longer-than** *N*
: Include only IPv4 networks with prefix length > N (smaller networks)

**--ipv6-shorter-than** *N*
: Include only IPv6 networks with prefix length < N (larger networks)

**--ipv6-longer-than** *N*
: Include only IPv6 networks with prefix length > N (smaller networks)

## Common Use Cases

**Find small subnets (more specific)**:
```bash
# Only /25 or smaller (more granular subdivisions)
grepnet --extract --ipv4-longer-than=24 networks.txt

# Result: /25, /26, /27, ... /32 only
```

**Find large aggregates (less specific)**:
```bash
# Only /16 or larger (broad coverage)
grepnet --extract --ipv4-shorter-than=16 networks.txt

# Result: /0, /1, /2, ... /15 only
```

**Find networks in a specific size range**:
```bash
# Only class C or smaller (between /24 and /32)
grepnet --extract --ipv4-longer-than=24 --ipv4-shorter-than=32 networks.txt

# Result: /25, /26, /27, /28, /29, /30, /31 only
```

**Audit IPv6 allocation (common /64 boundary)**:
```bash
# Find subnets smaller than standard /64 allocation
grepnet --extract --ipv6-longer-than=64 networks.txt

# Result: /65, /66, ... /128 (unusual, needs review)
```

**Find policy violations**:
```bash
# Policy: allocate in /25 blocks minimum
# Find anything smaller (over-subnetting)
grepnet --extract --ipv4-longer-than=25 violations.txt
```

**Consolidation validation**:
```bash
# Consolidate, then show only large aggregates (verify reduction)
grepnet --consolidate --ipv4-shorter-than=20 all_networks.txt

# Result: Only /0 to /19 (summary-level networks)
```

# STRICT CIDR VALIDATION

CIDR validation ensures that network addresses don't have "host bits" set. For example, `192.0.2.1/24` is technically invalid (host bits are set); the correct form is `192.0.2.0/24`.

**Why strict validation matters**:
- **Consistency**: Ensures all networks are represented canonically
- **Debugging**: Catches typos (e.g., pattern meant to be `192.0.2.0/24` but written as `192.0.2.1/24`)
- **Compliance**: Some network configurations use CIDR notation to denote both the interface IP address and the network in one string (e.g., `192.0.2.1/24` means "configure IP 192.0.2.1 on the 192.0.2.0/24 network"). Strict CIDR validation distinguishes between these uses.
- **Safety**: Avoid ambiguous network definitions

**Default behavior**: Non-strict (normalize silently). Malformed CIDRs like `192.0.2.1/24` are automatically corrected to `192.0.2.0/24` without warning. This provides flexibility but may hide mistakes.

## Flags

**--strict-cidr** {**pattern**|**input**|**both**|**none**}
: Where to apply strict CIDR validation (default: **none**)

- **pattern**: Validate search patterns only (reject malformed patterns)
- **input**: Validate data file content only (reject malformed networks found in files)
- **both**: Validate both patterns and input
- **none**: No strict validation (default; silently normalize)

**--strict-cidr-action** {**fail**|**normalize**|**ignore**|**warn**}
: Action when invalid CIDR detected (default: **normalize**)

- **fail** - Exit with error code 2 (stop processing)
- **normalize** - Silently correct to network address (default)
- **ignore** - Skip invalid CIDR (don't include in results)
- **warn** - Print warning to stderr, then skip

## Use Cases

**Audit configuration consistency**:
```bash
# Reject any malformed CIDR in input; show warnings
grepnet --strict-cidr input --strict-cidr-action warn '192.0.2.0/24' config.txt
```

**Enforce pattern validation**:
```bash
# Reject if user types malformed pattern (e.g., typo in script)
grepnet --strict-cidr pattern --strict-cidr-action fail '192.0.2.0/24' data.txt
```

**Strict everywhere with warnings**:
```bash
# Both patterns and input must be valid; warn on violations
grepnet --strict-cidr both --strict-cidr-action warn '192.0.2.0/24' config.txt
```

**Silent normalization (default)**:
```bash
# Accept `192.0.2.1/24`, automatically correct to `192.0.2.0/24`
grepnet '192.0.2.0/24' config.txt
# No warnings; output treats both as `192.0.2.0/24`
```

## Visual Highlighting of Normalized CIDRs

When a CIDR has been normalized (host bits were corrected), grepnet can highlight it in output using the `GREPNET_COLORS` environment variable. The color key `mn` controls the appearance of normalized CIDRs.

**Default**: Normalized CIDRs are underlined (`04`)

**Example**: Highlight normalized CIDRs in red:
```bash
export GREPNET_COLORS="mn=01;31"
grepnet '192.0.2.0/24' config.txt
# Any network found as 192.0.2.1/24 (normalized to 192.0.2.0/24) will be displayed in red
```

This helps visually identify which networks required correction, making it easy to spot potential data quality issues without enabling strict mode errors.

**Color code format**: ANSI escape codes (e.g., `01;31` = bold red)
- `01;31` - Bold red
- `01;33` - Bold yellow
- `01;36` - Bold cyan
- `04` - Underline
- `0` - Default color

## Strict Validation with Extraction and Consolidation

Strict CIDR validation is especially useful with `--extract` and `--consolidate` modes, since these operations normalize all networks to canonical form and the distinction between correct and malformed input becomes significant.

**Extraction behavior**:
- Non-strict (default): All networks extracted and normalized, no warning
- Strict mode: Rejects/warns/skips networks with host bits set (depending on action)
- Use case: Audit data quality before consolidation

**Consolidation behavior**:
- Strict validation applies during extraction phase (before merging)
- Consolidation result: Only valid networks are merged
- Use case: Ensure consolidated output contains only canonical networks

**Example: Audit and clean network data**:
```bash
# Strict input validation with warnings, then consolidate
grepnet --extract --strict-cidr input --strict-cidr-action warn \
  --consolidate --format cidr config.txt

# Output: Only canonical networks, with warnings for any malformed input
```

**Example: Identify data quality issues before consolidation**:
```bash
# Show which networks needed normalization
export GREPNET_COLORS="mn=01;31"
grepnet --extract --format cidr config.txt

# Red-highlighted networks indicate data with host bits set
# Use --strict-cidr input --strict-cidr-action fail to reject these
```

# BINARY FILE HANDLING

**-a**, **--text**
: Treat all files as text

**-I**
: Skip binary files

**--binary-files** {**binary**|**text**|**without-match**}
: How to handle binary files (default: **binary**)

# COMMENT FILTERING

Comment filtering prevents networks inside comments from being matched, but **comments are always preserved in output**. By default, grepnet strips comments during network extraction (to avoid false matches) but prints the full original line including comments in results.

**How it works**:
1. **Extraction phase**: Comments are identified and removed before searching for networks
2. **Matching phase**: Networks are only matched in the searchable (non-comment) portion
3. **Output phase**: The original line WITH comments is printed, comments appear uncolorized

**Recognized comment markers**: `#`, `!`, `--`, `//`, `/* */`, `;`

Support includes:
- Line comments: Start from marker to end of line
- Block comments: `/* ... */` (comments can span multiple lines)
- Multiple markers: First marker encountered ends searchable content

**Example - Default behavior**:
```
Input line: server 192.0.2.1 # production

Search for: 192.0.2.0/24
Result: MATCH (192.0.2.1 is found and printed with its comment)

Output:
server [GREEN]192.0.2.1[RESET] # production
             ↑ matched, highlighted    ↑ not highlighted, preserved
```

**Example - Network in comment (ignored)**:
```
Input line: # TODO: configure 192.0.3.0/24

Search for: 192.0.3.0/24
Result: NO MATCH (network is inside comment, ignored)
```

## Flags

**--no-filter-comments**
: Disable comment filtering; include comments in network extraction

When enabled, networks inside comments are also matched and highlighted.

**Use case**: When working with files where comments contain actual network data (e.g., documentation with network addresses, commented-out configuration examples).

**Example - With --no-filter-comments**:
```
Input line: # TODO: configure 192.0.3.0/24

Search for: 192.0.3.0/24
Result: MATCH (with --no-filter-comments enabled)

Output:
# TODO: configure [GREEN]192.0.3.0/24[RESET]
                   ↑ matched and highlighted (even in comment)
```

## Common Use Cases

**Normal configuration auditing** (comments disabled by default):
```bash
# Search config files; ignore networks in comments
grepnet '192.0.0.0/16' firewall.conf

# Only networks in actual config lines are matched
# Comments like "# old setting: 192.0.2.0/24" are ignored
```

**Auditing documentation with network examples** (comments enabled):
```bash
# Extract networks from docs that include networks in comments
grepnet --extract --no-filter-comments architecture.md

# Finds networks both in main text and in commented examples
```

**Finding active configurations only**:
```bash
# Ensure you're not matching networks in commented-out rules
grepnet -r '192.0.2.0/24' rules.conf

# Default: commented lines like "# allow 192.0.2.0/24" are skipped
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
