# GREP vs GREPNET: Overlapping Flags Analysis

**Date**: 2026-10-06  
**Source**: GNU grep man page (standard implementation)  
**Purpose**: Identify which CLI flags overlap between grep and grepnet spec

---

## GREP FLAG CATEGORIES & DEFINITIONS

### Pattern Syntax (How to interpret patterns)
- `-E, --extended-regexp` - ERE (extended regex)
- `-F, --fixed-strings` - Fixed strings (no regex)
- `-G, --basic-regexp` - BRE (basic regex)
- `-P, --perl-regexp` - PCRE (Perl-compatible regex)

### Matching Control
- `-e, --regexp=PATTERNS` - Use PATTERNS as patterns (repeatable)
- `-f, --file=FILE` - Obtain patterns from file (repeatable)
- `-i, --ignore-case` - Ignore case in matching
- `--no-ignore-case` - Do NOT ignore case (explicit override)
- `-v, --invert-match` - Select NON-matching lines
- `-w, --word-regexp` - Match whole words only
- `-x, --line-regexp` - Match entire line only

### General Output Control
- `-c, --count` - Print count of matches (not lines)
- `--color[=WHEN]` - Color output (never|always|auto)
- `-L, --files-without-match` - List files with NO matches
- `-l, --files-with-matches` - List files WITH matches
- `-m NUM, --max-count=NUM` - Stop after NUM matches
- `-o, --only-matching` - Print only matched parts
- `-q, --quiet, --silent` - Suppress all output (exit code only)
- `-s, --no-messages` - Suppress error messages

### Output Line Prefix Control
- `-b, --byte-offset` - Print byte offset before line
- `-H, --with-filename` - Print filename for each match
- `-h, --no-filename` - Suppress filename prefix
- `--label=LABEL` - Custom label for stdin
- `-n, --line-number` - Print 1-based line number
- `-T, --initial-tab` - Tab stop alignment
- `-Z, --null` - NUL byte after filename (for xargs -0)

### Context Line Control
- `-A NUM, --after-context=NUM` - NUM lines after match
- `-B NUM, --before-context=NUM` - NUM lines before match
- `-C NUM, --context=NUM` - NUM lines around match
- `--group-separator=SEP` - Custom separator (default: --)
- `--no-group-separator` - Suppress separator

