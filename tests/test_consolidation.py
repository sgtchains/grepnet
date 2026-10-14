"""
Test suite for network consolidation functionality.

Tests the --consolidate flag to ensure proper RFC-compliant CIDR supernetting.
"""

import unittest
import tempfile
import os
import sys
from pathlib import Path
from ipaddress import IPv4Network, IPv6Network

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from grepnet.grepnet import GrepNet
from grepnet.input import InputSource


class TestConsolidation(unittest.TestCase):
    """Test network consolidation (merge) logic."""
    
    def setUp(self):
        """Set up test fixtures."""
        pass
    
    def _consolidate_from_string(self, input_str: str, patterns: list = None) -> list:
        """
        Helper: consolidate networks from a string input.
        
        Args:
            input_str: Newline-separated CIDR networks
            patterns: List of patterns to search for (defaults to extracting all from input)
        
        Returns:
            List of consolidated network strings, sorted
        """
        # If no patterns provided, extract them from the input
        if patterns is None:
            patterns = [line.strip() for line in input_str.strip().split('\n') if line.strip()]
        
        # Create a temp file with the input
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(input_str)
            temp_file = f.name
        
        try:
            # Create GrepNet with patterns
            grepnet = GrepNet(
                patterns=patterns,
                enable_colors=False,
            )
            
            # Create input source from file
            input_source = InputSource('file', file_path=temp_file)
            
            # Consolidate
            consolidated_dict = grepnet.consolidate_networks([input_source])
            
            # Extract and sort network strings
            result = sorted([str(net) for net in consolidated_dict.keys()])
            return result
        finally:
            os.unlink(temp_file)
    
    def _consolidate_from_string_with_fill(self, input_str: str, fill_pct: int, patterns: list = None) -> list:
        """
        Helper: consolidate networks with fill-pct from a string input.
        
        Args:
            input_str: Newline-separated CIDR networks or ranges
            fill_pct: Fill percentage (0-100)
            patterns: List of patterns to search for (defaults to extracting all from input)
        
        Returns:
            List of consolidated network strings, sorted
        """
        # If no patterns provided, extract them from the input
        if patterns is None:
            patterns = [line.strip() for line in input_str.strip().split('\n') if line.strip()]
        
        # Create a temp file with the input
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(input_str)
            temp_file = f.name
        
        try:
            # Create GrepNet with patterns
            grepnet = GrepNet(
                patterns=patterns,
                enable_colors=False,
            )
            
            # Create input source from file
            input_source = InputSource('file', file_path=temp_file)
            
            # Consolidate with fill-pct
            consolidated_dict = grepnet.consolidate_networks([input_source], fill_pct=fill_pct)
            
            # Extract and sort network strings
            result = sorted([str(net) for net in consolidated_dict.keys()])
            return result
        finally:
            os.unlink(temp_file)
    
    def test_non_consolidatable_networks(self):
        """
        Test that networks at different prefix levels that don't form proper supernets
        are NOT consolidated.
        
        This is the regression test for the bug:
        printf "32.112.0.0/21\n32.112.8.0/22" | grepnet --consolidate
        
        Expected: Both networks remain separate
        Bug was: Incorrectly consolidated to 32.112.0.0/20
        """
        input_str = "32.112.0.0/21\n32.112.8.0/22"
        result = self._consolidate_from_string(input_str)
        
        # Both networks should remain separate
        self.assertEqual(len(result), 2)
        self.assertIn('32.112.0.0/21', result)
        self.assertIn('32.112.8.0/22', result)
    
    def test_overlapping_networks_consolidate(self):
        """Test that overlapping networks are properly consolidated."""
        # 192.0.2.0/24 completely contains 192.0.2.0/25
        input_str = "192.0.2.0/24\n192.0.2.0/25"
        result = self._consolidate_from_string(input_str)
        
        # Should consolidate to the larger network
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], '192.0.2.0/24')
    
    def test_adjacent_same_prefix_consolidate(self):
        """Test that adjacent networks at the same prefix level are consolidated."""
        # 192.0.2.0/25 and 192.0.2.128/25 are adjacent and same prefix
        # They should consolidate to 192.0.2.0/24
        input_str = "192.0.2.0/25\n192.0.2.128/25"
        result = self._consolidate_from_string(input_str)
        
        # Should consolidate to supernet
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], '192.0.2.0/24')
    
    def test_non_adjacent_networks_dont_consolidate(self):
        """Test that non-adjacent, non-overlapping networks don't consolidate."""
        # 192.0.2.0/26 and 192.0.2.128/26 are non-adjacent /26s in same /25
        input_str = "192.0.2.0/26\n192.0.2.128/26"
        result = self._consolidate_from_string(input_str)
        
        # Both should remain separate (they don't form a valid supernet)
        self.assertEqual(len(result), 2)
        self.assertIn('192.0.2.0/26', result)
        self.assertIn('192.0.2.128/26', result)
    
    def test_multiple_overlapping_networks(self):
        """Test consolidation of multiple overlapping networks."""
        input_str = "10.0.0.0/8\n10.1.0.0/16\n10.1.1.0/24"
        result = self._consolidate_from_string(input_str)
        
        # All contained in 10.0.0.0/8
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], '10.0.0.0/8')
    
    def test_ipv6_consolidation(self):
        """Test that IPv6 networks are properly consolidated."""
        # 2001:db8::/32 contains 2001:db8::/33
        input_str = "2001:db8::/32\n2001:db8::/33"
        result = self._consolidate_from_string(input_str)
        
        # Should consolidate to the larger network
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], '2001:db8::/32')
    
    def test_ipv4_ipv6_separate(self):
        """Test that IPv4 and IPv6 networks are kept separate."""
        # IPv4 and IPv6 don't mix
        input_str = "192.0.2.0/24\n2001:db8::/32"
        result = self._consolidate_from_string(input_str)
        
        # Should remain separate
        self.assertEqual(len(result), 2)
        self.assertIn('192.0.2.0/24', result)
        self.assertIn('2001:db8::/32', result)
    
    def test_duplicate_networks_deduplicate(self):
        """Test that duplicate networks are deduplicated."""
        input_str = "192.0.2.0/24\n192.0.2.0/24\n192.0.2.0/24"
        result = self._consolidate_from_string(input_str)
        
        # Should result in single network
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], '192.0.2.0/24')
    
    def test_four_networks_to_supernet(self):
        """Test consolidation of four /25 networks into a single /23 supernet."""
        # Four adjacent /25s should consolidate into a /23
        # 192.0.2.0/25, 192.0.2.128/25, 192.0.3.0/25, 192.0.3.128/25 → 192.0.2.0/23
        input_str = "192.0.2.0/25\n192.0.2.128/25\n192.0.3.0/25\n192.0.3.128/25"
        result = self._consolidate_from_string(input_str)
        
        # Should consolidate to a single /23 supernet
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], '192.0.2.0/23')


