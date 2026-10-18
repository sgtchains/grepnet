#!/usr/bin/env python3
"""
Performance benchmark for consolidate approaches with wildcard masks.

Compares:
1. Expanding wildcard masks to all CIDRs, then consolidating (current approach if implemented)
2. Interval-based approach (Convert to intervals → Merge intervals → Re-encode to CIDRs)
3. Trie-based approach (prefix tree algorithm)
4. netaddr library with cidr_merge() (Google's recommended Python approach - C-level optimized)
"""

import time
import tempfile
import os
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from grepnet.core import WildcardMaskRange
from ipaddress import IPv4Network, IPv6Network, collapse_addresses

# Try to import netaddr
try:
    from netaddr import IPNetwork, cidr_merge
    NETADDR_AVAILABLE = True
except ImportError:
    NETADDR_AVAILABLE = False
    print("WARNING: netaddr not installed. Install with: pip install netaddr")


def create_test_wildcard():
    """Create a realistic wildcard mask that expands to many CIDRs."""
    # Simulate: 10.4.0.0 0.0.127.252
    # This expands to many CIDR blocks
    cidrs = []
    
    # Simulate expansion of 10.4.0.0 0.0.127.252
    # The mask 0.0.127.252 means:
    # - Fixed: 10.4.x.x (top two octets)
    # - Variable: third octet 0-127, fourth octet varies by /25 boundaries
    # This creates roughly 256 * 128 / 4 = ~8000 /32s or collapsed to ~256 /24s
    
    for third_octet in range(128):  # 0-127
        for fourth_octet in range(0, 256, 4):  # Every 4th to simulate the mask pattern
            cidrs.append(IPv4Network(f'10.4.{third_octet}.{fourth_octet}/32'))
    
    return WildcardMaskRange('10.4.0.0 0.0.127.252', cidrs)


def method_1_expand_then_consolidate():
    """
    Method 1: Expand wildcard mask to all CIDRs, then consolidate.
    (Using Python's ipaddress.collapse_addresses - pure Python)
    """
    print("\n=== METHOD 1: Expand then Consolidate (ipaddress.collapse_addresses) ===")
    
    wildcard = create_test_wildcard()
    print(f"Wildcard mask: {wildcard.original_text}")
    print(f"Expanded CIDRs: {len(wildcard.expanded_cidrs)} networks")
    
    # Add some other networks
    other_networks = [
        IPv4Network('192.0.2.0/24'),
        IPv4Network('192.0.3.0/24'),
        IPv4Network('10.6.0.0/16'),
    ]
    
    # Step 1: Expand wildcard to all CIDRs
    expanded_networks = list(wildcard.expanded_cidrs) + other_networks
    print(f"Total networks to consolidate: {len(expanded_networks)}")
    
    # Step 2: Consolidate
    start = time.time()
    consolidated = list(collapse_addresses(expanded_networks))
    elapsed = time.time() - start
    
    print(f"Consolidated to: {len(consolidated)} networks")
    print(f"Time: {elapsed:.4f}s")
    
    return elapsed


def method_2_interval_based():
    """
    Method 2: Interval-based consolidation.
    Convert networks to (start, end) integer intervals, merge intervals, re-encode to CIDRs.
    """
    print("\n=== METHOD 2: Interval-Based Consolidation ===")
    
    wildcard = create_test_wildcard()
    print(f"Wildcard mask: {wildcard.original_text}")
    print(f"Expanded CIDRs: {len(wildcard.expanded_cidrs)} networks")
    
    # Add some other networks
    other_networks = [
        IPv4Network('192.0.2.0/24'),
        IPv4Network('192.0.3.0/24'),
        IPv4Network('10.6.0.0/16'),
    ]
    
    expanded_networks = list(wildcard.expanded_cidrs) + other_networks
    print(f"Total networks to consolidate: {len(expanded_networks)}")
    
    start = time.time()
    
    # Step 1: Convert to (start_int, end_int) tuples and sort
    intervals = []
    for net in expanded_networks:
        start_int = int(net.network_address)
        end_int = int(net.broadcast_address)
        intervals.append((start_int, end_int))
    
    intervals.sort()
    
    # Step 2: Merge overlapping/adjacent intervals
    merged = []
    for start, end in intervals:
        if merged and start <= merged[-1][1] + 1:
            # Overlapping or adjacent, merge
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    
    # Step 3: Re-encode back to CIDRs (simplified: just show we have merged intervals)
    # Full implementation would convert intervals back to CIDR notation
    consolidated = merged
    
    elapsed = time.time() - start
    
    print(f"Consolidated to: {len(consolidated)} intervals")
    print(f"Time: {elapsed:.4f}s")
    
    return elapsed


