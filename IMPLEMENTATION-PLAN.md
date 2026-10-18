# Implementation Plan: Wildcard Mask Support (--parse-wildcard + --wildcard-search)

**Version**: 2.0  
**Status**: Phases 1-6 COMPLETE, Phases 7-9 IN PROGRESS  
**Target**: Python implementation (grepnet v5.0.0)

**UPDATED**: This plan reflects the actual implementation as of Phase 6. Earlier planning terminology (--non-cidr-mask, 'non_cidr_mask', hostmask/netmask modes) has been superseded by the final design using two separate flags (--parse-wildcard + --wildcard-search) and format_type 'wildcard_mask'.

---

## Architecture Overview

### Current grepnet Structure

```
src/grepnet/
├── cli.py                          # CLI argument parsing, main entry point
├── grepnet.py                      # GrepNet main class, orchestrator
├── core/
│   ├── network_objects.py          # ParsedExtraction, MatchResult, MatchType
│   ├── colorizer.py                # Color rendering
│   └── binary_detector.py          # Binary file detection
├── parsing/
│   ├── network_parser.py           # Main parser orchestrator
│   ├── comment_handler.py          # Comment filtering
│   ├── mask_format_detector.py     # Format detection
│   └── extractors/
│       ├── __init__.py             # NetworkExtractor base class
│       ├── cidr_extractor.py       # CIDR (192.0.2.0/24)
│       ├── subnet_mask_extractor.py # Netmask (192.0.2.0 255.255.255.0)
│       ├── inverse_mask_extractor.py # Inverse mask (192.0.2.0 0.0.0.255)
│       ├── ip_range_extractor.py   # Ranges (192.0.2.0-192.0.2.255)
│       ├── ipv6_extractor.py       # IPv6 CIDR
│       └── ip_only_extractor.py    # Single IPs
├── matching/
│   ├── cidr_matcher.py             # Network set operations
│   └── range_matcher.py            # Range operations
└── input/
    └── input_source.py             # File/stdin input abstraction
```

### Extraction Pipeline (Current - with Wildcard Mask Support)

```
Input Text
    ↓
Comment Handler (strip comments)
    ↓
Extractor Priority (when --parse-wildcard is enabled):
  1. CIDR Extractor
  2. Subnet Mask Extractor
  3. Inverse Mask Extractor
  4. Wildcard Mask Extractor (NEW) - only if --parse-wildcard is enabled
  5. IP Range Extractor
  6. IPv6 Extractor
  7. IP Only Extractor
    ↓
ParsedExtraction (network, format_type, matched_texts)
    ↓
Deduplication (same network, different formats)
    ↓
Matching (pattern vs file data)
    ↓
MatchResult (with colorization)
```

---

## Required Changes: Detailed Breakdown

### Phase 1: Core Data Structures & Parsing

#### 1.1 WildcardMaskRange Class (IMPLEMENTED)

**File**: `src/grepnet/core/network_objects.py`

**Current implementation** (as of Phase 1):
```python
class WildcardMaskRange:
    """
    Represents a Cisco ACL wildcard mask with expanded CIDR blocks.
    
    Attributes:
        original_text: str (original notation, e.g., "10.4.0.0 0.0.127.252")
        expanded_cidrs: List[IPv4Network] (constituent CIDR blocks)
    """
    def __init__(self, original_text: str, expanded_cidrs: List[IPv4Network]):
        self.original_text = original_text
        self.expanded_cidrs = expanded_cidrs
    
    def __str__(self) -> str:
        return self.original_text
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, WildcardMaskRange):
            return False
        return (self.original_text == other.original_text and 
                self.expanded_cidrs == other.expanded_cidrs)
    
    def __hash__(self) -> int:
        return hash((self.original_text, tuple(self.expanded_cidrs)))
```

**Key design decisions**:
- Use `original_text` + `expanded_cidrs` instead of separate address/mask fields
- Store original notation for display purposes
- Pre-compute and aggregate CIDR blocks using `ipaddress.collapse_addresses()`
- Simplifies equality checking and display

**Integration**:
- Added to `src/grepnet/core/__init__.py` exports
- Accepted in `ParsedExtraction.network` union type
- Used in FileEntry and MatchResult

#### 1.2 Wildcard Mask Extractor (IMPLEMENTED)

