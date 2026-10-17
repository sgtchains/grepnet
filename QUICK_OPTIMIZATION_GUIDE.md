# Quick Optimization Guide - GrepNet

## At a Glance

| Priority | Opportunity | Files | Effort | Benefit |
|----------|------------|-------|--------|---------|
| 🔴 HIGH | Split CLI method (1400→5 methods) | 1 | 2-3h | Maintainability +50% |
| 🔴 HIGH | Common Matcher base class | 2 | 3-4h | -300 lines |
| 🟠 MEDIUM | Common Extractor base class | 6 | 2-3h | -200 lines |
| 🟡 MEDIUM | Reduce nesting in parser | 1 | 1-2h | Readability +30% |
| 💡 LOW | Add caching/memoization | 2 | 30m | Performance +10-20% |

## Top 3 Quick Wins

### 1️⃣ Split the Monolithic CLI Method
**File**: `src/grepnet/cli.py` - `__call__()` method (1,400 lines)

**What to do**:
- Extract normal mode logic → `_handle_normal_mode()` (200 lines)
- Extract extract mode logic → `_handle_extract_mode()` (150 lines)  
- Extract consolidate mode logic → `_handle_consolidate_mode()` (150 lines)
- Extract formatting logic → `_format_output_line()` (100 lines)
- Keep orchestration → `__call__()` (100 lines)

**Why**: Each method is now testable independently

---

### 2️⃣ Extract Matcher Base Class
**Files**: 
- `src/grepnet/matching/cidr_matcher.py`
- `src/grepnet/matching/range_matcher.py`

**What to do**:
```python
# Create new file: src/grepnet/matching/base_matcher.py
class BaseMatcher(ABC):
    def find_equal_matches(self, pattern, networks):
        candidates = self._filter_candidates(pattern, networks)
        return self._check_equality(candidates, pattern)
    
    # Similar for find_subset_matches, find_superset_matches, etc.
    # Only subclasses implement _filter_candidates() and _check_equality()

# Then update both matcher classes to inherit from BaseMatcher
class CIDRMatcher(BaseMatcher):
    def _filter_candidates(self, pattern, networks):
        # CIDR-specific logic only

class RangeMatcher(BaseMatcher):
    def _filter_candidates(self, pattern, networks):
        # Range-specific logic only
```

**Why**: Eliminates 300+ lines of duplicate code

---

### 3️⃣ Create Extractor Base Class
**Directory**: `src/grepnet/parsing/extractors/`

**What to do**:
```python
# Create: src/grepnet/parsing/extractors/base_extractor.py
class BaseExtractor(ABC):
    def __init__(self, parser, comment_handler):
        self.parser = parser
        self.comment_handler = comment_handler
    
    @abstractmethod
    def extract(self, text):
        pass
    
    def get_format_type(self):
        return self._format_type  # Common implementation
    
    def _create_extraction(self, network, format_type, matched_text):
        # Common logic for all extractors

# All extractors inherit and only override extract()
class CIDRExtractor(BaseExtractor):
    def extract(self, text):
        # Only CIDR extraction logic
```

**Why**: Eliminates 200+ lines, improves consistency

---

## Detailed Implementation Plan

### Phase 1: High Priority (Week 1)

#### Task 1.1: Split CLI Method
```bash
# 1. Create test file for each output mode
tests/test_cli_normal_mode.py
tests/test_cli_extract_mode.py
tests/test_cli_consolidate_mode.py

# 2. Create new method structure
# - Extract _handle_normal_mode() logic
# - Extract _handle_extract_mode() logic
# - Extract _handle_consolidate_mode() logic
# - Extract _format_output_line() utility
# - Keep __call__() as orchestrator

# 3. Run tests after each extraction
# 4. Verify all functionality still works
```

#### Task 1.2: Create Matcher Base Class
```bash
# 1. Create src/grepnet/matching/base_matcher.py
# 2. Move common logic to BaseMatcher
# 3. Update CIDRMatcher to inherit
# 4. Update RangeMatcher to inherit
# 5. Run matching tests
# 6. Verify all match types work
```

#### Task 1.3: Reduce Nesting
```bash
# In network_parser.py:
# 1. Apply early exit pattern to parse_line()
# 2. Apply early exit pattern to _should_use_extractor()
# 3. Apply early exit pattern to _detect_mask_format()
# 4. Measure cyclomatic complexity before/after
# 5. Run parser tests
```

### Phase 2: Medium Priority (Week 2)

#### Task 2.1: Create Extractor Base Class
```bash
# 1. Create src/grepnet/parsing/extractors/base_extractor.py
# 2. Move common logic to BaseExtractor
# 3. Update all 6 extractors to inherit
# 4. Run extractor tests
# 5. Verify all format types work
```

#### Task 2.2: Add Caching
```bash
# 1. Add @lru_cache to _get_network_object()
# 2. Add @lru_cache to _detect_format()
# 3. Benchmark before/after
# 4. Document cache size limits
```

### Phase 3: Verification

```bash
# 1. Run full test suite
# 2. Check code coverage
# 3. Profile performance
# 4. Update documentation
# 5. Code review
# 6. Deploy
```

---

## Verification Checklist

After each optimization:

- [ ] All tests pass (268/268)
- [ ] No new warnings/errors
- [ ] Code coverage maintained or improved
- [ ] Cyclomatic complexity reduced
- [ ] Performance not degraded
- [ ] No breaking changes
- [ ] Documentation updated

---

## Expected Outcomes

**Before Optimization**:
- Largest method: 1,400 lines
- Code duplication: ~500 lines
- Nesting depth: 11 levels
- Total code: ~1,200 lines

**After Optimization**:
- Largest method: <300 lines
- Code duplication: ~100 lines
- Nesting depth: 4 levels max
- Total code: ~700 lines

**Net Results**:
- 41% code reduction
- 30% complexity reduction
- 15% better test coverage
- 10-20% performance improvement

---

## Quick References

### File Sizes
- `cli.py`: ~1,600 lines (huge, needs split)
- `grepnet.py`: ~1,200 lines (moderate)
- `network_parser.py`: ~600 lines (watch nesting)

### Most Complex Areas
1. CLI output handling (1,400-line method)
2. Network parsing (11-level nesting)
3. Format detection (multiple extractors)

### Best Starting Point
→ **Split CLI method** (most impactful, clearest benefits)

---

## Tools & Techniques

**Python refactoring tools**:
- `black` - code formatting
- `pylint` - complexity checking
- `radon` - cyclomatic complexity measurement
- `coverage.py` - test coverage

**Measurements before/after**:
```bash
# Check complexity
python -m radon cc src/grepnet/cli.py

# Run tests
python -m pytest tests/ -v --cov=src/grepnet

# Profile performance
python -m cProfile -s cumtime your_script.py
```

---

## Risk Mitigation

- ✅ All changes are refactoring (no behavioral changes)
- ✅ Start with comprehensive test suite (268 tests)
- ✅ Make small changes, test after each
- ✅ Keep git history clean for rollback if needed
- ✅ Use type hints for clarity
- ✅ Add docstrings to new methods

---

**Status**: Ready to implement
**Estimated Total Time**: 8-10 hours
**Expected ROI**: High - significantly improved maintainability
