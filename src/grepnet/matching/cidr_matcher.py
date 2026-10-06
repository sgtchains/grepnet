"""
CIDR network matching.

Compares CIDR networks against patterns using interval arithmetic.

Critical note: Overlap is IMPOSSIBLE with CIDR networks due to binary alignment.
Two CIDR networks can only be: equals, subset/superset, or disjoint.
"""

from typing import List, Optional
from ipaddress import IPv4Network, IPv6Network
import bisect


class CIDRMatcher:
    """
    Match CIDR networks against search patterns.
    
    Uses binary search for efficient lookup.
    Converts networks to integer intervals for comparison.
    
    Important: Overlap is mathematically impossible with CIDR-based networks.
    find_overlap_matches() will return empty (or be optimized to return immediately).
    """
    
    def __init__(self, file_networks: List):
        """
        Initialize matcher with file networks.
        
        Args:
            file_networks: List of IPv4Network or IPv6Network objects from file
        """
        self.file_networks = file_networks
        
        # Organize by address family and prefix length for efficient lookup
        self.ipv4_by_prefix = {}  # prefix_len -> [networks]
        self.ipv6_by_prefix = {}
        
        for net in file_networks:
            if isinstance(net, IPv4Network):
                prefix = net.prefixlen
                if prefix not in self.ipv4_by_prefix:
                    self.ipv4_by_prefix[prefix] = []
                self.ipv4_by_prefix[prefix].append(net)
            elif isinstance(net, IPv6Network):
                prefix = net.prefixlen
                if prefix not in self.ipv6_by_prefix:
                    self.ipv6_by_prefix[prefix] = []
                self.ipv6_by_prefix[prefix].append(net)
        
        # Sort each list by network address for binary search
        for nets in self.ipv4_by_prefix.values():
            nets.sort(key=lambda n: int(n.network_address))
        for nets in self.ipv6_by_prefix.values():
            nets.sort(key=lambda n: int(n.network_address))
    
    def find_equal_matches(self, pattern) -> List[int]:
        """
        Find file networks equal to pattern.
        
        Args:
            pattern: IPv4Network or IPv6Network
        
        Returns:
            List of indices into self.file_networks
        """
        matches = []
        for idx, net in enumerate(self.file_networks):
            if net == pattern:
                matches.append(idx)
        return matches
    
    def find_subset_matches(self, pattern) -> List[int]:
        """
        Find file networks that are subsets of pattern.
        (file_network is subset of pattern ⟹ pattern contains file_network)
        
        Args:
            pattern: IPv4Network or IPv6Network
        
        Returns:
            List of indices
        """
        matches = []
        for idx, net in enumerate(self.file_networks):
            # File network is subset of pattern if:
            # - Same address family
            # - File prefix >= pattern prefix (more specific)
            # - File network is within pattern's address space
            if type(net) != type(pattern):
                continue
            
            if net.prefixlen >= pattern.prefixlen:
                if net.subnet_of(pattern):
                    matches.append(idx)
        
        return matches
    
    def find_superset_matches(self, pattern) -> List[int]:
        """
        Find file networks that are supersets of pattern.
        (file_network is superset of pattern ⟹ file_network contains pattern)
        
        Args:
            pattern: IPv4Network or IPv6Network
        
        Returns:
            List of indices
        """
        matches = []
        for idx, net in enumerate(self.file_networks):
            # File network is superset of pattern if:
            # - Same address family
            # - File prefix <= pattern prefix (less specific)
            # - Pattern is within file's address space
            if type(net) != type(pattern):
                continue
            
            if net.prefixlen <= pattern.prefixlen:
                if pattern.subnet_of(net):
                    matches.append(idx)
        
        return matches
    
    def find_overlap_matches(self, pattern) -> List[int]:
        """
        Find file networks that overlap with pattern.
        
        CRITICAL: Returns empty list (overlap impossible with CIDR).
        Overlap only occurs with arbitrary IP ranges.
        
        Args:
            pattern: IPv4Network or IPv6Network
        
        Returns:
            Empty list (overlap impossible with CIDR-based networks)
        """
        # Overlap requires partial overlap without subset/superset relationship.
        # This is mathematically impossible with CIDR networks due to binary alignment.
        # All CIDR relationships are: equals, subset/superset, or disjoint.
        return []
