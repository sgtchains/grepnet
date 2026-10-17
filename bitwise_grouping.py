#!/usr/bin/env python3
"""
Bitwise CIDR Grouping Algorithm
1. Groups CIDRs into sweeping_groups based on hostmask expansion
2. Identifies gaps within each group
"""

import ipaddress
from typing import List, Tuple


def popcount(n):
    """Count set bits."""
    return bin(n).count('1')


def fits_in_hostmask(cidr_ip: int, hostmask: int, base_ip: int) -> bool:
    """
    Check if a CIDR start IP fits within current hostmask.
    Per spec: (cidr_start_ip & ~current_hostmask) must equal (base_ip & ~current_hostmask)
    """
    if hostmask == 0:
        return False
    
    return (cidr_ip & ~hostmask) == (base_ip & ~hostmask)


def group_cidrs(cidrs: List[str], min_prefix: int, max_prefix: int) -> List[Tuple[List, str]]:
    """
    Group CIDRs into sweeping_groups.
    
    Returns: List of (group_cidrs, container_cidr_string)
    """
    # Parse and sort by start IP
    parsed = [ipaddress.ip_network(c) for c in cidrs]
    sorted_cidrs = sorted(parsed, key=lambda x: int(x.network_address))
    
    groups = []
    current_hostmask = 0
    current_group = []
    base_ip = None
    
    for cidr in sorted_cidrs:
        cidr_prefix = cidr.prefixlen
        cidr_ip = int(cidr.network_address)
        
        # Step 0: If prefix <= min_prefix_length, finalize and start new
        if cidr_prefix <= min_prefix:
            if current_group:
                # Finalize current group
                container_prefix = 32 - popcount(current_hostmask)
                container_ip = base_ip & ~current_hostmask
                container = ipaddress.ip_network((container_ip, container_prefix), strict=False)
                groups.append((current_group, str(container)))
            
            current_group = [cidr]
            current_hostmask = 0
            base_ip = cidr_ip
            continue
        
        # Initialize base_ip on first CIDR
        if base_ip is None:
            base_ip = cidr_ip
        
        # Step 1-2: Check if fits in current hostmask
        if current_hostmask == 0:
            # Prime with /31 hostmask (1 host bit)
            current_hostmask = 1
        
        # Try to fit CIDR
        while True:
            if fits_in_hostmask(cidr_ip, current_hostmask, base_ip):
                # Step 2: Fits! Add to group
                current_group.append(cidr)
                break
            else:
                # Step 3: Doesn't fit, need to expand
                next_hostmask = (current_hostmask << 1) | current_hostmask
                next_prefix = 32 - popcount(next_hostmask)
                
                if next_prefix < min_prefix:
                    # Step 3a: Would violate min_prefix_length
                    # Finalize current group
                    container_prefix = 32 - popcount(current_hostmask)
                    container_ip = base_ip & ~current_hostmask
                    container = ipaddress.ip_network((container_ip, container_prefix), strict=False)
                    groups.append((current_group, str(container)))
                    
                    # Start new group
                    current_group = [cidr]
                    current_hostmask = 1  # Prime for new group
                    base_ip = cidr_ip
                    break
                else:
                    # Step 3b: Expand and check again
                    current_hostmask = next_hostmask
    
    # Finalize last group
    if current_group:
        container_prefix = 32 - popcount(current_hostmask)
        container_ip = base_ip & ~current_hostmask
        container = ipaddress.ip_network((container_ip, container_prefix), strict=False)
        groups.append((current_group, str(container)))
    
    return groups


def identify_gaps(cidrs: List, container_cidr_str: str) -> List[str]:
    """
    Identify gaps within a sweeping_group.
    
    Process:
    1. Sort CIDRs by start IP
    2. Track prev_end
    3. For each CIDR, identify gaps between prev_end and current_start
    4. Collapse gap IPs into optimal CIDRs
    """
    container = ipaddress.ip_network(container_cidr_str)
    container_start = int(container.network_address)
    container_end = int(container.broadcast_address)
    
    # Sort by start IP
    sorted_cidrs = sorted(cidrs, key=lambda x: int(x.network_address))
    
    gaps = []
    prev_end = container_start - 1
    
    for cidr in sorted_cidrs:
        cidr_start = int(cidr.network_address)
        cidr_end = int(cidr.broadcast_address)
        
        # Gap between prev_end and current_start
        if cidr_start > prev_end + 1:
            gap_ips = list(range(prev_end + 1, cidr_start))
            gaps.extend(gap_ips)
        
        # Update prev_end (handles overlaps)
        prev_end = max(prev_end, cidr_end)
    
    # Gap at end of container
    if prev_end < container_end:
        gap_ips = list(range(prev_end + 1, container_end + 1))
        gaps.extend(gap_ips)
    
    # Collapse to CIDRs
    if gaps:
        ip_set = ipaddress.collapse_addresses([ipaddress.ip_address(ip) for ip in gaps])
        return [str(cidr) for cidr in sorted(ip_set)]
    
    return []


def main():
    print("=" * 80)
    print("BITWISE CIDR GROUPING WITH GAP IDENTIFICATION")
    print("=" * 80)
    
    # Test case
    cidrs = [
        "192.0.2.0/32",
        "192.0.2.1/32",
        "192.0.2.2/32",
        "192.0.2.16/28",
    ]
    
    min_prefix = 27
    max_prefix = 30
    
    print(f"\nInput CIDRs (unsorted):")
    for c in cidrs:
        net = ipaddress.ip_network(c)
        print(f"  {c:20} (.{int(net.network_address) - int(ipaddress.ip_address('192.0.2.0'))})")
    
    print(f"\nParameters: min_prefix={min_prefix}, max_prefix={max_prefix}")
    
    # Step 1: Group
    print(f"\n" + "-" * 80)
    print("STEP 1: SWEEPING GROUPS")
    print("-" * 80)
    
    groups = group_cidrs(cidrs, min_prefix, max_prefix)
    
    for group_idx, (group_items, container_str) in enumerate(groups, 1):
        print(f"\nSweeping Group {group_idx}:")
        print(f"  Container: {container_str}")
        print(f"  CIDRs:")
        for c in group_items:
            net = ipaddress.ip_network(str(c))
            print(f"    {str(c):20} (.{int(net.network_address) - int(ipaddress.ip_address('192.0.2.0'))}-{int(net.broadcast_address) - int(ipaddress.ip_address('192.0.2.0'))})")
        
        # Step 2: Identify gaps
        print(f"\n  STEP 2: GAPS IN THIS GROUP")
        gap_cidrs_list = identify_gaps(group_items, container_str)
        
        if gap_cidrs_list:
            print(f"  Gap CIDRs:")
            for c in gap_cidrs_list:
                net = ipaddress.ip_network(c)
                print(f"    {c:20} (.{int(net.network_address) - int(ipaddress.ip_address('192.0.2.0'))}-{int(net.broadcast_address) - int(ipaddress.ip_address('192.0.2.0'))})")
        else:
            print(f"  No gaps")


if __name__ == "__main__":
    main()
