"""
Test suite for --parse-netmask=none regression fix.

Issue: When --parse-netmask=none was used, space-separated IP pairs that
could be netmask format (e.g., "0.0.0.0 255.255.255.0") were being incorrectly
skipped even when parse_bare_ip=True, preventing them from being parsed as
two separate bare IPs.

Fix: Only mark an IP as "not bare-ip" when:
1. It looks like a netmask/hostmask format AND
2. That parsing mode is actually enabled in the current context

Tests ensure that:
- Space-separated pairs are treated as netmask when --parse-netmask=both (default)
- Space-separated pairs are treated as two bare IPs when --parse-netmask=none
- Both modes work correctly with extract and consolidate
"""

import unittest
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from grepnet.parsing.network_parser import NetworkParser
from grepnet.grepnet import GrepNet
from grepnet.input import InputSource
from ipaddress import IPv4Network
import tempfile
import os


class TestParseNetmaskNoneRegression(unittest.TestCase):
    """Test space-separated IP pairs with --parse-netmask=none."""
    
    def test_space_separated_pair_with_netmask_enabled(self):
        """With --parse-netmask=both (default), space-separated pairs are netmask format."""
        parser = NetworkParser(parse_netmask='both', parse_bare_ip='both')
        
        # "0.0.0.0 255.255.255.0" should be parsed as netmask pair
        results = parser.parse_line('0.0.0.0 255.255.255.0', context='input')
        self.assertEqual(len(results), 1)
        # Should produce 0.0.0.0/24 (netmask format)
        self.assertEqual(results[0].network, IPv4Network('0.0.0.0/24'))
        self.assertEqual(results[0].format_type, 'subnet_mask')
    
    def test_space_separated_pair_with_netmask_disabled(self):
        """With --parse-netmask=none, space-separated pairs should parse as two bare IPs."""
        parser = NetworkParser(parse_netmask='none', parse_bare_ip='both')
        
        # "0.0.0.0 255.255.255.0" should parse as two bare IPs
        results = parser.parse_line('0.0.0.0 255.255.255.0', context='input')
        self.assertEqual(len(results), 2)
        
        # Each should be /32 (bare IP)
        networks = sorted([r.network for r in results], key=str)
        self.assertEqual(networks[0], IPv4Network('0.0.0.0/32'))
        self.assertEqual(networks[1], IPv4Network('255.255.255.0/32'))
        
        # Both should be marked as ip_only format
        for result in results:
            self.assertEqual(result.format_type, 'ip_only')
    
    def test_space_separated_pair_netmask_disabled_bare_ip_disabled(self):
        """With both --parse-netmask=none and --parse-bare-ip=none, nothing is extracted."""
        parser = NetworkParser(parse_netmask='none', parse_bare_ip='none')
        
        # "0.0.0.0 255.255.255.0" - neither netmask nor bare IP parsing enabled
        results = parser.parse_line('0.0.0.0 255.255.255.0', context='input')
        self.assertEqual(len(results), 0)
    
    def test_space_separated_pair_input_context_only(self):
        """With --parse-netmask=input, netmask should only work in input context."""
        parser = NetworkParser(parse_netmask='input', parse_bare_ip='both')
        
        # In input context: should parse as netmask
        results = parser.parse_line('0.0.0.0 255.255.255.0', context='input')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].network, IPv4Network('0.0.0.0/24'))
        
        # In pattern context: should parse as two bare IPs
        results = parser.parse_line('0.0.0.0 255.255.255.0', context='pattern')
        self.assertEqual(len(results), 2)
    
    def test_space_separated_pair_pattern_context_only(self):
        """With --parse-netmask=pattern, netmask should only work in pattern context."""
        parser = NetworkParser(parse_netmask='pattern', parse_bare_ip='both')
        
        # In pattern context: should parse as netmask
        results = parser.parse_line('0.0.0.0 255.255.255.0', context='pattern')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].network, IPv4Network('0.0.0.0/24'))
        
        # In input context: should parse as two bare IPs
        results = parser.parse_line('0.0.0.0 255.255.255.0', context='input')
        self.assertEqual(len(results), 2)
    
    def test_hostmask_disabled_similar_to_netmask(self):
        """With --parse-hostmask=none, hostmask pairs should parse as two bare IPs."""
        parser = NetworkParser(parse_hostmask='none', parse_bare_ip='both')
        
        # "192.0.2.1 0.0.0.255" is a valid hostmask pair
        # With hostmask disabled, should parse as two bare IPs
        results = parser.parse_line('192.0.2.1 0.0.0.255', context='input')
        self.assertEqual(len(results), 2)
        
        networks = sorted([r.network for r in results], key=str)
        self.assertEqual(networks[0], IPv4Network('0.0.0.255/32'))
        self.assertEqual(networks[1], IPv4Network('192.0.2.1/32'))


