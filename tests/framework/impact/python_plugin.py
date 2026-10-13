"""Python language plugin for test impact analysis."""

import ast
import os
import re
from typing import Set, Dict, List, Optional, Tuple
from pathlib import Path

from .base import LanguagePlugin, CallGraph, Function, LanguagePluginError


class PythonPlugin(LanguagePlugin):
    """Python language support using AST analysis."""
    
    PYTHON_EXTENSIONS = {'.py'}
    
    def __init__(self):
        self.current_module = ""
        self.current_class = ""
        self.import_map: Dict[str, str] = {}  # alias → qualified_name
    
    def parse_codebase(self, root_dir: str) -> CallGraph:
        """Parse Python codebase and build call graph using AST."""
        start_time = time.time()
        functions: Dict[str, Function] = {}
        
        try:
            for py_file in self._find_python_files(root_dir):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        source = f.read()
                    
                    tree = ast.parse(source, filename=py_file)
                    relative_path = os.path.relpath(py_file, root_dir)
                    module_name = self._path_to_module(relative_path)
                    
                    # Extract functions and build call graph
                    self.current_module = module_name
                    self.import_map = {}
                    
                    visitor = FunctionExtractor(module_name, relative_path)
                    visitor.visit(tree)
                    
                    # Merge extracted functions
                    for func in visitor.functions.values():
                        functions[func.qualified_name] = func
                
                except SyntaxError as e:
                    # Skip files with syntax errors
                    print(f"Warning: Syntax error in {py_file}: {e}")
                except Exception as e:
                    print(f"Warning: Error parsing {py_file}: {e}")
            
            # Build reverse edges (called_by) after all functions extracted
            for func in functions.values():
                for callee in func.calls:
                    if callee in functions:
                        functions[callee].called_by.add(func.qualified_name)
            
            build_time = time.time() - start_time
            return CallGraph(
                functions=functions,
                language='python',
                build_time=build_time,
                root_dir=root_dir
            )
        
        except Exception as e:
            raise LanguagePluginError(f"Failed to parse Python codebase: {e}")
    
    def extract_changed_functions(self, git_diff: str, root_dir: str = '.') -> Set[str]:
        """Extract Python functions modified in git diff.
        
        Args:
            git_diff: Git diff output (or file path to diff)
            root_dir: Root directory to resolve relative file paths against
        
        Returns:
            Set of qualified function names that were changed
        """
        changed_functions = set()
        
        # Parse diff to find changed line ranges
        for hunk in self._parse_diff_hunks(git_diff):
            file_path = hunk['file']
            changed_lines = hunk['lines']
            
            # Only process Python files
            if not file_path.endswith('.py'):
                continue
            
            # Resolve file path relative to root_dir
            full_path = os.path.join(root_dir, file_path)
            
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    source = f.read()
                
                tree = ast.parse(source, filename=full_path)
                module_name = self._path_to_module(file_path)
                
                # Find functions that contain changed lines
                visitor = LineRangeVisitor(changed_lines)
                visitor.visit(tree)
                
                for func_name in visitor.functions_with_changes:
                    qualified_name = f"{module_name}.{func_name}"
                    changed_functions.add(qualified_name)
            
            except Exception as e:
                print(f"Warning: Could not extract changes from {full_path}: {e}")
        
        return changed_functions
    
    def _find_python_files(self, root_dir: str) -> List[str]:
        """Find all Python files in directory tree."""
        python_files = []
        
        # Skip common directories
        skip_dirs = {'.git', '__pycache__', '.pytest_cache', '.venv', 'venv', 'node_modules', '.egg-info'}
        
        for dirpath, dirnames, filenames in os.walk(root_dir):
            # Remove skip directories from traversal
            dirnames[:] = [d for d in dirnames if d not in skip_dirs]
            
            for filename in filenames:
                if filename.endswith('.py'):
                    full_path = os.path.join(dirpath, filename)
                    python_files.append(full_path)
        
        return sorted(python_files)
    
    def _path_to_module(self, file_path: str) -> str:
        """Convert file path to module name."""
        # Remove .py extension
        if file_path.endswith('.py'):
            file_path = file_path[:-3]
        
        # Replace path separators with dots
        module_name = file_path.replace(os.sep, '.')
        
        # Remove leading src/ if present
        if module_name.startswith('src.'):
            module_name = module_name[4:]
        
        return module_name
    
    def _parse_diff_hunks(self, git_diff: str) -> List[Dict]:
        """Parse git diff output into hunks with file paths and line ranges."""
        hunks = []
        current_file = None
        current_lines = set()
        
        # Handle case where git_diff is a file path
        if os.path.isfile(git_diff):
            with open(git_diff, 'r') as f:
                git_diff = f.read()
        
        for line in git_diff.split('\n'):
            # New file
            if line.startswith('diff --git'):
                if current_file:
                    hunks.append({'file': current_file, 'lines': current_lines})
                current_file = None
                current_lines = set()
            
            # File path
            elif line.startswith('+++ b/'):
                current_file = line[6:]
                current_lines = set()
            
            # Hunk header @@ -10,5 +15,7 @@
            elif line.startswith('@@'):
                match = re.search(r'\+(\d+)(?:,(\d+))?', line)
                if match:
                    start_line = int(match.group(1))
                    num_lines = int(match.group(2)) if match.group(2) else 1
                    for i in range(num_lines):
                        current_lines.add(start_line + i)
        
        if current_file:
            hunks.append({'file': current_file, 'lines': current_lines})
        
        return hunks


