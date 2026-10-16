"""
Test suite for --exclude-cidr-behavior option.

Tests the five exclusion behaviors: subset (default), superset, equals, related, and cut.
"""

import unittest
import subprocess
from pathlib import Path


class TestExcludeCidrBehaviour(unittest.TestCase):
    """Test --exclude-cidr-behavior option."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.grepnet_script = Path(__file__).parent.parent / 'grepnet'
    
    def run_grepnet(self, *args, stdin_data=None):
        """
        Run grepnet with given arguments.
        
        Returns:
            (stdout, stderr, returncode) tuple
        """
        cmd = [str(self.grepnet_script)] + list(args)
        result = subprocess.run(
            cmd,
            input=stdin_data,
            capture_output=True,
            text=True
        )
        return result.stdout, result.stderr, result.returncode


class TestCutBehaviour(TestExcludeCidrBehaviour):
    """Test cut behavior: carves out excluded network and returns remaining gaps."""
    
    def test_cut_basic_extraction(self):
        """Test cut behavior with basic extraction."""
        # Extract 192.0.2.0/24, cut out 192.0.2.0/30
        stdout, stderr, rc = self.run_grepnet(
            '--extract',
            '--exclude-cidr=192.0.2.0/30',
            '--exclude-cidr-behavior=cut',
            stdin_data='192.0.2.0/24'
        )
        
        self.assertEqual(rc, 0)
        lines = stdout.strip().split('\n')
        # Should have 6 networks (the gaps)
        self.assertEqual(len(lines), 6)
        self.assertIn('192.0.2.4/30', lines)
        self.assertIn('192.0.2.8/29', lines)
        self.assertIn('192.0.2.128/25', lines)
    
    def test_cut_different_position(self):
        """Test cut with exclude at different position."""
        # Extract 192.0.2.0/24, cut out 192.0.2.4/30
        stdout, stderr, rc = self.run_grepnet(
            '--extract',
            '--exclude-cidr=192.0.2.4/30',
            '--exclude-cidr-behavior=cut',
            stdin_data='192.0.2.0/24'
        )
        
        self.assertEqual(rc, 0)
        lines = stdout.strip().split('\n')
        self.assertEqual(len(lines), 6)
        self.assertIn('192.0.2.0/30', lines)
        self.assertIn('192.0.2.8/29', lines)
        self.assertIn('192.0.2.128/25', lines)
    
    def test_cut_full_network_excluded(self):
        """Test cut when entire network is excluded."""
        # Extract 192.0.2.0/24, cut out 192.0.2.0/24 (itself)
        stdout, stderr, rc = self.run_grepnet(
            '--extract',
            '--exclude-cidr=192.0.2.0/24',
            '--exclude-cidr-behavior=cut',
            stdin_data='192.0.2.0/24'
        )
        
        # No networks remain (the entire input is cut out)
        self.assertEqual(stdout.strip(), '')
    
    def test_cut_multiple_excludes(self):
        """Test cut with multiple exclude CIDRs."""
        # Extract 192.0.2.0/24, cut out both 192.0.2.0/30 and 192.0.2.64/26
        stdout, stderr, rc = self.run_grepnet(
            '--extract',
            '--exclude-cidr=192.0.2.0/30',
            '--exclude-cidr=192.0.2.64/26',
            '--exclude-cidr-behavior=cut',
            stdin_data='192.0.2.0/24'
        )
        
        self.assertEqual(rc, 0)
        lines = stdout.strip().split('\n')
        # Should not include the cut-out networks
        self.assertNotIn('192.0.2.0/30', lines)
        self.assertNotIn('192.0.2.64/26', lines)
        # But should have other gaps
        self.assertIn('192.0.2.4/30', lines)
        self.assertIn('192.0.2.128/25', lines)
    
    def test_cut_with_consolidate(self):
        """Test cut behavior with --consolidate."""
        stdout, stderr, rc = self.run_grepnet(
            '--consolidate',
            '--exclude-cidr=192.0.2.0/30',
            '--exclude-cidr-behavior=cut',
            stdin_data='192.0.2.0/25\n192.0.2.0/26'
        )
        
        self.assertEqual(rc, 0)
        lines = stdout.strip().split('\n')
        # Should have gaps from consolidated 192.0.2.0/25 with 192.0.2.0/30 removed
        self.assertIn('192.0.2.4/30', lines)
        self.assertIn('192.0.2.32/27', lines)
        self.assertIn('192.0.2.64/26', lines)
    
    def test_cut_requires_extract_or_consolidate(self):
        """Test that cut behavior errors without --extract or --consolidate."""
        stdout, stderr, rc = self.run_grepnet(
            '192.0.2.0/24',
            '--exclude-cidr-behavior=cut',
            stdin_data='192.0.2.1'
        )
        
        self.assertEqual(rc, 2)
        self.assertIn('--exclude-cidr-behavior=cut requires --extract or --consolidate', stderr)
    
    def test_cut_no_overlap_returns_original(self):
        """Test cut when exclude doesn't overlap with extracted network."""
        stdout, stderr, rc = self.run_grepnet(
            '--extract',
            '--exclude-cidr=10.0.0.0/8',
            '--exclude-cidr-behavior=cut',
            stdin_data='192.0.2.0/24'
        )
        
        self.assertEqual(rc, 0)
        lines = stdout.strip().split('\n')
        # Should return original network since exclude doesn't overlap
        self.assertEqual(lines[0], '192.0.2.0/24')


