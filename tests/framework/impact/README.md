# Test Impact Analysis Plugin System

Intelligent test selection based on code changes. Automatically determine which tests need to run when code changes, reducing feedback time and improving CI/CD efficiency.

## Quick Start

### View Impact Analysis

```bash
# Show which tests are affected by staged changes
python3 framework/impact/impact_cli.py --analyze

# Same thing, with confidence scores
python3 framework/impact/impact_cli.py --analyze --show-scores

# For unstaged changes
python3 framework/impact/impact_cli.py --analyze --unstaged
```

### Run Affected Tests Only

```bash
# Run only the affected tests
python3 framework/impact/impact_cli.py --run-affected

# With verbose output
python3 framework/impact/impact_cli.py --run-affected -v
```

### Example Output

```
======================================================================
TEST IMPACT ANALYSIS
======================================================================

5/50 tests affected (10%)
  Changed files: 1
  Changed functions: 2
  Estimated runtime: 20.0s

✓ AFFECTED TESTS:
  • tests/sub-tests/2-output/023_test_color_validation.sh [95%]
  • tests/sub-tests/2-output/027_test_output_features.sh [89%]
  • tests/sub-tests/2-output/004_test_output_control.sh [78%]
  • tests/sub-tests/2-output/005_test_line_prefixes.sh [65%]
  • tests/sub-tests/1-core/002_test_pattern_stdin.sh [42%]

======================================================================
```

## How It Works

### Three-Step Process

1. **Parse Codebase** → Build a call graph showing which functions call which other functions
2. **Detect Changes** → Use `git diff` to identify which functions were modified
3. **Trace Impact** → Follow the call graph to find all functions that depend on changed code, then map to tests

### Test Linking Strategies

Tests are linked to code via three strategies (in priority order):

#### 1. Explicit Dependencies (Highest Confidence)

Add a comment to your test file:

```bash
#!/bin/bash
# @depends: grepnet.core.colorizer
# @depends: grepnet.matching.cidr_matcher

# Test code here...
grepnet --color test.txt
```

#### 2. Filename Inference (Medium Confidence)

Filename convention automatically creates module links:
- `test_colorizer.sh` → links to `grepnet.core.colorizer`, `colorizer`, `grepnet.colorizer`
- `023_test_color_validation.sh` → links to `color_validation`, `color`, etc.

#### 3. Grep Patterns (Lower Confidence)

Scanner looks for function/flag usage in test:
- Test calls `grepnet --color` → links to `grepnet.core.colorizer`
- Test calls `--consolidate` → links to consolidation module

### Architecture

```
ImpactAnalyzer (orchestrator)
├── VcsPlugin (detect changes)
│   ├── GitPlugin (staged/unstaged changes)
│   ├── HgPlugin (Mercurial)
│   ├── P4Plugin (Perforce)
│   ├── FileMtimePlugin (file modification time)
│   └── ManualPlugin (explicit changes)
├── LanguagePlugin (parse code)
│   ├── PythonPlugin (AST analysis)
│   ├── GoPlugin (future)
│   ├── RustPlugin (future)
│   └── TypeScriptPlugin (future)
├── TestLinker (map functions to tests)
└── CallGraph (function dependencies)
```

## VCS Plugins

The framework supports multiple version control systems for change detection:

### Available VCS Plugins

| Plugin | VCS | Use Case | Common Options |
|--------|-----|----------|-----------------|
| **GitPlugin** | Git | Standard CI/CD, local dev | `--cached` (staged), `--unstaged`, `--head~1..head` |
| **HgPlugin** | Mercurial | Companies using Hg | `-r . -r .^` (last changeset) |
| **P4Plugin** | Perforce | Enterprise environments | `-du` (unified diff) |
| **FileMtimePlugin** | File mtime | Local dev, no VCS | Scans files by modification time |
| **ManualPlugin** | Manual | Testing, automation | Explicit list of changed files |

### Using Different VCS Systems

```bash
# Git (default) - staged changes
python3 framework/impact/impact_cli.py --analyze

# Git - unstaged changes
python3 framework/impact/impact_cli.py --analyze --unstaged

# Mercurial
python3 framework/impact/impact_cli.py --analyze --vcs hg

# Perforce
python3 framework/impact/impact_cli.py --analyze --vcs p4

# File modification time (useful for local dev without VCS)
python3 framework/impact/impact_cli.py --analyze --vcs mtime
```

### Python API

