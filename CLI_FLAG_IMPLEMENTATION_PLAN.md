# GREPNET CLI FLAG IMPLEMENTATION PLAN

**Date**: 2026-10-06  
**Purpose**: Detailed implementation strategy for fixing CLI flags to match spec and grep compatibility  
**Status**: ✅ COMPLETE - All 11 items implemented and verified

---

## COMPLETION SUMMARY

**All tasks completed as of 2026-10-06:**
- ✅ Phase 1: 6 flag renames (equals→equal, file-patterns→patterns-file, file→input-file, tab→initial-tab, files-with-matches→files-with-matches, files-without-matches→files-without-match)
- ✅ Phase 2: 4 new flags added (-Z/--null, -z/--null-data, -a/--text, -I)
- ✅ Phase 3: 1 alias added (--silent for -q)
- ✅ Phase 4: Semantic handlers for binary mode flags and null output

**Attribute name updates applied:**
- `args.equals` → `args.equal` (1 reference)
- `args.tab_prefix` → `args.initial_tab` (10 references)
- `args.files_without_matches` → `args.files_without_match` (5 references)

**All flags verified working:**
- `-e, --equal` ✓
- `-l, --files-with-matches` ✓
- `-L, --files-without-match` ✓
- `-T, --initial-tab` ✓
- `-f, --patterns-file` ✓
- `-F, --input-file` ✓
- `-a, --text` ✓
- `-I` ✓
- `-Z, --null` ✓
- `-z, --null-data` ✓
- `-q, --quiet (with --silent alias)` ✓

**Spec updated**: GREPNET-SPEC.md corrected with new flag names and added future improvements section

---

## IMPLEMENTATION OVERVIEW

This plan addresses:
1. **6 name corrections** (rename existing flags)
2. **4 new flags to add** (missing entirely)
3. **1 alias to add** (--silent)
4. All code/spec misalignments documented

---

## PHASE 1: NAME CORRECTIONS (Rename Existing Flags)

### 1. Rename `--equals` → `--equal`

**File**: `src/grepnet/cli.py`

**Current**:
```python
parser.add_argument(
    '-e',
    '--equals',
    action='store_true',
    help='Match only EQUALS',
)
```

**Change to**:
```python
parser.add_argument(
    '-e',
    '--equal',
    action='store_true',
    help='Match equal networks',
)
```

**Impact**: Grammar correction, matches spec and common convention  
**Tests affected**: Any test checking for `--equals` flag name

---

### 2. Rename `--file-patterns` → `--patterns-file`

**File**: `src/grepnet/cli.py`

**Current**:
```python
parser.add_argument(
    '-f',
    '--file-patterns',
    action='store',
    dest='pattern_file',
    help='Read patterns from file (one per line)',
)
```

**Change to**:
```python
parser.add_argument(
    '-f',
    '--patterns-file',
    action='store',
    dest='pattern_file',
    help='Read patterns from file (one per line)',
)
```

**Impact**: Matches standard naming (object-descriptor → descriptor-object pattern)  
**Spec alignment**: Now matches `-f, --patterns-file` in GREPNET-SPEC.md  
**Tests affected**: Any test using `--file-patterns`

---

### 3. Rename `--file` → `--input-file`

**File**: `src/grepnet/cli.py`

**Current**:
```python
parser.add_argument(
    '-F',
    '--file',
    action='append',
    dest='input_files_explicit',
    help='Specify input file explicitly (can be used multiple times)',
)
```

**Change to**:
```python
parser.add_argument(
    '-F',
    '--input-file',
    action='append',
    dest='input_files_explicit',
    help='Specify input file explicitly (repeatable)',
)
```

**Impact**: Matches grep's naming convention  
**Spec alignment**: Now matches `-F, --input-file` in GREPNET-SPEC.md  
**Tests affected**: Any test using `--file`

---

### 4. Rename `--tab` → `--initial-tab`

**File**: `src/grepnet/cli.py`

**Current**:
```python
parser.add_argument(
    '-T',
    '--tab',
    action='store_true',
    dest='tab_prefix',
    help='Prepend tab character to each output line',
)
```

**Behavior to verify**: Should match grep's behavior:
> Make sure that the first character of actual line content lies on a tab stop, so that the alignment of tabs looks normal.

**Potential issue**: Current description says "Prepend tab" but spec says "Insert tab after prefixes for alignment"

