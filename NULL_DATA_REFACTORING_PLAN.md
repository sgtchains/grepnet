# NULL-DATA FLAG (-z) REFACTORING PLAN

**Date**: 2026-10-06  
**Purpose**: Implement `-z, --null-data` flag for NUL-terminated record processing  
**Scope**: Cross-module refactoring touching input pipeline, output handling, and record processing  
**Effort**: ~3-4 hours

---

## OVERVIEW

The `-z` flag changes record delimiters from newline (`\n`) to NUL byte (`\0`). This is a common feature in Unix tools for handling filenames with spaces/special characters via xargs and find.

### Current State
- Flag recognized in argparse (dest: `null_data`)
- No implementation in input reading pipeline
- No implementation in output formatting

### Required Changes
1. **Input Pipeline** (`src/grepnet/input/input_source.py`): Split records on `\0` instead of `\n`
2. **Line Numbering**: Adjust how lines are counted (NUL-delimited records)
3. **Output Formatting** (`src/grepnet/cli.py`): End records with `\0` instead of `\n`
4. **Binary Detection**: Revisit for NUL-heavy data (may look like binary)

---

## PHASE 1: INPUT PIPELINE REFACTORING

### 1.1 Modify InputSource Class Constructor

**File**: `src/grepnet/input/input_source.py`

**Current signature**:
```python
def __init__(self, source_type, file_path=None, stdin_fd=None, display_name=None):
```

**Change to**:
```python
def __init__(self, source_type, file_path=None, stdin_fd=None, display_name=None, null_delimited=False):
    self.null_delimited = null_delimited
    self.record_delimiter = '\0' if null_delimited else '\n'
```

**Impact**: Store null-delimited mode flag for use in line reading methods

---

### 1.2 Refactor `_lines_from_file()`

**File**: `src/grepnet/input/input_source.py` line ~133

**Current approach**:
```python
for line_bytes in self._file_handle:  # Uses newline splitting
    line = line_bytes.decode('utf-8', errors='replace')
    line_content = line.rstrip('\n\r')  # Remove newlines
    yield line_num, line_content, byte_offset
```

**Required change**:
- For `-z` mode: Read file in binary chunks, split on `\0` instead of `\n`
- Maintain byte offset tracking for each record
- Handle edge case: records not ending with `\0` (read until EOF)

**Implementation approach**:
```python
def _lines_from_file(self) -> Iterator[Tuple[int, str, int]]:
    """Read lines/records from file with byte offset tracking."""
    self._file_handle = open(self.file_path, 'rb')
    line_num = 1
    byte_offset = 0
    
    if self.null_delimited:
        # Read entire file, split on NUL
        content = self._file_handle.read()
        records = content.split(b'\0')
        
        for record_bytes in records:
            if not record_bytes:  # Skip empty records
                continue
                
            # Decode record
            record_str = self._decode_bytes(record_bytes)
            
            # Yield with byte offset
            yield line_num, record_str, byte_offset
            byte_offset += len(record_bytes) + 1  # +1 for NUL delimiter
            line_num += 1
    else:
        # Original newline-delimited logic
        for line_bytes in self._file_handle:
            ...existing code...
```

**Tradeoff**: Loading entire file into memory for `-z` mode. For large files, consider chunked reading with buffer.

---

### 1.3 Refactor `_lines_from_stdin()`

**File**: `src/grepnet/input/input_source.py` line ~160

**Current approach**:
```python
for line in sys._stdin.readline():  # Newline-based
```

**Required change**:
- For `-z` mode: Read stdin in chunks, buffer and split on `\0`
- Handle incomplete records at buffer boundary
- Maintain line numbering