class TestParseNetmaskNoneExtractMode(unittest.TestCase):
    """Test --parse-netmask=none with extract mode."""
    
    def test_extract_with_netmask_enabled(self):
        """Extract with --parse-netmask=both should consolidate space-separated pairs."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write('0.0.0.0 255.255.255.0\n')
            f.flush()
            temp_file = f.name
        
        try:
            grepnet = GrepNet(
                patterns=['0.0.0.0/0'],
                parse_netmask='both',
                parse_bare_ip='both',
            )
            input_sources = [InputSource('file', file_path=temp_file)]
            networks_dict = grepnet.extract_networks(input_sources)
            
            # Should have one network: 0.0.0.0/24 (the netmask pair)
            self.assertEqual(len(networks_dict), 1)
            net = list(networks_dict.keys())[0]
            self.assertEqual(net, IPv4Network('0.0.0.0/24'))
        finally:
            os.unlink(temp_file)
    
    def test_extract_with_netmask_disabled(self):
        """Extract with --parse-netmask=none should get two bare IPs."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write('0.0.0.0 255.255.255.0\n')
            f.flush()
            temp_file = f.name
        
        try:
            grepnet = GrepNet(
                patterns=['0.0.0.0/0'],  # Matches both 0.0.0.0/32 and 255.255.255.0/32
                parse_netmask='none',
                parse_bare_ip='both',
            )
            input_sources = [InputSource('file', file_path=temp_file)]
            networks_dict = grepnet.extract_networks(input_sources)
            
            # Should have two networks: 0.0.0.0/32 and 255.255.255.0/32
            self.assertEqual(len(networks_dict), 2)
            networks = sorted([net for net in networks_dict.keys()], key=str)
            self.assertEqual(networks[0], IPv4Network('0.0.0.0/32'))
            self.assertEqual(networks[1], IPv4Network('255.255.255.0/32'))
        finally:
            os.unlink(temp_file)


class TestParseNetmaskNoneConsolidateMode(unittest.TestCase):
    """Test --parse-netmask=none with consolidate mode."""
    
    def test_consolidate_with_netmask_enabled(self):
        """Consolidate with --parse-netmask=both should parse space-separated pairs as netmask."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write('0.0.0.0 255.255.255.0\n')
            f.flush()
            temp_file = f.name
        
        try:
            grepnet = GrepNet(
                patterns=['0.0.0.0/0'],
                parse_netmask='both',
                parse_bare_ip='both',
            )
            input_sources = [InputSource('file', file_path=temp_file)]
            consolidated_dict = grepnet.consolidate_networks(input_sources)
            
            # Should consolidate to one network: 0.0.0.0/24
            self.assertEqual(len(consolidated_dict), 1)
            net = list(consolidated_dict.keys())[0]
            self.assertEqual(net, IPv4Network('0.0.0.0/24'))
        finally:
            os.unlink(temp_file)
    
    def test_consolidate_with_netmask_disabled(self):
        """Consolidate with --parse-netmask=none should parse space-separated pairs as bare IPs."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write('0.0.0.0 255.255.255.0\n')
            f.flush()
            temp_file = f.name
        
        try:
            grepnet = GrepNet(
                patterns=['0.0.0.0/0'],
                parse_netmask='none',
                parse_bare_ip='both',
            )
            input_sources = [InputSource('file', file_path=temp_file)]
            consolidated_dict = grepnet.consolidate_networks(input_sources)
            
            # Should have two bare IPs as separate /32 networks
            self.assertEqual(len(consolidated_dict), 2)
            networks = sorted([net for net in consolidated_dict.keys()], key=str)
            self.assertEqual(networks[0], IPv4Network('0.0.0.0/32'))
            self.assertEqual(networks[1], IPv4Network('255.255.255.0/32'))
        finally:
            os.unlink(temp_file)


