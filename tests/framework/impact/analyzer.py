"""Test impact analyzer that orchestrates language and VCS plugins."""

import json
import subprocess
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Set, Optional, Any
from pathlib import Path

from .base import CallGraph, LanguagePluginError
from .python_plugin import PythonPlugin
from .vcs_plugins import VcsPlugin, GitPlugin, VcsPluginError
from .linker import TestLinker


@dataclass
class ImpactConfig:
    """Configuration for impact analysis."""
    
    # Language plugin
    language: str = 'python'  # Language to analyze (e.g., 'python', 'go', 'rust')
    
    # VCS plugin configuration
    vcs_plugin: Optional[VcsPlugin] = None  # VCS plugin (if None, auto-detect or use git)
    vcs_type: str = 'git'  # VCS type if plugin not provided: 'git', 'hg', 'p4', 'mtime', 'manual'
    vcs_options: str = '--cached'  # VCS-specific options (e.g., '--unstaged' for git)
    
    # Tracking
    track_transitive: bool = True  # Follow A→B→C chains
    transitive_depth: int = -1  # -1 = unlimited, 0 = direct only
    
    # Accuracy
    min_confidence: float = 0.75  # Minimum confidence score (0.0-1.0)
    
    # Caching
    cache_enabled: bool = True
    cache_dir: str = '.test-cache'
    cache_ttl: int = 86400  # Seconds (1 day)
    
    # Test linking
    dependency_comment: str = '@depends'  # Comment prefix for explicit dependencies
    infer_from_filename: bool = True  # Use filename heuristics
    grep_patterns: bool = True  # Grep test files for function calls
    
    # Output
    include_confidence_scores: bool = True
    include_transitive_path: bool = True


@dataclass
class AffectedTest:
    """Represents a test affected by code changes."""
    
    test_file: str              # "tests/sub-tests/2-output/023_test_color_validation.sh"
    confidence: float           # 0.0-1.0
    reason: str                 # Why this test is affected
    affected_functions: List[str] = field(default_factory=list)  # Functions it depends on
    transitive_path: Optional[str] = None  # "colorizer→apply_color→test_color_validation"


@dataclass
class ImpactReport:
    """Result of impact analysis."""
    
    changed_files: List[str]
    changed_functions: List[str]
    affected_tests: List[AffectedTest]
    unaffected_tests: List[str]
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    total_affected: int = 0
    total_unaffected: int = 0
    execution_time_estimate: float = 0.0
    summary: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'changed_files': self.changed_files,
            'changed_functions': self.changed_functions,
            'affected_tests': [asdict(t) for t in self.affected_tests],
            'unaffected_tests': self.unaffected_tests,
            'total_affected': self.total_affected,
            'total_unaffected': self.total_unaffected,
            'execution_time_estimate': self.execution_time_estimate,
            'summary': self.summary,
        }


