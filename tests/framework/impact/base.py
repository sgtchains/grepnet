"""Base classes and data structures for language plugins."""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Set, Optional


@dataclass
class Function:
    """Represents a single function/method in the codebase."""
    
    qualified_name: str        # "module.submodule.Class.method"
    file_path: str             # "src/grepnet/core/colorizer.py"
    line_number: int           # First line of function definition
    calls: Set[str] = field(default_factory=set)      # Functions this calls
    called_by: Set[str] = field(default_factory=set)  # Functions that call this
    
    def __hash__(self):
        return hash(self.qualified_name)
    
    def __eq__(self, other):
        return isinstance(other, Function) and self.qualified_name == other.qualified_name


@dataclass
class CallGraph:
    """Complete call graph for a codebase."""
    
    functions: Dict[str, Function]  # qualified_name → Function
    language: str                   # "python", "go", "rust", etc.
    build_time: float               # Time to build (seconds)
    root_dir: str                   # Root directory analyzed
    
    def find_transitive_dependents(
        self, function_name: str, depth: int = -1, visited: Optional[Set[str]] = None
    ) -> Set[str]:
        """
        Find all functions that depend on this function (directly or indirectly).
        
        Args:
            function_name: Function to analyze
            depth: -1 = unlimited, 0 = direct only, N = N levels
            visited: Internal tracking for recursion
        
        Returns:
            Set of qualified function names that depend on this one
        """
        if visited is None:
            visited = set()
        
        if function_name not in self.functions:
            return set()
        
        if depth == 0:
            return set()
        
        if function_name in visited:
            return set()
        
        visited.add(function_name)
        result = set()
        
        # Find direct dependents (functions that call this function)
        func = self.functions[function_name]
        for caller_name in func.called_by:
            result.add(caller_name)
            if depth != 1:
                next_depth = -1 if depth == -1 else depth - 1
                transitive = self.find_transitive_dependents(caller_name, next_depth, visited)
                result.update(transitive)
        
        return result
    
    def find_transitive_dependencies(
        self, function_name: str, depth: int = -1, visited: Optional[Set[str]] = None
    ) -> Set[str]:
        """
        Find all functions that this function depends on (directly or indirectly).
        
        Args:
            function_name: Function to analyze
            depth: -1 = unlimited, 0 = direct only, N = N levels
            visited: Internal tracking for recursion
        
        Returns:
            Set of qualified function names this one depends on
        """
        if visited is None:
            visited = set()
        
        if function_name not in self.functions:
            return set()
        
        if depth == 0:
            return set()
        
        if function_name in visited:
            return set()
        
        visited.add(function_name)
        result = set()
        
        # Find functions this one calls
        func = self.functions[function_name]
        for callee_name in func.calls:
            result.add(callee_name)
            if depth != 1:
                next_depth = -1 if depth == -1 else depth - 1
                transitive = self.find_transitive_dependencies(callee_name, next_depth, visited)
                result.update(transitive)
        
        return result


class LanguagePluginError(Exception):
    """Raised when language plugin encounters an error."""
    pass


class LanguagePlugin(ABC):
    """Abstract base class for language-specific test impact analyzers."""
    
    @abstractmethod
    def parse_codebase(self, root_dir: str) -> CallGraph:
        """
        Parse source files and build a call graph.
        
        Args:
            root_dir: Root directory containing source code
        
        Returns:
            CallGraph with all functions and their dependencies
        
        Raises:
            LanguagePluginError: If parsing fails
        """
        pass
    
    @abstractmethod
    def extract_changed_functions(self, git_diff: str) -> Set[str]:
        """
        Extract changed function names from git diff output.
        
        Args:
            git_diff: Output from `git diff` command (or path to file with diff)
        
        Returns:
            Set of qualified function names (e.g., "module.Class.method")
        
        Raises:
            LanguagePluginError: If extraction fails
        """
        pass
    
    def get_language(self) -> str:
        """Return the language name (e.g., 'python', 'go', 'rust')."""
        class_name = self.__class__.__name__
        # PythonPlugin → python, GoPlugin → go, etc.
        language = class_name.replace('Plugin', '').lower()
        return language
