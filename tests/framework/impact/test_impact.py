#!/usr/bin/env python3
"""
Test suite for impact analysis framework.

This demonstrates:
1. How to parse a codebase
2. How to detect changes
3. How to find affected tests
"""

import unittest
import tempfile
import os
import sys
from pathlib import Path

# Add tests directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from framework.impact import (
    ImpactAnalyzer, ImpactConfig,
    CallGraph, Function
)
from framework.impact.python_plugin import PythonPlugin


class TestPythonPlugin(unittest.TestCase):
    """Test Python plugin AST parsing."""
    
    def setUp(self):
        self.plugin = PythonPlugin()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def create_python_file(self, name: str, content: str):
        """Helper to create a Python file."""
        file_path = os.path.join(self.temp_dir, name)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as f:
            f.write(content)
        return file_path
    
    def test_parse_simple_function(self):
        """Test parsing a simple function."""
        self.create_python_file('colorizer.py', '''
def apply_color(line):
    """Apply color to line."""
    return f"\\033[32m{line}\\033[0m"
''')
        
        graph = self.plugin.parse_codebase(self.temp_dir)
        
        self.assertIn('colorizer.apply_color', graph.functions)
        self.assertEqual(graph.language, 'python')
    
    def test_parse_function_calls(self):
        """Test that function calls are tracked."""
        self.create_python_file('helpers.py', '''
def format_output(line):
    return line.strip()

def process_line(line):
    return format_output(line)
''')
        
        graph = self.plugin.parse_codebase(self.temp_dir)
        
        # process_line should call format_output
        process_func = graph.functions['helpers.process_line']
        self.assertIn('helpers.format_output', process_func.calls)
        
        # format_output should be called by process_line
        format_func = graph.functions['helpers.format_output']
        self.assertIn('helpers.process_line', format_func.called_by)
    
    def test_parse_module_structure(self):
        """Test that module names are correct."""
        self.create_python_file('src/grepnet/core/colorizer.py', '''
def apply_color(line):
    pass
''')
        
        graph = self.plugin.parse_codebase(self.temp_dir)
        
        # Should convert path to qualified name
        self.assertIn('grepnet.core.colorizer.apply_color', graph.functions)
    
    def test_find_transitive_dependents(self):
        """Test tracing dependencies up the call chain."""
        self.create_python_file('chain.py', '''
def a():
    pass

def b():
    return a()

def c():
    return b()

def d():
    return c()
''')
        
        graph = self.plugin.parse_codebase(self.temp_dir)
        
        # c depends on b depends on a
        # So if a changes, c and d (transitively) are affected
        dependents = graph.find_transitive_dependents('chain.a')
        
        self.assertIn('chain.b', dependents)
        self.assertIn('chain.c', dependents)
        self.assertIn('chain.d', dependents)
    
    def test_extract_changed_functions(self):
        """Test extracting changed functions from diff."""
        diff = """diff --git a/colorizer.py b/colorizer.py
index abc123..def456 100644
--- a/colorizer.py
+++ b/colorizer.py
@@ -1,4 +1,4 @@ def apply_color(line):
 
 def apply_color(line):
-    return line.replace('X', 'Y')
+    return line.replace('X', 'Z')
"""
        
        # Create the file so the plugin can parse it
        self.create_python_file('colorizer.py', '''
def apply_color(line):
    return line.replace('X', 'Y')
''')
        
        changed = self.plugin.extract_changed_functions(diff, root_dir=self.temp_dir)
        
        # Should detect that apply_color was changed
        self.assertIn('colorizer.apply_color', changed)


class TestCallGraph(unittest.TestCase):
    """Test call graph operations."""
    
    def setUp(self):
        # Create a simple call graph for testing
        self.functions = {
            'a': Function('a', 'test.py', 1, calls={'b'}),
            'b': Function('b', 'test.py', 5, calls={'c'}),
            'c': Function('c', 'test.py', 10, calls=set()),
        }
        
        # Build reverse edges
        for func in self.functions.values():
            for callee in func.calls:
                if callee in self.functions:
                    self.functions[callee].called_by.add(func.qualified_name)
        
        self.graph = CallGraph(
            functions=self.functions,
            language='test',
            build_time=0.0,
            root_dir='.'
        )
    
    def test_find_transitive_dependents(self):
        """Test finding all functions that depend on a function."""
        # c is called by b, which is called by a
        dependents = self.graph.find_transitive_dependents('c')
        
        self.assertIn('b', dependents)
        self.assertIn('a', dependents)
    
    def test_find_transitive_dependencies(self):
        """Test finding all functions that a function depends on."""
        # a depends on b which depends on c
        dependencies = self.graph.find_transitive_dependencies('a')
        
        self.assertIn('b', dependencies)
        self.assertIn('c', dependencies)


class TestImpactAnalyzer(unittest.TestCase):
    """Test the impact analyzer."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def create_test_environment(self):
        """Create a simple project structure."""
        # Source code
        os.makedirs(f'{self.temp_dir}/src', exist_ok=True)
        with open(f'{self.temp_dir}/src/colorizer.py', 'w') as f:
            f.write('''
def apply_color(line):
    return f"\\033[32m{line}\\033[0m"

def strip_ansi(line):
    import re
    return re.sub(r'\\033\\[[0-9;]*m', '', line)
''')
        
        # Test files
        os.makedirs(f'{self.temp_dir}/tests', exist_ok=True)
        with open(f'{self.temp_dir}/tests/test_colorizer.sh', 'w') as f:
            f.write('''#!/bin/bash
# @depends: colorizer.apply_color
echo "Testing color"
''')
    
    def test_analyzer_initialization(self):
        """Test creating an analyzer."""
        config = ImpactConfig(language='python')
        analyzer = ImpactAnalyzer(config=config, root_dir=self.temp_dir)
        
        self.assertIsNotNone(analyzer.language_plugin)
        self.assertIsNotNone(analyzer.test_linker)


class TestIntegration(unittest.TestCase):
    """Integration tests showing full workflow."""
    
    def test_impact_workflow(self):
        """Test the complete workflow: parse → detect → map to tests."""
        import shutil
        
        temp_dir = tempfile.mkdtemp()
        try:
            # Create source structure
            os.makedirs(f'{temp_dir}/src', exist_ok=True)
            with open(f'{temp_dir}/src/colorizer.py', 'w') as f:
                f.write('''
def apply_color(line):
    return f"\\033[32m{line}\\033[0m"
''')
            
            # Create test
            os.makedirs(f'{temp_dir}/tests', exist_ok=True)
            with open(f'{temp_dir}/tests/test_color.sh', 'w') as f:
                f.write('''#!/bin/bash
# @depends: colorizer.apply_color
echo "test"
''')
            
            # Create analyzer
            config = ImpactConfig(language='python', min_confidence=0.5)
            analyzer = ImpactAnalyzer(config=config, root_dir=temp_dir)
            
            # Simulate a change to apply_color
            diff = """diff --git a/src/colorizer.py b/src/colorizer.py
index abc123..def456 100644
--- a/src/colorizer.py
+++ b/src/colorizer.py
@@ -1,3 +1,3 @@
 def apply_color(line):
-    return f"\\033[32m{line}\\033[0m"
+    return f"\\033[31m{line}\\033[0m"
"""
            
            # Analyze
            report = analyzer.analyze_changes(diff)
            
            # Verify
            self.assertEqual(len(report.affected_tests), 1)
            self.assertEqual(report.affected_tests[0].test_file, f'{temp_dir}/tests/test_color.sh')
        
        finally:
            shutil.rmtree(temp_dir)


if __name__ == '__main__':
    unittest.main()