class ImpactAnalyzer:
    """Orchestrates language and VCS plugins to determine test impact."""
    
    def __init__(self, config: Optional[ImpactConfig] = None, root_dir: str = '.'):
        self.config = config or ImpactConfig()
        self.root_dir = root_dir
        self.language_plugin = self._load_language_plugin()
        self.vcs_plugin = self._load_vcs_plugin()
        self.test_linker = TestLinker(root_dir)
        self.call_graph: Optional[CallGraph] = None
    
    def _load_language_plugin(self):
        """Load language plugin based on configuration."""
        language = self.config.language.lower()
        
        if language == 'python':
            return PythonPlugin()
        # Future: elif language == 'go': return GoPlugin()
        else:
            raise LanguagePluginError(f"Unsupported language: {language}")
    
    def _load_vcs_plugin(self) -> VcsPlugin:
        """Load VCS plugin based on configuration."""
        # If plugin explicitly provided, use it
        if self.config.vcs_plugin is not None:
            return self.config.vcs_plugin
        
        # Otherwise, create plugin based on vcs_type
        vcs_type = self.config.vcs_type.lower()
        
        if vcs_type == 'git':
            return GitPlugin(self.root_dir)
        elif vcs_type == 'hg':
            from .vcs_plugins import HgPlugin
            return HgPlugin(self.root_dir)
        elif vcs_type == 'p4':
            from .vcs_plugins import P4Plugin
            return P4Plugin(self.root_dir)
        elif vcs_type == 'mtime':
            from .vcs_plugins import FileMtimePlugin
            return FileMtimePlugin(self.root_dir)
        elif vcs_type == 'manual':
            from .vcs_plugins import ManualPlugin
            return ManualPlugin()
        else:
            raise VcsPluginError(f"Unsupported VCS type: {vcs_type}")
    
    def analyze_changes(self, git_diff: Optional[str] = None) -> ImpactReport:
        """
        Analyze code changes and return affected tests.
        
        Args:
            git_diff: Diff output (if None, fetches automatically from VCS)
        
        Returns:
            ImpactReport with affected tests and metadata
        """
        # Get diff if not provided
        if git_diff is None:
            git_diff = self.vcs_plugin.get_diff(self.config.vcs_options)
        
        # Build or load call graph
        if self.call_graph is None:
            self.call_graph = self.language_plugin.parse_codebase(self.root_dir)
        
        # Extract changed functions
        changed_functions = self.language_plugin.extract_changed_functions(git_diff, root_dir=self.root_dir)
        changed_files = self._extract_changed_files(git_diff)
        
        # Find affected functions (including transitive)
        affected_functions = set(changed_functions)
        if self.config.track_transitive:
            for func in changed_functions:
                transitive = self.call_graph.find_transitive_dependents(
                    func, self.config.transitive_depth
                )
                affected_functions.update(transitive)
        
        # Map to tests
        affected_tests = []
        test_files = self.test_linker.find_all_tests(self.root_dir)
        
        for test_file in test_files:
            dependencies = self.test_linker.extract_dependencies(test_file)
            test_affected_funcs = set()
            
            for dep in dependencies:
                if dep in affected_functions:
                    test_affected_funcs.add(dep)
            
            if test_affected_funcs:
                # Calculate confidence
                confidence = self._calculate_confidence(test_file, test_affected_funcs)
                
                if confidence >= self.config.min_confidence:
                    reason = self._generate_reason(test_affected_funcs)
                    affected_tests.append(AffectedTest(
                        test_file=test_file,
                        confidence=confidence,
                        reason=reason,
                        affected_functions=list(test_affected_funcs)
                    ))
        
        # Sort by confidence (highest first)
        affected_tests.sort(key=lambda t: t.confidence, reverse=True)
        
        # Generate summary
        unaffected_tests = [t for t in test_files if t not in {at.test_file for at in affected_tests}]
        execution_time = self._estimate_execution_time(len(affected_tests))
        
        report = ImpactReport(
            changed_files=sorted(changed_files),
            changed_functions=sorted(changed_functions),
            affected_tests=affected_tests,
            unaffected_tests=sorted(unaffected_tests),
            total_affected=len(affected_tests),
            total_unaffected=len(unaffected_tests),
            execution_time_estimate=execution_time,
            summary=self._generate_summary(len(affected_tests), len(test_files))
        )
        
        return report
    
    def _extract_changed_files(self, git_diff: str) -> List[str]:
        """Extract changed file paths from git diff."""
        import re
        changed_files = []
        
        for line in git_diff.split('\n'):
            if line.startswith('+++ b/'):
                file_path = line[6:]
                changed_files.append(file_path)
        
        return changed_files
    
    def _calculate_confidence(self, test_file: str, affected_functions: Set[str]) -> float:
        """Calculate confidence score for test impact."""
        # Base confidence increases with number of affected functions
        base = min(0.5 + len(affected_functions) * 0.15, 1.0)
        
        # Boost if explicit dependency comment found
        if self.test_linker.has_explicit_dependency(test_file):
            base = min(base + 0.2, 1.0)
        
        # Reduce if only filename-based inference
        if not self.test_linker.has_explicit_dependency(test_file):
            base = max(base - 0.1, 0.0)
        
        return round(base, 2)
    
    def _generate_reason(self, affected_functions: Set[str]) -> str:
        """Generate human-readable reason for test impact."""
        if len(affected_functions) == 1:
            return f"Depends on {list(affected_functions)[0]}"
        else:
            functions_str = ', '.join(sorted(list(affected_functions))[:3])
            if len(affected_functions) > 3:
                functions_str += f" (+{len(affected_functions) - 3} more)"
            return f"Depends on: {functions_str}"
    
    def _estimate_execution_time(self, num_tests: int) -> float:
        """Estimate execution time for affected tests."""
        # Rough estimate: 3-5 seconds per test
        return num_tests * 4.0
    
    def _generate_summary(self, affected: int, total: int) -> str:
        """Generate human-readable summary."""
        percentage = int((affected / total * 100) if total > 0 else 0)
        return f"{affected}/{total} tests affected ({percentage}%)"
