"""
Test suite for strict exclusion behaviors: subset-strict and superset-strict.

Tests the new strict variants of subset/superset that exclude exact equality matches.
"""

import unittest
import subprocess
from pathlib import Path


class TestStrictExclusionBehaviors(unittest.TestCase):
    """Test strict exclusion behaviors: subset-strict and superset-strict."""
    
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


class TestSubsetStrictBehavior(TestStrictExclusionBehaviors):
    """Test subset-strict behavior: exclude only strict subsets, not equality."""
    
    def test_subset_strict_excludes_strict_subset_only(self):
        """Test that subset-strict excludes only strict subsets, not exact matches."""
        # Exclude: 192.0.0.0/16
        # Networks: 10.0.0.0/8, 192.0.0.0/16 (exact match), 192.0.2.0/24 (strict subset)
        stdout, stderr, rc = self.run_grepnet(
            '--extract',
            '--exclude-cidr=192.0.0.0/16',
            '--exclude-cidr-behaviour=subset-strict',
            stdin_data='10.0.0.0/8\n192.0.0.0/16\n192.0.2.0/24'
        )
        
        self.assertEqual(rc, 0)
        lines = [line.strip() for line in stdout.strip().split('\n') if line.strip()]
        
        # Should keep 10.0.0.0/8 (not subset) and 192.0.0.0/16 (exact match)
        # Should exclude 192.0.2.0/24 (strict subset)
        self.assertIn('10.0.0.0/8', lines)
        self.assertIn('192.0.0.0/16', lines)
        self.assertNotIn('192.0.2.0/24', lines)
    
    def test_subset_strict_vs_subset(self):
        """Compare subset-strict with regular subset behavior."""
        networks = '10.0.0.0/8\n192.0.0.0/16\n192.0.2.0/24\n192.0.2.0/25'
        exclude = '192.0.0.0/16'
        
        # Regular subset (includes equality)
        stdout_subset, _, _ = self.run_grepnet(
            '--extract',
            f'--exclude-cidr={exclude}',
            '--exclude-cidr-behaviour=subset',
            stdin_data=networks
        )
        
        # Strict subset (excludes equality)
        stdout_strict, _, _ = self.run_grepnet(
            '--extract',
            f'--exclude-cidr={exclude}',
            '--exclude-cidr-behaviour=subset-strict',
            stdin_data=networks
        )
        
        subset_lines = set(stdout_subset.strip().split('\n'))
        strict_lines = set(stdout_strict.strip().split('\n'))
        
        # subset-strict should have one more line: 192.0.0.0/16
        self.assertEqual(len(strict_lines), len(subset_lines) + 1)
        self.assertIn('192.0.0.0/16', strict_lines)
        self.assertNotIn('192.0.0.0/16', subset_lines)
    
    def test_subset_strict_exact_match_not_excluded(self):
        """Test that subset-strict does not exclude exact match."""
        stdout, stderr, rc = self.run_grepnet(
            '--extract',
            '--exclude-cidr=192.0.2.0/24',
            '--exclude-cidr-behaviour=subset-strict',
            stdin_data='192.0.2.0/24'
        )
        
        # Exact match should NOT be excluded with subset-strict
        self.assertEqual(rc, 0)
        self.assertIn('192.0.2.0/24', stdout)
    
    def test_subset_strict_larger_network_not_excluded(self):
        """Test that subset-strict does not exclude larger networks."""
        stdout, stderr, rc = self.run_grepnet(
            '--extract',
            '--exclude-cidr=192.0.2.0/24',
            '--exclude-cidr-behaviour=subset-strict',
            stdin_data='192.0.0.0/16'
        )
        
        # Larger network should not be excluded
        self.assertEqual(rc, 0)
        self.assertIn('192.0.0.0/16', stdout)
    
    def test_subset_strict_multiple_exclusions(self):
        """Test subset-strict with multiple exclusion networks."""
        stdout, stderr, rc = self.run_grepnet(
            '--extract',
            '--exclude-cidr=192.0.0.0/16',
            '--exclude-cidr=10.0.0.0/8',
            '--exclude-cidr-behaviour=subset-strict',
            stdin_data='10.0.0.0/8\n10.0.1.0/24\n192.0.0.0/16\n192.0.2.0/24'
        )
        
        self.assertEqual(rc, 0)
        lines = set(stdout.strip().split('\n'))
        
        # Exact matches should be kept
        self.assertIn('10.0.0.0/8', lines)
        self.assertIn('192.0.0.0/16', lines)
        # Strict subsets should be excluded
        self.assertNotIn('10.0.1.0/24', lines)
        self.assertNotIn('192.0.2.0/24', lines)


