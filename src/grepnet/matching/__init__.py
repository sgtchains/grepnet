"""
Matching module: Compare networks and ranges against patterns.

Uses interval arithmetic for efficient comparison.
Supports CIDR networks and IP ranges.
"""

from .cidr_matcher import CIDRMatcher
from .range_matcher import RangeMatcher

__all__ = [
    'CIDRMatcher',
    'RangeMatcher',
]
