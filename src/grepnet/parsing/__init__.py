"""
Parsing module: Extract and validate network objects from text.

Components:
- NetworkParser: Main orchestrator for extraction pipeline
- CommentHandler: Handle comment filtering
- Extractors: Specific format extractors (CIDR, masks, ranges, IPs)
"""

from .network_parser import NetworkParser
from .comment_handler import CommentHandler
from . import extractors

__all__ = [
    'NetworkParser',
    'CommentHandler',
    'extractors',
]