import time


class FunctionExtractor(ast.NodeVisitor):
    """AST visitor that extracts function definitions and their calls."""
    
    def __init__(self, module_name: str, file_path: str):
        self.module_name = module_name
        self.file_path = file_path
        self.functions: Dict[str, Function] = {}
        self.current_class_stack: List[str] = []
        self.current_function: Optional[str] = None
    
    def visit_ClassDef(self, node: ast.ClassDef):
        """Visit class definition."""
        self.current_class_stack.append(node.name)
        self.generic_visit(node)
        self.current_class_stack.pop()
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visit function definition."""
        class_prefix = '.'.join(self.current_class_stack)
        func_name = f"{class_prefix}.{node.name}" if class_prefix else node.name
        qualified_name = f"{self.module_name}.{func_name}"
        
        # Extract calls made by this function
        calls = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                call_name = self._extract_call_target(child)
                if call_name:
                    calls.add(call_name)
        
        func = Function(
            qualified_name=qualified_name,
            file_path=self.file_path,
            line_number=node.lineno,
            calls=calls
        )
        self.functions[qualified_name] = func
        
        # Visit nested functions
        old_function = self.current_function
        self.current_function = func_name
        self.generic_visit(node)
        self.current_function = old_function
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Visit async function definition (same as FunctionDef)."""
        self.visit_FunctionDef(node)  # Treat as regular function
    
    def _extract_call_target(self, node: ast.Call) -> Optional[str]:
        """Extract the qualified name of a function call."""
        if isinstance(node.func, ast.Name):
            # Direct call: func()
            return f"{self.module_name}.{node.func.id}"
        elif isinstance(node.func, ast.Attribute):
            # Method call: obj.method()
            parts = []
            current = node.func
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            
            if isinstance(current, ast.Name):
                parts.append(current.id)
                parts.reverse()
                return f"{self.module_name}.{'.'.join(parts)}"
        
        return None


class LineRangeVisitor(ast.NodeVisitor):
    """AST visitor that finds functions containing specific line ranges."""
    
    def __init__(self, target_lines: Set[int]):
        self.target_lines = target_lines
        self.functions_with_changes: Set[str] = set()
        self.current_class_stack: List[str] = []
    
    def visit_ClassDef(self, node: ast.ClassDef):
        """Visit class definition."""
        self.current_class_stack.append(node.name)
        self.generic_visit(node)
        self.current_class_stack.pop()
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Check if function contains changed lines."""
        # Get function end line
        end_line = node.end_lineno if hasattr(node, 'end_lineno') else self._estimate_end_line(node)
        func_range = set(range(node.lineno, end_line + 1))
        
        # Check if any target lines are in this function
        if func_range & self.target_lines:
            class_prefix = '.'.join(self.current_class_stack)
            func_name = f"{class_prefix}.{node.name}" if class_prefix else node.name
            self.functions_with_changes.add(func_name)
        
        # Visit nested functions
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Visit async function definition."""
        self.visit_FunctionDef(node)
    
    def _estimate_end_line(self, node: ast.FunctionDef) -> int:
        """Estimate function end line for Python versions without end_lineno."""
        if hasattr(node, 'end_lineno') and node.end_lineno:
            return node.end_lineno
        
        # Fallback: estimate based on body
        if node.body:
            last_stmt = node.body[-1]
            if hasattr(last_stmt, 'lineno'):
                return last_stmt.lineno
        
        return node.lineno