```python
from framework.impact import ImpactAnalyzer, ImpactConfig, GitPlugin, ManualPlugin

# Git (staged changes)
config = ImpactConfig(vcs_type='git', vcs_options='--cached')
analyzer = ImpactAnalyzer(config=config)

# Git (unstaged changes)
config = ImpactConfig(vcs_type='git', vcs_options='--unstaged')
analyzer = ImpactAnalyzer(config=config)

# Mercurial
config = ImpactConfig(vcs_type='hg', vcs_options='-r . -r .^')
analyzer = ImpactAnalyzer(config=config)

# Manual plugin (for testing)
manual_vcs = ManualPlugin(changed_files=['src/colorizer.py', 'src/parser.py'])
config = ImpactConfig(vcs_plugin=manual_vcs)
analyzer = ImpactAnalyzer(config=config)

# Custom VCS plugin
class SvnPlugin(VcsPlugin):
    def get_diff(self, options: str = "") -> str:
        import subprocess
        result = subprocess.run(['svn', 'diff'], capture_output=True, text=True)
        return result.stdout
    
    def get_changed_files(self, options: str = "") -> List[str]:
        # Parse svn status output
        pass

custom_vcs = SvnPlugin()
config = ImpactConfig(vcs_plugin=custom_vcs)
analyzer = ImpactAnalyzer(config=config)
```



## Configuration

Create a `.test-impact.yml` file in your project root:

```yaml
impact_analysis:
  enabled: true
  language: python              # Language to analyze
  
  # Change Detection
  change_detection: git-diff    # or "file-mtime"
  git_diff_options: "--cached"  # Staged changes
  
  # Dependency Tracking
  track_transitive: true        # Follow A→B→C chains
  transitive_depth: -1          # -1 = unlimited, 0 = direct only
  
  # Accuracy
  min_confidence: 0.75          # 0.0-1.0 threshold
  
  # Test Linking
  dependency_comment: "@depends"
  infer_from_filename: true
  grep_patterns: true
```

## Python Plugin Deep Dive

The Python plugin uses AST (Abstract Syntax Tree) analysis to parse Python code.

### How Python Plugin Works

```python
# 1. Parse all Python files
for py_file in root_dir:
    tree = ast.parse(py_file)
    
# 2. Extract functions and their calls
class FunctionExtractor(ast.NodeVisitor):
    def visit_FunctionDef(node):
        # Find all calls made by this function
        for call in node.body:
            if isinstance(call, ast.Call):
                record_that_this_func_calls(call.func)

# 3. Build reverse edges (called_by relationships)
for func in functions:
    for callee in func.calls:
        callee.called_by.add(func)

# 4. Detect changes
def extract_changed_functions(git_diff):
    for hunk in parse_diff(git_diff):
        # Parse Python file
        # Find functions that contain changed lines
        return changed_functions

# 5. Trace impact
affected_functions = changed_functions
for func in changed_functions:
    # Find all functions that call this one
    transitive = call_graph.find_transitive_dependents(func)
    affected_functions.update(transitive)
```

### Call Graph Data Structures

```python
@dataclass
class Function:
    qualified_name: str        # "grepnet.core.colorizer.apply_color"
    file_path: str             # "src/grepnet/core/colorizer.py"
    line_number: int           # Line where function defined
    calls: Set[str]            # Functions this calls
    called_by: Set[str]        # Functions that call this

@dataclass
class CallGraph:
    functions: Dict[str, Function]
    
    # Trace which functions depend on this one
    def find_transitive_dependents(name, depth=-1) -> Set[str]
```

## Creating New Language Plugins

To add support for a new language (Go, Rust, TypeScript, etc.):

### 1. Create Plugin Class

```python
# plugins/go_plugin.py
from framework.impact.base import LanguagePlugin, CallGraph, Function

class GoPlugin(LanguagePlugin):
    """Go language support."""
    
    def parse_codebase(self, root_dir: str) -> CallGraph:
        """Parse Go files and build call graph."""
        # TODO: Implement Go AST parsing
        # Use go/parser or golang.org/x/tools
        pass
    
    def extract_changed_functions(self, git_diff: str) -> Set[str]:
        """Extract changed Go functions from diff."""
        # TODO: Parse git diff and identify Go functions
        pass
```

### 2. Implement Language Parsing

For Go, you could:
- Call `go/parser` via subprocess (requires Go installed)
- Use a Python Go parser library (if one exists)
- Parse Go syntax using regex (fragile but simple)

