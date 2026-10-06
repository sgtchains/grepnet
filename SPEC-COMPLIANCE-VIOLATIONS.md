# grepnet Spec Compliance Violations

**Document**: Comprehensive audit of grepnet implementation against GREPNET-SPEC.md (v5.0.0)

**Last Updated**: 2026-10-06

**Status**: Implementation significantly violates key architectural principles

---

## Executive Summary

The current grepnet implementation violates the **core architectural principle** defined in the spec: "All Input Is Input" (unified processing path). Specifically:

- ✅ **InputSource abstraction** is properly implemented
- ✅ **Basic infrastructure** (parsing, matching logic) is in place
- ❌ **Extract/Consolidate modes** violate unified architecture
- ❌ **Context buffering** violates streaming requirements
- ❌ **grepnet.search()** not used for all modes
- ❌ **Mode parameter** not implemented
- ❌ **Extract/Consolidate relationship** not properly composed

---

## Critical Architectural Violations

### Violation 1: Extract/Consolidate Bypass Unified Input Path

**Spec Requirement** (Implementation Architecture section):
> "All CLI output modes MUST funnel through a SINGLE unified input processing path"
> "GrepNet.search(input_sources) - SINGLE entry point for ALL output modes"

**Current Behavior**:
- **Normal mode**: Uses `grepnet.search(input_sources)` ✅
- **Extract mode**: Direct input loop in `cli.py:656-815` ❌
- **Consolidate mode**: Direct input loop in `cli.py:656-815` ❌

**Violation Details**:
```python
# CURRENT (WRONG): cli.py lines 656-815
if args.extract or args.consolidate:
    # Direct input loop - bypasses grepnet.search()
    for input_source in input_sources:
        for line_number, line_content, byte_offset in input_source.lines():
            # Direct parsing and matching
            parsed_extractions = grepnet.parser.parse_line(line)
            for parsed_ext in parsed_extractions:
                # Custom logic
```

**Spec Requirement**:
```python
# CORRECT (SPEC): Should use single path
if args.extract or args.consolidate:
    for match_result in grepnet.search(input_sources, mode='extract'|'consolidate'):
        # Apply formatting
```

**Impact**:
- Extract/Consolidate are not truly streaming
- Inconsistent binary detection handling
- Pattern filtering duplicated in extract/consolidate
- No single point of control for input processing

---

### Violation 2: grepnet.search() Missing Mode Parameter

**Spec Requirement**:
> "`GrepNet.search(input_sources, mode='normal'|'extract'|'consolidate')`"

**Current Signature** (`grepnet.py:545`):
```python
def search(self, input_sources: List[InputSource], yield_all_lines: bool = False) -> Iterator[MatchResult]:
```

**Missing Parameters**:
- `mode` parameter (should be 'normal', 'extract', or 'consolidate')
- Mode routing logic inside grepnet.search()

**Required Implementation**:
```python
def search(self, input_sources: List[InputSource], 
           mode: str = 'normal',  # NEW
           yield_all_lines: bool = False) -> Iterator[MatchResult]:
    """
    mode: 'normal' - standard matching with full MatchResult
          'extract' - extract unique networks from input
          'consolidate' - consolidate overlapping networks
    """
    if mode == 'extract':
        # Return deduplicated network stream
    elif mode == 'consolidate':
        # Return consolidated network stream
    else:  # normal
        # Return standard MatchResult stream
```

---

### Violation 3: Extract/Consolidate Helpers Not Implemented

**Spec Requirement** (Extract and Consolidate: Architectural Relationship section):
> "Consolidate MUST use extract's deduplication as input, then add merge step"
> "Implementation pattern: `unique_networks = extract(...); consolidated = consolidate_networks(unique_networks)`"

**Current State**:
- ❌ No `extract_networks()` function in grepnet.py
- ❌ No `consolidate_networks()` function in grepnet.py
- Extract/Consolidate are independent implementations in cli.py
- **No composition relationship**

**Current Implementation Issues**:
1. Extract logic is inline in cli.py (not reusable)
2. Consolidate re-implements extraction instead of using extract output
3. Can't share deduplication logic

**Required Functions** (grepnet.py):
```python
def extract_networks(self, input_sources: List[InputSource]) -> Dict[Network, ParsedExtraction]:
    """
    Extract unique networks from input.
    Returns deduplicated network dictionary.
    This is used by both --extract and --consolidate.
    """
    
def consolidate_networks(self, unique_networks: Dict[Network, ParsedExtraction]) -> List[Network]:
    """
    Consolidate (merge) overlapping/adjacent networks.
    Takes extract output as input.
    Returns consolidated network list.
    """
```

**Current Code Location**: Extract/consolidate logic inline in `cli.py:656-1050`

---

### Violation 4: Context Buffering Violates Streaming Requirement

**Spec Requirement**:
> "line-by-line processing with NO buffering between search and output (unless context flags require buffering)"
> "Only buffer what's necessary for the output mode (e.g., context lines)"

**Current Implementation** (`cli.py:1025+`):
```python
if use_context:
    # Streaming context mode with gap detection
    # Uses deque to buffer lines
    line_buffer = deque(maxlen=args.before_context)
```

**Violation Details**:
- Context buffering uses deque (OK for -B, -A limited buffering)
- **BUT**: No mention in spec of how context lines are validated
- **Unclear**: Whether context validation respects streaming (circular buffer vs full-file preload)

**Spec Requirement** (still missing detailed context implementation):
- Should use circular buffer (deque) for only N lines (not entire file)
- Should not preload entire file
- Current implementation appears to do this correctly (needs verification)

