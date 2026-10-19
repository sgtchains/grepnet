# Proposed Spec Changes for Filtering Architecture

## Section 1: The Extraction Pipeline (MODIFIED)

Current text describes extraction without filtering. **PROPOSED CHANGE:**

### Current (in spec):
```
The **extraction pipeline** is a sequence of operations applied to any text (pattern or file line) to:
1. Identify and extract network-like values
2. Filter out false positives
3. Handle comments and special syntax
4. Return a list of ParsedExtraction objects

**Every use of the extraction pipeline follows this sequence**:

1. **Comment Handling**: Strip comments from text
2. **Network Extraction**: Scan searchable content using extraction order
3. **False-Positive Filtering**: Apply semantic validation
4. **Deduplication**: Remove duplicate network objects
5. **Result**: Return list of ParsedExtraction objects
```

### PROPOSED (revised):
```
The **extraction pipeline** is a sequence of operations applied to any text (pattern or file line) to:
1. Identify and extract network-like values
2. Filter out false positives
3. Handle comments and special syntax
4. Apply pattern matching (if patterns provided)
5. Apply exclusion filters (if --exclude-string/--exclude-cidr provided)
6. Return a list of ParsedExtraction objects (may be empty if all filtered out)

**Every use of the extraction pipeline follows this sequence**:

1. **Comment Handling**: Strip comments from text using CommentHandler
2. **Network Extraction**: Scan searchable content using extraction order
3. **False-Positive Filtering**: Apply semantic validation
4. **Deduplication**: Remove duplicate network objects by network value
5. **Pattern Matching** (if patterns provided):
   - Each extracted network is tested against all provided patterns
   - Network must match at least one pattern (unless inverted)
   - Networks that don't match patterns are filtered out
6. **Exclusion Filtering** (if --exclude-string or --exclude-cidr provided):
   - Each network is tested against exclusion filters
   - Networks matching exclusion filters are filtered out
   - Applied AFTER pattern matching so excluded networks are never returned
7. **Result**: Return list of ParsedExtraction objects (only networks passing all filters)

**CRITICAL: All filtering happens INSIDE the extraction pipeline, not after.**
This ensures excluded networks never reach extract_networks() or consolidate_networks().
```

---

## Section 2: extract_networks() - Revised Description

### Current (in spec, around line 200):
```
**Consolidate mode**: Merge overlapping networks (builds on Extract)
- Input: Extract the deduplicated networks from all `MatchResult` objects
- Processing: 
  1. First: Run extract logic to get deduplicated network set (reuse extract's dedup)
  2. Then: Buffer ALL unique networks (cannot consolidate without full set)
  3. Finally: Merge overlapping/adjacent networks into supernets
```

### PROPOSED (revised):
```
**extract_networks(input_sources) Internal Flow**:
1. For each input source, iterate through lines
2. For each line: Call parse_line(line)
   - parse_line() extracts networks from text
   - parse_line() applies pattern matching (if patterns provided)
   - parse_line() applies exclusion filters (--exclude-string, --exclude-cidr)
   - parse_line() returns ONLY networks that passed all filters
3. Deduplicate across all lines (keep first occurrence of each network)
4. Return dict: {network_object → (ParsedExtraction, line_content)}

**CRITICAL: extract_networks() does NOT filter. Filtering happens INSIDE parse_line().**
extract_networks() only deduplicates and passes through the results.
```

---

## Section 3: consolidate_networks() - Signature Change

### Current (in spec, around line 161):
```
# ✅ CORRECT implementation
if args.consolidate:
    # Step 1: Extract unique networks (reuses extract logic)
    unique_networks = extract_networks_from_search(input_sources)
    
    # Step 2: Consolidate (merge) those networks
    consolidated = consolidate_networks(unique_networks)
    
    # Step 3: Output consolidated result
    output_consolidated(consolidated)
```

### PROPOSED (revised):
```
# ✅ CORRECT implementation
if args.consolidate:
    # Step 1: Extract and filter networks
    unique_networks = extract_networks(input_sources)
    # (Note: extract_networks() already applies pattern matching and exclusion filters
    #  via parse_line() - no additional filtering needed here)
    
    # Step 2: Consolidate (merge) those networks
    consolidated = consolidate_networks(unique_networks)
    # (Note: consolidate_networks() accepts pre-filtered dict, not input_sources)
    
    # Step 3: Output consolidated result
    output_consolidated(consolidated)
```

---

## Section 4: Extract and Consolidate Output Modes (CLARIFICATION)

### PROPOSED NEW SECTION:

```
### Filtering Behavior in Extract and Consolidate Modes

**Extract Mode** (`--extract`):
- Extracts all networks from input that match:
  1. Pattern matching (if search patterns provided)
  2. Exclusion filters (--exclude-string, --exclude-cidr)
- Returns unique networks (deduplicated by network value)
- Filtering happens INSIDE parse_line(), before extract_networks() sees them

**Consolidate Mode** (`--consolidate`):
- Extracts all networks from input (same filtering as extract mode)
- Then merges overlapping/adjacent networks into supernets
- Returns consolidated networks
- Filtering happens INSIDE parse_line(), NOT after consolidation
- This ensures excluded networks don't affect consolidation results

**CRITICAL GUARANTEE**:
Excluded networks (via --exclude-string or --exclude-cidr) are completely removed
from the extraction process. They never reach extract_networks() and never affect
consolidation results. This is true whether running in extract mode or consolidate mode.
```

---

## Section 5: Architecture Diagram Update

### Current (around line 50):
```
┌─────────────────────────────────────────────────────────┐
│ Processing Pipeline (within grepnet.search())           │
│ 1. Parse networks from line                             │
│ 2. Match against patterns                               │
│ 3. Generate MatchResult objects                         │
│ 4. Yield MatchResult stream                             │
└─────────────────────────────────────────────────────────┘
```

### PROPOSED (revised):
```
┌─────────────────────────────────────────────────────────┐
│ Processing Pipeline (within grepnet.search())           │
│                                                          │
│ For normal/extract/consolidate modes:                   │
│ 1. parse_line() extracts networks from text             │
│ 2. parse_line() applies pattern matching                │
│ 3. parse_line() applies exclusion filters               │
│ 4. extract_networks() deduplicates filtered results     │
│ 5a. For --extract: output deduped networks             │
│ 5b. For --consolidate: merge overlapping networks      │
│ 5c. For normal: generate MatchResult stream             │
│                                                          │
│ CRITICAL: All filtering in step 2-3 (within parse_line)│
│ Excluded networks never reach extract_networks()        │
└─────────────────────────────────────────────────────────┘
```

---

## Summary of Changes

1. **parse_line()** now documented as applying both pattern matching AND exclusion filters
2. **extract_networks()** now documented as ONLY deduplicating (not filtering)
3. **consolidate_networks()** now documented as accepting pre-filtered dict (not input_sources)
4. **New guarantee section** clarifying that excluded networks are completely removed before extraction
5. **Architecture diagram** updated to show filtering happening inside parse_line()

These changes reflect that **all filtering happens at the extraction source level (parse_line), not at output level**.