Example for Go:

```python
def parse_codebase(self, root_dir: str) -> CallGraph:
    functions = {}
    
    # Find Go files
    for go_file in glob.glob(f"{root_dir}/**/*.go", recursive=True):
        # Parse using go/parser (via subprocess)
        result = subprocess.run(
            ['go', 'parse', go_file],
            capture_output=True,
            text=True
        )
        
        # Parse JSON output to extract functions and calls
        data = json.loads(result.stdout)
        for func_data in data['functions']:
            func = Function(
                qualified_name=func_data['name'],
                file_path=go_file,
                line_number=func_data['line'],
                calls=set(func_data['calls'])
            )
            functions[func.qualified_name] = func
    
    return CallGraph(functions, 'go', 0.0, root_dir)
```

### 3. Register Plugin in Analyzer

```python
# In framework/impact/analyzer.py
def _load_plugin(self):
    language = self.config.language.lower()
    
    if language == 'python':
        return PythonPlugin()
    elif language == 'go':
        return GoPlugin()
    elif language == 'rust':
        return RustPlugin()
    else:
        raise LanguagePluginError(f"Unsupported language: {language}")
```

### 4. Plugin Testing

Create tests for your plugin:

```bash
# tests/test_go_plugin.py
def test_parse_simple_go_file():
    plugin = GoPlugin()
    graph = plugin.parse_codebase('test_fixtures/go')
    
    assert 'main.main' in graph.functions
    assert 'main.helper' in graph.functions
    assert 'main.helper' in graph.functions['main.main'].calls

def test_extract_changed_functions():
    plugin = GoPlugin()
    diff = open('test_fixtures/go.diff').read()
    
    changed = plugin.extract_changed_functions(diff)
    assert 'main.main' in changed
```

## Plugin Interface Specification

Every language plugin must implement this interface:

```python
class LanguagePlugin(ABC):
    @abstractmethod
    def parse_codebase(self, root_dir: str) -> CallGraph:
        """
        Parse source code and return call graph.
        
        Args:
            root_dir: Root directory with source code
        
        Returns:
            CallGraph with all functions and dependencies
        
        Raises:
            LanguagePluginError: If parsing fails
        """
        pass
    
    @abstractmethod
    def extract_changed_functions(self, git_diff: str) -> Set[str]:
        """
        Extract functions modified in git diff.
        
        Args:
            git_diff: Output from `git diff` (or file path to diff)
        
        Returns:
            Set of qualified function names (e.g., "module.Class.method")
        
        Raises:
            LanguagePluginError: If extraction fails
        """
        pass
    
    def get_language(self) -> str:
        """Return language name (e.g., 'python', 'go')."""
        # Default implementation works for {Language}Plugin class names
        pass
```

## Accuracy & Confidence Scores

### Confidence Scoring

Each affected test gets a confidence score (0.0-1.0):

```
Base = 0.5 + (num_affected_functions × 0.15)

Adjustments:
  + 0.2  if test has explicit @depends comment
  - 0.1  if only filename/grep inference used

Final = clamp(base, 0.0, 1.0)
```

### Min Confidence Threshold

Only tests above `min_confidence` are recommended to run:

```yaml
impact_analysis:
  min_confidence: 0.75  # Skip tests with <75% confidence
```

### Accuracy Considerations

| Scenario | Challenge | Mitigation |
|----------|-----------|-----------|
| Monkey patching | Runtime modifications invisible to AST | Disable for such modules; mark with `# @no-impact` |
| Dynamic imports | `__import__(var)` hard to track | Conservative: link entire module |
| Reflection | Can't trace at analysis time | Confidence < 0.5 |
| External deps | Upstream changes | Use git submodules; manual markers |
| Test ordering | Test B depends on test A | Out of scope; use test isolation |

### False Positives vs False Negatives

**Philosophy**: Accept false positives (run extra tests) over false negatives (miss real failures).

- Running extra tests wastes time but won't miss bugs
- Missing affected tests might let bugs slip through

## Performance

### Caching

Codebase parsing is cached:

```bash
# First run: ~3-5 seconds (parse entire codebase)
python3 framework/impact/impact_cli.py --analyze
# Cached in: .test-cache/callgraph.json

# Second run: <1 second (use cached graph)
python3 framework/impact/impact_cli.py --analyze

# Cache valid for 24 hours by default
# Force rebuild:
rm -rf .test-cache/
```

### Scalability