class TestSubsetBehaviour(TestExcludeCidrBehaviour):
    """Test subset behavior (default): exclude if file network is subset of exclude network."""
    
    def test_subset_default(self):
        """Test that subset is default behavior."""
        # Search for 0.0.0.0/0, exclude 192.0.0.0/16
        # 192.0.2.0/24 is subset of 192.0.0.0/16, should be excluded
        stdout, stderr, rc = self.run_grepnet(
            '0.0.0.0/0',
            '--exclude-cidr=192.0.0.0/16',
            stdin_data='192.0.2.0/24\n10.0.0.0/8'
        )
        
        # 192.0.2.0/24 should be excluded (it's a subset of 192.0.0.0/16)
        # 10.0.0.0/8 should match
        self.assertIn('10.0.0.0/8', stdout)
        self.assertNotIn('192.0.2.0/24', stdout)
    
    def test_subset_explicit(self):
        """Test explicit subset behavior."""
        stdout, stderr, rc = self.run_grepnet(
            '0.0.0.0/0',
            '--exclude-cidr-behavior=subset',
            '--exclude-cidr=192.0.0.0/16',
            stdin_data='192.0.2.0/24\n10.0.0.0/8'
        )
        
        self.assertIn('10.0.0.0/8', stdout)
        self.assertNotIn('192.0.2.0/24', stdout)


class TestSupersetBehaviour(TestExcludeCidrBehaviour):
    """Test superset behavior: exclude if file network is superset of exclude network."""
    
    def test_superset_excludes_larger_networks(self):
        """Test that superset excludes larger networks and equals."""
        # Search for 0.0.0.0/0, exclude 192.0.2.0/24
        # 192.0.0.0/16 is superset of 192.0.2.0/24, should be excluded
        # 192.0.2.0/24 equals exclude, should also be excluded  (by the ==check)
        stdout, stderr, rc = self.run_grepnet(
            '0.0.0.0/0',
            '--exclude-cidr-behavior=superset',
            '--exclude-cidr=192.0.2.0/24',
            stdin_data='192.0.0.0/16\n192.0.2.0/24\n10.0.0.0/8'
        )
        
        # 192.0.0.0/16 should be excluded (superset of 192.0.2.0/24)
        # 192.0.2.0/24 should be excluded (equals exclude CIDR)
        # 10.0.0.0/8 should not be excluded
        self.assertNotIn('192.0.0.0/16', stdout)
        self.assertNotIn('192.0.2.0/24', stdout)
        self.assertIn('10.0.0.0/8', stdout)


class TestEqualsBehaviour(TestExcludeCidrBehaviour):
    """Test equals behavior: exclude only exact matches."""
    
    def test_equals_exact_match_only(self):
        """Test that equals excludes only exact matches."""
        stdout, stderr, rc = self.run_grepnet(
            '192.0.2.0/24',
            '--exclude-cidr-behavior=equals',
            '--exclude-cidr=192.0.2.0/24',
            stdin_data='192.0.2.0/24\n192.0.2.0/25\n192.0.0.0/16'
        )
        
        # Only exact match should be excluded
        self.assertNotIn('192.0.2.0/24', stdout)
        self.assertIn('192.0.2.0/25', stdout)
        self.assertIn('192.0.0.0/16', stdout)


class TestRelatedBehaviour(TestExcludeCidrBehaviour):
    """Test related behavior: exclude if networks overlap or have subset/superset relationship."""
    
    def test_related_excludes_overlapping(self):
        """Test that related excludes overlapping networks."""
        stdout, stderr, rc = self.run_grepnet(
            '0.0.0.0/0',
            '--exclude-cidr-behavior=related',
            '--exclude-cidr=192.0.2.0/25',
            stdin_data='192.0.2.0/24\n192.0.2.0/25\n10.0.0.0/8'
        )
        
        # 192.0.2.0/24 should be excluded (contains 192.0.2.0/25)
        # 192.0.2.0/25 should be excluded (equals one of the related)
        # 10.0.0.0/8 should match
        self.assertNotIn('192.0.2.0/24', stdout)
        self.assertNotIn('192.0.2.0/25', stdout)
        self.assertIn('10.0.0.0/8', stdout)


if __name__ == '__main__':
    unittest.main()