class TestSupersetStrictBehavior(TestStrictExclusionBehaviors):
    """Test superset-strict behavior: exclude only strict supersets, not equality."""
    
    def test_superset_strict_excludes_strict_superset_only(self):
        """Test that superset-strict excludes only strict supersets, not exact matches."""
        # Exclude: 192.0.2.0/24
        # Networks: 192.0.0.0/16 (strict superset), 192.0.2.0/24 (exact match), 192.0.2.0/25 (strict subset)
        stdout, stderr, rc = self.run_grepnet(
            '--extract',
            '--exclude-cidr=192.0.2.0/24',
            '--exclude-cidr-behaviour=superset-strict',
            stdin_data='192.0.0.0/16\n192.0.2.0/24\n192.0.2.0/25'
        )
        
        self.assertEqual(rc, 0)
        lines = set(line.strip() for line in stdout.strip().split('\n') if line.strip())
        
        # Should keep 192.0.2.0/24 (exact match) and 192.0.2.0/25 (not superset)
        # Should exclude 192.0.0.0/16 (strict superset)
        self.assertIn('192.0.2.0/24', lines)
        self.assertIn('192.0.2.0/25', lines)
        self.assertNotIn('192.0.0.0/16', lines)
    
    def test_superset_strict_vs_superset(self):
        """Compare superset-strict with regular superset behavior."""
        networks = '10.0.0.0/8\n192.0.0.0/16\n192.0.2.0/24\n192.0.2.0/25'
        exclude = '192.0.2.0/24'
        
        # Regular superset (includes equality)
        stdout_superset, _, _ = self.run_grepnet(
            '--extract',
            f'--exclude-cidr={exclude}',
            '--exclude-cidr-behaviour=superset',
            stdin_data=networks
        )
        
        # Strict superset (excludes equality)
        stdout_strict, _, _ = self.run_grepnet(
            '--extract',
            f'--exclude-cidr={exclude}',
            '--exclude-cidr-behaviour=superset-strict',
            stdin_data=networks
        )
        
        superset_lines = set(line.strip() for line in stdout_superset.strip().split('\n') if line.strip())
        strict_lines = set(line.strip() for line in stdout_strict.strip().split('\n') if line.strip())
        
        # superset-strict should have one more line: 192.0.2.0/24
        self.assertEqual(len(strict_lines), len(superset_lines) + 1)
        self.assertIn('192.0.2.0/24', strict_lines)
        self.assertNotIn('192.0.2.0/24', superset_lines)
    
    def test_superset_strict_exact_match_not_excluded(self):
        """Test that superset-strict does not exclude exact match."""
        stdout, stderr, rc = self.run_grepnet(
            '--extract',
            '--exclude-cidr=192.0.2.0/24',
            '--exclude-cidr-behaviour=superset-strict',
            stdin_data='192.0.2.0/24'
        )
        
        # Exact match should NOT be excluded with superset-strict
        self.assertEqual(rc, 0)
        self.assertIn('192.0.2.0/24', stdout)
    
    def test_superset_strict_smaller_network_not_excluded(self):
        """Test that superset-strict does not exclude smaller networks."""
        stdout, stderr, rc = self.run_grepnet(
            '--extract',
            '--exclude-cidr=192.0.0.0/16',
            '--exclude-cidr-behaviour=superset-strict',
            stdin_data='192.0.2.0/24'
        )
        
        # Smaller network should not be excluded
        self.assertEqual(rc, 0)
        self.assertIn('192.0.2.0/24', stdout)
    
    def test_superset_strict_multiple_exclusions(self):
        """Test superset-strict with multiple exclusion networks."""
        stdout, stderr, rc = self.run_grepnet(
            '--extract',
            '--exclude-cidr=192.0.2.0/24',
            '--exclude-cidr=10.0.1.0/24',
            '--exclude-cidr-behaviour=superset-strict',
            stdin_data='10.0.0.0/8\n10.0.1.0/24\n192.0.0.0/16\n192.0.2.0/24'
        )
        
        self.assertEqual(rc, 0)
        lines = set(line.strip() for line in stdout.strip().split('\n') if line.strip())
        
        # Exact matches should be kept
        self.assertIn('10.0.1.0/24', lines)
        self.assertIn('192.0.2.0/24', lines)
        # Strict supersets should be excluded
        self.assertNotIn('10.0.0.0/8', lines)
        self.assertNotIn('192.0.0.0/16', lines)