class TestMaskFormatHints(unittest.TestCase):
    """Test that netmask/hostmask format detection from file content is respected."""
    
    def test_netmask_dominant_format_hint(self):
        """
        When file is netmask_dominant (has ≥2 clear netmask patterns),
        special cases should NOT apply.
        
        This ensures that 0.0.0.0 255.255.255.255 is NOT treated as special case
        when the file clearly uses netmask format (netmask_dominant hint).
        """
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            # First two lines establish netmask_dominant hint (need ≥2 clear patterns)
            f.write('192.0.2.0 255.255.255.0\n')
            f.write('10.0.0.0 255.0.0.0\n')
            # Third line: 0.0.0.0 255.255.255.255 should parse as normal netmask (0.0.0.0/32)
            # NOT as special case (0.0.0.0/0) because hint is netmask_dominant
            f.write('0.0.0.0 255.255.255.255\n')
            f.flush()
            temp_file = f.name
        
        try:
            grepnet = GrepNet(
                patterns=['0.0.0.0/0'],
                parse_netmask='both',
                parse_bare_ip='both',
            )
            input_sources = [InputSource('file', file_path=temp_file)]
            consolidated_dict = grepnet.consolidate_networks(input_sources)
            
            # Should have three networks:
            # 1. 192.0.2.0/24 from first line (netmask format)
            # 2. 10.0.0.0/8 from second line (netmask format)
            # 3. 0.0.0.0/32 from third line (normal netmask, NOT special case because hint is netmask_dominant)
            self.assertEqual(len(consolidated_dict), 3)
            networks = sorted([net for net in consolidated_dict.keys()], key=str)
            self.assertEqual(networks[0], IPv4Network('0.0.0.0/32'))
            self.assertEqual(networks[1], IPv4Network('10.0.0.0/8'))
            self.assertEqual(networks[2], IPv4Network('192.0.2.0/24'))
        finally:
            os.unlink(temp_file)
    
    def test_hostmask_dominant_format_hint(self):
        """
        When file is hostmask_dominant (has ≥2 clear hostmask patterns),
        space-separated pairs should be parsed with hostmask preference.
        """
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            # First two lines establish hostmask_dominant hint (need ≥2 clear patterns)
            f.write('192.0.2.0 0.0.0.255\n')
            f.write('10.0.0.0 0.255.255.255\n')
            f.flush()
            temp_file = f.name
        
        try:
            grepnet = GrepNet(
                patterns=['10.0.0.0/8'],  # Match second hostmask pattern
                parse_netmask='both',
                parse_bare_ip='both',
            )
            input_sources = [InputSource('file', file_path=temp_file)]
            consolidated_dict = grepnet.consolidate_networks(input_sources)
            
            # Should extract the hostmask pair that matches the pattern
            self.assertEqual(len(consolidated_dict), 1)
            net = list(consolidated_dict.keys())[0]
            self.assertEqual(net, IPv4Network('10.0.0.0/8'))
        finally:
            os.unlink(temp_file)
    
    def test_special_case_3_with_netmask_dominant_hint(self):
        """
        When file is netmask_dominant, Special Case 3 (0.0.0.0 as hostmask) should NOT apply.
        The pattern 255.255.255.255 0.0.0.0 should fall through to bare IP extraction.
        """
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            # First two lines establish netmask_dominant hint
            f.write('192.0.2.0 255.255.0.0\n')
            f.write('192.0.2.0 255.255.255.0\n')
            # Third line: 255.255.255.255 0.0.0.0
            # With netmask_dominant hint, Special Case 3 doesn't apply
            # Falls through to bare IP extraction: 255.255.255.255/32 and 0.0.0.0/32
            f.write('255.255.255.255 0.0.0.0\n')
            f.flush()
            temp_file = f.name
        
        try:
            grepnet = GrepNet(
                patterns=['0.0.0.0/0'],  # Match everything for consolidation
                parse_netmask='both',
                parse_bare_ip='both',
            )
            input_sources = [InputSource('file', file_path=temp_file)]
            consolidated_dict = grepnet.consolidate_networks(input_sources)
            
            # Should have three networks:
            # 1. 192.0.0.0/16 from first line (merged from first two netmasks)
            # 2. 255.255.255.255/32 from third line (bare IP, not special case)
            # 3. 0.0.0.0/32 from third line (bare IP, not hostmask inverse)
            self.assertEqual(len(consolidated_dict), 3)
            networks = sorted([net for net in consolidated_dict.keys()], key=str)
            self.assertEqual(networks[0], IPv4Network('0.0.0.0/32'))
            self.assertEqual(networks[1], IPv4Network('192.0.0.0/16'))
            self.assertEqual(networks[2], IPv4Network('255.255.255.255/32'))
        finally:
            os.unlink(temp_file)
    
    def test_special_case_3_with_hostmask_dominant_hint(self):
        """
        When file is hostmask_dominant, Special Case 3 SHOULD apply.
        The pattern 192.0.2.0 0.0.0.0 should be treated as hostmask: 192.0.2.0/32
        """
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            # First two lines establish hostmask_dominant hint
            f.write('192.0.2.0 0.0.0.255\n')
            f.write('192.0.2.0 0.0.0.7\n')
            # Third line: 192.0.2.0 0.0.0.0
            # With hostmask_dominant hint, Special Case 3 applies
            # Treated as hostmask: 0.0.0.0 inverts to /32
            f.write('192.0.2.0 0.0.0.0\n')
            f.flush()
            temp_file = f.name
        
        try:
            grepnet = GrepNet(
                patterns=['192.0.2.0/30'],  # Match for consolidation
                parse_netmask='both',
                parse_bare_ip='both',
            )
            input_sources = [InputSource('file', file_path=temp_file)]
            consolidated_dict = grepnet.consolidate_networks(input_sources)
            
            # All three are subsumed by /24, so consolidated result is just /24
            self.assertEqual(len(consolidated_dict), 1)
            net = list(consolidated_dict.keys())[0]
            self.assertEqual(net, IPv4Network('192.0.2.0/24'))
        finally:
            os.unlink(temp_file)
    
    def test_special_case_3_with_unknown_hint(self):
        """
        When hint is unknown (only 1 pattern or ambiguous patterns),
        Special Case 3 SHOULD apply.
        Single line: 192.0.2.0 0.0.0.0
        """
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            # Single line, only one pattern → hint will be 'unknown'
            f.write('192.0.2.0 0.0.0.0\n')
            f.flush()
            temp_file = f.name
        
        try:
            grepnet = GrepNet(
                patterns=['192.0.2.0/32'],  # Match for consolidation
                parse_netmask='both',
                parse_bare_ip='both',
            )
            input_sources = [InputSource('file', file_path=temp_file)]
            consolidated_dict = grepnet.consolidate_networks(input_sources)
            
            # With unknown hint, Special Case 3 applies: 0.0.0.0 is treated as hostmask
            # Result: 192.0.2.0/32 (0.0.0.0 inverted to /32)
            self.assertEqual(len(consolidated_dict), 1)
            net = list(consolidated_dict.keys())[0]
            self.assertEqual(net, IPv4Network('192.0.2.0/32'))
        finally:
            os.unlink(temp_file)


if __name__ == '__main__':
    unittest.main()
