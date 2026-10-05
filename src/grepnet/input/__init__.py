"""
Input module: Unified abstraction for different input sources.

Supports:
- Regular files
- Standard input
- File descriptors
- Process substitution

All sources use the same interface: lines() → Iterator[(line_number, line_content)]
"""

from .input_source import InputSource, InputDiscovery

__all__ = [
    'InputSource',
    'InputDiscovery',
]