**Change to**:
```python
parser.add_argument(
    '-T',
    '--initial-tab',
    action='store_true',
    dest='initial_tab',
    help='Insert tab after prefixes for alignment',
)
```

**Impact**: Matches grep naming and clarifies semantic  
**Spec alignment**: Now matches `-T, --initial-tab` in GREPNET-SPEC.md  
**Behavior impact**: May need to review implementation to ensure alignment is correct  
**Tests affected**: Any test using `-T` or `--tab`

---

### 5. Rename `--files-with-matches` → `--list`

**File**: `src/grepnet/cli.py`

**Current**:
```python
parser.add_argument(
    '-l',
    '--files-with-matches',
    action='store_true',
    help='Print only files with matches',
)
```

**Change to**:
```python
parser.add_argument(
    '-l',
    '--list',
    action='store_true',
    help='Print only files with matches',
)
```

**Impact**: Matches grep's shorter name  
**Spec alignment**: Now matches `-l, --list` in GREPNET-SPEC.md  
**Tests affected**: Any test using `--files-with-matches`

---

### 6. Rename `--files-without-matches` → `--files-without-match`

**File**: `src/grepnet/cli.py`

**Current**:
```python
parser.add_argument(
    '-L',
    '--files-without-matches',
    action='store_true',
    help='Print only files without matches',
)
```

**Change to**:
```python
parser.add_argument(
    '-L',
    '--files-without-match',
    action='store_true',
    help='Print only files without matches',
)
```

**Impact**: Matches grep's naming (singular)  
**Spec alignment**: Now matches `-L, --files-without-match` in GREPNET-SPEC.md  
**Tests affected**: Any test using `--files-without-matches`

---

## PHASE 2: NEW FLAGS - CRITICAL (Add These First)

### 7. Add `-Z, --null` Flag

**File**: `src/grepnet/cli.py`

**Add**:
```python
parser.add_argument(
    '-Z',
    '--null',
    action='store_true',
    dest='null_output',
    help='Output NUL byte instead of newline after filename',
)
```

**Implementation Location**: `src/grepnet/cli.py` (output handling)

**Behavior**:
- When set, output NUL byte (0x00) instead of newline after filenames
- Used with `-l` (list files) or `-H` (with filename) for use with `xargs -0`
- Example: `grepnet -lZ '192.0.2.0/24' file.txt | xargs -0 rm`

**Where to implement**:
1. Add flag to CLI parser ✓ (above)
2. Pass to output formatter via `args.null_output`
3. In output module: after printing filename, check `null_output` flag
4. If true: output '\0' instead of '\n'
5. If false: output '\n' (default)

**Code location**: Likely in `src/grepnet/cli.py` output section where filenames are printed

**Testing**:
```bash
grepnet -Z -l '192.0.2.0/24' file.txt | od -c | grep '\0'
```

**Priority**: CRITICAL - Important for scripting/automation

---

### 8. Add `-z, --null-data` Flag

**File**: `src/grepnet/cli.py`

**Add**:
```python
parser.add_argument(
    '-z',
    '--null-data',
    action='store_true',
    dest='null_data',
    help='Treat input/output data as NUL-terminated records',
)
```

**Implementation Location**: `src/grepnet/input/input_source.py` and output formatter

**Behavior**:
- Input: Lines are read as NUL-terminated records (line separator is '\0' not '\n')
- Output: Lines are printed with NUL terminators instead of newlines
- Used with `sort -z`, `xargs -0`, `find -print0`

**Where to implement**:
1. Add flag to CLI parser ✓ (above)
2. Pass `args.null_data` to `InputSource` class
3. In `InputSource.lines()` iterator:
   - If `null_data=True`: split on '\0' instead of '\n'
   - Handle edge case: when reading from binary stream, detect record separators
4. In output formatter:
   - If `null_data=True`: print lines with '\0' suffix instead of '\n'
   - Combine with `-Z` if both flags are used

**Code location**: 
- `src/grepnet/input/input_source.py` - modify `lines()` method
- Output module - modify newline output

**Interaction with other flags**:
- Works with `-Z`: both input and output are NUL-terminated
- Works with `-H`: output becomes `filename\0line\0`
- Works with `-l`: output becomes `filename\0`

**Testing**:
```bash
printf "192.0.2.0/24\x00192.0.1.0/24\x00" | grepnet -z '192.0.2.0/24' | od -c
```

