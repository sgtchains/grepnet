# Architecture Refactoring: Filtering at Source (parse_line)

## Executive Summary

This document proposes a **core architectural refactoring** to move all network filtering (pattern matching + exclusion filters) from the output layer into the extraction pipeline. This fixes the bug where `--consolidate --exclude-string` ignores exclusions.

**Root Cause**: Currently, `consolidate_networks()` calls `extract_networks(input_sources)` internally, extracting ALL networks before any filtering. Filters are applied AFTER consolidation, making them ineffective.

**Solution**: Apply all filtering INSIDE `parse_line()`, so `extract_networks()` only ever sees networks that should be included.

---

## Part 0: Spec Inconsistency

**CRITICAL NOTE**: The current GREPNET-SPEC.md has contradictory information:

1. **Line 215-218** (CORRECT pattern):
```python
unique_networks = extract_networks_from_search(input_sources)
consolidated = consolidate_networks(unique_networks)  ← Signature: dict
```

2. **Line 2309** (CONFLICTING pattern):
```python
result = consolidate_networks(input_sources)  ← Signature: input_sources
```

**This refactoring resolves the inconsistency** by implementing the pattern shown at line 215-218:
- `consolidate_networks(networks_dict)` - accepts dict, not input_sources
- Extraction and consolidation are separate steps
- Filtering happens during extraction (parse_line)
- Consolidation happens on pre-filtered data

**Post-Implementation Task**: Update GREPNET-SPEC.md line 2309 to match line 215-218 pattern.

---



### Current (Broken) Flow

```
For --consolidate --exclude-string '0.0.0.0/0':

search(mode='consolidate')
  ↓
consolidate_networks(input_sources)
  ↓
  extract_networks(input_sources)  ← Extracts ALL networks, no filtering!
    ↓
    For each line: parse_line(line) → returns all networks from line
    ↓
    Returns dict with ALL networks matching patterns
  ↓
  Merge networks (overlapping/adjacent)
  ↓
  Return consolidated dict with ALL networks
  ↓
search() returns _apply_extraction_filters(consolidated_dict)  ← Too late!
  ↓
  Filter applied AFTER consolidation already happened
```

**The Problem**: When you exclude `0.0.0.0/0` but input has `192.0.2.0/24\n0.0.0.0/0`, consolidation sees both:
- `0.0.0.0/0` is a superset
- Consolidation merges them into `0.0.0.0/0`
- Then we try to exclude `0.0.0.0/0`
- Result: empty output (wrong!)

Correct behavior: Exclude `0.0.0.0/0` BEFORE consolidation, so consolidation only sees `192.0.2.0/24`.

Per the spec consolidation MUST call extraction to get its list

---

## Part 2: The Solution - Filtering at Source

### Proposed (Fixed) Flow

```
For --consolidate --exclude-string '0.0.0.0/0':

search(mode='consolidate')
  ↓
extract_networks(input_sources)
  ↓
  For each line: parse_line(line)  ← NOW applies filtering!
    ↓
    1. Extract all networks from text
    2. Apply pattern matching (if patterns provided)
    3. Apply exclusion filters (--exclude-string, --exclude-cidr)
    4. Return ONLY networks that passed filters
    ↓
  Deduplicate filtered networks
  ↓
  Return dict with ONLY non-excluded networks
  ↓
consolidate_networks(filtered_dict)  ← Now accepts pre-filtered dict
  ↓
  Merge networks (only non-excluded networks)
  ↓
  Return consolidated dict with ONLY non-excluded networks
  ↓
Output directly (no additional filtering needed)
```

**Why This Works**: Networks matching the exclusion filter (`0.0.0.0/0` matches `--exclude-string '0.0.0.0/0'`) are filtered out in `parse_line()`, never reaching consolidation. Consolidation only sees `192.0.2.0/24`, returns `192.0.2.0/24`.

---

## Part 3: Detailed Changes by Component

### 3.1 NetworkParser (src/grepnet/parsing/network_parser.py)

#### Change 1: Add filter configuration to __init__

**Current**:
```python
def __init__(self,
    filter_comments: bool = True,
    strict_mode: bool = False,
    parse_cidr: str = 'both',
    # ... other parse settings ...
):
```

**Proposed**:
```python
def __init__(self,
    filter_comments: bool = True,
    strict_mode: bool = False,
    parse_cidr: str = 'both',
    # ... other parse settings ...
    # NEW: Filter configuration
    parsed_patterns: Optional[List] = None,
    exclude_strings: Optional[List[str]] = None,
    exclude_cidrs: Optional[List] = None,
    exclude_cidr_behavior: str = 'subset',
    match_type_filter: Optional[Set] = None,
    invert_match: bool = False,
):
    # Store as instance variables
    self.parsed_patterns = parsed_patterns or []
    self.exclude_strings = exclude_strings or []
    self.exclude_cidrs = exclude_cidrs or []
    self.exclude_cidr_behavior = exclude_cidr_behavior
    self.match_type_filter = match_type_filter or set()
    self.invert_match = invert_match
```