| Metric | Time | Memory |
|--------|------|--------|
| Parse 50,000 Python functions | 3-5s | 50-100 MB |
| Detect changes | <0.5s | - |
| Trace impact (50k funcs) | <1s | - |
| Link to tests | <1s | - |
| **Total E2E** | **~2s** | **~50-100 MB** |

For 1000+ tests with 50,000+ functions:
- Initial run: 5-10 seconds
- Cached runs: 1-2 seconds
- Cache size: 5-10 MB

## Limitations & Future Work

### Current Limitations

- Python plugin only (other languages planned)
- Local file system only (no remote code analysis)
- No support for "change from uncommitted files" (only git diff)
- Dynamic/reflective code invisible to static analysis

### Future Enhancements

- [ ] Machine learning mode (learn test-to-code patterns)
- [ ] Coverage correlation (combine with coverage data)
- [ ] Parallel test execution (run affected tests in parallel)
- [ ] Web UI (show impact analysis in browser)
- [ ] IDE integration (VSCode extension)
- [ ] Multi-language support (Go, Rust, TypeScript)
- [ ] Trend analysis (which code changes cause test failures?)

## Troubleshooting

### "No tests affected" but I changed code

Check these strategies in order:

1. **Add explicit dependency**:
   ```bash
   # In your test file:
   # @depends: grepnet.core.colorizer
   ```

2. **Check test filename**:
   ```bash
   # Rename to match module pattern
   # test_colorizer.sh for colorizer module
   ```

3. **Verify code was actually changed**:
   ```bash
   git diff --cached
   # or for unstaged:
   python3 framework/impact/impact_cli.py --analyze --unstaged
   ```

4. **Lower confidence threshold**:
   ```bash
   # In .test-impact.yml:
   min_confidence: 0.5
   ```

### "Too many tests selected"

1. **Increase confidence threshold**:
   ```yaml
   min_confidence: 0.90  # Only very confident matches
   ```

2. **Disable filename inference**:
   ```yaml
   infer_from_filename: false
   ```

3. **Use only explicit dependencies**:
   ```yaml
   infer_from_filename: false
   grep_patterns: false
   ```

### Plugin crashes

```bash
# Get detailed error:
python3 framework/impact/impact_cli.py --analyze --verbose

# Check Python syntax:
python3 -m py_compile src/grepnet/*.py
```

## Examples

### Example 1: Bug Fix in Colorizer

```bash
$ git diff --cached
diff --git a/src/grepnet/core/colorizer.py b/src/grepnet/core/colorizer.py
@@ -42,7 +42,7 @@ def apply_color(line):
     # Bug fix: handle ANSI escape codes
-    return line.replace('X', 'Y')
+    return line.replace('X', 'Z')  # Correct!

$ python3 framework/impact/impact_cli.py --analyze
✓ AFFECTED TESTS:
  • tests/sub-tests/2-output/023_test_color_validation.sh [95%]
  • tests/sub-tests/2-output/027_test_output_features.sh [89%]
```

### Example 2: New Feature in Parser

```bash
$ git diff --cached
# Added new function: parse_ipv6_range()

$ python3 framework/impact/impact_cli.py --analyze
✓ AFFECTED TESTS:
  • tests/sub-tests/5-parsing/010_test_ipv6_parsing.sh [82%]
  • tests/sub-tests/1-core/001_test_basic_matching.sh [65%]
```

### Example 3: Refactoring

```bash
$ git diff --cached
# Renamed: validate_ip() → is_valid_ip()
# Modified: 3 functions

$ python3 framework/impact/impact_cli.py --analyze --show-scores
6/50 tests affected (12%)

✓ AFFECTED TESTS:
  • tests/.../012_test_ip_validation.sh [0.95]
  • tests/.../013_test_output_validation.sh [0.78]
  • tests/.../014_test_parsing.sh [0.68]
  [etc...]
```

## Contributing

To improve the impact analysis:

1. **Add test dependencies**:
   ```bash
   # Add @depends comments to tests that don't have them
   grep -l "grepnet" tests/**/*.sh | while read f; do
       if ! grep -q "@depends" "$f"; then
           echo "# @depends: ??? needed in $f"
       fi
   done
   ```

2. **Create new language plugins**:
   - See "Creating New Language Plugins" section above

3. **Improve accuracy**:
   - Track false positives/false negatives
   - Adjust min_confidence threshold
   - Add machine learning feedback

## License

Same as the main project.