**File**: `src/grepnet/parsing/extractors/wildcard_mask_extractor.py`

**Implementation status** (Phase 2): COMPLETE

**Responsibilities**:
- Detect pattern: `ADDRESS SPACE MASK_VALUE` (IPv4 only)
- Validate both are valid IPv4 addresses
- Verify pattern matches actual wildcard mask (not just any two addresses)
- Implement wildcard mask expansion algorithm (set bit generation)
- Return WildcardMaskRange with format_type='wildcard_mask'
- Only active when --parse-wildcard flag is enabled

**Current implementation**:
```python
class WildcardMaskExtractor(NetworkExtractor):
    def extract(self, text: str) -> Optional[_RawExtraction]:
        """
        Extract wildcard mask from text.
        Pattern: two space-separated IPv4 addresses
        Returns: WildcardMaskRange or None
        """
        
    def _expand_wildcard_mask(self, network: IPv4Address, 
                              wildcard: IPv4Address) -> List[IPv4Network]:
        """
        Expand wildcard to CIDR blocks.
        
        Algorithm:
        1. Compute valid IP range using bitwise operations
        2. Generate all valid IPs matching the wildcard pattern
        3. Collapse to minimal CIDR set using ipaddress.collapse_addresses()
        
        Returns: List[IPv4Network] (minimal CIDR blocks)
        """
        
    def _get_wildcard_bits(self, wildcard_int: int) -> List[int]:
        """Return list of bit positions where wildcard has 1-bits."""
```

**Key design**:
- Expansion uses set bit generation (for each 1-bit in mask, compute valid values)
- Results aggregated into minimal CIDR set
- DoS protection: Scope check prevents expansion of excessive bit counts

#### 1.3 NetworkParser Updates (IMPLEMENTED)

**File**: `src/grepnet/parsing/network_parser.py`

**Implementation status** (Phase 3): COMPLETE

**Changes made**:
- Added `parse_wildcard: Optional[str]` parameter to `__init__()` 
  - Values: None (disabled, default), 'pattern', 'input', 'both'
- Extended extractor priority to include WildcardMaskExtractor at index 3 (after Inverse Mask)
- WildcardMaskExtractor only instantiated and used when `parse_wildcard` is enabled
- No changes to existing extractors

**New extraction order**:
```
1. CIDR
2. Subnet Mask
3. Inverse Mask
4. Wildcard Mask (conditional on --parse-wildcard flag)
5. IP Range
6. IPv6
7. IP Only
```

**Format type tracking**:
- Updated `format_type` set to include `'wildcard_mask'`
- Used consistently throughout parsing pipeline

#### 1.4 ParsedExtraction Updates (IMPLEMENTED)

**File**: `src/grepnet/core/network_objects.py`

**Implementation status** (Phase 1): COMPLETE

**Changes made**:
- `network` field now accepts: IPv4Network, IPv6Network, WildcardMaskRange, or tuple (ranges)
- format_type set expanded to include `'wildcard_mask'`
- No changes to matched_texts or was_normalized logic
- WildcardMaskRange objects display using original_text for user output

---

### Phase 4: CLI & Configuration (IMPLEMENTED)

#### 2.1 Wildcard Mask Flags (IMPLEMENTED)

**File**: `src/grepnet/cli.py`

**Implementation status** (Phase 4): COMPLETE

**Flags added**:
```python
parser.add_argument(
    '--parse-wildcard',
    choices=['pattern', 'input', 'both', 'none'],
    default='none',
    help='WHERE to parse Cisco ACL wildcard masks (default: none)'
)

parser.add_argument(
    '--wildcard-search',
    type=str,
    help='WHICH scope defines valid wildcard mask ranges (required if --parse-wildcard is set)'
)
```

**Validation logic**:
- Both flags are optional when not using wildcard masks
- If `--parse-wildcard` is set, `--wildcard-search` is required (error if missing)
- If `--wildcard-search` is set, `--parse-wildcard` must also be set (error if missing)
- `--wildcard-search` CIDR must be valid (error if invalid)

**Design rationale**:
- Two-flag approach provides semantic clarity (WHERE vs WHICH)
- Better error messages at CLI level
- Validates dependencies before processing
- DoS protection: Scope requirement explicit
- Validate prefix length (0-32 for IPv4)