#### Change 2: Modify parse_line() to apply filtering

**Current** (returns all extracted networks):
```python
def parse_line(self, line: str, line_number: int = 0, context: str = 'input', 
               mask_format_hint: Optional[str] = None) -> List[ParsedExtraction]:
    # ... extraction logic ...
    return deduped  # Returns ALL networks extracted from line
```

**Proposed** (returns filtered networks):
```python
def parse_line(self, line: str, line_number: int = 0, context: str = 'input', 
               mask_format_hint: Optional[str] = None) -> List[ParsedExtraction]:
    # ... extraction logic ...
    deduped = [...]  # All networks extracted from line
    
    # NEW: Apply filtering before returning
    filtered = []
    for extraction in deduped:
        # 1. Check pattern matching (if patterns provided)
        if self.parsed_patterns:
            match_found = False
            for pattern in self.parsed_patterns:
                match_type = self._find_match_type(extraction, pattern)
                if match_type in self.match_type_filter:
                    match_found = True
                    break
            if self.invert_match:
                match_found = not match_found
            if not match_found:
                continue  # Skip this network
        
        # 2. Check exclusion filters (if provided)
        if self._is_excluded(extraction):
            continue  # Skip this network
        
        # Network passed all filters
        filtered.append(extraction)
    
    return filtered  # Returns ONLY filtered networks
```

#### Change 3: Move exclusion checking logic

Move `_is_excluded()` and `_check_extraction_excluded()` from GrepNet class to NetworkParser so parse_line() can use them.

---

### 3.2 GrepNet.extract_networks() (src/grepnet/grepnet.py)

#### Change: Simplify to only deduplicate

**Current**:
```python
def extract_networks(self, input_sources: List[InputSource]) -> dict:
    networks_dict = {}
    for input_source in input_sources:
        for line_number, line_content, byte_offset in input_source.lines():
            line = line_content.rstrip('\n\r')
            parsed_extractions = self.parser.parse_line(line, context='input', ...)
            
            for parsed_ext in parsed_extractions:
                # Apply pattern filtering
                match_found = False
                for pattern in self.parsed_patterns:
                    match_type = self._find_match_type(parsed_ext, pattern)
                    if match_type in self.match_type_filter:
                        match_found = True
                        break
                if self.invert_match:
                    match_found = not match_found
                if not match_found:
                    continue
                
                # Deduplicate
                dedup_network = parsed_ext.network
                if dedup_network not in networks_dict:
                    networks_dict[dedup_network] = (parsed_ext, line)
    
    return networks_dict
```

**Proposed** (filtering already done by parse_line):
```python
def extract_networks(self, input_sources: List[InputSource]) -> dict:
    networks_dict = {}
    for input_source in input_sources:
        for line_number, line_content, byte_offset in input_source.lines():
            line = line_content.rstrip('\n\r')
            # parse_line() now returns ONLY filtered networks
            parsed_extractions = self.parser.parse_line(line, context='input', ...)
            
            for parsed_ext in parsed_extractions:
                # Just deduplicate (filtering already done in parse_line)
                dedup_network = parsed_ext.network
                if dedup_network not in networks_dict:
                    networks_dict[dedup_network] = (parsed_ext, line)
    
    return networks_dict
```

**Key Simplification**: No pattern matching or exclusion filtering in extract_networks(). It's already done by parse_line().

---

### 3.3 GrepNet.consolidate_networks() (src/grepnet/grepnet.py)

#### Change 1: Signature change - accept dict instead of input_sources

**CRITICAL**: Per spec, `consolidate_networks()` receives the dict result from `extract_networks()`, not input_sources.
The extraction is done separately, then consolidate operates on the extracted/filtered result.

**Current**:
```python
def consolidate_networks(self, input_sources: List[InputSource]) -> dict:
    # Step 1: Extract unique networks
    networks_dict = self.extract_networks(input_sources)  ← Wrong: Re-extracts and re-filters!
    
    if not networks_dict:
        return {}
    
    # Step 2: Convert ranges and consolidate...
```

**Proposed**:
```python
def consolidate_networks(self, networks_dict: dict) -> dict:
    # RECEIVES: Pre-extracted, pre-filtered dict from extract_networks()
    # Does NOT call extract_networks() - that happened in search() already
    # This ensures consolidation happens on filtered networks
    
    if not networks_dict:
        return {}
    
    # Convert ranges and consolidate...
    # Rest of logic stays the same
```

