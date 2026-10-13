"""Test impact analysis framework for selective test execution.

This module provides language-agnostic test impact analysis by:
1. Parsing source code and building call graphs
2. Detecting code changes via pluggable VCS integration
3. Tracing affected functions
4. Mapping to impacted tests
5. Recommending selective test execution
"""

from .base import LanguagePlugin, CallGraph, Function
from .analyzer import ImpactAnalyzer, ImpactReport, ImpactConfig
from .vcs_plugins import (
    VcsPlugin, VcsPluginError,
    GitPlugin, HgPlugin, P4Plugin,
    FileMtimePlugin, ManualPlugin
)
from .linker import TestLinker

__all__ = [
    'LanguagePlugin',
    'CallGraph',
    'Function',
    'ImpactAnalyzer',
    'ImpactReport',
    'ImpactConfig',
    'VcsPlugin',
    'VcsPluginError',
    'GitPlugin',
    'HgPlugin',
    'P4Plugin',
    'FileMtimePlugin',
    'ManualPlugin',
    'TestLinker',
]