class TestComparisonWithNonStrictVariants(TestStrictExclusionBehaviors):
    """Compare strict variants with their non-strict counterparts."""
    
    def test_subset_vs_subset_strict_difference(self):
        """Verify the key difference between subset and subset-strict."""
        networks = '192.0.0.0/16\n192.0.2.0/24'
        exclude = '192.0.0.0/16'
        
        # subset: keeps 192.0.0.0/16 if it's NOT a subset (but it is, so exclude it)
        stdout_subset, _, _ = self.run_grepnet(
            '--extract',
            f'--exclude-cidr={exclude}',
            '--exclude-cidr-behaviour=subset',
            stdin_data=networks
        )
        
        # subset-strict: keeps 192.0.0.0/16 because it's equal (not strict subset)
        stdout_strict, _, _ = self.run_grepnet(
            '--extract',
            f'--exclude-cidr={exclude}',
            '--exclude-cidr-behaviour=subset-strict',
            stdin_data=networks
        )
        
        # subset should have no 192.0.0.0/16
        self.assertNotIn('192.0.0.0/16', stdout_subset)
        # subset-strict should have 192.0.0.0/16
        self.assertIn('192.0.0.0/16', stdout_strict)
    
    def test_superset_vs_superset_strict_difference(self):
        """Verify the key difference between superset and superset-strict."""
        networks = '192.0.2.0/24\n192.0.0.0/16'
        exclude = '192.0.2.0/24'
        
        # superset: exclude both (one is equal, one is superset)
        stdout_superset, _, _ = self.run_grepnet(
            '--extract',
            f'--exclude-cidr={exclude}',
            '--exclude-cidr-behaviour=superset',
            stdin_data=networks
        )
        
        # superset-strict: keep 192.0.2.0/24 because it's equal (not strict superset)
        stdout_strict, _, _ = self.run_grepnet(
            '--extract',
            f'--exclude-cidr={exclude}',
            '--exclude-cidr-behaviour=superset-strict',
            stdin_data=networks
        )
        
        # superset should exclude both
        self.assertNotIn('192.0.2.0/24', stdout_superset)
        self.assertNotIn('192.0.0.0/16', stdout_superset)
        # superset-strict should keep 192.0.2.0/24
        self.assertIn('192.0.2.0/24', stdout_strict)
        self.assertNotIn('192.0.0.0/16', stdout_strict)
    
    def test_all_behaviors_summary(self):
        """Test all exclusion behaviors with same input for comparison."""
        networks = '192.0.0.0/16\n192.0.2.0/24\n192.0.3.0/25'
        exclude = '192.0.2.0/24'
        
        behaviors = ['subset', 'subset-strict', 'superset', 'superset-strict', 'equals', 'related']
        results = {}
        
        for behavior in behaviors:
            stdout, _, _ = self.run_grepnet(
                '--extract',
                f'--exclude-cidr={exclude}',
                f'--exclude-cidr-behaviour={behavior}',
                stdin_data=networks
            )
            results[behavior] = set(line.strip() for line in stdout.strip().split('\n') if line.strip())
        
        # subset: excludes 192.0.2.0/24 (exact match)
        self.assertEqual(results['subset'], {'192.0.0.0/16', '192.0.3.0/25'})
        
        # subset-strict: excludes nothing (no strict subsets of 192.0.2.0/24 in the list)
        self.assertEqual(results['subset-strict'], {'192.0.0.0/16', '192.0.2.0/24', '192.0.3.0/25'})
        
        # superset: excludes 192.0.0.0/16 and 192.0.2.0/24
        self.assertEqual(results['superset'], {'192.0.3.0/25'})
        
        # superset-strict: excludes only 192.0.0.0/16 (strict superset, not equal)
        self.assertEqual(results['superset-strict'], {'192.0.2.0/24', '192.0.3.0/25'})
        
        # equals: excludes only exact match
        self.assertEqual(results['equals'], {'192.0.0.0/16', '192.0.3.0/25'})
        
        # related: excludes everything that overlaps or has subset/superset relationship
        self.assertEqual(results['related'], {'192.0.3.0/25'})


class TestStrictWithIPv6(TestStrictExclusionBehaviors):
    """Test strict behaviors with IPv6 addresses."""
    
    def test_subset_strict_ipv6(self):
        """Test subset-strict with IPv6 CIDR blocks."""
        stdout, stderr, rc = self.run_grepnet(
            '--extract',
            '--exclude-cidr=2001:db8::/32',
            '--exclude-cidr-behaviour=subset-strict',
            stdin_data='2001:db8::/32\n2001:db8:1::/48\n2001:db8:1:1::/64'
        )
        
        self.assertEqual(rc, 0)
        lines = set(line.strip() for line in stdout.strip().split('\n') if line.strip())
        
        # Exact match should be kept
        self.assertIn('2001:db8::/32', lines)
        # Strict subsets should be excluded
        self.assertNotIn('2001:db8:1::/48', lines)
        self.assertNotIn('2001:db8:1:1::/64', lines)
    
    def test_superset_strict_ipv6(self):
        """Test superset-strict with IPv6 CIDR blocks."""
        stdout, stderr, rc = self.run_grepnet(
            '--extract',
            '--exclude-cidr=2001:db8:1::/48',
            '--exclude-cidr-behaviour=superset-strict',
            stdin_data='2001:db8::/32\n2001:db8:1::/48\n2001:db8:1:1::/64'
        )
        
        self.assertEqual(rc, 0)
        lines = set(line.strip() for line in stdout.strip().split('\n') if line.strip())
        
        # Exact match and strict subset should be kept
        self.assertIn('2001:db8:1::/48', lines)
        self.assertIn('2001:db8:1:1::/64', lines)
        # Strict supersets should be excluded
        self.assertNotIn('2001:db8::/32', lines)


if __name__ == '__main__':
    unittest.main()