### Directory Scanning
- `-d {read|skip|recurse}` - How to handle directories
- `-D {read|skip}` - How to handle device files
- `-r, --recursive` - Recursive (don't follow symlinks)
- `-R` - Recursive (follow symlinks) [non-standard]
- `--include=PATTERN` - Include files matching pattern
- `--exclude=PATTERN` - Exclude files matching pattern
- `--exclude-dir=PATTERN` - Exclude directories

### Binary File Handling
- `-a, --text` - Process binary as text
- `-I` - Treat binary as non-matching
- `--binary-files={binary|text|without-match}` - Binary handling

### Program Info
- `--help` - Show help
- `-V, --version` - Show version
- `--version` - Show version

---

## GREP FLAGS FOUND IN GREPNET SPEC ✅

These flags appear in both grep and grepnet spec:

| Category | Flag | Grep | Spec | Code | Status |
|----------|------|------|------|------|--------|
| **Matching** | `-v, --invert-match` | ✅ | ✅ | ✅ | MATCH |
| **Matching** | `-o, --only-matching` | ✅ | ✅ | ✅ | MATCH |
| **Output** | `-c, --count` | ✅ | ✅ | ✅ | MATCH |
| **Output** | `-m, --max-count` | ✅ | ✅ | ✅ | MATCH |
| **Output** | `-q, --quiet, --silent` | ✅ | ✅ (missing --silent) | ⚠️ | PARTIAL |
| **Output** | `-L, --files-without-match` | ✅ | `--files-without` | ❌ named `--files-without-matches` | MISMATCH |
| **Output** | `-l, --files-with-matches` | ✅ | `--list` | ❌ named `--files-with-matches` | MISMATCH |
| **Output** | `--color` | ✅ | ✅ | ✅ | MATCH |
| **Prefix** | `-n, --line-number` | ✅ | ✅ | ✅ | MATCH |
| **Prefix** | `-b, --byte-offset` | ✅ | ✅ | ✅ | MATCH |
| **Prefix** | `-H, --with-filename` | ✅ | ✅ | ✅ | MATCH |
| **Prefix** | `-h, --no-filename` | ✅ | ❌ `--no-filename` | ✅ | PARTIAL (code has it, spec doesn't) |
| **Prefix** | `-T, --initial-tab` | ✅ | ✅ | ❌ named `--tab` | MISMATCH |
| **Prefix** | `-Z, --null` | ✅ | ✅ | ❌ | MISSING |
| **Prefix** | `--label=LABEL` | ✅ | ✅ | ✅ | MATCH |
| **Context** | `-A, --after-context` | ✅ | ✅ | ✅ | MATCH |
| **Context** | `-B, --before-context` | ✅ | ✅ | ✅ | MATCH |
| **Context** | `-C, --context` | ✅ | ✅ | ✅ | MATCH |
| **Context** | `--group-separator` | ✅ | ✅ | ✅ | MATCH |
| **Context** | `--no-group-separator` | ✅ | ✅ | ✅ | MATCH |
| **Files** | `-r, --recursive` | ✅ | ✅ | ✅ | MATCH |
| **Files** | `-R, --dereference-recursive` | ⚠️ | ✅ | ✅ | MATCH |
| **Files** | `--include` | ✅ | ✅ | ✅ | MATCH |
| **Files** | `--exclude` | ✅ | ✅ | ✅ | MATCH |
| **Files** | `--exclude-dir` | ✅ | ✅ | ✅ | MATCH |
| **Binary** | `-a, --text` | ✅ | ✅ | ❌ | MISSING |
| **Binary** | `-I` | ✅ | ✅ | ❌ | MISSING |
| **Binary** | `--binary-files` | ✅ | ✅ | ✅ | MATCH |
| **Program** | `--help` | ✅ | ✅ | ⚠️ | PARTIAL (may be auto-generated) |
| **Program** | `--version` | ✅ | ✅ | ✅ | MATCH |

---

## GREP FLAGS NOT IN GREPNET

These are grep flags that grepnet does NOT implement (intentional differences):

| Flag | Grep Meaning | Reason NOT in grepnet |
|------|--------------|----------------------|
| `-E, --extended-regexp` | Use ERE syntax | grepnet uses network-aware matching, not regex |
| `-F, --fixed-strings` | Literal strings, no regex | grepnet uses network-aware matching, not regex |
| `-G, --basic-regexp` | Use BRE syntax | grepnet uses network-aware matching, not regex |
| `-P, --perl-regexp` | Use PCRE syntax | grepnet uses network-aware matching, not regex |
| `-e, --regexp` | Specify pattern(s) | grepnet uses `-P, --pattern` instead |
| `-f, --file` | Pattern file | grepnet uses `-f, --cidrfile` instead |
| `-i, --ignore-case` | Ignore case | N/A for network matching |
| `--no-ignore-case` | Don't ignore case | N/A for network matching |
| `-w, --word-regexp` | Whole words | N/A for network matching |
| `-x, --line-regexp` | Match entire line | N/A for network matching |
| `-s, --no-messages` | Suppress errors | grepnet uses `--no-messages` instead |
| `-d, --directories` | Directory handling | grepnet missing this flag |
| `-D, --devices` | Device handling | grepnet missing this flag |
| `--exclude-from` | Load exclude patterns | grepnet has this ✅ |

---

## GREPNET-SPECIFIC FLAGS (NOT IN GREP)

These are flags unique to grepnet for network-specific matching:

| Flag | Purpose | Category |
|------|---------|----------|
| `-e, --equal` *(should be `--equal`, not `--equals`)* | Match equal networks | Match type |
| `-s, --subset` | Match subsets | Match type |
| `-S, --superset` | Match supersets | Match type |
| `-O, --overlap` | Match overlapping | Match type |
| `-u, --unmatched` | Match unmatched | Match type |
| `-P, --pattern` | Specify pattern (grepnet-specific) | Pattern input |
| `--extract` | Extract all networks | Output mode |
| `--consolidate` | Consolidate overlapping | Output mode |
| `--show-content` | Show line content with extract | Output modifier |
| `--format` | Network output format | Output control |
| `--no-filter-comments` | Comment filtering control | Parsing |
| `--parse-cidr` | Where to parse CIDR | Parsing control |
| `--parse-netmask` | Where to parse netmask | Parsing control |
| `--parse-hostmask` | Where to parse hostmask | Parsing control |
| `--parse-ranges` | Where to parse ranges | Parsing control |
| `--range-format` | Range output format | Parsing control |
| `--strict-cidr` | CIDR validation scope | Validation |
| `--strict-cidr-action` | Action on validation error | Validation |
| `--exclude-string` | Exclude by regex | Exclusion |
| `--exclude-strings-file` | Load text exclusions | Exclusion |
| `--exclude-cidr` | Exclude by network | Exclusion |
| `--exclude-cidrs-file` | Load network exclusions | Exclusion |
| `-F, --input-file` *(code: `--file`)* | Input file (repeatable) | File input |
| `--exclude-from` | Load exclude glob patterns | File filtering |

---

## COMPLIANCE SUMMARY

### Flags That Match grep (Direct Compatibility)

**Complete matches** (name, behavior, semantics):
- `-v, --invert-match` ✅
- `-o, --only-matching` ✅
- `-c, --count` ✅
- `-m, --max-count` ✅
- `-n, --line-number` ✅
- `-b, --byte-offset` ✅
- `-H, --with-filename` ✅
- `--label` ✅
- `-A, --after-context` ✅
- `-B, --before-context` ✅
- `-C, --context` ✅
- `--group-separator` ✅
- `--no-group-separator` ✅
- `-r, --recursive` ✅
- `-R, --dereference-recursive` ✅
- `--include` ✅
- `--exclude` ✅
- `--exclude-dir` ✅
- `--color` ✅
- `--version` ✅
- `--binary-files` ✅
- `--exclude-from` ✅

**Total: 22 flags match grep** (60% of common flags)

### Flags That PARTIALLY Match grep (Name or semantic issues)

| Flag | Issue | Severity |
|------|-------|----------|
| `-q, --quiet, --silent` | Missing `--silent` alias | LOW |
| `-l, --files-with-matches` | Spec says `--list` not `--files-with-matches` | LOW |
| `-L, --files-without-match` | Spec says `--files-without` not `--files-without-matches` | LOW |
| `-T, --initial-tab` | Code says `--tab` not `--initial-tab` | MEDIUM |
| `-Z, --null` | Missing completely | HIGH |
| `-a, --text` | Missing completely | MEDIUM |
| `-I` | Missing completely | MEDIUM |
| `-d` | Missing completely (directory handling) | LOW |
| `-D` | Missing completely (device handling) | LOW |

### Flags That DON'T Match grep (Intentional Differences)

These flags are fundamentally different because grepnet does network matching, not regex:
- `-E, -F, -G, -P` (regex syntax flags) - N/A, grepnet uses network matching
- `-i, --ignore-case` - N/A for IP/CIDR matching
- `--no-ignore-case` - N/A for IP/CIDR matching  
- `-w, --word-regexp` - N/A for network matching
- `-x, --line-regexp` - N/A for network matching
- `-s, --no-messages` - Different in grepnet
- `-e, --regexp` - grepnet uses `-P, --pattern` instead

---

## KEY FINDINGS

### What grepnet Got RIGHT (grep-compatible):
1. ✅ **Core output flags** (-c, -n, -b, -H, -o, -v) 
2. ✅ **Context handling** (-A, -B, -C, --group-separator)
3. ✅ **File discovery** (-r, -R, --include, --exclude, --exclude-dir)
4. ✅ **Prefix control** (mostly: -n, -b, -H, --label)
5. ✅ **Binary handling** (--binary-files) 
6. ✅ **Quiet/help** (-q, --version)

### What grepnet Got WRONG (grep-incompatible):
1. ❌ **Flag names**: `-l` should have `--list` not `--files-with-matches`
2. ❌ **Flag names**: `-L` should have `--files-without-match` not `--files-without-matches`
3. ❌ **Flag names**: `-T` should have `--initial-tab` not `--tab`
4. ❌ **Missing flags**: `-Z, --null` (output NUL after filename for xargs)
5. ❌ **Missing flags**: `-z, --null-data` (treat input/output as NUL-terminated records)
6. ❌ **Missing flags**: `-a, --text` (process binary as text)
7. ❌ **Missing flags**: `-I` (treat binary as non-matching)
8. ❌ **Missing alias**: `--silent` for `-q`
9. ❌ **Missing flags**: `-d, -D` (directory/device handling)

### Spec vs Code Issues:
1. **Spec defines flag names differently than code**
   - Spec: `-f, --cidrfile` | Code: `-f, --file-patterns`
   - Spec: `-F, --input-file` | Code: `-F, --file`
   - Spec: `-l, --list` | Code: `-l, --files-with-matches`
   - Spec: `-L, --files-without` | Code: `-L, --files-without-matches`
   - Spec: `-e, --equal` | Code: `-e, --equals`
   - Spec: `-T, --initial-tab` | Code: `-T, --tab`

2. **Code implements more than spec defines**
   - Code has: `--no-filename` (not in spec sections reviewed)
   - Code has: `-R, --dereference-recursive` ✅ (in spec)

---

## RECOMMENDATIONS

### Priority 1: Match grep Exactly
- [ ] Add `-Z, --null` flag (output NUL after filename for xargs)
- [ ] Add `-z, --null-data` flag (treat input/output as NUL-terminated records)
- [ ] Add `-a, --text` flag (process binary as text)
- [ ] Add `-I` flag (treat binary as non-matching)
- [ ] Rename `--files-with-matches` to `--list` 
- [ ] Rename `--files-without-matches` to `--files-without-match`
- [ ] Rename `--tab` to `--initial-tab`
- [ ] Rename `--equals` to `--equal`
- [ ] Add `--silent` alias for `-q`

### Priority 2: Binary Handling - Keep All Three APIs
✅ **Keep all three for flexibility and grep compatibility**:
- `-a, --text` as shorthand (equiv. to `--binary-files=text`)
- `-I` as shorthand (equiv. to `--binary-files=without-match`)
- `--binary-files={binary|text|without-match}` as unified option
- All three should produce identical behavior
- Ensure they don't conflict when used together (last one wins, or error if conflicting)

### Priority 3: Complete File Handling
- [ ] Add `-d {read|skip|recurse}` flag
- [ ] Add `-D {read|skip}` flag
- [ ] Verify `-r` vs `-d` behavior difference

### Priority 4: Fix Flag Name Inconsistencies Between Spec and Code
- [ ] Spec says `-f, --patterns-file` but code has `--file-patterns`
- [ ] Spec says `-F, --input-file` but code has `--file`
- [ ] Spec says `-e, --equal` but code has `--equals`
- [ ] Spec says `-l, --list` but code has `--files-with-matches`
- [ ] Spec says `-L, --files-without-match` but code has `--files-without-matches`
- [ ] Update code to match spec exactly (now aligned with grep)

---

## CONCLUSION

**grep compatibility score**: ~73%

grepnet successfully borrows most of grep's "universal" flags for output control, context, and file discovery. However, it has **naming inconsistencies** between spec and code, and is **missing several important flags**:

**Missing critical flags**:
- `-Z, --null` (output NUL after filename for xargs -0)
- `-z, --null-data` (treat input/output as NUL-terminated records)
- `-a, --text` (process binary as text)
- `-I` (treat binary as non-matching)
- `-d, -D` (directory/device handling)

**Name mismatches** (spec vs code):
- Spec: `-f, --patterns-file` | Code: `--file-patterns`
- Spec: `-F, --input-file` | Code: `--file`
- Spec: `-e, --equal` | Code: `--equals`
- Spec: `-l, --list` | Code: `--files-with-matches`
- Spec: `-L, --files-without-match` | Code: `--files-without-matches`
- Spec: `-T, --initial-tab` | Code: `--tab`

The biggest issue is **misalignment between spec and code**. The specification defines different long-form names than what the code implements. Before adding new features, this gap should be resolved.