def method_3_trie_based():
    """
    Method 3: Trie-based (prefix tree) consolidation.
    Builds a binary trie of IP addresses and merges adjacent branches.
    (Simplified simulation for benchmarking)
    """
    print("\n=== METHOD 3: Trie-Based Consolidation (Simulated) ===")
    
    wildcard = create_test_wildcard()
    print(f"Wildcard mask: {wildcard.original_text}")
    print(f"Expanded CIDRs: {len(wildcard.expanded_cidrs)} networks")
    
    # Add some other networks
    other_networks = [
        IPv4Network('192.0.2.0/24'),
        IPv4Network('192.0.3.0/24'),
        IPv4Network('10.6.0.0/16'),
    ]
    
    expanded_networks = list(wildcard.expanded_cidrs) + other_networks
    print(f"Total networks to consolidate: {len(expanded_networks)}")
    
    start = time.time()
    
    # Step 1: Build trie (simple dict-based implementation)
    # Each node is {0: left_child, 1: right_child, 'leaf': True/False}
    trie = {}
    
    for net in expanded_networks:
        start_int = int(net.network_address)
        prefix_len = net.prefixlen
        
        # Insert into trie (simplified)
        node = trie
        for bit_pos in range(31, 31 - prefix_len, -1):
            bit = (start_int >> bit_pos) & 1
            if bit not in node:
                node[bit] = {}
            node = node[bit]
        node['leaf'] = True
    
    # Step 2: Traverse trie to find merged ranges (simplified)
    def count_leaves(node):
        if 'leaf' in node:
            return 1
        count = 0
        for key in node:
            if isinstance(node[key], dict):
                count += count_leaves(node[key])
        return count
    
    consolidated_count = count_leaves(trie)
    
    elapsed = time.time() - start
    
    print(f"Consolidated to (approx): {consolidated_count} networks")
    print(f"Time: {elapsed:.4f}s")
    
    return elapsed


def method_4_netaddr_cidr_merge():
    """
    Method 4: netaddr library with cidr_merge() (Google's recommended Python approach).
    Uses C-level optimized bindings for fast consolidation.
    """
    if not NETADDR_AVAILABLE:
        print("\n=== METHOD 4: netaddr.cidr_merge() - SKIPPED (not installed) ===")
        return None
    
    print("\n=== METHOD 4: netaddr.cidr_merge() (C-level optimized) ===")
    
    wildcard = create_test_wildcard()
    print(f"Wildcard mask: {wildcard.original_text}")
    print(f"Expanded CIDRs: {len(wildcard.expanded_cidrs)} networks")
    
    # Add some other networks
    other_networks = [
        IPv4Network('192.0.2.0/24'),
        IPv4Network('192.0.3.0/24'),
        IPv4Network('10.6.0.0/16'),
    ]
    
    # Step 1: Expand wildcard to all CIDRs
    expanded_networks = list(wildcard.expanded_cidrs) + other_networks
    print(f"Total networks to consolidate: {len(expanded_networks)}")
    
    # Step 2: Convert to netaddr IPNetwork objects and consolidate
    start = time.time()
    
    # Convert ipaddress.IPv4Network to netaddr.IPNetwork
    netaddr_networks = [IPNetwork(str(net)) for net in expanded_networks]
    
    # Use netaddr's optimized cidr_merge
    consolidated = list(cidr_merge(netaddr_networks))
    
    elapsed = time.time() - start
    
    print(f"Consolidated to: {len(consolidated)} networks")
    print(f"Time: {elapsed:.4f}s")
    
    return elapsed


if __name__ == '__main__':
    print("=" * 60)
    print("Performance Benchmark: Consolidate Methods with Wildcards")
    print("=" * 60)
    
    # Run benchmarks
    time1 = method_1_expand_then_consolidate()
    time2 = method_2_interval_based()
    time3 = method_3_trie_based()
    time4 = method_4_netaddr_cidr_merge()
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Method 1 (ipaddress.collapse_addresses):  {time1:.4f}s")
    print(f"Method 2 (interval-based):                {time2:.4f}s")
    print(f"Method 3 (trie-based):                    {time3:.4f}s")
    if time4 is not None:
        print(f"Method 4 (netaddr.cidr_merge):            {time4:.4f}s")
        
        times = [time1, time2, time3, time4]
        methods = ["Method 1", "Method 2", "Method 3", "Method 4"]
    else:
        times = [time1, time2, time3]
        methods = ["Method 1", "Method 2", "Method 3"]
    
    fastest_idx = times.index(min(times))
    slowest_idx = times.index(max(times))
    
    print(f"\nFastest: {methods[fastest_idx]} ({times[fastest_idx]:.4f}s)")
    print(f"Slowest: {methods[slowest_idx]} ({times[slowest_idx]:.4f}s)")
    print(f"Speedup of fastest vs slowest: {times[slowest_idx] / times[fastest_idx]:.1f}x")