**Status**: Partially compliant - implementation appears correct but needs code review

---

## Missing Required Components

### Missing 1: MatchResult Contract Validation

**Spec Requirement**:
> "MatchResult object MUST contain sufficient metadata to support all output modes"

**MatchResult Fields Required**:
```
line_number, line_content, content_colored, content_marked,
filename, is_binary_file, byte_offset,
file_extraction, pattern_extraction, match_type, match_index, is_match
```

**Current Status**: Need to verify all fields are populated in all code paths
- Requires code review of MatchResult generation in grepnet.py

### Missing 2: Unified Output Formatter

**Spec Requirement**:
> "Output Formatter (cli.py output handling): Mode-specific formatting"
> "Applies prefixes (-n, -b, -H flags), Applies colorization, Deduplicates or consolidates based on mode"

**Current Status**:
- Extract/consolidate formatting is in cli.py (not unified)
- Should be in output formatter using MatchResult stream
- Normal mode formatting may not use MatchResult contract fully

---

## Implementation Inconsistencies

### Issue 1: InputSource.display_name Semantics

**Current Implementation** (`input_source.py:60-70`):
```python
@property
def display_name(self) -> Optional[str]:
    if self.source_type == 'file':
        return self.file_path
    else:
        # stdin or fd: return label only if explicitly set
        return self._label
```

**Spec Requirement**:
> "Returns an optional string for display purposes in `-H`/`--with-filename` output contexts"
> "`display_name is None` means 'do not show a filename header for this source'"
> "`display_name is not None` means 'show this value as the filename in output headers'"

**Compliance**: ✅ Implementation matches spec

---

### Issue 2: Binary Detection Strategy

**Current Implementation** (`input_source.py:82-98`):
- Reads 8KB peek buffer for stdin/fd ✅
- Caches buffer internally ✅
- Prepends during line reading ✅

**Spec Requirement**:
> "Peek buffer is NOT lost: cached internally and prepended to line iteration"

**Compliance**: ✅ Implementation matches spec

---

## Violations by Module

### cli.py Violations

| Line(s) | Issue | Severity |
|---------|-------|----------|
| 656-815 | Extract/Consolidate direct input loop | CRITICAL |
| 531-535 | Pattern filtering duplicated in extract/consolidate | MAJOR |
| 822-1050 | Consolidate merge logic duplicated | MAJOR |
| 1025+ | Context buffering implementation (needs verification) | MEDIUM |

### grepnet.py Violations

| Line(s) | Issue | Severity |
|---------|-------|----------|
| 545 | search() missing mode parameter | CRITICAL |
| N/A | Missing extract_networks() function | CRITICAL |
| N/A | Missing consolidate_networks() function | CRITICAL |
| 545+ | search() not routing to extract/consolidate helpers | CRITICAL |

### input_source.py Compliance

- ✅ Properly implements InputSource abstraction
- ✅ Correctly implements peek buffer strategy
- ✅ Correctly implements display_name semantics
- ✅ Correctly implements binary detection

---

## Non-Compliance Summary

### Critical (Blocking Streaming Implementation)

1. ❌ Extract/Consolidate bypass unified input path
2. ❌ grepnet.search() missing mode parameter
3. ❌ extract_networks() helper not implemented
4. ❌ consolidate_networks() helper not implemented
5. ❌ Consolidate doesn't use Extract's deduplication

### Major (Violates Spec Principle)

1. ❌ "All Input Is Input" principle violated
2. ❌ Direct input loops in CLI instead of grepnet.search()
3. ❌ Mode-specific logic duplicated instead of unified

### Medium (Implementation Quality)

1. ⚠️ Context buffering needs verification (appears correct, needs review)
2. ⚠️ MatchResult contract completeness needs verification
3. ⚠️ Unified output formatter not implemented

---

## Required Fixes (Priority Order)

### Phase 1: Implement Unified Architecture

1. **Add mode parameter to grepnet.search()**: `mode='normal'|'extract'|'consolidate'`
2. **Create extract_networks() helper** in grepnet.py
3. **Create consolidate_networks() helper** in grepnet.py
4. **Refactor cli.py to use grepnet.search()** for all modes

### Phase 2: Implement Extract/Consolidate Composition

1. Consolidate calls extract_networks()
2. Then consolidate_networks() on extract output
3. Remove duplicate logic from cli.py

### Phase 3: Verify Streaming Compliance

1. Validate context buffering uses only B lines (not entire file)
2. Verify MatchResult contract is complete
3. Test streaming with pipes and large files

---

## Code Locations for Reference

**Key Files**:
- Spec: `/home/chains/dev/grepnet/GREPNET-SPEC.md`
- CLI: `/home/chains/dev/grepnet/src/grepnet/cli.py`
- Core: `/home/chains/dev/grepnet/src/grepnet/grepnet.py`
- Input: `/home/chains/dev/grepnet/src/grepnet/input/input_source.py`

**Extract/Consolidate Implementation**:
- Location: `cli.py:656-1050`
- Status: Blocks streaming implementation
- Impact: High (architectural violation)

**Required Refactor**:
- Move extract logic to `grepnet.py:extract_networks()`
- Move consolidate logic to `grepnet.py:consolidate_networks()`
- Update cli.py to call `grepnet.search(mode='extract'|'consolidate')`

---

## Next Steps

1. ✅ Identify violations (THIS DOCUMENT)
2. ⏳ Create implementation plan for Phase 1
3. ⏳ Implement grepnet.search(mode=...) routing
4. ⏳ Refactor extract/consolidate as helper functions
5. ⏳ Update cli.py to use unified path
6. ⏳ Verify streaming compliance with tests