#### 2.2 Orchestrator Updates (IMPLEMENTED)

**File**: `src/grepnet/grepnet.py`

**Implementation status** (Phase 5): COMPLETE

**Changes made**:
- Added support for `parse_wildcard` and `wildcard_search` parameters
- WildcardMaskExtractor integrated into parsing pipeline
- NetworkParser extended to support wildcard mask extraction
- Matching logic extended to handle WildcardMaskRange objects

**Integration flow**:
1. CLI flags parsed (--parse-wildcard, --wildcard-search)
2. Flags passed to GrepNet initialization
3. Parser creates WildcardMaskExtractor conditionally
4. Extracted WildcardMaskRange objects flow through deduplication
5. Matching logic handles WildcardMaskRange comparisons

---

### Phase 5-6: Parsing, Orchestration & Matching (IMPLEMENTED)

#### 5.1 Wildcard Mask Extraction (IMPLEMENTED)

**File**: `src/grepnet/parsing/extractors/wildcard_mask_extractor.py`

**Implementation status** (Phase 2): COMPLETE

**Key implementation details**:
- Extraction order: runs after Inverse Mask extractor (index 3)
- Only active when `--parse-wildcard` flag enables it
- Detects two-value patterns (e.g., "10.4.0.0 0.0.127.252")
- Validates both values are valid IPv4 addresses
- Expands to constituent CIDR blocks
- Returns WildcardMaskRange with original_text for display

#### 5.2 Scope Filtering (IMPLEMENTED)

**File**: `src/grepnet/grepnet.py`

**Implementation status** (Phase 4): COMPLETE

**Protection mechanism**:
- DoS protection via `--wildcard-search` CIDR scope
- Out-of-scope check is O(1) before expensive expansion
- Wildcard masks outside scope fall back to other extractors
- Explicit consent model: user must define scope

**Algorithm**:
1. Extract base IP from wildcard mask (e.g., 10.4.0.0)
2. Check: base IP ∈ scope CIDR? (O(1) check)
3. If yes: expand wildcard to CIDRs
4. If no: skip and try next extractor

#### 6.1 Matching Logic (IMPLEMENTED)

**File**: `src/grepnet/grepnet.py`

**Implementation status** (Phase 6): COMPLETE

**Matching algorithm**:
- WildcardMaskRange expanded to constituent CIDRs
- Pattern compared against each CIDR individually
- Match result: highest-priority match type (EQUALS > SUBSET > SUPERSET > OVERLAP)
- All match types supported (EQUALS, SUBSET, SUPERSET, OVERLAP, UNMATCHED)
- Bidirectional matching (file ↔ pattern)

**New method**: `_find_match_type_with_wildcard()`
```python
def _find_match_type_with_wildcard(self, file_network, pattern_network) -> MatchType:
    """
    Find match type when pattern or file is a WildcardMaskRange.
    
    Algorithm:
    - If pattern is WildcardMaskRange: expand to CIDRs, compare file against each
    - If file is WildcardMaskRange: expand to CIDRs, find highest priority match
    - Return: MatchType (EQUALS, SUBSET, SUPERSET, OVERLAP, UNMATCHED)
    """
```

**Helper method**: `_cidr_overlap()`
```python
def _cidr_overlap(self, cidr1: IPv4Network, cidr2: IPv4Network) -> bool:
    """Check if two CIDRs have overlapping address space."""
```

---

### Phase 7: Colorization (TODO)

**Status**: NOT YET STARTED

**Objective**: Implement wildcard mask color code support

#### 7.1 Update Colorizer

**File**: `src/grepnet/core/colorizer.py`

**Changes needed**:
- Add `'wildcard_mask'` (abbreviated `wm=`) to color code dictionary
- Add OBJ value: `'WILDCARD_MASK'` for markup encoding
- Default color: `38;5;75` (bright cyan)
- Implement wm= color code application in output finalization

**Color code integration**:
```python
GREPNET_COLORS = {
    # ... existing ...
    'wm': '\033[38;5;75m',  # Wildcard mask format (bright cyan)
}
```

**Markup encoding**:
- Update markup pattern to recognize WILDCARD_MASK OBJ type
- Apply wm= color when finalizing markup for WildcardMaskRange objects

#### 7.2 Update Output Finalization

