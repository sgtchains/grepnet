"""
GrepNet: Network-aware grep for CIDR, IP ranges, and other network formats.

Main entry point and package exports.
"""

from .grepnet import GrepNet
from .core import ParsedExtraction, MatchResult, MatchType, Colorizer, BinaryDetector
from .parsing import NetworkParser, CommentHandler
from .input import InputSource, InputDiscovery
from .matching import CIDRMatcher, RangeMatcher

__version__ = '3.0.0'
__all__ = [
    'GrepNet',
    'ParsedExtraction',
    'MatchResult',
    'MatchType',
    'Colorizer',
    'BinaryDetector',
    'NetworkParser',
    'CommentHandler',
    'InputSource',
    'FileSource',
    'StdinSource',
    'FDSource',
    'InputDiscovery',
    'CIDRMatcher',
    'RangeMatcher',
]
