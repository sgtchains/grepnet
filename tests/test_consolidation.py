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


if __name__ == '__main__':
    unittest.main()