**Implementation**:
```python
def _lines_from_stdin(self) -> Iterator[Tuple[int, str, int]]:
    """Read lines/records from stdin."""
    line_num = 1
    partial_record = b''
    
    if self.null_delimited:
        # Read stdin in chunks, split on NUL
        chunk_size = 8192
        byte_offset = 0
        
        while True:
            chunk = sys.stdin.buffer.read(chunk_size)
            if not chunk:
                # Handle final partial record
                if partial_record:
                    record_str = self._decode_bytes(partial_record)
                    yield line_num, record_str, byte_offset
                break
            
            # Combine with leftover from previous chunk
            buffer = partial_record + chunk
            records = buffer.split(b'\0')
            
            # Last element might be incomplete - save for next iteration
            partial_record = records[-1]
            
            # Process complete records
            for record_bytes in records[:-1]:
                record_str = self._decode_bytes(record_bytes)
                yield line_num, record_str, byte_offset
                byte_offset += len(record_bytes) + 1
                line_num += 1
    else:
        # Original newline-based logic
        ...existing code...
```

---

### 1.4 Refactor `_lines_from_fd()`

**File**: `src/grepnet/input/input_source.py` line ~180

**Required change**: Same chunked reading approach as `_lines_from_stdin()` but reading from file descriptor

---

### 1.5 Update InputDiscovery to Pass Null-Delimited Flag

**File**: `src/grepnet/input/input_source.py` or `src/grepnet/cli.py`

**Current**:
```python
input_sources = InputDiscovery.get_sources(
    files=files,
    recursive=args.recursive,
    dereference_recursive=args.dereference_recursive,
    include_patterns=args.include_patterns,
    exclude_patterns=args.exclude_patterns,
    exclude_dirs=args.exclude_dirs,
)
```

**Change to**:
```python
input_sources = InputDiscovery.get_sources(
    files=files,
    recursive=args.recursive,
    dereference_recursive=args.dereference_recursive,
    include_patterns=args.include_patterns,
    exclude_patterns=args.exclude_patterns,
    exclude_dirs=args.exclude_dirs,
    null_delimited=args.null_data,  # NEW
)
```

---

## PHASE 2: OUTPUT FORMATTING REFACTORING

### 2.1 Create Output Delimiter Variable

**File**: `src/grepnet/cli.py` (early in `run()` function)

```python
# Set output record delimiter based on -z flag
output_delimiter = '\0' if args.null_data else '\n'
```

### 2.2 Update All Print Statements

Replace all stdout output calls to respect the delimiter:

**Before**:
```python
print(output)
print(f"{filename}:{line_num}")
```

**After**:
```python
print(output, end=output_delimiter)
print(f"{filename}:{line_num}", end=output_delimiter)
```

**Affected locations** (in `src/grepnet/cli.py`):
- Line 754: Extract mode output
- Line 756: Extract mode network only
- Line 789: Consolidate mode output
- Line 841: Group separator
- Line 881: Normal mode output
- Line 957: Only-matching mode
- Line 973: Normal mode (alternative path)
- Line 1007: Output (alternative path)
- Line 1040: Binary file message
- Line 1133: Only-matching mode (alternative)
- Line 1162: Output with debug
- Line 1181: Files-with-matches (-l)
- Line 1201: Files-without-match (-L)
- Line 1217-1219: Count mode per-file
- Line 1222: Count mode total

---

## PHASE 3: RECORD NUMBERING ADJUSTMENT

### 3.1 Context Lines with NUL Delimiters

**Current issue**: Context tracking assumes newline-delimited records

**File**: `src/grepnet/cli.py` (context handling section)

**Required change**: When `-z` is set, context line handling needs adjustment since line numbers refer to NUL-delimited records, not actual text lines.

**Approach**: No change needed - record numbers correspond to what would be "lines" in grep terminology with `-z`

---

## PHASE 4: TESTING STRATEGY

### 4.1 Create Test Files

```bash
# Create NUL-delimited test file
printf '192.0.2.0/24\0192.0.2.1\010.0.0.0/8\0' > tests/files/null_delimited_test.txt

# Create patterns file with NUL delimiters
printf '192.0.2.0/24\0' > tests/files/null_patterns.txt
```

### 4.2 Test Cases

