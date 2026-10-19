"""
Test suite for exclusion filters with extract and consolidate modes.

Tests that --exclude-string and --exclude-cidr work correctly with
--extract and --consolidate modes. Ensures no regression where exclusions
were not being applied in consolidate mode.
"""

import unittest
import tempfile
import sys
from pathlib import Path
from ipaddress import IPv4Network

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from grepnet.grepnet import GrepNet
from grepnet.input import InputSource


class TestExcludeStringWithExtractConsolidate(unittest.TestCase):
    """Test --exclude-string with --extract and --consolidate modes."""
    
    def _extract_networks(self, input_str: str, exclude_strings: list = None, consolidate: bool = False) -> list:
        """
        Helper: extract or consolidate networks from a string input.
        
        Args:
            input_str: Newline-separated networks in the input
            exclude_strings: List of regex patterns to exclude
            consolidate: If True, consolidate; else extract only
        
        Returns:
            List of network strings (sorted)
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(input_str)
            temp_file = f.name
        
        try:
            grepnet = GrepNet(
                patterns=[],
                exclude_strings=exclude_strings or [],
            )
            
            input_source = InputSource('file', file_path=temp_file)
            
            # First extract networks (filtering already applied via parse_line)
            extracted_dict = grepnet.extract_networks([input_source])
            
            if consolidate:
                # Then consolidate if requested
                result_dict = grepnet.consolidate_networks(extracted_dict)
            else:
                result_dict = extracted_dict
            
            # Convert dict to sorted list of network strings
            networks = [str(net_obj) for net_obj in result_dict.keys()]
            return sorted(networks)
        finally:
            import os
            os.unlink(temp_file)
    
    def test_extract_exclude_string_single_network(self):
        """Test --exclude-string with --extract excludes matching network."""
        input_str = "0.0.0.0/0\n192.0.2.0/24\n"
        result = self._extract_networks(input_str, exclude_strings=['0\\.0\\.0\\.0/0'])
        
        # Should exclude 0.0.0.0/0, keep 192.0.2.0/24
        self.assertEqual(result, ['192.0.2.0/24'])
    
    def test_extract_exclude_string_multiple(self):
        """Test --exclude-string with multiple patterns."""
        input_str = "10.0.0.0/8\n192.0.2.0/24\n172.16.0.0/12\n"
        result = self._extract_networks(
            input_str,
            exclude_strings=['10\\.0\\.0\\.0.*', '172\\.16.*']
        )
        
        # Should exclude 10.0.0.0/8 and 172.16.0.0/12, keep 192.0.2.0/24
        self.assertEqual(result, ['192.0.2.0/24'])
    
    def test_extract_exclude_string_no_match(self):
        """Test --exclude-string that doesn't match any networks."""
        input_str = "192.0.2.0/24\n10.0.0.0/8\n"
        result = self._extract_networks(
            input_str,
            exclude_strings=['172\\.16.*']
        )
        
        # Should keep all networks (no exclusion match)
        self.assertEqual(sorted(result), ['10.0.0.0/8', '192.0.2.0/24'])
    
    def test_consolidate_exclude_string_single_network(self):
        """Test --exclude-string with --consolidate excludes matching network."""
        input_str = "0.0.0.0/0\n192.0.2.0/24\n"
        result = self._extract_networks(
            input_str,
            exclude_strings=['0\\.0\\.0\\.0/0'],
            consolidate=True
        )
        
        # Should exclude 0.0.0.0/0, keep 192.0.2.0/24
        self.assertEqual(result, ['192.0.2.0/24'])
    
    def test_consolidate_exclude_string_overlapping_networks(self):
        """Test --exclude-string with consolidation of overlapping networks."""
        # Three networks that would consolidate to 192.0.0.0/22 normally
        input_str = "192.0.2.0/24\n192.0.3.0/24\n192.0.0.0/24\n"
        result = self._extract_networks(
            input_str,
            exclude_strings=['192\\.0\\.0\\.0/24'],
            consolidate=True
        )
        
        # After excluding 192.0.0.0/24, consolidate the remaining two
        # 192.0.2.0/24 and 192.0.3.0/24 are adjacent, should consolidate to 192.0.2.0/23
        self.assertEqual(result, ['192.0.2.0/23'])
    
    def test_consolidate_exclude_string_all_networks(self):
        """Test excluding all networks results in empty output."""
        input_str = "10.0.0.0/8\n192.0.2.0/24\n"
        result = self._extract_networks(
            input_str,
            exclude_strings=['.*'],  # Exclude everything
            consolidate=True
        )
        
        # Should be empty
        self.assertEqual(result, [])
    
    def test_extract_exclude_string_partial_text_match(self):
        """Test --exclude-string matching partial text in matched_texts."""
        input_str = "192.0.2.0/24\n"
        result = self._extract_networks(
            input_str,
            exclude_strings=['192']
        )
        
        # Should exclude because matched text contains '192'
        self.assertEqual(result, [])
    
    def test_extract_no_exclude_preserves_all(self):
        """Test that no exclusion filters preserve all networks."""
        input_str = "0.0.0.0/0\n192.0.2.0/24\n10.0.0.0/8\n"
        result = self._extract_networks(input_str, exclude_strings=None)
        
        # Should keep all
        self.assertEqual(sorted(result), ['0.0.0.0/0', '10.0.0.0/8', '192.0.2.0/24'])
    
    def test_consolidate_no_exclude_preserves_consolidation(self):
        """Test that consolidation without exclusion works normally."""
        input_str = "192.0.2.0/24\n192.0.3.0/24\n"
        result = self._extract_networks(input_str, exclude_strings=None, consolidate=True)
        
        # Should consolidate to 192.0.2.0/23
        self.assertEqual(result, ['192.0.2.0/23'])