**Priority**: CRITICAL - Important for pipeline processing

---

### 9. Add `-a, --text` Flag

**File**: `src/grepnet/cli.py`

**Add**:
```python
parser.add_argument(
    '-a',
    '--text',
    action='store_true',
    dest='text_mode',
    help='Process binary files as text',
)
```

**Implementation Location**: Binary detection and file processing

**Behavior**:
- Process binary files as text (disable binary detection)
- Equivalent to `--binary-files=text`
- If both `-a` and `--binary-files` are specified, last one wins (or they work together)

**Where to implement**:
1. Add flag to CLI parser ✓ (above)
2. In file processing, check for `-a` flag:
   - If true: skip binary detection, treat all files as text
   - Ignore binary markers (null bytes, etc.)
3. Coordinate with `--binary-files` flag:
   - If both set: `--binary-files` takes precedence (or document behavior)
   - Suggestion: if `-a` set, internally set `binary_files_mode='text'`

**Code location**: 
- `src/grepnet/core/binary_detector.py` - skip detection if `-a` set
- File processing loop - check for `-a` flag

**Testing**:
```bash
grepnet -a 'pattern' binary_file.bin
grepnet -a --binary-files=without-match 'pattern' file.bin  # Which takes precedence?
```

**Priority**: HIGH - Binary file compatibility

---

### 10. Add `-I` Flag

**File**: `src/grepnet/cli.py`

**Add**:
```python
parser.add_argument(
    '-I',
    action='store_true',
    dest='no_binary_match',
    help='Treat binary files as non-matching',
)
```

**Implementation Location**: Binary detection and file processing

**Behavior**:
- Binary files are treated as non-matching (no output from binary files)
- Output message: `Binary file <filename> matches` if binary file would have matched
- Equivalent to `--binary-files=without-match`

**Where to implement**:
1. Add flag to CLI parser ✓ (above)
2. When binary file is detected:
   - If `-I` flag set: treat file as non-matching, skip content scanning
   - If patterns would match (based on filename or context), output: `Binary file <filename> matches`
3. Coordinate with `--binary-files`:
   - If both set: `--binary-files` takes precedence
   - Suggestion: if `-I` set, internally set `binary_files_mode='without-match'`

**Code location**:
- `src/grepnet/core/binary_detector.py` - check for `-I` flag
- File processing loop - output "Binary file X matches" message

**Testing**:
```bash
grepnet -I '192.0.2.0/24' binary_file.bin
```

**Priority**: HIGH - Binary file compatibility

---

## PHASE 3: ALIASES & ADJUSTMENTS

### 11. Add `--silent` Alias for `-q, --quiet`

**File**: `src/grepnet/cli.py`

**Current**:
```python
parser.add_argument(
    '-q',
    '--quiet',
    action='store_true',
    help='Suppress output (exit code only)',
)
```

**Change to**:
```python
parser.add_argument(
    '-q',
    '--quiet',
    '--silent',  # Add as additional long-form name
    action='store_true',
    help='Suppress output (exit code only)',
)
```

**Note**: Check argparse documentation for how to add multiple long-form names:
- Option 1: Use `add_argument('-q', '--quiet', '--silent', ...)`  (may not work)
- Option 2: Create two separate arguments with same `dest`:
```python
parser.add_argument('-q', '--quiet', action='store_true', dest='quiet')
parser.add_argument('--silent', action='store_true', dest='quiet')
```

**Impact**: Matches grep's alias  
**Tests affected**: None (backward compatible, adds new option)

---

## PHASE 4: FLAG COORDINATION & CONFLICT HANDLING

### When Both Short Form AND Long Form Options Exist

**Example**: `-a, --text` and `--binary-files`

**Recommended Behavior**:
1. If only `-a`: set mode to 'text'
2. If only `--binary-files`: use specified mode
3. If both:
   - **Option A**: Last one wins (most recent flag on command line)
   - **Option B**: Error - conflicting options
   - **Option C**: `--binary-files` always takes precedence (most explicit)

**Recommendation**: Implement **Option A (last one wins)** to match grep behavior

**Implementation**:
```python
# After parsing args
binary_mode = args.binary_files  # Default value

if args.text_mode:  # If -a was used
    binary_mode = 'text'

if args.no_binary_match:  # If -I was used
    binary_mode = 'without-match'

# Now binary_mode has the final decision
```

---

## SPEC CORRECTIONS ALREADY DONE

