"""Test linker that maps code functions to tests."""

import os
import re
from typing import Set, List, Optional
from pathlib import Path


class TestLinker:
    """Maps code dependencies to tests using multiple strategies."""
    
    def __init__(self, root_dir: str = '.'):
        self.root_dir = root_dir
    
    def find_all_tests(self, root_dir: str) -> List[str]:
        """Find all test files in directory tree."""
        test_files = []
        test_patterns = [
            '**/test_*.sh',
            '**/*_test.sh',
            '**/tests/*.sh',
            '**/test-*.sh',
        ]
        
        # Common test directories
        test_dirs = [
            'tests/sub-tests',
            'tests',
            't',
            'spec',
        ]
        
        for test_dir in test_dirs:
            full_path = os.path.join(root_dir, test_dir)
            if os.path.isdir(full_path):
                for dirpath, dirnames, filenames in os.walk(full_path):
                    for filename in filenames:
                        if filename.endswith('.sh'):
                            full_file = os.path.join(dirpath, filename)
                            test_files.append(full_file)
        
        return sorted(test_files)
    
    def extract_dependencies(self, test_file: str) -> Set[str]:
        """
        Extract code dependencies from a test file.
        
        Supports three strategies:
        1. Explicit: # @depends: module.function
        2. Filename: test_colorizer.sh → colorizer module
        3. Grep: Scan test for function calls
        """
        dependencies = set()
        
        try:
            with open(test_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Strategy 1: Explicit dependency comments
            dependencies.update(self._extract_explicit_dependencies(content))
            
            # Strategy 2: Filename-based inference
            dependencies.update(self._infer_from_filename(test_file))
            
            # Strategy 3: Grep patterns (if no explicit deps found)
            if not dependencies:
                dependencies.update(self._extract_grep_patterns(content))
        
        except Exception as e:
            print(f"Warning: Could not extract dependencies from {test_file}: {e}")
        
        return dependencies
    
    def has_explicit_dependency(self, test_file: str) -> bool:
        """Check if test has explicit dependency comments."""
        try:
            with open(test_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            return '@depends' in content
        except:
            return False
    
    def _extract_explicit_dependencies(self, content: str) -> Set[str]:
        """Extract explicit @depends comments."""
        dependencies = set()
        
        # Pattern: # @depends: module.function or // @depends: module.function
        pattern = r'(?:#|//)\s*@depends:\s*(\S+)'
        matches = re.findall(pattern, content)
        
        for match in matches:
            dependencies.add(match.strip())
        
        return dependencies
    
    def _infer_from_filename(self, test_file: str) -> Set[str]:
        """Infer module dependencies from test filename."""
        dependencies = set()
        
        # Extract base name without extension
        filename = os.path.basename(test_file)
        base_name = os.path.splitext(filename)[0]
        
        # Remove test prefixes: test_colorizer.sh → colorizer
        base_name = re.sub(r'^test[_-]', '', base_name)
        base_name = re.sub(r'_test$', '', base_name)
        base_name = re.sub(r'-test$', '', base_name)
        
        # Common module patterns
        if base_name:
            # Full module name
            dependencies.add(base_name)
            
            # Try with grepnet prefix (for grepnet tests)
            dependencies.add(f"grepnet.{base_name}")
            dependencies.add(f"grepnet.core.{base_name}")
            dependencies.add(f"grepnet.matching.{base_name}")
            dependencies.add(f"grepnet.parsing.{base_name}")
            dependencies.add(f"grepnet.input.{base_name}")
        
        return dependencies
    
    def _extract_grep_patterns(self, content: str) -> Set[str]:
        """
        Extract dependencies from grep patterns in test file.
        
        Looks for grepnet command invocations and extracts flags/patterns.
        """
        dependencies = set()
        
        # Look for grepnet invocations
        grepnet_pattern = r'grepnet\s+([^|>]*?)(?:\||>|$)'
        matches = re.findall(grepnet_pattern, content)
        
        for match in matches:
            # Extract flags that indicate specific modules
            if '--color' in match:
                dependencies.add('grepnet.core.colorizer')
            if '--extract' in match:
                dependencies.add('grepnet.core.extractor')
            if '--consolidate' in match or '--merge' in match:
                dependencies.add('grepnet.core.consolidator')
            if '--invert' in match:
                dependencies.add('grepnet.core.filter')
            if '--parse' in match:
                dependencies.add('grepnet.parsing.network_parser')
        
        # Generic grepnet dependency
        if matches:
            dependencies.add('grepnet.grepnet')
        
        return dependencies


class TestLinkerConfig:
    """Configuration for test linker strategies."""
    
    def __init__(
        self,
        enable_explicit: bool = True,
        enable_filename: bool = True,
        enable_grep: bool = True,
        dependency_comment: str = '@depends',
        test_dir_patterns: Optional[List[str]] = None,
    ):
        self.enable_explicit = enable_explicit
        self.enable_filename = enable_filename
        self.enable_grep = enable_grep
        self.dependency_comment = dependency_comment
        self.test_dir_patterns = test_dir_patterns or [
            'tests/sub-tests',
            'tests',
            't',
            'spec',
        ]