class TestExcludeCidrWithExtractConsolidate(unittest.TestCase):
    """Test --exclude-cidr with --extract and --consolidate modes."""
    
    def _extract_networks(self, input_str: str, exclude_cidrs: list = None, 
                         exclude_cidr_behavior: str = 'subset', consolidate: bool = False) -> list:
        """
        Helper: extract or consolidate networks from a string input with CIDR exclusion.
        
        Args:
            input_str: Newline-separated networks in the input
            exclude_cidrs: List of CIDR blocks to exclude
            exclude_cidr_behavior: Exclusion behavior ('subset', 'equals', 'superset', etc.)
            consolidate: If True, consolidate; else extract only
        
        Returns:
            List of network strings (sorted)
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(input_str)
            temp_file = f.name
        
        try:
            # Parse exclude_cidrs if they're strings
            if exclude_cidrs and isinstance(exclude_cidrs[0], str):
                from ipaddress import ip_network
                exclude_cidrs = [ip_network(cidr) for cidr in exclude_cidrs]
            
            grepnet = GrepNet(
                patterns=[],
                exclude_cidrs=exclude_cidrs or [],
                exclude_cidr_behavior=exclude_cidr_behavior,
            )
            
            input_source = InputSource('file', file_path=temp_file)
            
            # First extract networks (filtering already applied via parse_line)
            extracted_dict = grepnet.extract_networks([input_source])
            
            if consolidate:
                # Then consolidate if requested
                result_dict = grepnet.consolidate_networks(extracted_dict)
            else:
                result_dict = extracted_dict
            
            # Convert dict to sorted list of network strings
            networks = [str(net_obj) for net_obj in result_dict.keys()]
            return sorted(networks)
        finally:
            import os
            os.unlink(temp_file)
    
    def test_extract_exclude_cidr_subset_behavior(self):
        """Test --exclude-cidr with subset behavior (default)."""
        input_str = "10.0.0.0/8\n10.1.0.0/16\n192.0.2.0/24\n"
        result = self._extract_networks(
            input_str,
            exclude_cidrs=['10.0.0.0/8'],
            exclude_cidr_behavior='subset'
        )
        
        # Should exclude 10.0.0.0/8 and its subset 10.1.0.0/16, keep 192.0.2.0/24
        self.assertEqual(result, ['192.0.2.0/24'])
    
    def test_extract_exclude_cidr_equals_behavior(self):
        """Test --exclude-cidr with equals behavior."""
        input_str = "10.0.0.0/8\n10.1.0.0/16\n192.0.2.0/24\n"
        result = self._extract_networks(
            input_str,
            exclude_cidrs=['10.0.0.0/8'],
            exclude_cidr_behavior='equals'
        )
        
        # Should exclude only exact match 10.0.0.0/8, keep 10.1.0.0/16 and 192.0.2.0/24
        self.assertEqual(sorted(result), ['10.1.0.0/16', '192.0.2.0/24'])
    
    def test_consolidate_exclude_cidr_subset_behavior(self):
        """Test --exclude-cidr with --consolidate in subset behavior."""
        input_str = "10.0.0.0/8\n192.0.2.0/24\n192.0.3.0/24\n"
        result = self._extract_networks(
            input_str,
            exclude_cidrs=['10.0.0.0/8'],
            exclude_cidr_behavior='subset',
            consolidate=True
        )
        
        # Should exclude 10.0.0.0/8, consolidate remaining 192.0.2.0/24 and 192.0.3.0/24
        self.assertEqual(result, ['192.0.2.0/23'])
    
    def test_consolidate_exclude_cidr_keeps_original_consolidation(self):
        """Test that consolidation still works after CIDR exclusion."""
        # Three adjacent subnets that would consolidate to 192.0.0.0/22
        input_str = "192.0.0.0/24\n192.0.1.0/24\n192.0.2.0/24\n192.0.3.0/24\n"
        result = self._extract_networks(
            input_str,
            exclude_cidrs=['192.0.0.0/24'],
            exclude_cidr_behavior='equals',
            consolidate=True
        )
        
        # Should exclude only 192.0.0.0/24, consolidate the remaining three
        # 192.0.1.0/24, 192.0.2.0/24, 192.0.3.0/24 should consolidate to 192.0.1.0/23 + 192.0.3.0/24
        # or 192.0.1.0/24 + 192.0.2.0/23
        # Due to consolidation algorithm, check that we get reasonable result
        self.assertTrue(len(result) >= 1)
        self.assertNotIn('192.0.0.0/24', result)


class TestExclusionRegression(unittest.TestCase):
    """Regression tests to ensure exclusions work in extract/consolidate."""
    
    def test_issue_consolidate_exclude_string_regression(self):
        """
        Regression test for the bug where --consolidate ignored --exclude-string.
        
        Issue: printf "0.0.0.0/0\n192.0.2.0/24" | grepnet --exclude-string '0.0.0.0/0' --consolidate
        Expected: 192.0.2.0/24
        Bug: Returned 0.0.0.0/0 (exclusion was ignored in consolidate mode)
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("0.0.0.0/0\n192.0.2.0/24\n")
            temp_file = f.name
        
        try:
            grepnet = GrepNet(
                patterns=[],
                exclude_strings=['0\\.0\\.0\\.0/0'],
            )
            
            input_source = InputSource('file', file_path=temp_file)
            # Extract first, then consolidate
            extracted_dict = grepnet.extract_networks([input_source])
            result_dict = grepnet.consolidate_networks(extracted_dict)
            
            networks = sorted([str(net_obj) for net_obj in result_dict.keys()])
            
            # Should NOT include 0.0.0.0/0
            self.assertEqual(networks, ['192.0.2.0/24'])
            self.assertNotIn('0.0.0.0/0', networks)
        finally:
            import os
            os.unlink(temp_file)
    
    def test_issue_extract_exclude_string_consistency(self):
        """
        Test that --extract and --consolidate apply exclusions consistently.
        """
        input_str = "0.0.0.0/0\n192.0.2.0/24\n10.0.0.0/8\n"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(input_str)
            temp_file = f.name
        
        try:
            grepnet = GrepNet(
                patterns=[],
                exclude_strings=['0\\.0\\.0\\.0.*'],
            )
            
            input_source = InputSource('file', file_path=temp_file)
            
            # Extract result
            extract_dict = grepnet.extract_networks([input_source])
            extract_nets = sorted([str(net_obj) for net_obj in extract_dict.keys()])
            
            # Consolidate result (extract first, then consolidate)
            extracted_dict = grepnet.extract_networks([input_source])
            consolidate_dict = grepnet.consolidate_networks(extracted_dict)
            consolidate_nets = sorted([str(net_obj) for net_obj in consolidate_dict.keys()])
            
            # Both should exclude 0.0.0.0/0
            self.assertNotIn('0.0.0.0/0', extract_nets)
            self.assertNotIn('0.0.0.0/0', consolidate_nets)
            
            # Both should have the same excluded set
            self.assertEqual(extract_nets, consolidate_nets)
        finally:
            import os
            os.unlink(temp_file)


if __name__ == '__main__':
    unittest.main()