1. **Basic null-delimited input**:
   ```bash
   grepnet -z '192.0.2.0/24' tests/files/null_delimited_test.txt
   # Should match first record, output with \0 delimiter
   ```

2. **Null-delimited input + null output**:
   ```bash
   grepnet -z -l '192.0.2.0/24' tests/files/null_delimited_test.txt | od -c
   # Should output filenames with \0 instead of \n
   ```

3. **Pattern from null-delimited file**:
   ```bash
   grepnet -z -f tests/files/null_patterns.txt tests/files/null_delimited_test.txt
   ```

4. **Stdin with NUL delimiters**:
   ```bash
   printf '192.0.2.0/24\0192.0.2.1\0' | grepnet -z '192.0.2.0/24'
   ```

5. **Integration with xargs**:
   ```bash
   find tests/files -type f -print0 | xargs -0 grepnet -z '192.0.2.0/24'
   ```

---

## PHASE 5: EDGE CASES & CONSIDERATIONS

### 5.1 Binary File Detection

**Issue**: Files with many NUL bytes might be detected as binary

**Solution**: Pass `null_delimited` flag to binary detector to skip detection when `-z` is used

**File**: `src/grepnet/cli.py` or `src/grepnet/core/binary_detector.py`

```python
# Skip binary detection if -z is set (NUL is expected)
if args.null_data:
    is_binary = False
else:
    is_binary = detect_binary(...)
```

### 5.2 Empty Records

**Current**: Treat empty records as valid (may have matches)

**Consideration**: Skip empty records or process normally? Standard grep behavior with `-z` processes empty records.

### 5.3 Records Not Ending with NUL

**Current file format assumption**: All records end with `\0`

**Edge case**: Last record may not have trailing `\0`

**Solution**: Handled by final buffer flush in chunked reading

### 5.4 Mixed Output Modes

**Case**: User provides both `-z` and `-Z`?

**Decision**: Both flags orthogonal
- `-z`: Input/record delimiter (splits on `\0` instead of `\n`)
- `-Z`: Output filename delimiter (use `\0` instead of `\n` after filenames)

Result: Can be used together: `grepnet -z -Z -l` for NUL-delimited input and output

---

## IMPLEMENTATION CHECKLIST

- [ ] Update `InputSource.__init__()` to accept `null_delimited` parameter
- [ ] Refactor `_lines_from_file()` for NUL-delimited records
- [ ] Refactor `_lines_from_stdin()` for chunked NUL-delimited reading
- [ ] Refactor `_lines_from_fd()` for NUL-delimited reading
- [ ] Update `InputDiscovery.get_sources()` to pass `null_delimited` flag
- [ ] Add `output_delimiter` variable to CLI
- [ ] Update all ~15 print() statements to use `output_delimiter`
- [ ] Test binary file detection with `-z`
- [ ] Create test files and test cases
- [ ] Test integration with xargs/find
- [ ] Run full test suite
- [ ] Document in manpage

---

## EFFORT ESTIMATE

| Phase | Task | Hours |
|-------|------|-------|
| 1 | Input pipeline refactoring | 1.5 |
| 2 | Output formatting updates | 0.5 |
| 3 | Context line adjustment | 0.25 |
| 4 | Testing & debugging | 1 |
| 5 | Edge cases & integration | 0.75 |
| **Total** | | **4** |

---

## ROLLOUT STRATEGY

1. **Branch**: Create feature branch for null-data support
2. **Implement Phase 1**: Input pipeline (highest risk, most testing needed)
3. **Implement Phase 2**: Output formatting (quick, low risk)
4. **Test thoroughly**: All edge cases before merge
5. **Documentation**: Update manpage and spec
6. **Release**: Include in v5.1 or later

---

## RISKS & MITIGATION

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Memory usage with large files | High | Implement chunked reading for files >1GB |
| Breaking existing behavior | High | Comprehensive regression tests |
| Performance regression | Medium | Benchmark input pipeline before/after |
| Binary detection false positives | Low | Skip detection when `-z` is set |