#### Change 2: Update search() method to handle extraction separately

**Current**:
```python
elif mode == 'consolidate':
    consolidated_dict = self.consolidate_networks(input_sources)  ← Wrong signature
    return self._apply_extraction_filters(consolidated_dict)  ← Filters after consolidation (too late!)
```

**Proposed**:
```python
elif mode == 'consolidate':
    # Step 1: Extract and filter (parse_line applies filtering here)
    networks_dict = self.extract_networks(input_sources)
    
    # Step 2: Consolidate the filtered networks (not all networks)
    consolidated_dict = self.consolidate_networks(networks_dict)
    
    # Step 3: Return (no additional filtering needed - already done in parse_line)
    return consolidated_dict
```

---

### 3.4 GrepNet.search() method

#### Change: Update both extract and consolidate modes

**Current**:
```python
def search(self, input_sources, mode='normal'):
    if mode == 'extract':
        networks_dict = self.extract_networks(input_sources)
        return self._apply_extraction_filters(networks_dict)  ← Filters after extract
    elif mode == 'consolidate':
        consolidated_dict = self.consolidate_networks(input_sources)  ← Wrong signature
        return self._apply_extraction_filters(consolidated_dict)  ← Filters after consolidate
```

**Proposed**:
```python
def search(self, input_sources, mode='normal'):
    if mode == 'extract':
        # extract_networks() calls parse_line() which already filters
        networks_dict = self.extract_networks(input_sources)
        return networks_dict  ← No additional filtering needed
    elif mode == 'consolidate':
        # Same: parse_line() does filtering, then consolidate on filtered dict
        networks_dict = self.extract_networks(input_sources)
        consolidated_dict = self.consolidate_networks(networks_dict)
        return consolidated_dict  ← No additional filtering needed
    else:  # mode == 'normal'
        return self._search_generator(input_sources, yield_all_lines)
```

#### Change: Delete _apply_extraction_filters()

This method becomes unnecessary since filtering happens in parse_line().

---

### 3.5 GrepNet initialization

#### Change: Pass filter config to parser

**Current**:
```python
self.parser = NetworkParser(
    filter_comments=self.filter_comments,
    strict_mode=self.strict_cidr_mode == 'both',
    parse_cidr=self.parse_cidr,
    # ... other settings ...
)
```

**Proposed**:
```python
self.parser = NetworkParser(
    filter_comments=self.filter_comments,
    strict_mode=self.strict_cidr_mode == 'both',
    parse_cidr=self.parse_cidr,
    # ... other settings ...
    # NEW: Pass filter config
    parsed_patterns=self.parsed_patterns,
    exclude_strings=self.exclude_strings,
    exclude_cidrs=self.exclude_cidrs,
    exclude_cidr_behavior=self.exclude_cidr_behavior,
    match_type_filter=self.match_type_filter,
    invert_match=self.invert_match,
)
```

---

## Part 4: Impact Analysis

### Files That Change

1. **src/grepnet/parsing/network_parser.py** (Major)
   - Add filter parameters to __init__
   - Modify parse_line() to apply filtering
   - Move/copy exclusion logic from GrepNet

2. **src/grepnet/grepnet.py** (Major)
   - Simplify extract_networks() (remove filtering logic)
   - Change consolidate_networks() signature (accept dict, not input_sources)
   - Simplify search() method (remove _apply_extraction_filters calls)
   - Delete _apply_extraction_filters() method
   - Update parser initialization (pass filter config)
   - Update _search_source() if it uses parse_line() (check context handling)

3. **Tests** (All extract/consolidate tests affected)
   - Update consolidate_networks() calls (pass dict, not input_sources)
   - May need new tests to verify filtering happens in parse_line()

### Backward Compatibility

**Breaking Changes**:
- consolidate_networks() signature changes (internal API, not CLI-facing)
- parse_line() behavior changes (adds filtering)

**Non-Breaking**:
- CLI interface unchanged
- search() behavior unchanged (fixes bug but same external behavior)

### Edge Cases to Consider

1. **No patterns provided** (extract/consolidate mode)
   - parse_line() should match everything (default behavior)
   
2. **No exclusion filters provided**
   - parse_line() should return all extracted networks (default behavior)
   
3. **Both patterns AND exclusions provided**
   - Network must pass BOTH filters (pattern match AND not excluded)
   
4. **invert_match with exclusions**
   - Inversion applies to pattern matching, not exclusions
   - Networks matching exclusions are always filtered out

5. **parse_line() called in normal mode vs extract mode**
   - In normal mode: parse_line() is called, but filtering should also happen here!
   - Normal mode needs to benefit from filtering at source too

---

## Part 5: Migration Strategy