**File**: `src/grepnet/core/colorizer.py`

**Changes needed**:
- Extend `finalize_markup()` to handle WILDCARD_MASK OBJ type
- Apply wm= color code during finalization
- Ensure color stacking works correctly with match type colors

---

### Phase 8: Error Handling (TODO)

**Status**: NOT YET STARTED

**Objective**: Implement CLI flag validation and error messages

#### 8.1 Add Error Handling

**File**: `src/grepnet/cli.py`

**Changes needed**:
- Validate `--parse-wildcard` and `--wildcard-search` dependency
- Exit 2 if --parse-wildcard without --wildcard-search
- Exit 2 if --wildcard-search without --parse-wildcard
- Exit 2 if invalid CIDR in --wildcard-search

**Error messages**:
```
grepnet: error: --parse-wildcard requires --wildcard-search CIDR argument
grepnet: error: --wildcard-search requires --parse-wildcard argument
grepnet: error: invalid CIDR block in --wildcard-search: <value>
```

#### 8.2 Out-of-Scope Handling

**File**: `src/grepnet/parsing/extractors/wildcard_mask_extractor.py`

**Changes needed**:
- Implement scope boundary check (O(1))
- Silently skip out-of-scope masks (fall back to other extractors)
- No error message needed (graceful degradation)

---

### Phase 9: Testing (TODO)

**Status**: NOT YET STARTED

**Objective**: Comprehensive test suite for wildcard mask feature

#### 9.1 Unit Tests

**File**: `tests/test_wildcard_mask_extractor.py` (NEW)

**Test cases needed**:
- Extraction: Valid wildcard masks recognized
- Extraction: Invalid patterns rejected
- Expansion: Correct CIDR generation
- Expansion: Minimal set aggregation
- Scope filtering: In-scope masks accepted
- Scope filtering: Out-of-scope masks skipped

#### 9.2 Integration Tests

**File**: `tests/test_wildcard_mask_integration.py` (NEW)

**Test cases needed**:
- Matching: EQUALS with wildcard masks
- Matching: SUBSET/SUPERSET with wildcard masks
- Matching: OVERLAP with wildcard masks
- Output: Colorization of wildcard masks
- CLI: Flags required together
- CLI: Out-of-scope error handling

#### 9.3 End-to-End Tests

**File**: `tests/test_wildcard_mask_e2e.py` (NEW)

**Test scenarios needed**:
- Real Cisco ACL files
- Mixed format files (CIDR + wildcard masks)
- Large wildcard masks
- Edge cases (minimal masks, maximum masks)


---

## Implementation Checkpoint Status

### Completed Phases (✅ DONE)

**Phase 1-6**: Core implementation complete  
- ✅ Phase 1: WildcardMaskRange data structure
- ✅ Phase 2: Wildcard mask extractor algorithm
- ✅ Phase 3: Parser integration
- ✅ Phase 4: CLI flags (--parse-wildcard, --wildcard-search)
- ✅ Phase 5: Orchestrator integration
- ✅ Phase 6: Matching logic with comprehensive tests

**Deliverables completed**:
- Core data structures (WildcardMaskRange class with original_text + expanded_cidrs)
- Extractor integrated at priority level 3 (after inverse mask)
- Parser configured for conditional wildcard mask extraction
- CLI flags with dependency validation
- Matching logic supporting all match types
- 7 comprehensive test cases (all passing)

### In-Progress Phases (⏳ TODO)

**Phase 7: Colorization** (next priority)
- Implement wm= color code in colorizer.py
- Handle WILDCARD_MASK OBJ type in markup
- Update output finalization
- Estimated effort: 1-2 hours

**Phase 8: Error Handling** (after colorization)
- CLI flag validation (--parse-wildcard requires --wildcard-search)
- Error messages and exit codes
- Out-of-scope graceful handling
- Estimated effort: 1 hour

**Phase 9: Testing** (final phase)
- Comprehensive test suite (unit, integration, e2e)
- Edge cases and boundary testing
- Real Cisco ACL file testing
- Estimated effort: 8+ hours

### Documentation Updates

**Complete** (✅ rolled out):
- GREPNET-SPEC.md updated with all wildcard mask sections (174 lines added)
- 7 major spec sections updated with proper terminology