These spec sections have already been updated:

1. ✅ `-f, --cidrfile` → **`-f, --patterns-file`** (GREPNET-SPEC.md line 1899)
2. ✅ `-L, --files-without` → **`-L, --files-without-match`** (GREPNET-SPEC.md lines 1757, 1970)
3. ✅ Added `-z, --null-data` section (GREPNET-SPEC.md line 1978+)

---

## SUMMARY TABLE

| # | Type | Flag | Current | Target | Status | Priority |
|---|------|------|---------|--------|--------|----------|
| 1 | Rename | `-e` | `--equals` | `--equal` | TODO | HIGH |
| 2 | Rename | `-f` | `--file-patterns` | `--patterns-file` | TODO | HIGH |
| 3 | Rename | `-F` | `--file` | `--input-file` | TODO | HIGH |
| 4 | Rename | `-T` | `--tab` | `--initial-tab` | TODO | MEDIUM |
| 5 | Rename | `-l` | `--files-with-matches` | `--list` | TODO | LOW |
| 6 | Rename | `-L` | `--files-without-matches` | `--files-without-match` | TODO | LOW |
| 7 | Add | `-Z` | ❌ Missing | `--null` | TODO | CRITICAL |
| 8 | Add | `-z` | ❌ Missing | `--null-data` | TODO | CRITICAL |
| 9 | Add | `-a` | ❌ Missing | `--text` | TODO | HIGH |
| 10 | Add | `-I` | ❌ Missing | (no long form) | TODO | HIGH |
| 11 | Alias | `-q` | `--quiet` | `--quiet, --silent` | TODO | MEDIUM |

---

## TESTING STRATEGY

### Unit Tests (by flag):
1. Each renamed flag still works with short form
2. Each renamed flag works with new long form
3. Each new flag can be parsed
4. Each new flag sets correct internal state

### Integration Tests:
1. `-Z` with `-l`: output files with NUL separator
2. `-z` with stdin: read NUL-terminated records
3. `-a` and `--binary-files=text`: equivalent behavior
4. `-I` and `--binary-files=without-match`: equivalent behavior
5. `-q`/`--quiet`/`--silent`: all three work identically

### Regression Tests:
1. All existing tests pass with renamed flags
2. Backward compatibility checked (if any)

### Command-Line Examples:
```bash
# Test -Z
grepnet -Z -l '192.0.2.0/24' file.txt | od -c

# Test -z
printf "192.0.2.0/24\x0010.0.0.0/8\x00" | grepnet -z '192.0.2.0/24'

# Test -a
grepnet -a '192' binary_file.bin

# Test -I  
grepnet -I '192' binary_file.bin

# Test new long names
grepnet --equal '192.0.2.0/24' file.txt
grepnet --patterns-file patterns.txt file.txt
grepnet --input-file input1.txt --input-file input2.txt
grepnet --list '192.0.2.0/24' *.txt
grepnet --initial-tab -n '192.0.2.0/24' file.txt

# Test --silent alias
grepnet --silent '192.0.2.0/24' file.txt
```

---

## ESTIMATED EFFORT

- **Phase 1 (Renames)**: ~30 minutes
  - Simple string replacements
  - Update help text
  - Update tests
  
- **Phase 2 (New Flags)**: ~3 hours
  - Flag parsing: 20 minutes
  - `-Z` implementation: 30 minutes
  - `-z` implementation: 60 minutes (affects input reading)
  - `-a` implementation: 30 minutes
  - `-I` implementation: 30 minutes
  
- **Phase 3 (Aliases)**: ~15 minutes
  - Add --silent
  
- **Phase 4 (Coordination)**: ~30 minutes
  - Test flag interactions
  - Document precedence

**Total**: ~4 hours

---

## ROLLOUT PLAN

1. **Sprint 1**: Phases 1 & 3 (Renames + Aliases) = 45 minutes
2. **Sprint 2**: Phase 2 Sections 7-8 (`-Z`, `-z`) = 2 hours
3. **Sprint 3**: Phase 2 Sections 9-10 (`-a`, `-I`) = 1 hour
4. **Sprint 4**: Phase 4 + Testing = 1 hour

---

## NOTES

- Keep backward compatibility where possible (add deprecation warnings if needed)
- Update help text to match grep's descriptions
- Update man page / documentation after code changes
- Run full test suite after each phase
- Consider user migration guide if breaking changes