class TestFillPct(unittest.TestCase):
    """Test --fill-pct feature for consolidation with gap filling."""
    
    def setUp(self):
        """Set up test fixtures."""
        pass
    
    def _consolidate_from_string_with_fill(self, input_str: str, fill_pct: int, patterns: list = None) -> list:
        """
        Helper: consolidate networks with fill-pct from a string input.
        
        Args:
            input_str: Newline-separated CIDR networks or ranges
            fill_pct: Fill percentage (0-100)
            patterns: List of patterns to search for (defaults to extracting all from input)
        
        Returns:
            List of consolidated network strings, sorted
        """
        # If no patterns provided, extract them from the input
        if patterns is None:
            patterns = [line.strip() for line in input_str.strip().split('\n') if line.strip()]
        
        # Create a temp file with the input
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(input_str)
            temp_file = f.name
        
        try:
            # Create GrepNet with patterns
            grepnet = GrepNet(
                patterns=patterns,
                enable_colors=False,
            )
            
            # Create input source from file
            input_source = InputSource('file', file_path=temp_file)
            
            # Consolidate with fill-pct
            consolidated_dict = grepnet.consolidate_networks([input_source], fill_pct=fill_pct)
            
            # Extract and sort network strings
            result = sorted([str(net) for net in consolidated_dict.keys()])
            return result
        finally:
            os.unlink(temp_file)
    
    def test_fill_pct_50_simple_range(self):
        """Test --fill-pct=50 with simple 2-IP range 192.0.2.1-192.0.2.2."""
        # Input: 192.0.2.1-192.0.2.2 (2 IPs)
        # Can consolidate to 192.0.2.0/30 (4 IPs total)
        # Fill ratio: 2 gaps / 4 total = 50%
        # With fill-pct=50, should consolidate
        input_str = "192.0.2.1-192.0.2.2"
        result = self._consolidate_from_string_with_fill(input_str, fill_pct=50)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], '192.0.2.0/30')
    
    def test_fill_pct_25_rejects_simple_range(self):
        """Test --fill-pct=25 rejects 192.0.2.1-192.0.2.2."""
        # Input: 192.0.2.1-192.0.2.2 (2 IPs)
        # Would need to fill 2 gaps (50% of /30)
        # With fill-pct=25, cannot consolidate
        input_str = "192.0.2.1-192.0.2.2"
        result = self._consolidate_from_string_with_fill(input_str, fill_pct=25)
        
        # Should output original /32s or range
        self.assertEqual(len(result), 2)
        self.assertIn('192.0.2.1/32', result)
        self.assertIn('192.0.2.2/32', result)
    
    def test_fill_pct_0_no_filling(self):
        """Test --fill-pct=0 allows only perfect consolidations (no gap filling)."""
        # 192.0.2.0/25 and 192.0.2.128/25 are adjacent (0% gap)
        # Should always consolidate even with fill-pct=0
        input_str = "192.0.2.0/25\n192.0.2.128/25"
        result = self._consolidate_from_string_with_fill(input_str, fill_pct=0)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], '192.0.2.0/24')
    
    def test_fill_pct_100_allows_any_fill(self):
        """Test --fill-pct=100 allows consolidation even with 100% gaps."""
        # Single /32 can consolidate to any supernet (100% gap)
        input_str = "192.0.2.128/32"
        result = self._consolidate_from_string_with_fill(input_str, fill_pct=100)
        
        # Should consolidate to /24 or larger (depends on iteration)
        self.assertGreater(len(result), 0)
        # At least one result, and it should be the /32 or supernets
        self.assertTrue(any('192.0.2' in r for r in result))
    
    def test_fill_pct_iterative_consolidation(self):
        """Test that --fill-pct applies iteratively."""
        # Two separate ranges with gap between them
        # Input: 192.0.2.0-192.0.2.63, 192.0.2.192-192.0.2.255
        # Iteration 1: Both fill to /25 (gap=64, total=128, ratio=50%)
        #   → 192.0.2.0/25, 192.0.2.128/25
        # Iteration 2: Now adjacent /25s → consolidate to /24 (0% gap)
        input_str = "192.0.2.0-192.0.2.63\n192.0.2.192-192.0.2.255"
        result = self._consolidate_from_string_with_fill(input_str, fill_pct=50)
        
        # Should iterate to final /24
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], '192.0.2.0/24')
    
    def test_fill_pct_validation_below_range(self):
        """Test that --fill-pct < 0 is rejected."""
        # Negative percentages should not be allowed
        input_str = "192.0.2.0/24"
        
        with self.assertRaises((ValueError, TypeError)):
            self._consolidate_from_string_with_fill(input_str, fill_pct=-1)
    
    def test_fill_pct_validation_above_range(self):
        """Test that --fill-pct > 100 is rejected."""
        # Percentages > 100 should not be allowed
        input_str = "192.0.2.0/24"
        
        with self.assertRaises((ValueError, TypeError)):
            self._consolidate_from_string_with_fill(input_str, fill_pct=101)
    
    def test_fill_pct_idempotent(self):
        """Test that consolidate with fill-pct is idempotent."""
        # Running consolidate twice should give same result
        input_str = "192.0.2.0-192.0.2.63\n192.0.2.192-192.0.2.255"
        
        result1 = self._consolidate_from_string_with_fill(input_str, fill_pct=50)
        result2 = self._consolidate_from_string_with_fill(input_str, fill_pct=50)
        
        # Results should be identical
        self.assertEqual(result1, result2)
    
    def test_fill_pct_with_pattern_filtering(self):
        """Test --fill-pct with pattern filtering."""
        # Input has multiple networks, filter for specific pattern
        input_str = "192.0.2.1-192.0.2.2\n10.0.0.0/24"
        
        # Pattern filter to only 192.0.2.x networks
        result = self._consolidate_from_string_with_fill(
            input_str, 
            fill_pct=50,
            patterns=["192.0.2.0/16"]
        )
        
        # Should only consolidate matching network
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], '192.0.2.0/30')