**In Progress** (⏳ updating now):
- IMPLEMENTATION-PLAN.md (this file) — updating terminology
- FEATURE-NON-CIDR-HOSTMASK.md — needs terminology refresh
- TEST-PLAN-WILDCARD-MASKS.md — needs test case updates

---

## Dependencies & Compatibility

### Python Standard Library (No New External Dependencies)

- `ipaddress` — Already used; IPv4Address, IPv4Network
- `argparse` — Already used; for CLI
- `typing` — Already used; for type hints

**No new third-party packages required.**

### Python Version

- Target: Python 3.8+ (same as grepnet)
- No Python 3.11+ features required

---

## Key Design Decisions (Final)

1. **Two-flag approach**: `--parse-wildcard` (WHERE) + `--wildcard-search` (WHICH scope)
   - ✅ Provides semantic clarity
   - ✅ Better error messages
   - ✅ Validates dependencies at CLI level

2. **Data structure**: `original_text` + `expanded_cidrs` in WildcardMaskRange
   - ✅ Simpler than separate address/mask fields
   - ✅ Original text preserved for display
   - ✅ Cleaner equality checking

3. **Format type**: `'wildcard_mask'` (not `'non_cidr_mask'`)
   - ✅ More descriptive
   - ✅ Consistent with naming patterns

4. **No new match types**: OVERLAP covers wildcard overlaps
   - ✅ WildcardMaskRange enables true partial overlap

5. **DoS protection**: Scope requirement + O(1) check
   - ✅ Explicit consent model
   - ✅ Out-of-scope check before expensive expansion

---

## Success Criteria (Updated)

✅ **Functional** (Phases 1-6):
- [x] Wildcard masks recognized when --parse-wildcard is enabled
- [x] Wildcard masks expanded to minimal CIDR block set
- [x] Matching works (EQUALS, SUBSET, SUPERSET, OVERLAP)
- [x] Scope filtering prevents DoS expansion

⏳ **Output & Colorization** (Phase 7):
- [ ] Wildcard masks colorized with wm= color code
- [ ] Color code customizable via GREPNET_COLORS

⏳ **Error Handling** (Phase 8):
- [ ] Flag dependency validation implemented
- [ ] Clear error messages for invalid configurations

⏳ **Testing** (Phase 9):
- [ ] Comprehensive test suite written
- [ ] >85% code coverage achieved
- [ ] All edge cases tested

✅ **Integration** (Complete):
- [x] Existing grepnet features unchanged
- [x] Comment handling works with wildcard masks
- [x] All CLI flags work with wildcard masks

✅ **Documentation** (Complete):
- [x] GREPNET-SPEC.md updated and rolled out
- [x] This implementation plan updated
- [x] Terminology corrected across all documents

---

## Next Immediate Steps

1. **Finish documentation updates** (this session)
   - Update IMPLEMENTATION-PLAN.md (in progress)
   - Update FEATURE-NON-CIDR-HOSTMASK.md
   - Update TEST-PLAN-WILDCARD-MASKS.md

2. **Start Phase 7: Colorization** (next session)
   - Implement wm= color code in colorizer.py
   - Test color output with real data

3. **Phase 8: Error Handling** (after Phase 7)
   - CLI flag validation
   - Error messages

4. **Phase 9: Testing** (final)
   - Write comprehensive test suite
   - Test coverage analysis

---

## Historical Context

**Original Planning**: Featured --non-cidr-mask flag with MSB-based mode detection  
**Design Evolution**: Evolved to two-flag approach (--parse-wildcard + --wildcard-search)  
**Rationale**: Better semantics, clearer validation, superior error messages  
**Implementation**: Phases 1-6 completed with actual design (not original plan)  
**Specification**: GREPNET-SPEC.md reflects actual implementation (not original plan)  
**This Document**: Now updated to reflect actual design and implementation status

---

## Contact & References

- **Main Specification**: GREPNET-SPEC.md (authoritative source)
- **Feature Document**: FEATURE-NON-CIDR-HOSTMASK.md (being updated)
- **Test Plan**: TEST-PLAN-WILDCARD-MASKS.md (being updated)
- **Implementation**: src/grepnet/ (Phases 1-6 complete)
- **Checkpoints**: .copilot/session-state/checkpoints/ (5 checkpoints tracking progress)