### Phase 1: Parser Updates
1. Add filter parameters to NetworkParser.__init__()
2. Move _is_excluded(), _check_extraction_excluded(), _check_cidr_exclusion() to NetworkParser
3. Move _find_match_type() to NetworkParser (for pattern matching)
4. Implement filtering logic in parse_line()

### Phase 2: GrepNet Updates
1. Update GrepNet.__init__() to pass filter config to parser
2. Simplify extract_networks() (remove pattern/exclusion filtering)
3. Update consolidate_networks() signature and implementation
4. Update search() method
5. Delete _apply_extraction_filters()
6. Update all calls to consolidate_networks() with new signature

### Phase 3: Testing
1. Run existing extract/consolidate tests (update consolidate_networks calls)
2. Run exclude_extract_consolidate tests to verify fix works
3. Run full test suite to verify no regressions
4. Add new tests to verify filtering happens in parse_line()

### Phase 4: Documentation
1. Update GREPNET-SPEC.md with new architecture
2. Update inline code comments
3. Update any README/developer docs

---

## Part 6: Testing Strategy

### Tests That Will Break (Expected)
- Any test calling consolidate_networks(input_sources) directly
- Must change to: extract first, then call consolidate_networks(dict)

### New Tests Needed
1. **parse_line() filtering**
   - Verify exclusions work in parse_line()
   - Verify pattern matching works in parse_line()
   - Verify both together work correctly

2. **extract/consolidate with filters**
   - Existing test suite (should pass after updates)
   - Test that excluded networks never reach consolidate
   - Test that consolidation result respects exclusions

3. **Edge cases**
   - No patterns + has exclusions
   - No exclusions + has patterns
   - Both patterns and exclusions
   - invert_match + exclusions
   - Empty result after filtering

### Regression Tests (Must Pass)
- All CLI tests
- All normal mode search tests
- All extract/consolidate tests (after sig updates)
- All exclusion tests (--exclude-string, --exclude-cidr)
- All pattern matching tests

---

## Part 7: Risk Analysis

### Low Risk
- search() behavior (same external interface, internal restructure)
- extract_networks() simplification (cleaner code, same result)
- Parser initialization (just passing more config)

### Medium Risk
- consolidate_networks() signature change (might miss a caller)
- Filter logic movement to parser (duplication of logic in two places?)

### High Risk
- parse_line() changes (heavily used in multiple contexts)
  - Normal mode: should work (patterns already applied in _search_source)
  - Pattern parsing: should work (no exclusions, but need to verify)
  - Extract mode: MUST work (this is the fix)

---

## Part 8: Success Criteria

### The Bug is Fixed
```bash
printf "0.0.0.0/0\n192.0.2.0/24" | grepnet --exclude-string '0.0.0.0/0' --consolidate
# Expected: 192.0.2.0/24
# Current: (empty)
```

### All Tests Pass
- Existing test suite (with signature updates)
- New tests for parse_line() filtering
- Regression tests for normal mode search

### Architecture is Clean
- No _apply_extraction_filters() method (not needed)
- extract_networks() simple and focused
- consolidate_networks() accepts pre-filtered dict
- All filtering in one place (parse_line)

---

## Appendix: Before/After Code Example

### Before (Broken)

```
Input: "0.0.0.0/0" and "192.0.2.0/24" lines
Exclude: "0.0.0.0/0"
Mode: consolidate

extract_networks():
  Extracts: {0.0.0.0/0, 192.0.2.0/24}
  
consolidate_networks():
  Sees: {0.0.0.0/0, 192.0.2.0/24}
  Consolidates to: {0.0.0.0/0}  ← Superset wins
  
search() applies filter:
  Excludes 0.0.0.0/0
  Result: {}  ← WRONG! No output
```

### After (Fixed)

```
Input: "0.0.0.0/0" and "192.0.2.0/24" lines
Exclude: "0.0.0.0/0"
Mode: consolidate

parse_line() for "0.0.0.0/0":
  Extracts: {0.0.0.0/0}
  Checks exclusion: EXCLUDED
  Returns: {}
  
parse_line() for "192.0.2.0/24":
  Extracts: {192.0.2.0/24}
  Checks exclusion: OK
  Returns: {192.0.2.0/24}

extract_networks():
  Deduplicates: {192.0.2.0/24}
  
consolidate_networks():
  Sees: {192.0.2.0/24}
  Consolidates to: {192.0.2.0/24}
  
Result: 192.0.2.0/24  ← CORRECT!
```

---

## Questions for Review

1. Is the filtering logic correct (pattern matching before/after exclusions)?
2. Are there any other callers of consolidate_networks() that need updating?
3. Should parse_line() filtering also apply in normal mode search?
4. How should context='pattern' handle exclusion filtering?
5. Is duplicating exclusion logic in NetworkParser acceptable or should it stay in GrepNet?

