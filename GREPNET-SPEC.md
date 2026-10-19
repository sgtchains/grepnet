# GREPNET: Complete API Specification for Language Porting

**Version**: 5.0.0  
**Status**: Complete specification for cross-language implementation  
**Objective**: Enable exact replication of grepnet functionality in C++, Go, Rust, or any other language while maintaining identical CLI behavior and API contract.

## Table of Contents

- [Overview](#overview)
- [Implementation Architecture: Unified Input Processing](#implementation-architecture-unified-input-processing)
- [Program Initialization and Argument Processing](#program-initialization-and-argument-processing)
- [Data Structures](#data-structures)
- [Color and Output System](#color-and-output-system)
- [Network Parsing Pipeline](#network-parsing-pipeline)
- [File Discovery and Scanning](#file-discovery-and-scanning)
- [Search and Matching Logic](#search-and-matching-logic)
- [Result Filtering and Output Rendering](#result-filtering-and-output-rendering)
- [Exit Codes and Error Handling](#exit-codes-and-error-handling)
- [Environment Variables](#environment-variables)
- [Command-Line Interface Specification](#command-line-interface-specification)

---

## Overview

grepnet is a network-aware grep alternative that searches text files for CIDR blocks, IP addresses, and IP ranges. Instead of simple substring matching, it compares network objects using set operations: equality, subset, superset, and overlap.

### Core Behavior

- **Input**: Search patterns (one or more network expressions), input files (or stdin)
- **Processing**: Parse network expressions from both patterns and files, normalize them, and compare using network algebra
- **Output**: Lines containing matching networks, with optional metadata (line numbers, byte offsets, filenames, color, context)
- **Exit Code**: 0 if matches found, 1 if no matches, 2 if error (file not found, no valid patterns, malformed CIDR in strict mode, etc.)

### NOT a Substring Tool

grepnet is fundamentally different from grep. It does not match substrings. Instead:

- It detects network-like values in text (CIDR blocks, IP+mask pairs, ranges, single IPs)
- It converts these into network objects with a canonical internal representation
- It compares networks using relational logic (superset/subset), not textual equivalence
- Two syntactically different expressions (e.g., `192.0.2.0/24` vs `192.0.2.0 255.255.255.0`) represent the same network and match equally

---

## Implementation Architecture: Unified Input Processing

### Core Principle: "All Input Is Input"

**Critical architectural requirement**: All CLI output modes MUST funnel through a SINGLE unified input processing path. This ensures consistent handling of stdin, files, binary detection, and streaming behavior regardless of the requested output mode.

### The Single Processing Path

```
┌─────────────────────────────────────────────────────────┐
│ CLI Entry Point (cli.py / main.cpp / etc.)              │
│ - Parse command-line arguments                          │
│ - Validate arguments and patterns                       │
│ - Determine output mode (normal/extract/consolidate)   │
└─────────┬───────────────────────────────────────────────┘
          │
          ↓
┌─────────────────────────────────────────────────────────┐
│ GrepNet.search(input_sources, mode='normal'|'extract'|  │
│              'consolidate', **output_options)          │
│ - SINGLE entry point for ALL output modes              │
│ - Abstracts input source type via InputSource           │
└─────────┬───────────────────────────────────────────────┘
          │
          ↓
┌─────────────────────────────────────────────────────────┐
│ InputSource.lines() Iterator                            │
│ - ONLY place where actual file/stdin reading occurs     │
│ - Yields: (line_number, line_content, byte_offset)      │
│ - Handles: regular files, stdin, file descriptors       │
│ - Binary detection cached (respects stream-destructive  │
│   nature of stdin via peek buffer)                      │
└─────────┬───────────────────────────────────────────────┘
          │
          ↓
┌─────────────────────────────────────────────────────────┐
│ Processing Pipeline (within grepnet.search())           │
│ 1. Parse networks from line                             │
│ 2. Match against patterns                               │
│ 3. Generate MatchResult objects                         │
│ 4. Yield MatchResult stream                             │
└─────────┬───────────────────────────────────────────────┘
          │
          ↓
┌─────────────────────────────────────────────────────────┐
│ Output Formatter (cli.py output handling)               │
│ - Mode-specific formatting (normal/extract/consolidate) │
│ - Applies prefixes (-n, -b, -H flags)                   │
│ - Applies colorization                                  │
│ - Deduplicates or consolidates based on mode            │
└─────────────────────────────────────────────────────────┘
```

### Why This Architecture Matters

1. **Single input reader**: Only `InputSource.lines()` reads from the actual input stream
   - No alternate input loops in CLI or output code
   - Binary detection happens once (not per-mode)
   - Peek buffer strategy works (8KB cache prevents stream data loss)
   - Stdin streaming works correctly (single pass, no seek/rewind)

2. **Abstraction of input type**: CLI code doesn't know or care if input is file/stdin/fd
   - Same code path for all sources
   - Easy to add new input types (e.g., URLs, databases) without changing search logic

3. **Mode-agnostic search**: `grepnet.search()` doesn't know about output format
   - Yields `MatchResult` objects with complete match metadata
   - Output formatter decides how to present results
   - Easy to add new output modes (JSON, XML, etc.) without modifying search

4. **Streaming compliance**: Input processing is always line-by-line with minimal buffering
   - Only buffers what's necessary for the output mode (e.g., context lines, consolidation)
   - Works with pipes, FIFOs, and infinite streams
   - Matches spec requirement: "line-by-line processing with NO buffering between search and output (unless context flags require buffering)"

### MatchResult Contract

The `MatchResult` object yielded by `grepnet.search()` MUST contain sufficient metadata to support all output modes:

```
MatchResult {
    line_number: int (1-based)
    line_content: str (original line, no newline)
    content_colored: str (ANSI-colored line for output)
    content_marked: str (internal markup encoding match metadata)
    filename: str or None (source display name)
    is_binary_file: bool (whether source is binary)
    byte_offset: int (0-based position in file)
    
    file_extraction: ParsedExtraction (the matched network from file)
    pattern_extraction: ParsedExtraction (the pattern network that matched)
    match_type: MatchType enum (EQUALS, SUBSET, SUPERSET, OVERLAP, UNMATCHED)
    match_index: int (index within line for multiple-matches-per-line handling)
    
    is_match: bool (whether this is a matching line or context line)
}
```

### Output Mode Implementations

All modes consume the same `MatchResult` stream from `grepnet.search()`:

**Normal output**: Print each `MatchResult` with prefixes and coloring
- Deduplication: per-line (all matches on same line print once)
- Buffering: minimal (only for context lines if -B/-A/-C used)

**Extract mode**: Stream unique networks with optional deduplication
- Input: `MatchResult` stream from `grepnet.search()`
- Processing: Collect into deduplicated set (by network object)
- Output: Each unique network on separate line (streaming)
- Note: Cannot fully stream because deduplication requires tracking seen networks across entire input

**Consolidate mode**: Merge overlapping networks (builds on Extract)
- Input: Extract the deduplicated networks from all `MatchResult` objects
- Processing: 
  1. First: Run extract logic to get deduplicated network set (reuse extract's dedup)
  2. Then: Buffer ALL unique networks (cannot consolidate without full set)
  3. Finally: Merge overlapping/adjacent networks into supernets
- Algorithm: Merge overlapping/adjacent networks into supernets
  - Sort networks by (version, start_address)
  - For each network: check if overlaps/adjacent to previous
  - If yes: merge into supernet, replace last entry
  - If no: append as new entry
- Output: Consolidated network list (sorted, merged)
- Note: Full file buffering required; cannot be truly streaming
- Architecture: Consolidate MUST use extract's deduplication as input, then add merge step

**Count mode** (`-c`): Print count of matching lines
- Input: `MatchResult` stream from `grepnet.search()`
- Processing: Count results (skip duplicate lines)
- Output: Single count number

**File list modes** (`-l`, `-L`): Print filenames with/without matches
- Input: `MatchResult` stream from `grepnet.search()`
- Processing: Collect unique filenames (with/without matches)
- Output: Filename list

### Extract and Consolidate: Architectural Relationship

**Key insight**: Consolidate mode MUST build on top of Extract mode's deduplication logic.

**Architectural flow**:
```
MatchResult stream from grepnet.search()
        │
        ├─→ Extract mode
        │   - Deduplicate networks
        │   - Output unique networks
        │   - (streaming with dedup tracking)
        │
        └─→ Consolidate mode
            - Use Extract's deduplication (same set of unique networks)
            - Buffer those unique networks
            - Merge overlapping/adjacent networks
            - Output consolidated networks
```

**Why this relationship matters**:
1. **No duplication of dedup logic**: Consolidate reuses Extract's network deduplication
2. **Same input stream**: Both modes consume identical MatchResult objects from search
3. **Clear separation of concerns**: 
   - Extract handles: network identification + deduplication
   - Consolidate adds: network merging on top of Extract output

**Implementation pattern**:
```python
# ✅ CORRECT implementation
if args.consolidate:
    # Step 1: Extract unique networks (reuses extract logic)
    unique_networks = extract_networks_from_search(input_sources)
    
    # Step 2: Consolidate (merge) those networks
    consolidated = consolidate_networks(unique_networks)
    
    # Step 3: Output consolidated result
    output_consolidated(consolidated)
```

### Constraint: No Direct Input Iteration in CLI

**Forbidden pattern**:
```python
# ❌ WRONG - violates "All Input Is Input" principle
for input_source in input_sources:
    for line_number, line_content, byte_offset in input_source.lines():
        # mode-specific logic here
```

**Correct pattern**:
```python
# ✅ CORRECT - uses single unified path
for match_result in grepnet.search(input_sources, mode='extract'):
    # apply output formatting
```

---

## Program Initialization and Argument Processing

### Startup Sequence

1. Parse command-line arguments using a standard argument parser (argparse in Python, C++ via getopt, Boost.Program_options, or similar)
2. Validate and normalize arguments:
   - Resolve strict CIDR modes based on flag combinations
   - Apply grep-compatible positional parsing: first non-option operand is the pattern, remaining operands are files
   - Determine input source: stdin, explicit file list, or directory recursion
   - Determine match type: resolve which of `--equal`, `--subset`, `--superset` were specified
3. **Initialize colorization** (CRITICAL - BEFORE file processing):
   - Check if stdout is a terminal (isatty)
   - Determine if color will be used at all (based on `--color=` flag and isatty)
   - Load default color codes into memory (do NOT re-parse on each line)
   - This determination happens ONCE at startup, enabling efficient per-line colorization later
4. Initialize parsers (two independent parser instances):
   - Pattern parser: For search patterns (respects `--strict-cidr={pattern|both|...}`)
   - Input parser: For file content (respects `--strict-cidr={input|both|...}`)
5. Discover input files: If `--recursive` or `--dereference-recursive`, walk directory tree; otherwise use explicit file list
6. Load search patterns: From positional argument, `-P` flags, or `-f` pattern files
7. Execute search: For each input file, extract networks and compare against patterns

### Positional Argument Disambiguation

grepnet must follow standard grep positional parsing rules. It must not guess based on file existence or network-looking syntax.

**grep-compatible rule**:

1. Parse all flags first.
2. If any pattern source is explicitly supplied via `-P`, `-e`, or `-f`, those values define the pattern set.
3. Otherwise, the first non-option positional argument is the pattern.
4. All remaining positional arguments are input files.
5. If there is no explicit pattern source and only one positional operand exists, it is treated as the pattern and stdin is searched.

This means a path-like string is not reinterpreted as a file merely because it exists. Standard grep does not do that.

**Examples**:
```
grepnet 192.0.2.0/24 myfile.txt # pattern = 192.0.2.0/24, files = myfile.txt
grepnet -f patterns.txt datafile # pattern file = patterns.txt, files = datafile
grepnet -P 192.0.2.0/24 # pattern = 192.0.2.0/24, stdin input
grepnet myfile.txt # pattern = myfile.txt, stdin input
```

**Important compatibility note**: `grepnet /path/to/patterns.txt datafile` is not interpreted as "pattern file then data file" unless the user explicitly uses `-f` or `-P`. That would be a grep-style pattern value plus a file argument, not a file-based pattern loader.

### Strict CIDR Mode Resolution (v2.0 API)

Two independent flags control CIDR strictness:

- `--strict-cidr={pattern|input|both|none}`: WHERE to apply strict validation (default: none)
- `--strict-cidr-action={fail|normalize|ignore|warn}`: WHAT to do on validation error (default: normalize)

**Behavior**:

- **Strict ON**: Reject malformed CIDRs (e.g., `192.0.2.1/24` where host bits are set)
- **Strict OFF (default)**: Silently normalize malformed CIDRs to their network address (e.g., `192.0.2.1/24` → `192.0.2.0/24`)

Each parser instance has its own strictness setting, so patterns can have different rules than input data.

---

## Data Structures

### 1. IPRange Object

Represents a contiguous range of IP addresses using integer arithmetic.

**Fields**:
- `start`: Integer representation of the start IP address
- `end`: Integer representation of the end IP address
- `family`: Address family (4 for IPv4, 6 for IPv6)

**Purpose**: Support IP range syntax (e.g., `192.0.2.0-192.0.2.255` or short form `192.0.2.0-255`) without converting to CIDR blocks.

**Key property**: Two ranges are equal if start, end, and family match.

### 2. Network Object

The standard library provides network objects (e.g., Python's `ipaddress.IPv4Network`, C++'s equivalent).

**Essential properties**:
- Network address: The lowest address in the network
- Broadcast/last address: The highest address in the network
- Prefix length: The number of network bits (e.g., 24 in `/24`)
- Family: IPv4 or IPv6
- Integer conversion: Ability to convert network address and broadcast address to integers

**Key invariant**: Two networks are equal if they represent the same set of addresses (regardless of syntax). E.g., `192.0.2.0/24` and `192.0.2.0 255.255.255.0` are equal.

### 2.1 WildcardMaskRange Object

Represents Cisco ACL wildcard mask notation using network address and wildcard mask (non-CIDR-aligned).

**Fields**:
- `original_text`: String representation of the wildcard mask notation (e.g., `"10.4.0.0 0.0.127.252"`)
  - Stored as-is from input for display purposes
  - Format: "{base_ip} {wildcard_mask}"
- `expanded_cidrs`: List of IPv4Network objects representing the constituent CIDR blocks that exactly cover the IP range specified by the wildcard mask
  - Already aggregated into minimal set using `ipaddress.collapse_addresses()`
  - Example: `"10.4.0.0 0.0.127.252"` expands to multiple /24, /25 blocks covering 10.4.0.0-10.4.127.252

**Purpose**: Support Cisco ACL wildcard mask notation (e.g., `10.4.0.0 0.0.127.252`). Internally expanded into constituent CIDRs using standard wildcard mask computation for matching, but preserves original format for display.

**Key property**: Two WildcardMaskRange objects are equal if their original_text and expanded_cidrs are identical. The expanded_cidrs set represents the exact IP space covered.

**Wildcard Mask Computation**: Based on standard Cisco ACL algorithm:
- Range: [network_address & ~wildcard_mask, (network_address & ~wildcard_mask) | wildcard_mask]
- Valid IPs: Only those where (ip & ~wildcard_mask) == (network_address & ~wildcard_mask)
  - 1-bits in wildcard mask = "don't care" (can be 0 or 1)
  - 0-bits in wildcard mask = "must match exactly"

**Example**:
```
Input: 10.4.0.0 0.0.127.252
Interpretation:
  - Base: 10.4.0.0
  - Wildcard: 0.0.127.252 (binary: ...01111111.11111100)
  - 1-bits at positions allow variation, 0-bits must match
Valid IP range: 10.4.0.0 through 10.4.127.252 (constrained by 0-bits)
Valid count: ~32K addresses matching (ip & ~mask) == (base & ~mask)
expanded_cidrs: [10.4.0.0/25, 10.4.1.0/25, ..., 10.4.127.0/25] (aggregated)
```

### 3. ParsedExtraction Tuple

When extracting networks from a line, each unique network is represented as a single ParsedExtraction:
```
(network_object, format_type, was_normalized, matched_texts)
```

- `network_object`: Network or IPRange object (canonical form, e.g., IPv4Network('192.0.2.0/24'))
- `format_type`: String indicating how it was found:
  - `'cidr_notation'` (e.g., `192.0.2.0/24`)
  - `'subnet_mask'` (IPv4 only, e.g., `192.0.2.0 255.255.255.0`)
  - `'inverse_mask'` (IPv4 only, Cisco hostmask, e.g., `192.0.2.0 0.0.0.255`)
  - `'wildcard_mask'` (IPv4 only, Cisco wildcard mask, e.g., `10.4.0.0 0.0.127.252`; requires `--parse-wildcard {pattern|input|both}` and `--wildcard-search` to enable parsing)
  - `'ipv4_range'` (e.g., `192.0.2.0-192.0.2.255`)
  - `'ipv6_range'` (e.g., `2001:db8::0-2001:db8::255`)
  - `'ip_only'` (single IP, treated as /32 or /128)
- `was_normalized`: Boolean flag - True if ANY matched text required normalization (host bits were corrected)
- `matched_texts`: List of matched text variations with per-text normalization info:
  ```python
  [
    {"text": "192.0.2.0/24", "was_normalized": False},
    {"text": "192.0.2.0 255.255.255.0", "was_normalized": False},
    {"text": "192.0.2.2/24", "was_normalized": True},
    {"text": "192.0.2.0 0.0.0.255", "was_normalized": False}
  ]
  ```

**Key design**: Same network appearing multiple times in different formats is deduplicated to a single ParsedExtraction. The `matched_texts` list contains ALL text representations found on the line, preserving which specific texts were normalized (e.g., `192.0.2.2/24` → `192.0.2.0/24`). The group-level `was_normalized` flag indicates if ANY variation required normalization.

**Note on wildcard_mask format**: When format_type is 'wildcard_mask', the matched_texts list contains the original space-separated Cisco wildcard mask notation (e.g., `"10.4.0.0 0.0.127.252"`). No normalization occurs for wildcard mask format; `was_normalized` is always False for this format type.

### 4. FileEntry Object

When networks are extracted from a file, each unique network is stored with aggregated information:
```
{
'network': (Network or IPRange or WildcardMaskRange object),
'format_type': (format_type string from ParsedExtraction),
'line_number': (1-based line number),
'line_content': (raw line text, newline stripped),
'matched_texts': (list of {"text": str, "was_normalized": bool} dicts),
'was_normalized': (boolean - True if ANY matched text was normalized)
}
```

Used later for matching and result assembly. The `matched_texts` list preserves all text representations so each occurrence can be marked with its specific normalization status.

### 5. MatchResult Object

After a match is found, results are assembled into a match result containing:
```
{
'file': (filepath),
'line': (1-based line number),
'content': (original line text, uncolorized),
'content_colored': (line text with ANSI color codes applied - pre-rendered for text output),
'match_index': (index into extracted networks on this line for lookup),
'discovered': {
'network': (string representation of matched network),
'format_type': (format_type string: 'cidr_notation', 'subnet_mask', 'inverse_mask', 'wildcard_mask', 'ipv4_range', 'ipv6_range', 'ip_only'),
'was_normalized': (boolean - True if ANY matched_text was normalized),
'matched_texts': (list of {"text": str, "was_normalized": bool} - all text variations),
'match_type': ('EQUALS', 'SUBSET', 'SUPERSET', 'OVERLAP', 'UNMATCHED')
},
'is_context': (boolean - is this a context line or an actual match?)
}
```

**Note**: If a line contains multiple networks, each unique network produces a separate MatchResult object with the same line/content but different discovered values. All matched_texts for that network are marked in the single content_colored output.

---

## Color and Output System

### Color Code Categories

**Match type codes** (outermost layer, one applied per match):
- `me=ANSI_CODE`: Match type equals (exact network match) — default: bright green (01;32)
- `mb=ANSI_CODE`: Match type subset (pattern is subset of file data) — default: bright blue (01;34)
- `mS=ANSI_CODE`: Match type superset (pattern is superset of file data) — default: bright yellow (01;33)
- `mo=ANSI_CODE`: Match type overlap (partial overlap) — default: no color (0)
- `mu=ANSI_CODE`: Match type unmatched (networks that don't match any pattern when using `-u` flag) — default: no color (0)

**Format-specific codes** (applied inside match type, when applicable):
- `wm=ANSI_CODE`: Wildcard mask format (Cisco ACL notation) — default: curly underline (4:3), only used when `--parse-wildcard` is enabled

**Normalization flag** (innermost layer, applied when CIDR was corrected):
- `mn=ANSI_CODE`: Normalized CIDR (malformed input was corrected from non-strict mode) — default: underlined (04)

**Other codes** (parsed but not used for highlighting):
- `mt=ANSI_CODE`: Matched text in the matched line
- `mc=ANSI_CODE`: Matched text in context line containing matches
- `ms=ANSI_CODE`: Matched text in context line without matches
- `fn=ANSI_CODE`: Filename color
- `ln=ANSI_CODE`: Line number color
- `bn=ANSI_CODE`: Byte offset color
- `se=ANSI_CODE`: Separator color
- `sl=ANSI_CODE`: Entire selected line background

### Color Nesting Hierarchy

Colors are applied in nested layers, with the outermost layer taking precedence for terminal interpretation:

**Nesting order** (outermost to innermost):
1. **Match type** (`me=`, `mb=`, `mS=`, `mo=`, `mu=`) — outermost
2. **Format-specific** (`wm=` for wildcard masks) — middle
3. **Normalization** (`mn=` if corrected) — innermost

**Example renderings**:
- Plain EQUALS match: `\033[01;32m192.0.2.0/24\033[0m` (bright green)
- EQUALS + normalized: `\033[01;32m\033[04m192.0.2.0/24\033[0m` (bright green wrapping underline)
- SUBSET + wildcard mask: `\033[01;34m\033[4:3m10.4.0.0 0.0.127.252\033[0m` (bright blue wrapping curly underline)
- SUPERSET + wildcard + normalized: `\033[01;33m\033[4:3m\033[04m10.4.0.0 0.0.127.252\033[0m` (bright yellow wrapping curly underline wrapping underline)

### Color Auto Detection

By default, color is only used if stdout is a terminal (isatty check). Override with:

- `--color=always`: Force color even when piping
- `--color=never`: Disable color
- `--color=auto`: Default terminal detection

### Color Rendering Process

When rendering a match line, the system uses an internal markup system that encodes match information at match time:

1. **During matching phase** (NOT output phase):
   - Extract all networks from the line
   - Test all networks against search pattern(s)
   - For each matched network, wrap it with internal markup encoding match metadata
   - Markup format: `◀TYPE:MATCH_TYPE|OBJ:OBJECT_TYPE|NORM:WAS_NORMALIZED▶network_text◀/TYPE▶`
   - Store marked-up line in MatchResult.content_colored
   - Example: `◀TYPE:EQUALS|OBJ:CIDR|NORM:false▶192.0.2.0/25◀/TYPE▶`

2. **Markup encoding details**:
   - Uses Unicode Private Use Area characters (U+E000, U+E001) that never appear in network data
   - `◀` (U+E000) = markup start delimiter
   - `▶` = field separator
   - `◀/TYPE▶` = markup end delimiter
   - TYPE values: EQUALS, SUBSET, SUPERSET, OVERLAP, UNMATCHED
   - OBJ values: CIDR, BARE_IP, RANGE, SUBNET_MASK, INVERSE_MASK, WILDCARD_MASK
   - NORM values: true or false

3. **Output phase** (NO re-scanning, only finalization):
   - Group MatchResults by line_number (one line, one output)
   - Before printing, finalize markup: convert internal markup to ANSI color codes based on GREPNET_COLORS
   - If colors disabled, strip markup entirely (leaving plain text)
   - Pattern: `\uE000TYPE:([A-Z_]+)\|OBJ:([A-Z_]+)\|NORM:(\w+)\uE001(.*?)\uE000/TYPE\uE001`

4. **Example with all networks highlighted**:
```
Input line: test 192.0.2.0/24 192.0.2.0/25 192.0.2.1 # comment
Pattern: 192.0.2.0/25

During matching, all networks tested and marked:
- 192.0.2.0/24 → SUPERSET
- 192.0.2.0/25 → EQUALS
- 192.0.2.1/32 → SUBSET

Content_colored (marked-up):
test ◀TYPE:SUPERSET|OBJ:CIDR|NORM:false▶192.0.2.0/24◀/TYPE▶ ◀TYPE:EQUALS|OBJ:CIDR|NORM:false▶192.0.2.0/25◀/TYPE▶ ◀TYPE:SUBSET|OBJ:BARE_IP|NORM:false▶192.0.2.1◀/TYPE▶ # comment

During output finalization:
test [YELLOW]192.0.2.0/24[RESET] [GREEN]192.0.2.0/25[RESET] [BLUE]192.0.2.1[RESET] # comment

Printed ONCE (not three times) with all networks highlighted appropriately
```

### Critical Architectural Requirements

- **No line re-scanning at output time**: Markup applied at match time; output only finalizes to ANSI codes
- **Tight coupling**: Match type determination and content marking happen together during matching
- **One line, one output**: Multiple networks on same line produce multiple internal MatchResults but print as ONE line with all networks colored
- **VTY safe**: Private Use Area characters don't interfere with terminal escape sequences
- **Parse color codes once at startup**: GREPNET_COLORS parsed once, cached, used during finalization

---

## Network Parsing Pipeline

### Overview

The parser is responsible for detecting network-like values in a line and extracting them. It is NOT a simple tokenizer; it performs semantic filtering to avoid false positives.

**Unified Parser Architecture**: The same extraction pipeline is used for both search patterns and file content. This means:
- Pattern arguments are parsed through the exact same extraction process as file lines
- Both respect the same strictness settings (pattern parser vs input parser, which can differ)
- Both use the same extraction order, comment handling, and false-positive filters
- This ensures consistency: a network expressed in a pattern will be recognized identically when found in a file

### The Extraction Pipeline (Formal Definition)

The **extraction pipeline** is a sequence of operations applied to any text (pattern or file line) to:
1. Identify and extract network-like values
2. Filter out false positives
3. Handle comments and special syntax
4. Return a list of ParsedExtraction objects

**Every use of the extraction pipeline follows this sequence**:

1. **Comment Handling**: Strip comments from text using CommentHandler
   - Identify comment markers (#, //, /*, --, !, ;)
   - Preserve searchable content before comment marker
   - Discard comment portion
   - Handle block comments (/* ... */) across line boundaries if applicable

2. **Network Extraction**: Scan searchable content using extraction order
   - Try each network format in priority order (see "Extraction Order" section)
   - Extract networks and their original text representation
   - Track format type (CIDR, subnet_mask, inverse_mask, wildcard_mask, ip_range, bare_ip)

3. **False-Positive Filtering**: Apply semantic validation
   - Reject OID patterns (1.2.3.4.5.6... with more than 4 octets)
   - Reject IPv6 addresses embedded in URLs
   - Reject invalid prefix lengths
   - Other format-specific validation

4. **Deduplication**: Remove duplicate network objects
   - Track already-extracted networks from this line
   - Skip re-extraction of same network in different format

5. **Result**: Return list of ParsedExtraction objects (may be empty)

**What MUST use the extraction pipeline:**
- ✓ Pattern arguments (positional, -P, -f from file/stdin)
- ✓ Patterns from files (--exclude-cidr, --exclude-from, etc.)
- ✓ File input lines (standard grep mode)
- ✓ Stdin input (when piped)
- ✓ --extract mode (extract networks from input)
- ✓ --consolidate mode (consolidate networks from input)

**Result**: Identical treatment ensures a network pattern is recognized the same way whether it appears in:
- A pattern argument
- A file line being searched
- An exclusion pattern
- Any other input context

### Extraction Order (Critical)

Networks are extracted in a deliberate fixed order to avoid duplication:

1. CIDR notation (e.g., `192.0.2.0/24`)
2. Subnet mask format (e.g., `192.0.2.0 255.255.255.0`) – IPv4 only, try first
3. Inverse/Cisco mask format (e.g., `192.0.2.0 0.0.0.255`) – IPv4 only, try if subnet mask fails
4. Wildcard/Cisco ACL mask format (e.g., `10.4.0.0 0.0.127.252`) – IPv4 only, requires `--parse-wildcard {pattern|input|both}` and `--wildcard-search` scope to enable; try if inverse mask fails
5. IP ranges (long form) (e.g., `192.0.2.0-192.0.2.255`)
6. IP ranges (short form) (e.g., `192.0.2.0-255`)
7. Plain IP addresses (treated as /32 or /128)

**Important**: Subnet mask, inverse mask, and wildcard mask formats compete for the same pattern space (two space-separated values). When a pattern matching two IP addresses is found:

1. First, attempt to parse as a subnet mask (must have contiguous all 1 bits from MSB followed by contiguous all 0 bits; e.g., `255.255.255.0`, `255.240.0.0`, `255.255.0.0`)
2. If that fails and MSB is 0 (not netmask format), attempt to parse as an inverse mask (must have contiguous all 0 bits from MSB followed by contiguous all 1 bits; e.g., `0.0.0.255`, `0.15.255.255`, `0.255.255.255`)
3. If that fails and wildcard mask parsing is enabled (`--parse-wildcard` and `--wildcard-search`), attempt to parse as a wildcard mask (represents a valid ACL range with 1-bits for "don't care" positions and 0-bits for "must match" positions)
4. If all three fail, do NOT extract the individual IPs from this pattern (treat as failed extraction)

**Why this order matters**: If you extract plain IPs first, then a CIDR block `192.0.2.0/24` would produce five matches: the network address, three intermediate addresses, and the broadcast address—all from the same logical network. The extraction order prevents this.

### Disabled Format Handling

When a format is disabled via parsing control flags (e.g., `--parse-cidr=none`), that step in the extraction order is **skipped**. The parser attempts to match with the next enabled format in the priority list.

**Examples**:

1. **Input**: `192.0.2.0/24` with `--parse-cidr=none` (CIDR disabled in input scope)
   - Step 1 (CIDR): Skipped (disabled)
   - Step 2-4 (Masks): Text doesn't match mask format (no space separator) → Fail
   - Step 5-6 (Ranges): Text doesn't contain `-` → Fail
   - Step 7 (Plain IPs): Extracts `192.0.2.0` as bare /32 IP
   - **Result**: Single match for `192.0.2.0/32`

2. **Input**: `192.0.2.0 255.255.255.0` with `--parse-netmask=none` (subnet mask disabled)
   - Step 1 (CIDR): Text has space → Not CIDR format → Fail
   - Step 2 (Subnet Mask): Skipped (disabled)
   - Step 3 (Inverse Mask): Text has MSB=1 in second value → Invalid for inverse mask → Fail
   - Step 4-6 (Wildcard, Ranges): Don't match → Fail
   - Step 7 (Plain IPs): Extracts both IPs as separate bare addresses
   - **Result**: Two matches: `192.0.2.0/32` and `255.255.255.0/32`

3. **Input**: `192.0.2.0 0.0.0.255` with both `--parse-netmask=none` and `--parse-hostmask=none` (both mask formats disabled)
   - Steps 2-3 (Masks): Both skipped
   - Step 7 (Plain IPs): Extracts both IPs as separate bare addresses
   - **Result**: Two matches: `192.0.2.0/32` and `0.0.0.255/32`

**Note on bare IP extraction**: Bare IP extraction itself can be disabled via `--parse-bare-ip=none`. When ALL formats are disabled, no networks are extracted from that input.

### Deduplication During Extraction

A set tracks already-extracted tokens. When a broader network is found (e.g., CIDR block), all components (individual IPs, smaller ranges) are marked as "found" to prevent re-extraction.

**Invariant**: No line produces duplicate matches for the same network, even if it appears in multiple formats.

### Comment Marker Precedence (Critical)

When multiple comment marker types appear on the same line, **the marker appearing earliest (leftmost) takes precedence and determines where the comment starts**. All markers that appear after the first marker are treated as part of the comment and have no special meaning.

**Single-line markers**: Once the first marker is found, everything from that marker to end-of-line is treated as comment (no further markers are recognized).

**Multi-line block comments**: The outermost comment delimiters "swallow" inner markers. Inner markers appearing before the outer block comment ends are treated as regular text within the comment.

**Examples**:
- `192.0.2.1!192.0.2.2#192.0.2.3` → Comment starts at `!` (position 9) → Extracted: `192.0.2.1` → Comment portion: `!192.0.2.2#192.0.2.3` (the `#` is ignored as it's already in comment)
- `192.0.2.1 # comment ! more` → Comment starts at `#` (position 9) → Extracted: `192.0.2.1` → Comment portion: `# comment ! more` (the `!` is ignored)
- `192.0.2.1 /* comment -- text */ 192.0.2.2` → Block comment starts at `/*` → Everything until `*/` is comment → Extracted: `192.0.2.1` and `192.0.2.2` → SQL marker `--` inside block comment is ignored
- `<!-- comment /* text --> 192.0.2.1` → HTML comment starts at `<!--` → C-style marker `/*` inside is ignored → Comment ends at `-->`

### Comment Handling

Comments are recognized and separated from searchable content BEFORE extraction begins.

**Comment patterns recognized**:
```
#   Python/shell comments
!   Cisco comments
//  C/Java comments
/* */ Block comments
--  SQL comments
;   Lisp comments
```

**Process**:
1. Check if entire line is a comment (starts with comment marker)
2. If not, scan line for inline comment markers (whitespace followed by marker)
3. Split line into searchable portion (before marker) and comment portion (after marker)
4. Perform extraction only on searchable portion
5. Preserve comment portion in output (displayed uncolorized)

**Critical Clarification: Two-Phase Comment Handling**:

Comments are handled in two distinct phases:

1. **Extraction Phase** (during network parsing):
   - Comments are stripped from the line ONLY for the purpose of network extraction
   - Networks found in comments are NOT matched
   - The comment removal is internal to the parser and does not affect output

2. **Output Phase** (when printing results):
   - If a line produces network matches and is selected for output, the FULL ORIGINAL LINE is printed (including comments)
   - The comment portion appears in the output uncolorized (no highlighting)
   - Networks found before the comment marker are highlighted normally
   - If a line is entirely a comment (produces no network extractions), NO output is printed for that line at all

**Examples**:
- Input: `! Version1 192.0.2.2` with pattern `0.0.0.0/0`
  - Extraction phase: Entire line is a comment, extracts to empty, no networks found
  - Output: **Nothing printed** (entire line was comment-only)

- Input: `192.0.2.1!192.0.2.2` with pattern `0.0.0.0/0`
  - Extraction phase: Comment at `!` marker, extracts `192.0.2.1`, matches pattern
  - Output: `192.0.2.1!192.0.2.2` printed with `192.0.2.1` highlighted and `!192.0.2.2` uncolorized

- Input: `192.0.2.1 # This is a comment` with pattern `0.0.0.0/0`
  - Extraction phase: Comment at `#` marker, extracts `192.0.2.1`, matches pattern
  - Output: `192.0.2.1 # This is a comment` printed with `192.0.2.1` highlighted and `# This is a comment` uncolorized

### Comment Filtering

By default, comment lines are filtered (excluded from search). Control comment filtering scope with `--no-filter-comments`.

**Supported comment prefixes**:
- `#` - Standard Unix/Linux comment (shell, Python, YAML, Terraform, Ansible, INI)
- `!` - Cisco IOS comment
- `--` - SQL, Lua, Ada comment
- `//` - C-style comment (Terraform, PHP, Go, Java, JavaScript, etc.)
- `;` - INI file, Lisp, assembly comment
- `remark` or `rem` (abbreviated) - Cisco configuration description (case-insensitive)
- `description` or `desc` (abbreviated) - Cisco interface/object description (case-insensitive)
- `<!-- ... -->` - HTML/XML block comment
- `/* ... */` - C-style block comment (multi-line)

**Filtering control**:

The `--no-filter-comments` flag accepts optional arguments to control which scopes have filtering disabled:

- `--no-filter-comments` (no argument) → Defaults to `both`, disables filtering in patterns AND input lines
- `--no-filter-comments=pattern` → Disable filtering for patterns only (comments in input are still filtered)
- `--no-filter-comments=input` → Disable filtering for input lines only (patterns are still filtered)
- `--no-filter-comments=both` → Disable filtering in both patterns and input lines
- `--no-filter-comments=none` → Explicitly enable filtering everywhere (same as default, no flag)

**Default behavior** (no flag):
- Comment filtering is applied to both patterns and input (`filter-comments=both`)
- Comment-only lines are excluded from input processing
- Comment lines do not contribute to network extraction

**Behavior**:
- Comment-only lines are skipped entirely (not added to file entries)
- Comment detection is case-insensitive for Cisco keywords (`REMARK`, `REM`, `DESCRIPTION`, `DESC` all recognized)

**Single-line comment markers** (1 or 2 characters: `#`, `!`, `--`, `//`, `;`):
- **Recognition**: Marker can appear anywhere in a line (no preceding whitespace required for inline recognition)
- **Behavior**: Everything from marker onward is treated as a comment and stripped (during extraction phase only)
- Do NOT require trailing whitespace (marker is recognized even if followed directly by text)
- Examples (during extraction phase, with pattern `0.0.0.0/0`):
  - `#anything` → Extraction: empty, no networks extracted → No output (entire line is comment)
  - `value#comment` → Extraction: finds networks in `value` portion only → If match, output entire line: `value#comment`
  - `192.0.2.1!192.0.2.2` → Extraction: finds `192.0.2.1` only, matches pattern → Output: `192.0.2.1!192.0.2.2` (with `!192.0.2.2` uncolorized)
  - `192.0.2.1--192.0.2.2` → Extraction: finds `192.0.2.1` only, matches pattern → Output: `192.0.2.1--192.0.2.2` (with `--192.0.2.2` uncolorized)

**Cisco keywords** (`remark`, `rem`, `description`, `desc` - single-line only):
- **Leading requirement**: Keyword must be preceded by whitespace (or be at line start after optional leading whitespace)
- **Trailing requirement**: Keyword must be followed by whitespace (or end-of-line)
- **Behavior**: Everything from keyword onward is treated as a comment and stripped during extraction (only the searchable portion before the keyword is processed for networks)
- Case-insensitive
- Comments out the rest of the line only (not a multi-line block)
- Examples (during extraction phase):
  - `remark This is a comment` → Keyword at line start → Extracts: empty (no searchable content before keyword) → No output
  - `  rem This is a comment` → Keyword at line start (after leading whitespace) → Extracts: empty → No output
  - `access-list 101 remark This is a comment` → Keyword in middle, but before it is only `access-list 101` (no networks) → Extracts: empty → No output
  - `192.0.2.0/24 remark This is a comment` → Keyword in middle, before it is `192.0.2.0/24` (network found) → Extracts: `192.0.2.0/24` → If matches, outputs full line `192.0.2.0/24 remark This is a comment`
  - `text101rem` → NOT a comment (keyword not preceded by whitespace) → Searches entire line for networks
  - `text101 rem` → Keyword in middle, before it is `text101` (no networks) → Extracts: empty → No output

**Multi-line block comments** (only these span multiple lines):
- `/* ... */` (C-style)
- `<!-- ... -->` (HTML/XML)
- Content between markers is removed entirely
- Remark and description keywords are NOT block comments and cannot span multiple lines

**Inline comments**:
- Single-line comment markers (1 or 2 characters: `#`, `!`, `--`, `//`, `;`): Can appear anywhere in a line (no preceding whitespace required), everything after marker is stripped
  - Examples: `192.0.2.1#comment` → `192.0.2.1` output; `192.0.2.1!192.0.2.2` → `192.0.2.1` output; `192.0.2.1--192.0.2.2` → `192.0.2.1` output
- Cisco keywords (`remark`, `rem`, `description`, `desc`): Must be preceded by whitespace AND followed by whitespace, everything after keyword is stripped from extraction
  - Examples: `access-list 101 remark This is a description` → searches `access-list 101` (no networks) → no output; `192.0.2.0/24 remark description` → searches `192.0.2.0/24` (network found) → output full line
- The full original line is output by default; use `-o/--only-matching` to see only extracted networks

### CIDR Notation Parsing

**Format**: IP address followed by `/` and numeric prefix length in valid range.

**CIDR Pattern Regex (IPv4 example)**:
```regex
Match only if prefix is numeric AND in valid range (0-32 for IPv4)
(\d{1,3}.){3}\d{1,3}/([0-2]?[0-9]|3[0-2])(?![0-9])
```

**IPv6 example**:
```regex
Similar pattern adapted for IPv6, prefix 0-128
[0-9a-fA-F:]+/([0-9]{1,3})(?![0-9])
Then validate 0 ≤ prefix ≤ 128 during parsing
```

**Key principle**: The regex is strict from the start. It only matches strings where:
- Prefix contains digits only (no letters or other characters)
- Prefix value is in the valid range (0-32 for IPv4, 0-128 for IPv6)

**Non-matching patterns** (fail at regex stage, no extraction attempted):
- `192.0.2.0/33` (prefix out of range) → Regex does NOT match → extraction fails → move to next format → extract `192.0.2.0` as plain IP
- `192.0.2.0/abc` (prefix not numeric) → Regex does NOT match → extraction fails → move to next format → extract `192.0.2.0` as plain IP
- `192.0.2.0/024` (leading zero, still in range but treated as non-numeric) → Depends on implementation; ideally reject at regex stage
- No error, no normalization; these are simply not CIDR notation

**Matching patterns** (regex matches, now validate host bits):
- `192.0.2.1/24` → Regex matches (valid format) → Check for host bits set
  - Strict mode: Reject (error message, may exit)
  - Non-strict mode (default): Normalize to `192.0.2.0/24` and set `was_normalized=True`
- `192.0.2.0/24` → Regex matches, host bits not set → Extract as-is

**Network object creation**: After regex confirms valid format and range, parse IP address and prefix, then use standard library to create network object.

## Two-Value Mask Formats

When a line contains two IPv4 addresses separated by one or more horizontal whitespace characters (spaces, tabs), the parser must determine if this is a mask notation pattern (either subnet mask or hostmask) or two separate IPs.

### Format Definitions

**Both formats** follow this pattern:
- First value: An IPv4 address (network address, or any address within the network)
- Separator: One or more horizontal whitespace characters
- Second value: An IPv4 mask (interpretation depends on MSB)

**Whitespace handling**: Separator must be horizontal space (ASCII space, tab, or Unicode horizontal whitespace). Do NOT split on vertical whitespace (newlines, carriage returns).

**Pattern prerequisites**:
1. Exactly two parts produced (no dashes, no extra values)
2. Both parts parse as valid IPv4 addresses (not CIDR, not containing `-`)
3. Neither part contains `/` or `-` (these indicate CIDR or range formats, not mask formats)

### Subnet Mask Format (Netmask)

**Recognition**: MSB of second value is 1 (starts with binary 1)

**Binary structure**: All ones from MSB, followed by all zeros (contiguous 1s then 0s)
- Example: `11111111.11111111.11111111.00000000` = 255.255.255.0

**Parsing**:
1. Verify second value is contiguous 1s-then-0s (no interleaved bits)
2. Calculate prefix length by counting 1-bits: e.g., 24 ones = /24
3. Create IPv4Network(first_ip, prefix_length)

**Examples**:
- `192.0.2.0 255.255.255.0` → 192.0.2.0/24
- `10.0.0.0 255.0.0.0` → 10.0.0.0/8
- `192.0.2.5 255.255.255.255` → 192.0.2.5/32

**Reject patterns**:
- Non-contiguous (e.g., 255.255.254.1)
- Invalid as netmask (e.g., second value is not a valid netmask)
- Second value is 0.0.0.0 (reserved for hostmask format)
- IPv6 addresses

### Hostmask Format (Inverse Mask / Cisco Format)

**Recognition**: MSB of second value is 0 (starts with binary 0)

**Binary structure**: All zeros from MSB, followed by all ones (contiguous 0s then 1s)
- Example: `00000000.00000000.00000000.11111111` = 0.0.0.255

**Parsing**:
1. Verify second value is contiguous 0s-then-1s (no interleaved bits)
2. Invert hostmask to get netmask: XOR with 0xFFFFFFFF
3. Calculate prefix length from inverted netmask
4. Create IPv4Network(first_ip, prefix_length)

**Examples**:
- `192.0.2.0 0.0.0.255` → invert(0.0.0.255) = 255.255.255.0 → 192.0.2.0/24
- `10.0.0.0 0.255.255.255` → invert(0.255.255.255) = 255.0.0.0 → 10.0.0.0/8
- `192.0.2.1 0.0.0.0` → invert(0.0.0.0) = 255.255.255.255 → 192.0.2.1/32

**Reject patterns**:
- Non-contiguous hostmask (e.g., after inversion, has interleaved bits)
- Invalid hostmask (e.g., second value is not contiguous 0s-then-1s)
- Second value is 255.255.255.255 (reserved for netmask format)
- IPv6 addresses

### Key Distinction

| Aspect | Subnet Mask (Netmask) | Hostmask (Inverse Mask) |
|--------|----------------------|-------------------------|
| MSB of second value | 1 (starts with binary 1) | 0 (starts with binary 0) |
| Binary pattern | 1s from MSB, then 0s | 0s from MSB, then 1s |
| Common notation | 255.255.255.0 | 0.0.0.255 |
| Interpretation | "Number of 1-bits" | "Number of 0-bits inverted" |
| Standard | RFC 791 standard notation | Cisco IOS notation |

### Reserved Values (Special Patterns)

Two special mask values have reserved patterns based on the first IP address:

**Pattern 1: `255.255.255.255 0.0.0.0` (Broadcast + All-Zeros Mask)**
- First value: 255.255.255.255 (broadcast address)
- Second value: 0.0.0.0 (reserved, normally suggests netmask MSB=0)
- Interpretation: Treat 0.0.0.0 as hostmask format (exception to MSB rule)
- Invert: 0.0.0.0 XOR 0xFFFFFFFF = 255.255.255.255
- Result: `255.255.255.255/32` (single host)
- Rationale: When first IP is broadcast and second is all-zeros, hostmask interpretation is more semantically correct

**Pattern 2: `0.0.0.0 255.255.255.255` (All-Zeros + Broadcast Mask)**
- First value: 0.0.0.0 (all-zeros address)
- Second value: 255.255.255.255 (reserved, normally suggests netmask MSB=1)
- Interpretation: Treat 255.255.255.255 as hostmask format (exception to MSB rule)
- Invert: 255.255.255.255 XOR 0xFFFFFFFF = 0.0.0.0
- Result: `0.0.0.0/0` (entire IPv4 space)
- Rationale: When first IP is all-zeros and second is broadcast, hostmask interpretation represents "all networks"

**General Reserved Value Handling (when not matching special patterns above)**:

When second value is 0.0.0.0 or 255.255.255.255 but NOT in the special patterns above:
- If format hint is conclusive (`netmask_dominant` or `hostmask_dominant`): Use hint (hint takes priority)
- If format hint is inconclusive (`mixed` or `unknown`):
  - 0.0.0.0: Try hostmask (MSB=0 preference)
  - 255.255.255.255: Try netmask (MSB=1 preference)
  - If selected format fails validation, try the other format as fallback

**Important Context**: Format hints are generated only from values that could be parsed in the current parsing context. Therefore:
- If `--parse-hostmask=none` for this context, no hostmask values are scanned during hint generation
- No `hostmask_dominant` hint can be generated for that context
- If a hint IS conclusive in a context, that format is guaranteed to be enabled
- Hints have priority over reserved value fallback logic when conclusive

---

## Two-Value Pattern Parsing Algorithm

When processing a two-IP-address pattern:

### Step 0: Check Prerequisites
1. Verify exactly two whitespace-separated IPv4 values
2. Neither contains `/` or `-` (not CIDR or range)
3. Both parse as valid IPv4 addresses
4. If any prerequisite fails → treat as two separate IPs

### Step 1: Determine Parsing Availability
- Check if `--parse-netmask` is enabled in this context (pattern or input)
- Check if `--parse-hostmask` is enabled in this context
- If both disabled → extract both values as separate /32 IPs

### Step 2: Determine Format via MSB and Format Hints

Determine which format (netmask or hostmask) to attempt based on MSB and format hints:

1. **Check special patterns first** (see Reserved Values section):
   - If pattern is `255.255.255.255 0.0.0.0`: Handle per special pattern rules
   - If pattern is `0.0.0.0 255.255.255.255`: Handle per special pattern rules
   - Otherwise, continue to standard MSB logic

2. **Determine MSB of second value**:
   - MSB = 1 (binary starts with 1) → netmask format preference
   - MSB = 0 (binary starts with 0) → hostmask format preference

3. **Apply format hint if conclusive**:
   - If hint is `netmask_dominant`: Override MSB, try netmask first
   - If hint is `hostmask_dominant`: Override MSB, try hostmask first

4. **Follow standard logic if hint inconclusive**:
   - If hint is `mixed` or `unknown`: Use MSB preference from step 2

### Step 3: Try Netmask Format (if MSB=1 or netmask_dominant hint)

**Condition**: (MSB is 1 OR hint is `netmask_dominant`) AND netmask parsing enabled

1. Verify second value is contiguous 1s-then-0s
2. If yes → Parse as subnet mask, done
3. If no → Extraction fails, continue to Step 4

### Step 4: Try Hostmask Format (if MSB=0 or hostmask_dominant hint)

**Condition**: (MSB is 0 OR hint is `hostmask_dominant`) AND hostmask parsing enabled

1. Verify second value is contiguous 0s-then-1s
2. Invert to get netmask
3. If inversion is valid → Parse as hostmask, done
4. If no → Extraction fails, continue to Step 5

### Step 5: Fallback to Two Separate IPs

If neither netmask nor hostmask format succeeded, extract both values as separate /32 addresses.

---

## Format Hint Detection

**What are hints?** When parsing input files, grepnet analyzes the first 8KB to detect if two-value patterns prefer netmask or hostmask format. This hint improves heuristics for ambiguous values.

**Four hint values**:
- `netmask_dominant`: ≥66% of clear two-value patterns are netmask format
- `hostmask_dominant`: ≥66% of clear two-value patterns are hostmask format
- `mixed`: Roughly equal netmask and hostmask patterns detected
- `unknown`: Too few patterns or all ambiguous to determine

**Detection process**:
1. Scan first 8KB of input for two-value patterns
2. Skip ambiguous values (0.0.0.0, 255.255.255.255)
3. Classify each pattern by MSB and contiguity
4. Calculate percentages
5. Assign hint value

**Scope**: Hints apply to all lines from an input source, NOT to patterns (CLI arguments)

**Gating**:
- `--scan-mask=both` (default): Detect from both patterns and input
- `--scan-mask=input`: Detect from input files only
- `--scan-mask=pattern`: Detect from patterns only
- `--scan-mask=none`: Disable detection (always use MSB-based logic)

**Critical behavior**: Hints are context-aware by design. Since hint generation respects parsing context constraints (only scans enabled formats), any conclusive hint generated is guaranteed compatible with that context. Therefore:
- Hints DO override reserved value fallback logic when conclusive and context allows
- If hint is `netmask_dominant`: Apply netmask parsing even for 255.255.255.255
- If hint is `hostmask_dominant`: Apply hostmask parsing even for 0.0.0.0
- Reserved value fallback logic only applies when hints are `mixed` or `unknown`

---

## Examples

### Example 1: Basic Netmask Pattern
```
Input: "192.0.2.0 255.255.255.0"
MSB of 255.255.255.0 = 1 (netmask format)
Contiguous? Yes (24 ones, 8 zeros)
Result: 192.0.2.0/24
```

### Example 2: Basic Hostmask Pattern
```
Input: "192.0.2.0 0.0.0.255"
MSB of 0.0.0.255 = 0 (hostmask format)
Contiguous? Yes (0 zeros, 8 ones)
Inverted: 0.0.0.255 XOR 0xFFFFFFFF = 255.255.255.0
Result: 192.0.2.0/24
```

### Example 3: Reserved Value 0.0.0.0 with No Hint
```
Input: "192.0.2.1 0.0.0.0"
MSB of 0.0.0.0 = 0 (RESERVED, suggests hostmask)
Hint = unknown (no conclusive hint)
Apply fallback: 0.0.0.0 → Use hostmask (if enabled)
Inverted: 0.0.0.0 XOR 0xFFFFFFFF = 255.255.255.255
Result: 192.0.2.1/32
```

### Example 3b: Reserved Value 0.0.0.0 with Netmask-Dominant Hint
```
Input: "192.0.2.1 0.0.0.0"
MSB of 0.0.0.0 = 0 (normally suggests hostmask)
Hint = netmask_dominant (conclusive hint that netmask parsing is enabled)
Hint takes priority: Try netmask parsing for 0.0.0.0
Note: 0.0.0.0 is NOT contiguous 1s-then-0s, so netmask parsing fails
Fall through to hostmask parsing for 0.0.0.0
Inverted: 0.0.0.0 XOR 0xFFFFFFFF = 255.255.255.255 (valid hostmask)
Result: 192.0.2.1/32
```

### Example 4: Reserved Value 255.255.255.255 with No Hint
```
Input: "192.0.2.5 255.255.255.255"
MSB of 255.255.255.255 = 1 (RESERVED, suggests netmask)
Hint = unknown (no conclusive hint)
Apply fallback: 255.255.255.255 → Use netmask (if enabled)
Result: 192.0.2.5/32
```

### Example 4b: Reserved Value 255.255.255.255 with Hostmask-Dominant Hint
```
Input: "192.0.2.5 255.255.255.255"
MSB of 255.255.255.255 = 1 (normally suggests netmask)
Hint = hostmask_dominant (conclusive hint that hostmask parsing is enabled)
Hint takes priority: Try hostmask parsing for 255.255.255.255
Note: 255.255.255.255 is NOT contiguous 0s-then-1s, so hostmask parsing fails
Fall through to netmask parsing for 255.255.255.255
Result: 192.0.2.5/32
```

### Example 5: Format Hint Tie-Breaking
```
File contains: "192.0.2.0 255.255.255.0" and "192.0.2.0 255.255.255.255"
Detected as: netmask_dominant

Line 1: "192.0.2.0 255.255.255.0"
  MSB = 1, hint = netmask_dominant
  Try netmask → Success → 192.0.2.0/24

Line 2: "192.0.2.0 255.255.255.255"
  MSB = 1, hint = netmask_dominant
  Try netmask → Success → 192.0.2.0/0
```

### Example 6: Parsing Flags Control Format Choice
```
Input: "192.0.2.1 0.0.0.255"
MSB = 0 (hostmask format)

--parse-hostmask=both → Try hostmask first → Success → 192.0.2.0/24
--parse-hostmask=none → Hostmask disabled → Try netmask → Fail → Two IPs: 192.0.2.1/32, 0.0.0.255/32
```

### IP Range Parsing

Two formats supported, with no spaces around the dash:

**Long form**: `192.0.2.0-192.0.2.255` (full start and end addresses, dash is compact)
1. Split on `-` character (must be immediately adjacent to both IPs)
2. Parse both parts as IP addresses
3. Validate start ≤ end
4. Create IPRange object with integer representation of both addresses

**Short form**: `192.0.2.0-255` (start IP, then only last octet of end, dash is compact)
1. Split on `-` character (must be immediately adjacent to both parts)
2. Parse first part as IPv4 address
3. Parse second part as single 0-255 octet
4. Construct full end IP by replacing last octet of start with second part
5. Validate start ≤ end
6. Create IPRange object

**Important**: `192.0.2.0 - 192.0.2.1` (with spaces around the dash) is NOT a range. It fails range parsing and continues to plain IP extraction, producing two separate IPs (`192.0.2.0/32` and `192.0.2.1/32`).

**Parsing control**:
- `--parse-ranges`: Enable both forms (compact only)
- `--parse-ranges-long`: Long form only (compact only)
- `--parse-ranges-short`: Short form only (compact only)

### Unsupported Network Formats

The following formats are explicitly NOT supported and will not be recognized:

**Short-form CIDR notation** (e.g., `192.0.2/24`, `10/8`, `0/0`):
- These abbreviated CIDR expressions omit the final octet
- NOT recognized by grepnet
- Will be treated as plain text/patterns, not network objects
- Reason: Ambiguous in some contexts; canonical CIDR (`192.0.2.0/24`) is unambiguous and recommended

**IP ranges with spaces** (e.g., `192.0.2.0 - 192.0.2.255`):
- Spaces around the dash are NOT supported
- The compact format `192.0.2.0-192.0.2.255` (no spaces) IS supported
- If spaces are present, parsing fails and falls through to plain IP extraction
- Example: `192.0.2.0 - 192.0.2.255` extracts two separate IPs: `192.0.2.0/32` and `192.0.2.1/32`
- Reason: Spaces introduce parsing ambiguity; compact format is more reliable

**IPv6 with zone identifiers** (e.g., `fe80::1%eth0`, `fe80::1%1`):
- Zone IDs (the `%` suffix) are NOT supported
- Only standard RFC 4291 IPv6 formats (compressed and uncompressed) are recognized
- Zone IDs are non-routable and context-specific; excluded from network matching

### Plain IP Address Parsing

**Format**: Single IP address (IPv4 or IPv6)

**Treatment**: Convert to /32 (IPv4) or /128 (IPv6) network object.

**Gating control**: The `--parse-bare-ip` option controls whether plain IP addresses (bare IPs without explicit prefix notation) are extracted. When disabled, only IP addresses with explicit prefix notation (e.g., `192.0.2.0/32` or `::1/128`) are accepted.

**Examples**:
- If `--parse-bare-ip=both` (default): Both `192.0.2.0` and `192.0.2.0/32` are parsed, both treated as /32 networks
- If `--parse-bare-ip=pattern`: Only bare IPs in patterns are parsed, bare IPs in input files are skipped
- If `--parse-bare-ip=input`: Only bare IPs in input files are parsed, bare IPs in patterns are treated as literals
- If `--parse-bare-ip=none`: Neither `192.0.2.0` nor `::1` are parsed (skipped entirely); only explicit notation like `192.0.2.0/32` or `::1/128` can be used to specify single addresses

### False-Positive Filters

The parser contains semantic filters to avoid matching things that look like IP addresses but are not:

**Numeric OID detection**: Numeric SNMP OIDs (e.g., `1.3.6.1.2.1.1.1.0`) look like dotted-decimal addresses and can be mistaken for networks. Detect these by checking if a line contains 4+ dot-separated numeric parts where each part is 0-4 digits (matching SNMP OID structure). If such a pattern is detected on a line, do not extract plain IPs from that line (they are OID components, not addresses). However, CIDR notation (with `/` and prefix) should still be extracted even on such lines.

**IPv6 embedding**: Prevent matching IPv6 addresses embedded in larger identifiers (e.g., don't match `2001:db8::1` inside `foo2001:db8::1bar`). Use boundary checks to ensure IPv6 is not adjacent to alphanumeric characters or additional colons.

**IPv6 zone IDs**: IPv6 addresses with zone identifiers (e.g., `fe80::1%eth0` or `fe80::1%1`) are NOT supported and should not be matched. Only standard RFC 4291 compressed and uncompressed IPv6 formats are recognized.

### Strict CIDR Enforcement (v2.0 API)

Strict mode is controlled by two independent flags:
- **WHERE**: `--strict-cidr={pattern|input|both|none}` determines which scope to validate
- **WHAT**: `--strict-cidr-action={fail|normalize|ignore|warn}` determines the error handling

**Behaviors**:
- **Pattern strictness** (`--strict-cidr=pattern`): Validate patterns for malformed CIDR
- **Input strictness** (`--strict-cidr=input`): Validate input file content for malformed CIDR
- **Both strictness** (`--strict-cidr=both`): Validate both patterns and input
- **No strictness** (`--strict-cidr=none`, default): Permissive parsing, normalize malformed CIDR

**Error handling**:
- `--strict-cidr-action=fail`: Exit immediately with error code 2 on first malformed CIDR
- `--strict-cidr-action=normalize`: Accept and normalize malformed CIDR (default)
- `--strict-cidr-action=ignore`: Silently skip any malformed CIDR
- `--strict-cidr-action=warn`: Print warning to STDERR, then skip and continue

**Real-world CIDR notation** (host bits in CIDR expression):

CIDR expressions with host bits set are COMMON in operational configurations and are NOT errors:
- Router interface configs: `ip addr 192.0.2.5/24` (device's IP is .5 within the /24 network)
- Cisco static routes: `ip route 192.0.2.5 255.255.255.0` (route to host .5 in a /24)
- Network device logs: `gateway 192.0.2.1/24` (gateway address within /24)

These expressions use the device's actual IP address (with host bits set) rather than the network address. grepnet must accept and normalize these:
- `192.0.2.5/24` → Normalized to `192.0.2.0/24` (canonical network form)
- `192.0.2.1 255.255.255.0` → Normalized to `192.0.2.0/24`
- Each text variation tracks its own normalization: `{"text": "192.0.2.5/24", "was_normalized": true}`
- Network object uses canonical form: `network=192.0.2.0/24` (what's actually matched)
- Group-level was_normalized flag indicates if ANY matched_text required normalization

**Strict mode behavior**:
- `--strict-cidr=input` + `--strict-cidr-action=fail`: Exit immediately when host bits detected (for validation/audit)
- `--strict-cidr=input` + `--strict-cidr-action=warn`: Log warning, continue processing
- `--strict-cidr=input` + `--strict-cidr-action=ignore`: Skip networks with host bits silently
- Default (no strict mode): Accept, normalize, and process (most common use case)

**Invalid CIDR patterns** (not CIDR notation; regex fails at pattern stage):
- `192.0.2.0/33` (prefix out of range) → Regex does not match → treated as plain IP `192.0.2.0` (no strict mode error)
- `192.0.2.0/abc` (prefix not numeric) → Regex does not match → treated as plain IP `192.0.2.0` (no strict mode error)
- These do NOT trigger strict mode errors because they never matched the CIDR regex in the first place; they are not CIDR notation at all

---

## File Discovery and Scanning

### Input Source Determination

Three possible input sources, in order of priority:

1. **Stdin**: If no files specified and stdin is not a terminal (piped data)
2. **Explicit file list**: Files from positional argument or `-F` flags
3. **Directory recursion**: If `--recursive` or `--dereference-recursive`

If none of these yield files, exit with error code 2.

### File List Validation

Before scanning, validate all files:
1. Check each file exists
2. If file does not exist and not stdin, emit warning (unless `--quiet` or `--no-messages`)
3. Continue with remaining valid files

### Binary File Handling

Before scanning a file, detect if it is binary:

**Detection method**: Read the first chunk (8KB) and check for:
- Null bytes (strong indicator of binary)
- Lack of printable text markers
- High percentage of non-printable control characters (>30%)

**Critical Optimization: Single 8KB Buffer for Multiple Operations**

The first 8KB is read ONCE and cached. This buffer is reused for BOTH:
1. **Binary detection** — scanned for null bytes and non-printable characters
2. **Mask format hint detection** — analyzed to determine netmask vs hostmask preference

Then the file continues to be read sequentially from byte 8KB onward. This eliminates:
- No redundant file reads
- No file close/reopen cycles
- No seeking back to the beginning
- One file handle open for the entire scan

The file remains open from initial 8KB read through complete line iteration.

**VTY Protection**: grepnet applies VTY (Virtual Terminal) protection for binary input, similar to grep:
- Binary files are **always searched** to find matches (this matches grep's default behavior)
- When binary data (null bytes or improperly encoded data) is detected, **line output is suppressed** to prevent terminal corruption
- Instead of showing line content, report "Binary file <filename> matches" to indicate matches were found
- This prevents terminal state corruption from unexpected control characters or binary sequences

**Handling modes** (controlled by `--binary-files`):
- `binary` (default): Search binary files normally. When null bytes or improperly encoded data is found, suppress line output and report "Binary file X matches". Note: this means `-l`, `-L`, `-c` modes will work (they don't output line content anyway).
- `text`: Process all files as text, output line content normally regardless of null bytes (equivalent to `-a` flag)
- `without-match` (equivalent to `-I`): When null bytes detected, treat the entire file as non-matching (don't report matches)

**Why special modes work with binary files**:
- `-l` / `--files-with-matches`: Works because it outputs filename, not line content
- `-L` / `--files-without-match`: Works because it outputs filename, not line content  
- `-c` / `--count`: Works because it outputs count, not line content
- These modes benefit from the default binary-file search behavior

**Null-data mode interaction** (`-z` / `--null-data`):
- When `-z` is used, NUL bytes are intentional record delimiters, not binary corruption markers
- NUL-delimited files should be processed as text, not skipped
- Automatically sets `binary_files=text` mode to ensure proper processing

**Implementation**: When binary is detected in default mode with normal output (not `-l`, `-L`, `-c`):
1. Search the file for matches (iterate through lines)
2. When matches are found but contain null bytes or improperly encoded data, suppress line output
3. Report "Binary file <filename> matches" to indicate matches exist but output is suppressed

### Implementation Note: VTY Protection Strategy with Single 8KB Buffer

**Recommended approach** for implementers:

1. **Unified 8KB buffer workflow**:
   - Read first 8KB from file and cache it
   - Keep file handle open (do NOT close after reading 8KB)
   - Use cached 8KB buffer for BOTH binary detection AND mask format hint detection
   - Continue reading the file sequentially from byte 8KB onward
   - This ensures single file open, zero file seeks, zero redundant reads

2. **Early detection**: Check if file is binary **before** processing begins (not during line iteration)
   - Avoid reading entire binary file searching for networks (expensive)
   - Single 8KB chunk read is sufficient for detection
   - Reuse this same 8KB for format detection (masked format patterns)

3. **Mode-based handling**:
   - **Mode `binary` (default)**: Always search and iterate, but suppress line output when improperly-encoded data detected. Report "Binary file X matches" if matches found.
   - **Mode `text`**: Process normally, output as text (user accepts terminal risk)
   - **Mode `without-match`**: Iterate normally to find matches, but replace output with "Binary file X matches" if matches found

4. **Integration with InputSource abstraction**:
   - Each InputSource knows its binary status (`get_binary_status()` method)
   - Each InputSource caches mask format hint via `get_mask_format_hint()` method
   - Both methods use the SAME cached 8KB buffer
   - Caller decides action: skip, process, or report
   - No binary-specific code in main processing loop
   - Mask format hint is applied to all line parsing after 8KB

5. **Error handling**:
   - Malformed UTF-8 in text/without-match modes: Use replacement characters or skip line
   - Null bytes in text mode: Preserve or replace depending on output format
   - Graceful degradation: Continue processing even with binary-safe encoding errors

**Example implementation**:
```
source = InputSource('file', file_path='example.txt')

# Both of these call get_binary_status() which reads and caches 8KB
is_binary = source.get_binary_status()
mask_hint = source.get_mask_format_hint(scan_mask='both')

# File handle is still open, positioned at byte 8KB
# Now iterate lines, which continues reading from 8KB onward
if is_binary:
    if args.binary_files == "binary":
        skip_file()  # Return immediately
    elif args.binary_files == "without_match":
        process_file()  # Find matches
        if matches_found:
            output("Binary file X matches")
        return  # Don't output content
    # else: text mode, fall through to normal processing

# Normal processing (text files or binary in text mode)
# Apply mask_hint to all parse_line() calls
for line_number, line_content, byte_offset in source.lines():
    # Use mask_hint when parsing this line
    extractions = parser.parse_line(line_content, mask_format_hint=mask_hint)
    ...
```

### Recursive Directory Discovery

When `--recursive` or `--dereference-recursive`:

1. Walk directory tree starting from specified paths
2. For each entry, check:
   - Is it a directory?
     - If `--directories=recurse` (default): descend
     - If `--directories=skip`: skip
     - If `--directories=read`: attempt to read as a file (usually fails)
   - Is it a device file? (special file, socket, etc.)
     - If `--devices=skip` (default): skip
     - If `--devices=read`: read as a file
   - Is it a symlink?
     - If `-R` (`--dereference-recursive`): follow
     - If `-r` (`--recursive`): follow only if on command line, not in recursion
3. Apply include/exclude glob patterns to filename
4. Apply exclude directory patterns to directory names (to skip branches)
5. Collect valid files in result list

**Exclude patterns** (loaded from `--exclude`, `--exclude-from`):
- Glob-style patterns (e.g., `.log`, `.git/`)
- One pattern per line in exclude file

---

## InputSource Abstraction

### Overview

The InputSource abstraction provides a unified interface for reading text from multiple input sources: regular files, standard input (stdin), and file descriptors (e.g., from process substitution). This abstraction eliminates ad-hoc type-checking code throughout the codebase and provides a clean contract for binary file detection that respects the stream-destructive nature of stdin.

**Design principle**: "INPUT IS INPUT" — All input sources yield identical data structures regardless of origin, allowing the matching pipeline to remain agnostic about input type.

### InputSource Specification

#### Constructor

```
InputSource(
    source_type: str,
    file_path: Optional[str] = None,
    fd: Optional[int] = None,
    label: Optional[str] = None
)
```

**Parameters**:
- `source_type`: One of three values:
  - `'file'`: Input from a regular file on disk; `file_path` must be provided
  - `'stdin'`: Input from standard input stream
  - `'fd'`: Input from a file descriptor; `fd` must be provided
  
- `file_path`: (required for `'file'`) Absolute or relative path to input file

- `fd`: (required for `'fd'`) File descriptor number (typically 0 for stdin aliasing, or descriptor from process substitution)

- `label`: (optional, used with `--label` flag) Custom display label for stdin or fd sources. Used in output contexts like `-H`/`--with-filename` to identify the source when a user-friendly name is desired. If not provided, stdin/fd sources display as unnamed.

#### Properties

##### `file_type`

Returns the source type as a string: `'file'`, `'stdin'`, or `'fd'`.

**Rationale**: Provides caller with source classification for display logic (e.g., in MatchResult assembly).

##### `display_name`

Returns an optional string for display purposes in `-H`/`--with-filename` output contexts:
- **For `'file'` sources**: Returns the `file_path` 
- **For `'stdin'` and `'fd'` sources**:
  - If `label` was provided (from `--label` flag): Returns the label string
  - If `label` was NOT provided: Returns `None` (indicating the source should not be labeled)

**Semantic guarantee**: `display_name is None` means "do not show a filename header for this source" (only true for unlabeled stdin/fd). `display_name is not None` means "show this value as the filename in output headers."

#### Methods

##### `get_binary_status() -> bool`

Detects whether the input source contains binary data.

**Contract**:
- Returns `True` if the source appears to be binary; `False` if text-like
- Lazy evaluation: Result is computed once on first call and cached for subsequent calls
- **Peek buffer strategy (ALL input sources)**: Reads and caches the first 8KB (8192 bytes) from the source before analyzing. This buffer is stored internally and will be prepended during line iteration. This applies uniformly to all input types (files, stdin, fd) to be consistent with the "All Input Is Input" principle.

**Binary detection algorithm** (applies to ALL input sources uniformly):
1. Read first 8KB (8192 bytes) of source and cache in peek buffer (internal `_peek_buffer`)
2. Check for null bytes (0x00) — strong indicator of binary
3. Count non-printable control characters (excluding common whitespace like \n, \r, \t)
4. If null bytes present OR >30% non-printable characters, mark as binary
5. Return boolean result
6. Cached peek buffer will be used during line iteration (see below)

**Critical design**: The 8KB buffer read during binary detection is NEVER lost. It is cached internally in the InputSource and will be prepended to line iteration output. This prevents inefficient double-reads:
- For stdin/fd: Avoids the common bug where binary detection consumes the first 8KB, leaving the stream at byte 8193
- For files: Avoids redundant file opens/reads for binary detection and line iteration by caching the first chunk
- Unified approach: All input types (files, stdin, fd) use the same peek buffer mechanism

##### `lines() -> Iterator[Tuple[int, str, int]]`

Yields all lines from the input source in order.

**Yields**:
- **Line number** (integer, 1-based): Absolute position in the stream (1 is first line, 2 is second, etc.)
- **Line content** (string): The text of the line, with trailing newline and carriage return characters removed (`\n` and `\r` stripped)
- **Byte offset** (integer, 0-based): Position in the file where the line starts (byte index). 
  - For file sources: Accurate byte offset within the file
  - For stdin/fd sources: Always 0 (stdin/fd streams don't have meaningful absolute positions)

**Iteration contract**:
- Yields lines in order from the source
- Each line is a distinct iteration step
- Does not include the trailing newline character in the yielded text
- Handles both Unix (`\n`) and Windows (`\r\n`) line endings
- If the source ends without a trailing newline (incomplete final line), that final line is still yielded

**Peek buffer integration** (ALL input sources):
- If `get_binary_status()` was called prior to line iteration:
  - The first 8KB (peek buffer) was cached during binary detection
  - Line iteration automatically yields lines from the cached buffer first
  - After cached lines are exhausted, continues reading remaining source data
  - Caller is unaware of buffering; iteration appears seamless
- Applies uniformly to files, stdin, and fd sources

##### `close() -> None`

Closes and cleans up resources associated with the input source.

**Behavior**:
- For file sources: Closes the open file handle (if one exists)
- For stdin/fd sources: Typically a no-op (stdin and fd are managed by the runtime)
- Safe to call multiple times: Subsequent calls after first close() are no-ops

### Peek Buffer Strategy (GREPNET-SPEC Implementation)

**Problem**: Binary detection requires reading ahead from the source without wasting that read:
- For stdin/fd: `os.read(fd)` consumes stream data, leaving it at byte 8193 and losing the first 8KB
- For files: Without caching, file must be opened twice (once for binary detection, once for iteration) - wasteful

**Solution: Unified peek buffer caching (applies to ALL input sources)**:

**Principle**: Consistent with "All Input Is Input" - all input types use the same efficient approach.

**Implementation**:

1. **Early read** (`get_binary_status()` call):
   - Read first 8KB (8192 bytes) from the source (file, stdin, or fd)
   - Store result in internal `_peek_buffer` (bytes object)
   - Analyze buffer with `BinaryDetector.is_binary_from_buffer()` to avoid additional stream reading

2. **Cached analysis**:
   - New method `BinaryDetector.is_binary_from_buffer(buffer)` takes pre-read bytes and returns binary status
   - Does NOT perform additional file opens or stream reads
   - Works identically for files, stdin, and fd

3. **Buffered iteration** (`lines()` method):
   - Check if peek buffer exists (was cached during binary detection)
   - If yes, yield lines from buffer first (split on `\n`)
   - Then continue yielding from remaining source data via normal iteration
   - Caller sees seamless iteration; buffering is transparent

**Benefits**:
- **Files**: Single file open; 8KB read is reused for both binary detection and line iteration (no double-read)
- **Stdin/fd**: First 8KB is cached and safely returned to caller during iteration (no data loss)
- **Unified**: All input types behave consistently; same code path for all

**This implements the directive**: "YOU HAVE SPECIFIC INSTRUCTIONS TO CACHE THE FIRST 8K, SCAN IT, UNLOAD IT AND CONTINUE TO READ THE FILE"

### Mask Format Detection from Peek Buffer (--scan-mask flag)

**Objective**: Use the cached 8KB peek buffer (from binary detection) to analyze what format predominates in the file/pattern - netmask or hostmask - and provide hints to the parser for more intelligent extraction decisions.

**Critical Optimization**: Mask format scanning reuses the SAME cached 8KB peek buffer populated during binary detection. This ensures single 8KB read for both binary detection AND format hint detection, with ZERO redundant file reads.

**Mechanism**:

1. **Reuse cached 8KB peek buffer from binary detection**:
   - During binary detection, first 8KB is read and cached in InputSource
   - Format detection analyzes this SAME cached buffer (no new read)
   - **CRITICAL**: Respect parsing context constraints during hint generation
     - If `--parse-netmask=none` for this source: Do NOT scan for netmask patterns
     - If `--parse-hostmask=none` for this source: Do NOT scan for hostmask patterns
     - Only scan formats that are enabled in the current parsing context
     - This ensures hints generated are guaranteed compatible with that context
   - Analyze the buffer for format indicators (separate from binary detection analysis)
   - Scan two-value patterns and classify each second value (only for enabled formats):
     - **Clearly netmask** (if netmask parsing enabled): Contiguous 1-bits from MSB followed by 0-bits (e.g., 255.255.255.0)
     - **Clearly hostmask** (if hostmask parsing enabled): Contiguous 0-bits from MSB followed by 1-bits (e.g., 0.0.0.255)
     - **Ambiguous**: All zeros (0.0.0.0), all ones (255.255.255.255), non-contiguous, or invalid
   - Count only clearly netmask and clearly hostmask patterns (from enabled formats only)
   - Skip all ambiguous patterns (hoping neighboring patterns provide clarity)
   - Calculate format dominance ratio from counted patterns (threshold: >66% for dominance)

2. **Cache format hint** in InputSource:
   - Store detected format preference (`'netmask_dominant'`, `'hostmask_dominant'`, `'mixed'`, `'unknown'`)
   - This hint is cached per InputSource instance and reused for all parsing of that source
   - No re-scanning occurs; one analysis per input source using the cached buffer
   - `'unknown'` is returned if no clearly-identifiable patterns found (≤1 total patterns)
   - **IMPORTANT**: Since hint generation respects parsing context, any hint generated is guaranteed compatible with that context
     - A `netmask_dominant` hint means netmask parsing IS enabled for this source
     - A `hostmask_dominant` hint means hostmask parsing IS enabled for this source
     - This guarantee ensures hints can be safely applied during parsing

3. **Use hint during parsing** (for all lines from that source):
   - The cached format hint applies to all lines parsed from this input source
   - When encountering ambiguous two-value patterns (e.g., `192.0.2.1 0.0.0.0`), the format hint MAY influence extraction strategy
   - If format hint is `'netmask_dominant'` or `'hostmask_dominant'`, use it as a tie-breaker for edge cases
   - If format hint is `'mixed'` or `'unknown'`, fall back to standard MSB-based two-value parsing algorithm (see "Normal Two-Value Parsing Algorithm" section)
   - The hint is NEVER a directive; standard MSB-based logic is always the authoritative source

   **Fallback behavior**:
   - Format detection is best-effort; ambiguous patterns don't contribute to the hint
   - When hint is `'unknown'`, parsing uses the standard MSB-based algorithm with no special heuristics
   - When hint is `'mixed'`, both formats appear in the peek buffer; parsing uses standard algorithm to handle each pattern individually
   - This ensures predictable, spec-compliant behavior when format cannot be determined

**Gating with --scan-mask flag**:
- `--scan-mask=both` (default): Analyze patterns and input files
- `--scan-mask=input`: Analyze only input files
- `--scan-mask=pattern`: Analyze only patterns
- `--scan-mask=none`: Disable format detection (treat all two-value patterns with standard MSB-based logic)

**Examples**:
- File contains `0.0.0.0 0.0.0.0` and `192.0.2.1 0.0.0.255` → Skip first (all zeros), count second as hostmask → Detected as `'hostmask_dominant'`
- File contains `192.0.2.1 0.0.0.0` only → Skip (all zeros) → No clear patterns → Detected as `'unknown'` → FALLBACK
- File contains `192.0.2.0 0.0.0.255` and `192.0.2.0 255.255.255.0` → Conflicting formats → Detected as `'mixed'` → FALLBACK
- File contains `192.0.2.0 255.255.255.0` patterns → All clearly netmask → Detected as `'netmask_dominant'`

**Implementation note**: Format detection is a hint, not a directive. Ambiguous patterns (all zeros, all ones, non-contiguous) are excluded from analysis. The standard MSB-based two-value parsing algorithm (see "Normal Two-Value Parsing Algorithm" section) is always the authoritative source. 

**Critical behavior**: Since hint generation respects parsing context constraints (does not scan disabled formats), any conclusive hint generated is guaranteed to be compatible with that context. Therefore:
- If hint is `'netmask_dominant'`, use it as tie-breaker even for reserved values like 255.255.255.255 (netmask parsing IS enabled)
- If hint is `'hostmask_dominant'`, use it as tie-breaker even for reserved values like 0.0.0.0 (hostmask parsing IS enabled)
- Only the reserved value fallback logic (MSB-based) applies when hint is `'mixed'` or `'unknown'`

### Code Pattern Elimination

The InputSource abstraction eliminates these anti-patterns:

**Before** (ad-hoc type checking):
```python
if hasattr(source, 'file_path'):
    filename = source.file_path
else:
    filename = '(standard input)'

if filename != '(standard input)':
    print_with_filename(filename)

# Stream consumption bug: first 8KB lost
is_binary = BinaryDetector.is_binary_fd(fd)
for line_num, content in lines(fd):
    # First 8KB missing!
```

**After** (unified InputSource):
```python
# No type checking needed
if source.display_name:  # None for unlabeled stdin/fd
    output_header = source.display_name

# Binary detection respects streaming
is_binary = source.get_binary_status()  # Caches 8KB internally
for line_num, content, offset in source.lines():
    # All data (including first 8KB) is available!
```

### InputDiscovery Helper Class

The InputDiscovery class provides a factory interface for creating InputSource instances based on command-line arguments and environment state.

**Priority logic**:
1. If `use_stdin=True`: Return a single `InputSource('stdin', label=stdin_label)`
2. Else if `files` is non-empty: Create InputSource for each file/directory (recursively if flags set)
3. Else: Default to stdin if not a terminal

---

## Search and Matching Logic

### Pattern Preprocessing

When patterns are provided, they must be normalized:

**Pattern extraction**: Each pattern argument is processed using the same extraction pipeline as file content:
- Apply comment handling (strip comments before parsing)
- Run extraction order: CIDR notation, subnet mask, inverse mask, ranges, plain IPs
- All false-positive filters (OID detection, IPv6 embedding checks) apply
- If multiple networks are extracted from a single pattern argument, each becomes a separate search pattern
  - Example: `192.0.2.0/24:198.51.100.0/24` → extracts two networks → two patterns
  - Example: `2001:db8::1` → single IPv6 → one pattern (colon is NOT a delimiter for IPv6)
  - Example: `1.3.6.1.2.1.1.0` on a line with other networks → OID detection skips plain IPs but other networks still extract

**Deduplication**: Remove exact duplicate patterns (networks representing the identical set of IP addresses) after extraction. Different-sized networks are preserved as separate patterns—for example, `192.0.2.0/24` and `192.0.2.0/25` are both retained because they represent different address spaces (256 vs. 128 addresses). A duplicate is only removed if extracted networks are network equal (same address family, same network address, same prefix length).

**Error handling**: Each pattern is parsed using the pattern parser (with its strictness settings)
- If a pattern argument yields no valid networks, skip silently (do not emit warning or error)
- Each unique network extracted from patterns becomes a ParsedExtraction with format_type and matched_texts

### Match Type Resolution

Determine which match types to perform based on flags:

- If `-e` specified: add `'equals'`
- If `-s` specified: add `'subset'`
- If `-S` specified: add `'superset'`
- If `-O` specified: add `'overlap'`
- If `-u` specified: add `'unmatched'` (networks that don't match any pattern)
- If none of these five are specified: use default four match types `['equals', 'subset', 'superset', 'overlap']`

**Combining match types**: Any or all flags can be combined. For example:
- `-e -s` → equals and subset only
- `-e -s -u` → equals, subset, and unmatched networks
- `-O -u` → overlap and unmatched networks
- `-u` alone → only unmatched networks (match_type 'unmatched')
- (no flags) → all four default match types (equals, subset, superset, overlap)

**Standard grep inversion** applied to match types:
A line is "extracted" (matched) if any network on the line has a `match_type` in the active match type set. The `-v` flag inverts this: show only lines that are NOT extracted.

**Active match type set** determined by flags:
- Default (no flags): {equals, subset, superset, overlap}
- With `-e`: add equals
- With `-s`: add subset
- With `-S`: add superset
- With `-O`: add overlap
- With `-u`: add unmatched

**Examples**:
- `-v 192.0.2.0/24`: Active types = {equals, subset, superset, overlap}. Show lines where NO networks match these types.
- `-u 192.0.2.0/24`: Active types = {equals, subset, superset, overlap, unmatched}. Show lines where ANY network matches these types (including unmatched networks).
- `-v -u 192.0.2.0/24`: Active types = {equals, subset, superset, overlap, unmatched}. Show lines where NO networks match these types (even 'unmatched'). Since 'unmatched' is now active, unmatched networks are considered matches and thus excluded by `-v`.

### Network Comparison Logic

Four relational predicates are implemented:

**1. Equality (`equals`)**

Two networks are equal if they represent the same set of IP addresses.

For CIDR networks:
- Network address is the same
- Prefix length is the same
- (Implicitly: broadcast address is the same)

For ranges:
- Start address is the same
- End address is the same
- Family is the same (IPv4 vs IPv6)

Cross-type: A CIDR can be equal to a range if the range covers exactly the CIDR's address space.

Color code when equality match found: `me=` (match type equals, meaning networks are identical)

**2. Subset (`subset`)**

Pattern is a SUBSET of file data (file contains pattern), but NOT equal.

Logical definition: All addresses in the pattern are also in the file data, AND the networks are not identical.

For CIDR: Pattern prefix > file prefix (strictly more specific), and pattern is within file's address space.
         Equivalently: file must NOT equal pattern.

For ranges: Pattern start ≥ file start AND pattern end ≤ file end AND (pattern start > file start OR pattern end < file end).
           Equivalently: ranges must NOT be equal.

Note: EQUAL networks are reported with match_type EQUALS, never with SUBSET or SUPERSET.

Color code when subset match found: `mb=` (match type subset, meaning pattern is a subset of data)

**3. Superset (`superset`)**

Pattern is a SUPERSET of file data (pattern contains file), but NOT equal.

Logical definition: All addresses in the file data are also in the pattern, AND the networks are not identical.

For CIDR: Pattern prefix < file prefix (strictly less specific), and file is within pattern's address space.
         Equivalently: file must NOT equal pattern.

For ranges: Pattern start ≤ file start AND pattern end ≥ file end AND (pattern start < file start OR pattern end > file end).
           Equivalently: ranges must NOT be equal.

Note: EQUAL networks are reported with match_type EQUALS, never with SUBSET or SUPERSET.

Color code when superset match found: `mS=` (match type superset, meaning pattern is a superset of data)

**4. Overlap (`overlap`)**

Pattern and file data have overlapping but neither is subset/superset.

Logical definition: Some but not all addresses overlap; neither network contains the other.

**Critical note - CIDR networks CANNOT overlap**: Due to binary alignment and the contiguous nature of subnet masks and hostmasks, two CIDR-based networks can only have three relationships:
- **Equals**: Same network
- **Subset/Superset**: One contains the other
- **Disjoint**: Completely separate address spaces (no relationship, not "overlap")

OVERLAP ONLY OCCURS WITH IP RANGES: Arbitrary ranges like `192.0.0.0-192.0.0.100` and `192.0.0.50-192.0.0.150` can partially overlap (sharing `192.0.0.50-192.0.0.100` but each having unique addresses).

Example (ranges only): Pattern range `192.0.0.0-192.0.0.100` with file data range `192.0.0.50-192.0.0.150`. They share addresses `192.0.0.50-192.0.0.100`, but pattern has `192.0.0.0-192.0.0.49` and file has `192.0.0.101-192.0.0.150` unique to each.

Color code: `mo=` (match type overlap)

**5. Unmatched (`unmatched`)**

When using the `-u` flag, networks that do not match any search pattern are included in results with a special match_type.

Logical definition: Network exists in file but has no relation to any search pattern (not equals, subset, superset, or overlap).

Color code: `mu=` (match type unmatched, defaults to normal line text color `mt=` if `mu=` is not specified)

### Search Execution

For each search pattern:

1. Separate file entries into two groups: CIDR networks and ranges
2. Create two matcher objects: CIDRMatcher and RangeMatcher
3. For each search pattern:
   - Determine pattern type (CIDR or range)
   - Convert between types as needed (CIDR ↔ range)
   - Search against file networks using CIDRMatcher
   - Search against file ranges using RangeMatcher
   - Collect all matching indices and their match type (equals/subset/superset/overlap)
4. Filter results:
   - Keep only matches for requested match types
   - If `--invert-match`: Include lines that do NOT match any pattern
   - Apply exclusion filters (--exclude-string, --exclude-strings-file)
   - Apply inversion (--invert-match inverts entire line)
5. Assemble result objects with metadata (see detailed description in next section)

### Match Result Ordering

When a single file network matches multiple search patterns or matches the same pattern with different relational types, a deterministic priority order ensures consistent results across all implementations.

**Match Type Priority**:
When a network from the file is compared against all search patterns and yields multiple match types, the highest-priority match type is recorded:

```
Priority: equals > subset > superset > overlap > unmatched
```

Example: File network `192.0.2.0/24` is searched against patterns `192.0.2.0/24 192.0.2.0/29 192.0.0.0/8`:
- Matches `192.0.2.0/24` as equals ✓ (highest priority)
- Also matches `192.0.2.0/29` as superset (ignored, lower priority)
- Also matches `192.0.0.0/8` as superset (ignored, lower priority)
- Result: Single MatchResult with `match_type = 'equals'`

**Within Same Match Type**:
If a file network matches multiple patterns with the same match type, all patterns produce matches, but the network appears only once per line with that single match_type. The MatchResult shows all text variations (matched_texts) for that network, each preserving its own normalization status. For example, file line `192.0.2.0/24 and 192.0.2.0 255.255.255.0` searched against pattern `192.0.2.0/25` produces:
- One MatchResult with both `192.0.2.0/24` and `192.0.2.0 255.255.255.0` in matched_texts
- Both marked as SUPERSET (same match type)
- Content_colored shows both text variations styled with the same color

Example: File network `192.0.2.0/24 192.0.2.0 255.255.255.0` searched against `192.0.2.0/25`:
- Extracts as two texts representing same network (deduplicated to one ParsedExtraction)
- Matched_texts: [{"text": "192.0.2.0/24", "was_normalized": false}, {"text": "192.0.2.0 255.255.255.0", "was_normalized": false}]
- Result: Single MatchResult, both text variations marked in output

**Result Ordering Within a Line**:
Within a single line containing multiple networks:
- Networks ordered by extraction order: CIDR notation, subnet mask, inverse mask, ranges, plain IPs
- Within each network type, order by position in line: Networks are ordered by their byte offset (where they appear in the original line text)

Example: Line `Route 192.0.2.0/24 to 10.0.0.0/8 or 192.0.1.1`:
- Extraction: `192.0.2.0/24` (CIDR), then `10.0.0.0/8` (CIDR), then `192.0.1.1` (plain IP, treated as /32)
- Result ordering: Same order as extraction

**Result Ordering Across Lines**:
Results maintain file reading order:
- Lines are processed sequentially (line 1, line 2, ... line N)
- All matches from line 1 are output before any matches from line 2
- Within each line, networks follow extraction order (see above)

**Result Ordering Across Patterns**:
When multiple independent patterns are provided (via `-P`, `-f`, or pattern files), results are grouped by file and line, not by pattern order. The priority order within a line supersedes pattern sequence:

Example: Patterns `192.0.2.0/24` (pattern 1) and `192.0.0.0/8` (pattern 2), file has line: `192.0.2.0/24`:
- File network `192.0.2.0/24` matches pattern 1 as equals
- Same network matches pattern 2 as subset
- Result: Single MatchResult with `match_type = 'equals'` (priority)
- Pattern order is irrelevant; match type priority determines output

### Network Set Matching

Two matcher classes implement efficient network comparison:

**CIDRMatcher**

Optimized for comparing CIDR blocks. Internally organizes networks by:
- Address family (IPv4 vs IPv6)
- Prefix length (grouped by length)

Methods:
- `find_equal_matches(pattern)`: Networks equal to pattern
- `find_subset_matches(pattern)`: Networks that are subsets of pattern (file is subset of pattern)
- `find_superset_matches(pattern)`: Networks that are supersets of pattern (file is superset of pattern)
- `find_overlap_matches(pattern)`: Networks that overlap with pattern (but no subset/superset relation)

Implementation strategy: Use interval/range arithmetic on integer IP addresses. Convert CIDR to numeric start/end interval, then search for overlapping intervals in the matcher's data structure. Use binary search (bisect) on sorted prefix lengths to quickly locate candidates.

**RangeMatcher**

Optimized for comparing IP ranges. Internally stores ranges as (start, end) tuples organized by family and sorted by start address.

Methods:
- `find_equal_matches(start, end)`: Ranges with identical start and end
- `find_subset_matches(start, end)`: Ranges that are subsets (file range start ≥ pattern start AND file range end ≤ pattern end)
- `find_superset_matches(start, end)`: Ranges that are supersets (file range start ≤ pattern start AND file range end ≥ pattern end)
- `find_overlap_matches(start, end)`: Ranges that overlap (file range start ≤ pattern end AND file range end ≥ pattern start)

Implementation strategy: Use integer interval arithmetic. For subset/superset checks, use simple numeric comparisons. For overlap, use the standard interval overlap formula. Use binary search (bisect) on start addresses for quick location of candidates.

**Cross-Type Matching (CIDR ↔ Range)**

When the pattern is a CIDR and file contains ranges (or vice versa), convert between types:
- **CIDR → Range**: Convert CIDR network to its start and end integer addresses.
- **Range → CIDR**: Use `summarize_address_range()` (or equivalent) to convert a range into the minimal set of CIDR blocks covering that range. A range may require multiple CIDR blocks. Match the pattern against each block.

**Wildcard Mask Matching (WildcardMaskRange)**

When wildcard masks are enabled (`--parse-wildcard` and `--wildcard-search`):

- **Wildcard mask expansion**: Each WildcardMaskRange is expanded into a list of constituent CIDR blocks (stored in `expanded_cidrs`), pre-computed and aggregated using `ipaddress.collapse_addresses()`
- **Matching against wildcard masks**: Pattern is matched against each CIDR in the wildcard mask's expanded_cidrs list individually
  - Pattern matches if it has any relationship (equals, subset, superset, overlap) with ANY CIDR in the expanded list
  - All individual CIDR matches are treated as a single WildcardMaskRange match (not split into separate matches per CIDR)
- **Wildcard mask as pattern**: If a pattern is itself a wildcard mask:
  - Pattern is expanded to its constituent CIDRs
  - Each file network (whether CIDR, range, or wildcard mask) is compared against the pattern's expanded_cidrs
  - A file network matches if any of its addresses overlap with the pattern's address space
- **Bidirectional matching**:
  - File contains wildcard mask, pattern is CIDR → Compare pattern CIDR against all expanded_cidrs from file wildcard mask
  - File contains CIDR, pattern is wildcard mask → Compare file CIDR against all expanded_cidrs from pattern wildcard mask
  - Both are wildcard masks → Expand both, compare constituent CIDRs

**Match type priority** (unchanged): EQUALS > SUBSET > SUPERSET > OVERLAP > UNMATCHED

**Example**:
```
File line: deny 10.4.0.0 0.0.127.252 any
Pattern: 10.4.0.0/25

During parsing:
  - File: 10.4.0.0 0.0.127.252 → WildcardMaskRange(
      original_text='10.4.0.0 0.0.127.252',
      expanded_cidrs=[10.4.0.0/25, 10.4.1.0/24, 10.4.2.0/23, ..., 10.4.127.0/25]
    )
  - Pattern: 10.4.0.0/25 → CIDR(10.4.0.0/25)

During matching:
  - Pattern 10.4.0.0/25 compared against file WildcardMaskRange
  - Check: Does pattern equal any expanded CIDR? YES, 10.4.0.0/25 ∈ expanded_cidrs → EQUALS match
  - Result: Single MatchResult with match_type='equals', displayed as "deny [EQUALS: 10.4.0.0 0.0.127.252] any"
```

---

## Result Filtering and Output Rendering

### Extraction Logic (Applies to All Output Modes)

A line is "extracted" (considered a match) if any network on the line has a `match_type` in the active match type set.

**Active match type set** is determined by flags:
- Default (no flags): {equals, subset, superset, overlap}
- Each flag adds its corresponding type: `-e` adds equals, `-s` adds subset, `-S` adds superset, `-O` adds overlap, `-u` adds unmatched
- Flags are combinable: `-e -s` = {equals, subset}; `-u -O` = {overlap, unmatched}; etc.

The `-v` flag inverts this logic: Show only lines that are NOT extracted (none of their networks match the active types).

This extraction logic applies consistently across:
- Text output in normal mode (normal line display)
- JSON output (one object per extracted network)
- Table output (one row per extracted network)
- `-o` flag in normal mode (only-matching: show only the network text from matched lines)
- `--extract` mode (list all unique networks from input files)
- `--consolidate` mode (merge overlapping and adjacent networks from input files)

### Result Assembly

After matching, for each match, create a result object containing:
- File path
- Line number (1-based)
- Line content
- Pattern matched
- Match type (equals/subset/superset/overlap)
- Was the file CIDR normalized?
- Is this a context line?

### Exclusion Filtering

Two separate exclusion mechanisms can be combined:

#### --exclude-string (Textual/Regex Patterns)

If `--exclude-string` or `--exclude-strings-file` specified, filter results by text matching:

**Load patterns**: For each pattern specified (via `--exclude-string` or loaded from file):
- Treat as a PCRE regex pattern
- Store in regex exclusion list

**For each result**: Test each text in the discovered `matched_texts` against each regex pattern:
- If ANY text in `matched_texts` matches ANY regex pattern, exclude this result

**Line filtering**: If a line has NO remaining results after exclusion, remove the entire line from output

**Stacking behavior**: Multiple `--exclude-string` flags accumulate; a result is excluded if any of its matched_texts matches ANY regex pattern

**Example**:
```bash
grepnet 192.0.0.0/8 file.txt \
--exclude-string '192.0.[34]..' \
--exclude-string '\b0::0/[01]\b'
```

Results are excluded if their original text matches:
- Regex `192.0.[34]..` (IP addresses matching 192.0.3. or 192.0.4.)
- Regex `\b0::0/[01]\b` (IPv6 patterns like `::0/0`, `::0/1`, or variants with leading zeros)
- Regex `(test|deprecated)` (text containing "test" or "deprecated")

#### --exclude-cidr (Network-based Exclusions)

If `--exclude-cidr` or `--exclude-cidrs-file` specified, filter results by network algebra:

**Load patterns**: For each pattern specified (via `--exclude-cidr` or loaded from file):
- Parse as a network expression using the input parser (CIDR notation, subnet mask, range, or single IP)
- Error if parsing fails (not a valid network expression)
- Store in network exclusion list

**For each result**: Compare the discovered network against excluded networks using network algebra:
- Check if the discovered network overlaps with ANY excluded network (equality, subset, superset, or overlap)
- If there is any overlap, exclude this result

**Line filtering**: If a line has NO remaining results after exclusion, remove the entire line from output

**Stacking behavior**: Multiple `--exclude-cidr` flags accumulate; a result is excluded if it overlaps with ANY excluded network

**Example**:
```bash
grepnet 0.0.0.0/0 file.txt \
--exclude-cidr 192.0.2.0/24 \
--exclude-cidr '192.0.3.0 255.255.255.0' \
--exclude-cidr '10.0.0.0-10.255.255.255'
```

Results are excluded if their network overlaps with:
- Network `192.0.2.0/24` (exact CIDR match)
- Network `192.0.3.0/24` (parsed from subnet mask format)
- Range `10.0.0.0-10.255.255.255` (parsed from range format)

#### Combined Usage

`--exclude-string` and `--exclude-cidr` can be used together. A result is excluded if it matches ANY pattern (textual OR network-based).

#### Current Behavior (v5.0.0)

**--exclude-string**: Pure PCRE regex matching
- Patterns are treated as literal PCRE regular expressions
- Matched against the original extracted text (matched_texts)
- Does NOT parse patterns as networks
- Example: `--exclude-string '192\.0\.2'` matches text containing "192.0.2" but NOT network equivalents in other formats
- Example: `--exclude-string '192.0.2.0/24'` only matches the literal string "192.0.2.0/24", NOT "192.0.2.0 255.255.255.0"

**--exclude-cidr**: Network-based exclusion with "subset" default behavior
- Default behavior: Exclude file networks that are SUBSETS of (or EQUAL to) the excluded network
- Patterns are parsed as network expressions (CIDR, subnet mask, range, or single IP)
- Comparison uses network algebra (not text matching)
- Example: `--exclude-cidr 192.0.0.0/16` excludes both `192.0.2.0/24` (subset) and `192.0.0.0/16` (equal)
- Example: `--exclude-cidr 192.0.0.0/16` does NOT exclude `192.0.0.0/15` (superset)

### CIDR Exclusion Behavior: --exclude-cidr-behavior

The `--exclude-cidr-behavior` flag controls how excluded networks are matched against extracted or searched networks.

**Flag Format**: `--exclude-cidr-behavior={subset|subset-strict|superset|superset-strict|equals|related|cut}`

**Behaviors**:
- **subset** (default): Exclude if file network is subset of (or equal to) excluded network (⊆)
  - Includes exact equality matches
  - Example: `--exclude-cidr-behavior=subset --exclude-cidr 192.0.0.0/16` excludes `192.0.2.0/24` and `192.0.0.0/16`, but not `10.0.0.0/8`

- **subset-strict**: Exclude if file network is a strict subset of excluded network (⊂, no equality)
  - Excludes only networks strictly contained within the excluded network, not exact matches
  - Example: `--exclude-cidr-behavior=subset-strict --exclude-cidr 192.0.0.0/16` excludes `192.0.2.0/24`, but NOT `192.0.0.0/16` or `10.0.0.0/8`

- **superset**: Exclude if file network is superset of (or equal to) excluded network (⊇)
  - Includes exact equality matches
  - Example: `--exclude-cidr-behavior=superset --exclude-cidr 192.0.2.0/24` excludes `192.0.0.0/16` and `192.0.2.0/24`, but not `10.0.0.0/8`

- **superset-strict**: Exclude if file network is a strict superset of excluded network (⊃, no equality)
  - Excludes only networks that strictly contain the excluded network, not exact matches
  - Example: `--exclude-cidr-behavior=superset-strict --exclude-cidr 192.0.2.0/24` excludes `192.0.0.0/16`, but NOT `192.0.2.0/24` or `10.0.0.0/8`

- **equals**: Exclude only if file network exactly equals excluded network
  - Example: `--exclude-cidr-behavior=equals --exclude-cidr 192.0.2.0/24` excludes only exact matches of `192.0.2.0/24`

- **related**: Exclude if networks overlap or have any subset/superset relationship (union of subset+superset+overlap)
  - Includes overlaps, containment, and exact equality
  - Example: `--exclude-cidr-behavior=related --exclude-cidr 192.0.2.0/24` excludes any network that touches, contains, or is contained by `192.0.2.0/24`

- **cut**: Carve out excluded network(s) and return the remaining address space as minimal CIDR blocks
  - **Scope**: Only valid with `--extract` and `--consolidate` (will error if used without these flags)
  - **Behavior**: When extracting networks, remove the excluded CIDR block(s) from the extracted networks and return all minimal non-overlapping CIDR blocks that represent what remains
  - **Result format**: Complete list of CIDR blocks covering the remaining address space with no gaps or overlaps
  - **Examples**:
    - `echo 192.0.2.0/24 | ./grepnet --extract --exclude-cidr=192.0.2.0/30 --exclude-cidr-behavior=cut` → Removes `192.0.2.0/30`, returns the 6 CIDR blocks that fill the gap: `192.0.2.4/30`, `192.0.2.8/29`, `192.0.2.16/28`, `192.0.2.32/27`, `192.0.2.64/26`, `192.0.2.128/25`
    - `echo 192.0.2.0/24 | ./grepnet --extract --exclude-cidr=192.0.2.4/30 --exclude-cidr-behavior=cut` → Removes `192.0.2.4/30`, returns the 6 CIDR blocks: `192.0.2.0/30`, `192.0.2.8/29`, `192.0.2.16/28`, `192.0.2.32/27`, `192.0.2.64/26`, `192.0.2.128/25`
  - **Use cases**: Computing network complements, finding gaps in allocations, inverse lists

**Constraints**:
- Only one `--exclude-cidr-behavior` flag allowed (last one wins if multiple specified)
- The keywords "cut" and "related" are NOT cumulative; they represent specific behaviors
- Behaviors apply to all `--exclude-cidr` patterns in the command
- Behaviors apply consistently across CIDR and range formats
- `cut` behavior requires `--extract` or `--consolidate` and will error otherwise
- Strict variants (`subset-strict`, `superset-strict`) exclude equality matching; use these when you want pure subset/superset relationships only

### Prefix Length Filtering: --ipv4-shorter-than, --ipv4-longer-than, --ipv6-shorter-than, --ipv6-longer-than

These flags filter networks based on prefix length (number of network bits). Useful for finding networks of specific sizes.

**Flag Format**: 
- `--ipv4-shorter-than=N` - Include only IPv4 networks with prefix length < N
- `--ipv4-longer-than=N` - Include only IPv4 networks with prefix length > N
- `--ipv6-shorter-than=N` - Include only IPv6 networks with prefix length < N
- `--ipv6-longer-than=N` - Include only IPv6 networks with prefix length > N

**Scope**: Only valid with `--extract` and `--consolidate` (will error if used without these flags)

**Prefix Length Semantics**:
- "Shorter prefix" = fewer bits = larger address block (smaller prefix number)
  - IPv4: `/8` is shorter than `/16` which is shorter than `/32`
  - IPv6: `/32` is shorter than `/64` which is shorter than `/128`
- "Longer prefix" = more bits = smaller address block (larger prefix number)
- Bare IPs treated as `/32` (IPv4) or `/128` (IPv6) for comparison
- IP ranges converted to smallest containing CIDR before comparison

**Filter Application**:
1. With `--extract`: Filter applied **after** extraction (on the output networks)
2. With `--consolidate`: Filter applied **after** consolidation (on the consolidated output)

**Examples**:
- `echo "192.0.2.0/25 192.0.2.0/29 192.0.2.1 10.0.0.0/8" | ./grepnet --extract --ipv4-shorter-than=29 192.0.2.0/24`
  - Input networks: `192.0.2.0/25` (25 bits), `192.0.2.0/29` (29 bits), `192.0.2.1` (/32), `10.0.0.0/8` (8 bits)
  - Filter: prefix < 29 (shorter than /29)
  - Output: `192.0.2.0/25` (25 < 29 ✓) and `10.0.0.0/8` (8 < 29 ✓)
  - Excluded: `192.0.2.0/29` (29 NOT < 29) and `192.0.2.1` (/32 NOT < 29)

- `echo "192.0.2.0/25 192.0.2.1 10.0.0.0/8" | ./grepnet --extract --ipv4-shorter-than=29`
  - Filter: prefix < 29
  - Output: `192.0.2.0/25` (25 < 29) and `10.0.0.0/8` (8 < 29)
  - Excluded: `192.0.2.1` (/32 NOT < 29)

**Multiple Filters**:
- Can combine `--ipv4-shorter-than` and `--ipv4-longer-than` on same command
- Result must satisfy both conditions: `longer_than < prefix < shorter_than`
- Example: `--ipv4-longer-than=24 --ipv4-shorter-than=32` → 24 < prefix < 32
- IPv4 and IPv6 filters are independent (filter one without affecting the other)

**Constraints**:
- Only one value per flag type (last one wins if multiple specified)
- Only valid with `--extract` or `--consolidate` (will error if used without these modes)
- Value must be valid prefix length: 0-32 for IPv4, 0-128 for IPv6

### Inversion (Negation)

If `--invert-match` specified:
- Include only lines that do NOT match any search pattern
- Exclude lines that do match

### Output Processing Model

**Line-by-line Processing with Tight Coupling**: grepnet processes input one line at a time with NO buffering between search and output (unless context flags require buffering).

**Core principle**: Search and print are tightly coupled. As soon as a pattern is found on a line, the line is printed immediately—not buffered, not sent to another function for later output. This ensures:
- Real-time output for interactive use
- Minimal memory overhead even with large files
- Streaming behavior compatible with pipelines
- No finding a line to print, then scanning it again to figure out if it needs to be colorized.

**Exception for context flags** (`-B` and `-A`):
- When `-B N` is used, a window of the last N lines is maintained in memory
- As a match is found, the window (previous context) is printed first, then the matched line
- When `-A N` is used, the N lines following the match are printed after the matched line
- If a new match is found before the previous match's after-context is fully printed, the new match's after-context is printed, potentially overlapping or replacing the previous context window
- Behavior mirrors grep: context windows merge naturally without duplication

**Implementation guidance**:
- Maintain a circular buffer (or queue) of the last B lines
- When a match is found: flush buffer → print match → begin collecting next A lines
- Track whether we're in a context group to properly handle group separators

### Context Lines

Context lines are displayed but not counted as matches.

**Before context** (`-B N`): Include N lines before each match
**After context** (`-A N`): Include N lines after each match
**Context shorthand** (`-C N`): Include N lines before and after (equivalent to `-B N -A N`)

**Context assembly**:
1. For each matching line, collect line numbers within range
2. For lines that don't contain matches but are within context range, mark as context
3. Maintain order (don't reorder lines)
4. Output all lines (matches + context) in original order

**Group separator**: Between context groups (e.g., between matches from different regions), print a separator line (default `--`). Disable with `--no-group-separator`.

**Context flag restrictions**: Context flags (`-B`, `-A`, `-C`) cannot be used with output modes that don't produce line-based output:
- Cannot combine with `-l` (list files only)
- Cannot combine with `-L` (files without matches)
- Cannot combine with `--extract` (network extraction mode)
- Cannot combine with `--consolidate` (network consolidation mode)
Attempting to use context with these modes will error (exit 2). See [Exit Codes and Error Handling](#exit-codes-and-error-handling) for details.

**Context window implementation** (when -B is used):
- Maintain a fixed-size circular buffer of the previous B lines
- Each line stored as `(line_number, content, is_match, colored_content)`
- When a match is found:
  1. Print all buffered lines (these are the B context lines before the match), marking them as context
  2. Print the matched line
  3. Clear the buffer
  4. Begin collecting the next N lines for after-context (if -A is used)
- This ensures before-context is always printed immediately when a match is found, maintaining real-time output

**After-context handling** (when -A is used):
- After printing a matched line, read exactly A subsequent lines
- Print each line, marking them as context
- If a new match is encountered within these A lines, note it and handle according to overlap rules
- If a new match is found before the previous match's after-context completes, the new match takes precedence (similar to grep)

### Output Modes

#### 1. Normal (Text) Output

Default behavior: Print matching lines to stdout.

**Prefix behavior** (grep-like):
- Single file: No prefix (unless forced with `-H`)
- Multiple files: Prefix with `filename:` (unless suppressed with `--no-filename`)
- Stdin: Use `(standard input)` as filename (or custom label if `--label` provided)

**Optional prefixes** (additive, in order):
- With `-n`: Prepend line number (`N:`)
- With `-b`: Prepend byte offset (`B:`)

**Null separator** (`-Z`): Use NUL byte instead of newline after filename (for use with `xargs -0`)

**Only matching** (`-o`): Output only the network expression (original text as found in the file) from matching lines. NO deduplication.

Example: If a line contains `192.0.2.0 192.0.2.1 192.0.2.0/31 192.0.2.1`, with `-o` all four are output:
```
192.0.2.0
192.0.2.1
192.0.2.0/31
192.0.2.1
```

Networks are extracted if they have a match_type in the active set (determined by `-e -s -S -O -u` flags). 

**Note on `-v` with `-o`**: The flags `-v` (invert-match) and `-o` (only-matching) are incompatible. With `-v`, lines contain NO matching networks, so there is nothing for `-o` to extract. This matches grep's behavior: `grep -v -o pattern` produces no output. Use `-v` alone to show non-matching lines.

#### 2. Extract Mode

With `--extract`, list all networks found in files, deduplicated by network-object (not by original syntax):

```
Found 42 networks in file.txt:
192.0.2.0/24
198.51.100.0/24
192.0.2.1-192.0.2.255
...
```

**Output format**: Networks are output in canonical form:
- CIDR notation (e.g., `192.0.2.0/24`)
- IP ranges (e.g., `192.0.2.1-192.0.2.255`)

Subnet masks (`192.0.2.0 255.255.255.0`) and inverse masks (`192.0.2.0 0.0.0.255`) are automatically converted to CIDR notation in output.

**Deduplication**: Only unique network-objects are output. Two different representations of the same network (e.g., `192.0.2.1/32` and `192.0.2.1`) are deduplicated to one entry.

**Pattern filtering** (optional, **network-level**): 
- When no pattern is provided: extract all networks from all input
- When a pattern is provided: extract only networks that match the pattern (using active match type set)
- Match type flags (`-e`, `-s`, `-S`, `-O`, `-u`) control which networks match the pattern
- `-v` inverts the filter: extract networks that do NOT match the pattern

**Example**:
```bash
grepnet --extract file.txt                    # All networks
grepnet 192.0.2.0/24 --extract file.txt       # Only networks matching 192.0.2.0/24
grepnet -s 192.0.2.0/24 --extract file.txt    # Only networks that are subsets of 192.0.2.0/24
grepnet 192.0.2.0/24 -v --extract file.txt    # Only networks that do NOT match 192.0.2.0/24
```

#### 3. Consolidate Mode

With `--consolidate`, extract all networks from files, then merge overlapping and adjacent networks:

```
Consolidated 42 networks into 8 ranges:
192.0.2.0/23
198.51.100.0/24
192.0.2.1-192.0.2.255
...
```

**Process**: 
1. Extract all networks from input (same as `--extract` mode)
2. Merge overlapping and adjacent networks using RFC-compliant consolidation
3. Output the consolidated result

**Output format**: Networks are output in canonical form (CIDR notation or IP ranges).

**Pattern filtering** (optional, **network-level**):
- When no pattern is provided: extract and consolidate all networks from all input
- When a pattern is provided: extract and consolidate only networks that match the pattern
- Match type flags (`-e`, `-s`, `-S`, `-O`, `-u`) control which networks match the pattern
- `-v` inverts the filter: extract and consolidate networks that do NOT match the pattern

**Example**:
```bash
grepnet --consolidate file.txt                    # All networks, merged
grepnet 192.0.2.0/24 --consolidate file.txt       # Networks from matching lines, merged
grepnet -O 192.0.2.0/24 --consolidate file.txt    # Only overlapping networks, merged
grepnet 192.0.2.0/24 -v --consolidate file.txt    # Networks from non-matching lines, merged
```

**With format option**:
```bash
grepnet --extract --format cidr file.txt              # All networks as CIDR
grepnet --consolidate --format range file.txt         # Consolidated networks as ranges
grepnet 192.0.2.0/24 --extract --format short-range file.txt  # Matching networks as short-range
```

**Consolidation Pipeline**

The `--consolidate` mode follows a two-stage pipeline:

**Stage 1: RFC-Compliant Consolidation (always)**
```python
if mode == 'consolidate':
    result = consolidate_networks(input_sources)
```
This extracts all networks and merges overlapping and adjacent networks into deduplicated blocks.

**Stage 2: Bitshift Grouping with Gap Analysis (only if `--fill-pct` or `--fill-boundary`) — FUTURE RELEASE**
```python
    if fill_pct is not None or fill_boundary:
        result = apply_bitshift_grouping(result, fill_pct, fill_boundary)
    return result
```

This is why `--fill-pct` and `--fill-boundary` require `--consolidate`: they need the deduplicated networks from Stage 1 to work with.

**Note**: The `--fill-pct` and `--fill-boundary` options are planned for a future release and are not available in the current version.

**RFC-Compliant Consolidation (Stage 1)**

Merges overlapping and adjacent networks using standard IP consolidation rules.

**Bitshift Grouping Algorithm (Stage 2) — FUTURE RELEASE**

Applies additional consolidation based on IP address coverage gaps. Only runs when `--fill-pct` or `--fill-boundary` is specified.

**Note**: These options are planned for a future release and are not available in the current version.

**Bitshift Grouping Algorithm: Input Preparation**

Input: Deduplicated networks from RFC-Compliant Consolidation (Stage 1)
1. Convert all networks to integer representations (network start address)
2. Sort networks by integer address (ascending order)
3. For each network, record: `start_int`, `end_int`, `prefix_length`

**Grouping Algorithm (Core):**
For each prefix level (from 1 to 32 for IPv4, 1 to 128 for IPv6):
1. Initialize empty current group
2. Iterate through sorted networks
3. For each network, calculate group key: `group_key = start_int >> prefix_len`
4. If group key matches previous network's key: add to current group
5. If group key differs: 
   - Analyze current group (see below)
   - Apply consolidation criterion (see below)
   - Start new group

**Group Analysis:**
For each completed group:
1. Calculate `total_ips = 2^prefix_len`
2. Calculate `covered_ips = sum of all IP addresses in all networks in group`
   - For CIDR: `covered_ips += (network.num_addresses)`
   - For ranges: `covered_ips += (end_int - start_int + 1)`
3. Calculate `gap_ips = total_ips - covered_ips`
4. Calculate `gap_ratio = (gap_ips / total_ips) * 100`

**Consolidation Criteria (Decision Point):**
When a group boundary is reached, decide whether to consolidate based on `gap_ratio`:

- **`--fill-pct N`** (FUTURE RELEASE): Accept group if `gap_ratio <= N%` (allow up to N% gap)
- **`--fill-boundary`** (FUTURE RELEASE): Accept group if `gap_ratio <= 1%` (only boundary IPs missing)

When accepted, consolidate the entire group to a single CIDR block at that prefix level.

When rejected, output original networks and continue to next prefix level.

**IPv6 Handling:**
Same algorithm, but prefix levels range from 1 to 128, and shift operations work on 128-bit integers.

**Examples:**

Input: `192.0.2.0/32` + `192.0.2.4/30` (after RFC consolidation)

At /29 level (>> 3):
- Both have same group key → same group
- total_ips = 2^3 = 8
- covered_ips = 1 + 4 = 5
- gap_ratio = (8 - 5) / 8 * 100 = 37.5%
- `--fill-pct 37`: reject (37.5% > 37%)
- `--fill-pct 38`: accept → outputs `192.0.2.0/29`
- `--fill-boundary`: reject (37.5% >> 1%)

Input: `192.0.2.1/32` through `192.0.2.254/32` (254 addresses, missing .0 and .255) (after RFC consolidation)

At /24 level (>> 8):
- All have same group key → same group
- total_ips = 2^8 = 256
- covered_ips = 254
- gap_ratio = (256 - 254) / 256 * 100 = 0.78%
- `--fill-pct 50`: accept → outputs `192.0.2.0/24`
- `--fill-boundary`: accept (0.78% <= 1%) → outputs `192.0.2.0/24`

#### `--fill-boundary` (with `--consolidate`) — FUTURE RELEASE

**Syntax**: `grepnet --consolidate --fill-boundary [PATTERN] [FILE...]`

**Status**: Planned for future release. Not available in current version.

**Description**: 
When used with `--consolidate`, automatically inject missing network and broadcast addresses before applying the bitshift grouping algorithm. This enables complete CIDR consolidation when input covers all usable addresses but lacks the boundary addresses.

**Behavior**:
- Only valid with `--consolidate` mode (error if used without it)
- First applies RFC-compliant consolidation to deduplicate networks
- Detects contiguous ranges of networks that nearly cover a complete subnet
- Identifies missing network address (x.x.x.0) and broadcast address (x.x.x.255)
- Automatically injects these boundary addresses before bitshift grouping analysis
- Bitshift grouping then produces complete parent network consolidation instead of fragmented subnets

**Example**:
```
Input (192.0.2.1-192.0.2.254, missing 192.0.2.0/32 and 192.0.2.255/32):
192.0.2.1/32
192.0.2.2/31
192.0.2.4/30
192.0.2.8/29
192.0.2.16/28
192.0.2.32/27
192.0.2.64/26
192.0.2.128/26
192.0.2.192/27
192.0.2.224/28
192.0.2.240/29
192.0.2.248/30
192.0.2.252/31
192.0.2.254/32

Without --fill-boundary: Outputs 14 separate CIDR blocks
With --fill-boundary: Consolidates to single 192.0.2.0/24
```

**Error handling**:
- `--fill-boundary` without `--consolidate`: error (exit code 2)
- `--fill-boundary` with `-v`: warning, flag ignored (incompatible semantics)

#### 4. Count Mode

With `--count` (`-c`), output count of matching lines:

```
file1.txt:3
file2.txt:1
```

Or just:
```
4
```
(if single file)

#### Output Control Flags

- `-l` (`--files-with-matches`): Output only filenames containing matches (one per line)
- `-L` (`--files-without-match`): Output only filenames with NO matches
- `-q` (`--quiet`): Suppress all output, exit code only
- `--no-messages`: Suppress error/warning messages to stderr
- `--show-content`: Include line content in extract/consolidate modes

#### Max Count Limit

With `-m N`, stop processing after N matches (across all files). Exit after reaching limit.

---

## Exit Codes and Error Handling

### Exit Code Semantics

- **Exit 0**: Search completed; matches found (or quiet mode; or file list mode with matches)
- **Exit 1**: Search completed; no matches found
- **Exit 2**: Error occurred (file not found, invalid argument, malformed pattern in strict mode, etc.)

**Special case**: With `--quiet`, exit 0 if matches found, exit 1 if no matches (ignoring count).

### Error Messages

All error messages are written to stderr in format:
```
grepnet: error: <message>
```

Warnings use:
```
grepnet: warning: <message>
```

Suppress all messages with `--no-messages`.

### Error Handling Behaviors (v2.0 API)

**File not found**:
- Warning message (unless `--quiet`)
- Continue processing other files
- Exit 1 if no valid files remain

**Malformed CIDR in non-strict mode** (default):
- Normalize silently
- Mark as normalized in output
- No exit code change

**Malformed CIDR in strict mode** (when `--strict-cidr` is set):
- `--strict-cidr-action=fail`: Error message and exit 2 immediately
- `--strict-cidr-action=normalize`: Normalize silently (default behavior)
- `--strict-cidr-action=ignore`: Skip silently without processing
- `--strict-cidr-action=warn`: Print warning to STDERR, then skip and continue

**Invalid pattern**:
- Skip pattern silently (no warning or error message)
- Continue with next pattern

**No valid patterns**:
- If no valid networks are extracted from all pattern arguments combined, exit with code 2
- Error message: `grepnet: error: no patterns to search for`

**Incompatible flag combinations**:
Context flags (`-B`, `-A`, `-C`) are incompatible with certain output modes because context (surrounding lines) doesn't apply:
- **With `-l` (list files only)**: Files are listed without line content. Context has no meaning.
- **With `-L` (files without matches)**: Only filenames of non-matching files are listed. Context doesn't apply.
- **With `--extract`**: Only extracted networks are output, not full lines with context.
- **With `--consolidate`**: Only consolidated networks are output, not context lines.

If attempted, print error and exit with code 2:
```
grepnet: error: context flags (-B/-A/-C) cannot be used with -l, -L, --extract, or --consolidate
```

**Wildcard mask flag errors**:
- **`--parse-wildcard` without `--wildcard-search`**: Error and exit 2
  ```
  grepnet: error: --parse-wildcard requires --wildcard-search CIDR argument
  ```
- **`--wildcard-search` without `--parse-wildcard`**: Error and exit 2
  ```
  grepnet: error: --wildcard-search requires --parse-wildcard argument
  ```
- **Invalid CIDR in `--wildcard-search`**: Error and exit 2
  ```
  grepnet: error: invalid CIDR block in --wildcard-search: 999.999.999.999/32
  ```

---

## Environment Variables

### GREPNET_COLORS

Grepnet-specific extension for color codes. Format: `code=value:code=value:...`

**Supported codes**:
- `mt=` (matched text in matched line)
- `mc=` (matched text in context with matches)
- `ms=` (matched text in context without matches)
- `sl=` (selected line background)
- `me=` (match type equals)
- `mb=` (match type subset)
- `mS=` (match type superset)
- `mo=` (match type overlap)
- `mn=` (normalized CIDR)
- `mu=` (match type unmatched, for use with `-u` flag)
- `fn=` (filename prefix)
- `ln=` (line number prefix)
- `bn=` (byte offset prefix)
- `se=` (separator/colon between prefix parts)
- `wm=` (wildcard mask format, when --parse-wildcard is enabled)

**Example with custom colors**:
```
export GREPNET_COLORS="me=01;31:mb=01;36:mS=01;35:mo=0:mu=0:mn=04:fn=35:ln=32:bn=32:se=36:wm=4:3"
```

**Default values**:
```
me=01;32     # Match type equals (bright green)
mb=01;34     # Match type subset (bright blue)
mS=01;33     # Match type superset (bright yellow)
mo=01;31     # Match type overlap (bright red)
mu=0         # Match type unmatched (no color)
mn=04        # Normalized CIDR (underlined)
mt=0         # Matched text (no color)
fn=35        # Filename (magenta, grep-compatible)
ln=32        # Line number (green, grep-compatible)
bn=32        # Byte offset (green, grep-compatible)
se=36        # Separator colon (cyan, grep-compatible)
wm=4:3       # Wildcard mask (curly underline) - only used when --parse-wildcard is enabled
```

**Wildcard Mask Color Code** (`wm=`):
- **Used when**: `--parse-wildcard` flag is enabled
- **Applies to**: Cisco ACL wildcard mask notation in original format
- **Example**: With default `wm=4:3`, the text `10.4.0.0 0.0.127.252` appears with curly underline
- **Default value**: `4:3` (curly underline)
- **Customization**: Set to any valid ANSI code; ignored if `--parse-wildcard` is not enabled

---

## Command-Line Interface Specification

## Command-Line Interface Specification

### Argument Parser Behavior

All arguments must be parsed using a standard argument parser that supports:
- Positional arguments (pattern, files)
- Optional flags (-x, --long-option)
- Repeatable flags (e.g., `-F file1 -F file2`)
- Flag aliases (-h vs --help)
- Mutually exclusive groups
- Type coercion (strings, integers)
- Default values

### Complete Argument List

#### Pattern/File Input
```
pattern                          CIDR pattern (optional if -P/-f specified)
file                             Files to search (repeatable positional)
-F, --input-file FILE            Input file (repeatable: -F f1 -F f2)
-P, --pattern PATTERN            Additional pattern (repeatable)
-f, --patterns-file FILE         Pattern file (repeatable)
```

#### Match Type Flags (can be combined)
```
-e, --equal                      Match equal networks
-s, --subset                     Match subsets (file is subset of pattern)
-S, --superset                   Match supersets (file is superset of pattern)
-O, --overlap                    Match overlapping networks (partial overlap)
-u, --unmatched                  Match networks that don't match any pattern
```

Default if none specified: all four match types (any match)

**Note**: Specify any combination of the search type flags (`-e`, `-s`, `-S`, `-O`, `-u`) to customize which networks are included. If none are specified, the default four match types are enabled. The `-u` flag adds `match_type 'unmatched'` to the set of match types being searched for. The `-v` flag inverts the line selection based on whatever match types are active (default or customized with flags).

#### Network Output Format
```
--format {cidr|range|short-range|ips|original}
                                 Network output format (--extract, --consolidate only; default: cidr)
```

**Valid only with `--extract` or `--consolidate`**. Using this flag with any other mode results in an error.

**Format options**:
- `cidr` (default): Output networks as CIDR notation (e.g., `192.0.2.0/24`). Ranges are converted to equivalent CIDR blocks.
- `range`: Output networks as IP ranges (e.g., `192.0.2.0-192.0.2.255`)
- `short-range`: Output networks as abbreviated ranges (e.g., `192.0.2.0-255` where only the final octet is shown)
- `ips` (--consolidate only): Output all individual IP addresses that compose the consolidated network(s). One IP per line. **Cannot be used with `--extract` alone; requires `--consolidate`.** ⚠️ Warning: Only practical for small networks; `/0` would output 4.3 billion IPs!
- `original`: Output networks in their original parsed format (e.g., CIDR inputs as CIDR, ranges as ranges, subnet masks as subnet masks). **Cannot be used with `--consolidate` because consolidated networks lose their original format identity.**

**Short-range format details**:
- IPv4 only: Short-range abbreviation (`START_IP-FINAL_OCTET`) is applied only to IPv4 addresses, and **only when the range varies in the last octet only**. For example: `192.0.2.0-255` represents the range `192.0.2.0-192.0.2.255` (the last octet value of 255 is abbreviated to just the octet part).
- IPv4 ranges spanning multiple octets: When an IPv4 range spans beyond just the final octet, it defaults to full long-range notation. For example: `192.0.2.10-192.255.2.100` cannot be abbreviated, so it uses the full form.
- IPv6 and other cases: When IPv6 addresses or other network types are encountered, the format defaults to full long-range notation (e.g., `2001:db8::-2001:db8::ffff`) since last-octet abbreviation is not practical for IPv6's 128-bit addresses.
- Single IPs: Display as `/32` (IPv4) or `/128` (IPv6) in CIDR format even in range/short-range modes

**IPS format details** (`--format=ips`, consolidate only):
- Expands each consolidated network to its constituent IP addresses
- One IP address per line
- IPv4 addresses in dotted-quad notation (e.g., `192.0.2.0`, `192.0.2.1`, ..., `192.0.2.255`)
- IPv6 addresses in canonical notation (e.g., `2001:db8::`, `2001:db8::1`, ..., `2001:db8::ffff`)
- **Warning: Only practical for small networks.** A `/24` network has 256 IPs; a `/0` has 4,294,967,296 IPs. Use with caution on large networks or server loads may spike.

⚠️ **Warning: Short-range format is highly discouraged for most use cases** because:
  - Abbreviated notation is ambiguous and easy to misread (e.g., `192.0.2.0-4` vs `192.0.2.0-40`)
  - It only works for IPv4 addresses with single-octet variation
  - It may not be portable across tools or systems
  - For scripting and automation, use `--format=range` (full notation) or `--format=cidr` instead

**Example**:
```bash
grepnet --extract --format cidr file.txt          # Output as CIDR (recommended)
grepnet --consolidate --format range file.txt      # Output as ranges (recommended)
grepnet --extract --format short-range file.txt    # Output as abbreviated ranges (not recommended)
grepnet --extract --format original file.txt       # Output in original parsed format
grepnet --consolidate --format ips file.txt        # Output all IPs in consolidated networks (consolidate only)

# Example with --format=ips:
# Input: 192.0.2.0-192.0.2.2
# Output:
#   192.0.2.0
#   192.0.2.1
#   192.0.2.2

# Example with mixed networks and --format=ips:
# Input: 192.0.2.0/30 192.0.3.0/30
# Output:
#   192.0.2.0
#   192.0.2.1
#   192.0.2.2
#   192.0.2.3
#   192.0.3.0
#   192.0.3.1
#   192.0.3.2
#   192.0.3.3

# Example with mixed formats in original format:
# Input:
#   192.0.2.0/24           (CIDR)
#   10.0.0.0 255.0.0.0     (subnet mask)
#   172.16.0.0-172.16.255.255  (range)
# Output:
#   192.0.2.0/24           (preserved as CIDR)
#   10.0.0.0 255.0.0.0     (preserved as subnet mask)
#   172.16.0.0-172.16.255.255  (preserved as range)

# Example with mixed ranges in short-range format:
# Input: 192.0.2.0-4 (last octet only) and 192.0.2.10-192.255.2.100 (spans multiple octets)
# Output:
#   192.0.2.0-4                      (abbreviated, only last octet changes)
#   192.0.2.10-192.255.2.100         (full form, spans multiple octets)
```

#### Line/File Output Control
```
-H, --with-filename              Show filename:content
--no-filename                    Suppress filename prefix
-l, --files-with-matches         Show only files with matches
-L, --files-without-match       Show only files without matches
-q, --quiet, --silent            Suppress output (exit code only)
-v, --invert-match               Show non-matching lines (inverts based on current match type set)
```

#### Line Prefixes
```
-n, --line-number                Print 1-based line number
-b, --byte-offset                Print 0-based byte offset
-Z, --null                       NUL separator after filename
--label LABEL                    Display stdin as LABEL
```

#### Line Termination
```
-z, --null-data                  Treat input/output as NUL-terminated records
```

**-z, --null-data**: Treat input and output data as sequences of lines, each terminated by a zero byte (NUL character, ASCII 0x00) instead of newline (LF, ASCII 0x0A).

Behavior:
- Input: Lines are read as NUL-terminated records instead of newline-terminated
- Output: Lines are output with NUL terminators instead of newlines
- Usage: For processing filenames or data that may contain newlines (use with `sort -z`, `xargs -0`, etc.)
- Encoding: Null bytes in the middle of data are treated as line separators
- Pattern matching: Network patterns and file content matching work normally; only line termination changes

Example:
```bash
grepnet -z '192.0.2.0/24' file.txt | xargs -0 process.sh    # Process matches with null-separated output
find . -print0 | grepnet -z -Z '192.0.2.0/24'               # NUL-separated input and output
```

#### Context Lines
```
-A NUM, --after-context NUM      Print NUM lines after each match
-B NUM, --before-context NUM     Print NUM lines before each match
-C NUM, --context NUM            Print NUM lines around each match
--group-separator SEP            Print SEP between groups (default: "--")
--no-group-separator             Don't print group separator
```

#### Counting and Limiting
```
-c, --count                      Print count instead of lines
-m NUM, --max-count NUM          Stop after NUM matches
```

**-m, --max-count NUM**: Stop processing after NUM matching lines.

Behavior:
- NUM = 0: Stop immediately without reading input (no output)
- NUM = -1 or default (no -m flag): No limit, process all input (standard grep behavior)
- NUM > 0: Stop after finding NUM matching lines, then exit

Details:
- Applies per-file: Each file is processed until NUM matches found, then moves to next file
- With `-c` (count): Output count value is limited to NUM (does not exceed NUM)
- With `-v` (invert-match): Stops after NUM non-matching lines instead of matching lines
- With context flags (-A, -B, -C): Trailing context lines are still output before stopping
- Exit codes: Standard (0 if matches, 1 if no matches)

Examples:
```bash
grepnet -m 5 '192.0.2.0/24' file.txt          # Stop after 5 matches
grepnet -c -m 10 '192.0.2.0/24' file.txt      # Count, but max 10
grepnet -v -m 20 '192.0.2.0/24' file.txt      # Stop after 20 non-matches
grepnet -A2 -m 3 '192.0.2.0/24' file.txt      # 3 matches + trailing context
```

---

#### Extraction and Consolidation
```
--extract                        Extract all networks from files
--consolidate                    Consolidate overlapping networks
--fill-pct=N                     Allow consolidation to fill gaps up to N% (FUTURE RELEASE - only with --consolidate)
--show-content                   Show line content in extract mode
--no-filter-comments [scope]     Do not filter comments (pattern|input|both|none; default: both)
```

**Note**: `-o/--only-matching` is for normal mode only and cannot be used with `--extract` or `--consolidate`.

**--fill-pct=N** (FUTURE RELEASE — only valid with `--consolidate`): Allow consolidation to fill IP address gaps up to N percent of the network size.

**Status**: Planned for future release. Not available in current version.

**Semantics** (FUTURE RELEASE):
- `N` is an integer from 0 to 100 (percentage)
- When enabled, consolidate in a single pass:
  1. Extract all networks from input
  2. For each extracted network, find the first (smallest) supernet where `(gap_ips / supernet_total_ips) × 100 ≤ N`
     - Stop at the first supernet that fits; do NOT continue searching for larger supernets
     - If no supernet fits the threshold, keep the original network unchanged
  3. Merge all filled networks using RFC-compliant `collapse_addresses()`
  4. Return the consolidated result

**Gap Calculation**:
- For a network and a candidate supernet: `gap_ips = supernet_ips - original_network_ips`
- Fill ratio: `(gap_ips / supernet_ips) × 100` must be ≤ N%
- Example: Network `192.0.2.1-192.0.2.2` (2 IPs) can consolidate to `192.0.2.0/30` (4 IPs total)
  - Gap: 4 - 2 = 2 IPs
  - Fill ratio: (2 / 4) × 100 = 50%
  - `--fill-pct=50` allows this consolidation
  - `--fill-pct=25` rejects this consolidation

**Consolidation Behavior**:
- `--fill-pct` applies **once per extracted network**, not iteratively
- Multiple adjacent networks may still merge after filling due to `collapse_addresses()`
- Example: Two networks `192.0.2.1-192.0.2.2` and `192.0.2.4-192.0.2.5` with `--fill-pct=50`:
  - Both expand to /30 networks: `192.0.2.0/30` and `192.0.2.4/30`
  - These are now adjacent, so `collapse_addresses()` merges them to `192.0.2.0/29`
  - This is a single-pass operation; no further fill-pct is applied to the /29 result

**Examples**:
```bash
grepnet 192.0.2.1-192.0.2.2 --consolidate --fill-pct=50
# Input: Range 192.0.2.1-192.0.2.2 expands to 192.0.2.1/32, 192.0.2.2/32
# Fill-pct applied: 192.0.2.1/32 → 192.0.2.0/31 (50% fill), 192.0.2.2/32 → 192.0.2.0/31 (50% fill, but same network)
# After collapse: Adjacent /31 networks merge to 192.0.2.0/30
# Output: 192.0.2.0/30

grepnet 192.0.2.1-192.0.2.2 --consolidate --fill-pct=25
# Input: Range expands to 192.0.2.1/32, 192.0.2.2/32
# Fill-pct applied: No supernet fits ≤ 25% fill threshold
# Output: 192.0.2.1/32, 192.0.2.2/32 (unchanged)

echo -e "192.0.2.1-192.0.2.2\n192.0.2.4-192.0.2.5\n192.0.2.9-192.0.2.10" | grepnet --consolidate --fill-pct=50
# Input: Three ranges expand to six /32 networks
# Fill-pct applied (single pass): Each /32 → /31 (50% fill)
#   - 192.0.2.1-2 → 192.0.2.0/30, 192.0.2.4-5 → 192.0.2.4/30, 192.0.2.9-10 → 192.0.2.8/30
# After collapse: Adjacent /30 networks merge
#   - 192.0.2.0/30 (contains .0-.3) and 192.0.2.4/30 (contains .4-.7) → 192.0.2.0/29
#   - 192.0.2.8/30 (contains .8-.11) remains separate
# Output: 192.0.2.0/29, 192.0.2.8/30
```

**Interaction with other flags** (FUTURE RELEASE):
- Valid only with `--consolidate` (will error if used without it)
- Pattern filtering: If a pattern is provided, consolidate only matching networks
- Works with `--format` to control output notation (cidr, range, short-range)
- Cannot be used with `--extract` alone (consolidation feature only)

**Error handling**:
- If `--fill-pct` is used without `--consolidate`, exit with error code 2
- N must be 0-100; values outside this range are rejected

**--no-filter-comments [scope]**: Control which scopes have comment filtering disabled.

Arguments (optional):
- `pattern` - Comments in patterns are not filtered (but input lines are)
- `input` - Comments in input lines are not filtered (but patterns are)
- `both` - Comments in neither patterns nor input lines are filtered (default if flag with no arg)
- `none` - Comments everywhere are filtered (same as no flag; explicit override)

If flag is used without argument, defaults to `both`.

Behavior in normal search mode:
- Output only the matched networks found on each line, not the full line content
- Each matched network appears on a separate output line
- Filename prefix, line numbers, byte offsets still shown (if those flags enabled: -H, -n, -b)
- Context flags (-A, -B, -C) are allowed but behave specially (see below)

Behavior with context flags (-A, -B, -C):
- Context LINES (before/after content) are SUPPRESSED - no surrounding line content shown
- Group separators (--) between contiguous groups of matches ARE STILL SHOWN
- Matches are output normally, just without the context lines around them
- Example: `grepnet -o -C1 '192.0.2'` shows matched networks with `--` separators but no surrounding lines

Interaction with other modes:
- Only valid in normal search mode
- Cannot be used with --extract (extract is a different mode of operation)
- Cannot be used with --consolidate (consolidate is a different mode of operation)
- Cannot be used with -l or -L (contradictory: -l shows files only, -o shows networks only)

Examples (normal mode only):
```bash
grepnet -o '192.0.2.0/24' file.txt                    # Matched networks in order seen, with duplicates
grepnet -o -n '192.0.2.0/24' file.txt                 # Networks with line numbers
grepnet -o -C1 '192.0.2.0/24' file.txt                # Networks with -- separators, no context lines
```

---
```
--parse-cidr={pattern|input|both|none}      Where to accept CIDR notation (default: both)
--parse-netmask={pattern|input|both|none}   Where to accept subnet masks (default: both)
--parse-hostmask={pattern|input|both|none}  Where to accept hostmasks (default: both)
--parse-ranges={pattern|input|both|none}    Where to accept IP ranges (default: both)
--parse-bare-ip={pattern|input|both|none}    Where to accept single IP address (default: both)
--scan-mask={pattern|input|both|none}       Scan peek buffer for format hints (default: both)
--range-format={long|short}       Range format preference (default: both)
```

**Options**:
- `pattern` - (parse-* only) Accept this format in patterns only
- `input` - (parse-* only) Accept this format in input files only
- `both` - (parse-* only) Accept this format in both patterns and input (default)
- `none` - (parse-* only) Don't accept this format anywhere
- `long` (range-format only) - Accept only long-form ranges (192.0.2.1-192.0.2.254)
- `short` (range-format only) - Accept only short-form ranges (192.0.2.1-254)

**--scan-mask options** (peek buffer format detection):
- `pattern` - Scan patterns only (analyze pattern strings for netmask vs hostmask format hints)
- `input` - Scan input files only (analyze first 8KB for format hints)
- `both` - Scan both patterns and input (default, provides format hints for all sources)
- `none` - Don't scan; disable format detection optimization

#### Wildcard Mask Configuration
```
--parse-wildcard {pattern|input|both|none}   WHERE to parse Cisco ACL wildcard masks (default: none)
--wildcard-search CIDR                       WHICH scope defines valid wildcard mask ranges (required if --parse-wildcard is set)
```

**--parse-wildcard {pattern|input|both|none}**: Enable parsing of Cisco ACL wildcard mask notation (e.g., `10.4.0.0 0.0.127.252`).

Arguments:
- `pattern` - Parse wildcard masks in search patterns only
- `input` - Parse wildcard masks in file input only
- `both` - Parse wildcard masks in both patterns and input files (recommended)
- `none` - Don't parse wildcard masks (default; wildcard format treated as failed extraction)

Behavior:
- When enabled, two-value patterns like `10.4.0.0 0.0.127.252` are parsed as Cisco ACL wildcard masks
- The wildcard mask is converted to its constituent CIDR blocks for internal matching
- Original format is preserved for display purposes
- Networks found in wildcard mask format are marked with `format_type: 'wildcard_mask'`

**Dependency**: This flag MUST be used together with `--wildcard-search`; using one without the other produces an error.

**--wildcard-search CIDR**: Define the scope (boundary CIDR block) within which wildcard **mask values** (the second IP in the pair) are considered valid.

**CRITICAL**: Only the mask value is scope-checked. The base address (first IP) is completely ignored for scope validation and can be any valid IPv4 address.

Arguments:
- `CIDR` - Any valid IPv4 CIDR block (e.g., `0.0.0.0/0`, `10.0.0.0/8`, `192.168.0.0/16`)
- Only the wildcard mask value (second IP) is checked against this scope
- Wildcard masks whose mask values fall within this scope are accepted
- Wildcard masks whose mask values fall outside this scope are rejected and fall back to other extractors
- Base address (first IP) is irrelevant to scope validation

Behavior:
- Acts as a DoS protection mechanism: prevents parsing of unbounded wildcard masks
- Scope check is O(1) using IPv4Address containment check against mask value only
- If a wildcard mask is out-of-scope, parsing falls back to trying other format extractors
- Explicit consent model: User must define scope; error if `--parse-wildcard` is set without `--wildcard-search`

**Examples**:
```bash
# Enable wildcard mask parsing for both patterns and input; scope to 10.0.0.0/8
grepnet --parse-wildcard both --wildcard-search 10.0.0.0/8 '10.4.0.0 0.0.127.252' input.txt

# Parse only in file input; scope to private address space (RFC 1918)
grepnet --parse-wildcard input --wildcard-search 10.0.0.0/8 config.txt

# Unrestricted scope (not recommended for untrusted input)
grepnet --parse-wildcard both --wildcard-search 0.0.0.0/0 file.txt

# Error: missing scope (this will fail)
grepnet --parse-wildcard both file.txt    # ERROR: --wildcard-search required

# Error: missing --parse-wildcard (this will fail)
grepnet --wildcard-search 10.0.0.0/8 file.txt  # ERROR: --parse-wildcard required
```

**Interaction with other flags**:
- Works with all match type flags (-e, -s, -S, -O, -u)
- Works with --extract and --consolidate (wildcard masks expanded and consolidated with other networks)
- Works with --format for output formatting (original, cidr, range, short-range, ips)
- Works with --no-filter-comments (wildcard masks in comments are still rejected during comment stripping)

**Error handling**:
- If `--parse-wildcard` is used without `--wildcard-search`, exit with error code 2
- If `--wildcard-search` is used without `--parse-wildcard`, exit with error code 2
- If `CIDR` argument to `--wildcard-search` is invalid, exit with error code 2
- If no `--wildcard-search` scope is defined, wildcard masks are never parsed (treated as failed extraction)

#### Strict CIDR Validation (v2.0 API)
```
--strict-cidr={pattern|input|both|none}     WHERE to apply strict CIDR validation (default: none)
--strict-cidr-action={fail|normalize|ignore|warn}  WHAT to do on validation error (default: normalize)
```

**--strict-cidr options**:
- `pattern` - Strict validation for patterns only
- `input` - Strict validation for input files only
- `both` - Strict validation for both patterns and input
- `none` - No strict validation (default, permissive)

**--strict-cidr-action options**:
- `fail` - Exit immediately with error code 2 on first malformed CIDR
- `normalize` - Accept malformed CIDR and attempt to normalize it (default)
- `ignore` - Silently skip any malformed CIDR without processing
- `warn` - Print warning to STDERR, then skip and continue processing

#### Exclusion Filtering
```
--exclude-string PATTERN         Exclude by text pattern (PCRE regex; repeatable; stacks)
--exclude-strings-file FILE      Load text patterns from file (one regex per line)
--exclude-cidr NETWORK           Exclude by network (CIDR/subnet/range/IP; repeatable; stacks)
--exclude-cidrs-file FILE        Load network patterns from file (one network per line)
```

**--exclude-string**: Pure PCRE regex matching against discovered text
- Each pattern is a PCRE regular expression (NOT parsed as a network)
- Matched against matched_texts (the original text of each extracted network)
- Results are excluded if ANY text matches ANY regex pattern
- Example: `--exclude-string '192\.0\.2'` matches any text containing "192.0.2"
- Example: `--exclude-string '192.0.2.0/24'` matches ONLY the literal string "192.0.2.0/24", NOT equivalent networks in other formats

**--exclude-cidr**: Network-based exclusion using network algebra (default: "subset" behavior)
- Each pattern is parsed as a network expression (CIDR notation, subnet mask, range, or single IP)
- Results are excluded if their network is a SUBSET OF (or EQUAL TO) the excluded network
- Example: `--exclude-cidr 192.0.0.0/16` excludes both `192.0.2.0/24` (subset) and `192.0.0.0/16` (equal)
- Example: `--exclude-cidr 192.0.0.0/16` does NOT exclude `192.0.0.0/15` (superset)
- Future: Behavior can be controlled via `--exclude-cidr-behavior` flag (not yet implemented)

**Combined usage**: `--exclude-string` and `--exclude-cidr` can be used together. A result is excluded if it matches ANY pattern (textual OR network-based).

#### File Discovery
```
-r, --recursive                  Recursive search (don't follow symlinks)
-R, --dereference-recursive      Recursive search (follow all symlinks)
-d {read|skip|recurse}           Directory handling (default: recurse)
-D {read|skip}                   Device file handling (default: skip)
--include PATTERN                Include files matching glob (repeatable)
--exclude PATTERN                Exclude files matching glob (repeatable)
--exclude-from FILE              Load exclude patterns from file
--exclude-dir PATTERN            Exclude directories (repeatable)
```

#### Binary File Handling
```
-a, --text                       Process binary files as text
-I                               Treat binary files as non-matching
--binary-files {binary|text|without-match}
                                 Binary file handling (default: binary)
```

#### Color Output
```
--color {auto|always|never}      Color mode (default: auto)
```

#### Debug and Diagnostic Flags
```
--debug [FUNCTIONS]              Enable debug output to stderr (optional filter for functions)
--no-messages                    Suppress all error messages
-h                               Brief help
--help                           Full help
--version                        Show version and exit
```

**Debug flag behavior**:
- `--debug` or `--debug=all`: Output debugging information from all functions to stderr
- `--debug=extract`: Debug network extraction process (parse input lines, show extracted networks)
- `--debug=match`: Debug matching process (show which patterns match which networks, match type priority)
- `--debug=FUNCTION`: Filter debug output to specific function (extensible for future functions)
- Multiple function filters can be combined (implementation may support comma-separated list or multiple flags)
- Debug output does NOT affect normal stdout output (debug goes to stderr only)
- Debug output is verbose and intended for troubleshooting parsing and matching issues

**Example debug output**:
```
# Extract debug shows what networks were parsed from text
[DEBUG extract_networks] input line: 'text 192.0.2.0 255.0.255.0 text'
[DEBUG subnet_mask] rejected '192.0.2.0 255.0.255.0' (non-contiguous mask: 255.0.255.0)
[DEBUG extract_networks] extracted 2 networks:
  [0] text='192.0.2.0' format=IP_ONLY network=192.0.2.0/32
  [1] text='255.0.255.0' format=IP_ONLY network=255.0.255.0/32

# Match debug shows matching logic
[DEBUG match] pattern=192.0.2.0/24 file_network=192.0.2.0 result=EQUALS
```

This is useful for:
- Understanding why a pattern isn't matching expected networks
- Verifying mask/range parsing is correct
- Debugging non-contiguous masks or invalid formats
- Troubleshooting test failures

### Help and Error Reporting

**Brief help** (`-h`):
- Show usage line
- Show one-line description
- Suggest `--help` for more info
- Exit 0

**Full help** (`--help`):
- Show full help text with all options and examples
- Exit 0

**Error format**:
```
grepnet: error: <message>
<usage line>
Try 'grepnet --help' for more information.
```
Exit 2

**Warning format**:
```
grepnet: warning: <message>
```
Exit 0 (does not affect exit code)

---

## Implementation Notes for Porting

### Key Algorithms and Structures

- **Binary Search (Bisect)**: Used extensively in matchers to quickly locate networks by prefix length or address range. Implement or import a binary search library.

- **Regular Expressions**: Regex is used for pattern matching in file content and for parsing CIDR/mask/range syntax. Port the regex patterns as-is; they are language-agnostic.

- **Interval Arithmetic**: Network comparison reduces to interval comparison on integer addresses. Implement efficient start/end comparison for subset/superset/overlap checks.

- **Priority Queue/Sorted Data Structures**: Matchers maintain networks sorted by prefix length (CIDR) or start address (range). Use a language's native sorted collection (e.g., TreeMap in Java, sorted_container in Python, std::set in C++).

- **String Processing**: Comment detection and stripping; line splitting; pattern delimiter splitting. Use regex or manual string scanning.

### Testing Strategy

Critical behaviors to test:
- CIDR parsing and normalization: Malformed CIDRs, edge cases (0.0.0.0/0, /32, /128)
- Network comparison: All four match types, both IPv4 and IPv6, cross-type matching (CIDR ↔ range)
- File scanning: Comment lines, inline comments, multiple formats on one line
- Argument disambiguation: Pattern vs file detection
- Color output: All color codes, environment variable priorities
- Exit codes: All scenarios (match found, no match, error)

### Performance Considerations

- **File scanning**: Process line-by-line with minimal buffering for large files
- **Pattern matching**: Use efficient matchers (binary search on sorted data)
- **Deduplication**: Use hash sets for O(1) lookup during extraction
- **Regex caching**: Compile regex patterns once at startup, reuse
- **Concurrency (optional)**: File scanning can be parallelized across files (if language supports threads/processes)

### Language-Specific Guidance

**C++**:
- Use `<ipaddress>` library (C++20) or Boost for IP address manipulation
- Use `<regex>` for pattern matching
- Use `std::set`, `std::map` for sorted collections
- Use `<filesystem>` for directory walking
- Manage memory carefully (consider smart pointers)

**Rust**:
- Use `ipnetwork` or `cidr` crate for network operations
- Use `regex` crate for patterns
- Use `std::collections::BTreeMap` for sorted collections
- Use `walkdir` crate for recursive directory traversal
- Leverage Rust's type system for correctness (avoid Option/Result misuse)

**Go**:
- Use `net` package for IP address operations
- Use `regexp` for patterns
- Use `sync.Map` or channel-based concurrency for parallel file scanning
- Use `filepath.Walk` for directory traversal
- Keep goroutines under control (worker pool pattern)

---

## Future Improvements (Post v5.0)

### Output Handling Refactoring

**Recommended for Next Major Release**: Centralize all output through a single unified function that accepts:
- `mode` (extract, consolidate, normal, count, list, silent)
- `content` (text to output)
- `flags` (null_output, null_data, color, quiet)

**Current State (v5.0)**: Output handling is scattered across ~15 separate `print()` statements throughout the CLI layer, making it difficult to:
- Add new output features consistently
- Ensure all modes respect output flags uniformly
- Maintain feature parity when adding new flags

**Refactoring Benefits**:
- Single point of control for all stdout output
- Easier to add new flags (like `-Z` for NUL-terminated filenames)
- Reduced code duplication
- Better testability of output formatting

**Implementation Note**: This refactoring is backward-compatible and does not affect the API contract. It is purely an internal architectural improvement.

---

## Conclusion

This specification provides a complete blueprint for reimplementing grepnet in any programming language while maintaining exact API and behavioral parity. The key to success is faithfully implementing:

1. The network parsing pipeline (comment handling, extraction order, deduplication, false-positive filters)
2. The network comparison logic (equals, subset, superset, overlap)
3. The CLI argument processing (disambiguation, mode resolution, validation)
4. The output rendering system (colors, prefixes, context, formatting)
5. The error handling and exit codes

All other details (internal optimizations, data structure choices) can vary based on language strengths and conventions.