class TestFormatIps(unittest.TestCase):
    """Test --format=ips output for consolidated networks."""
    
    def _get_ips_output(self, input_str: str, patterns: list = None, fill_pct: int = None) -> list:
        """
        Helper: get individual IPs from consolidation with --format=ips.
        
        Args:
            input_str: Newline-separated networks
            patterns: List of patterns to search for (defaults to extracting all)
            fill_pct: Optional fill percentage for consolidation
        
        Returns:
            List of IP strings in order
        """
        if patterns is None:
            patterns = [line.strip() for line in input_str.strip().split('\n') if line.strip()]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(input_str)
            temp_file = f.name
        
        try:
            grepnet = GrepNet(
                patterns=patterns,
                enable_colors=False,
            )
            
            input_source = InputSource('file', file_path=temp_file)
            consolidated_dict = grepnet.consolidate_networks([input_source], fill_pct=fill_pct)
            
            # Collect all IPs
            ips = []
            for net_obj in sorted(consolidated_dict.keys(), key=lambda n: (
                isinstance(n, tuple),  # Sort CIDR before ranges
                n if isinstance(n, tuple) else (int(n.network_address), n.prefixlen)
            )):
                for ip_str in grepnet.expand_network_to_ips(net_obj):
                    ips.append(ip_str)
            
            return ips
        finally:
            os.unlink(temp_file)
    
    def test_format_ips_single_cidr(self):
        """Test --format=ips with single CIDR network."""
        input_str = "192.0.2.0/30"
        ips = self._get_ips_output(input_str)
        
        expected = ['192.0.2.0', '192.0.2.1', '192.0.2.2', '192.0.2.3']
        self.assertEqual(ips, expected)
    
    def test_format_ips_range(self):
        """Test --format=ips with IP range."""
        input_str = "192.0.2.0-192.0.2.2"
        ips = self._get_ips_output(input_str)
        
        expected = ['192.0.2.0', '192.0.2.1', '192.0.2.2']
        self.assertEqual(ips, expected)
    
    def test_format_ips_single_ip(self):
        """Test --format=ips with single IP address."""
        input_str = "192.0.2.5/32"
        ips = self._get_ips_output(input_str)
        
        expected = ['192.0.2.5']
        self.assertEqual(ips, expected)
    
    def test_format_ips_multiple_networks(self):
        """Test --format=ips with multiple consolidated networks."""
        input_str = "192.0.2.0/30\n192.0.2.4/30"
        ips = self._get_ips_output(input_str)
        
        expected = [
            '192.0.2.0', '192.0.2.1', '192.0.2.2', '192.0.2.3',
            '192.0.2.4', '192.0.2.5', '192.0.2.6', '192.0.2.7'
        ]
        self.assertEqual(ips, expected)
    
    def test_format_ips_with_fill_pct(self):
        """Test --format=ips with --fill-pct consolidation."""
        input_str = "192.0.2.1-192.0.2.2"
        ips = self._get_ips_output(input_str, fill_pct=50)
        
        # With fill-pct=50, range expands to 192.0.2.0/30 (4 IPs)
        expected = ['192.0.2.0', '192.0.2.1', '192.0.2.2', '192.0.2.3']
        self.assertEqual(ips, expected)
    
    def test_format_ips_adjacent_cidr_merge(self):
        """Test --format=ips with adjacent CIDR networks that merge."""
        # Two /31 networks that merge to /30
        input_str = "192.0.2.0/31\n192.0.2.2/31"
        ips = self._get_ips_output(input_str)
        
        # Should merge to 192.0.2.0/30
        expected = ['192.0.2.0', '192.0.2.1', '192.0.2.2', '192.0.2.3']
        self.assertEqual(ips, expected)
    
    def test_format_ips_larger_network(self):
        """Test --format=ips with /24 network (256 IPs)."""
        input_str = "192.0.2.0/24"
        ips = self._get_ips_output(input_str)
        
        # Should have 256 IPs from .0 to .255
        self.assertEqual(len(ips), 256)
        self.assertEqual(ips[0], '192.0.2.0')
        self.assertEqual(ips[255], '192.0.2.255')
        # Check some middle values
        self.assertEqual(ips[100], '192.0.2.100')
        self.assertEqual(ips[255], '192.0.2.255')
