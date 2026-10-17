"""
Test suite for --parse-bare-ip option.

Tests that bare IP addresses (single IPs without explicit prefix notation)
are properly gated based on the --parse-bare-ip flag.
"""

import unittest
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from grepnet.parsing.network_parser import NetworkParser
from ipaddress import IPv4Network, IPv6Network


class TestParseBareIPOption(unittest.TestCase):
    """Test --parse-bare-ip option gating for bare IP addresses."""
    
    def test_bare_ip_default_both(self):
        """With --parse-bare-ip=both (default), bare IPs should be parsed."""
        parser = NetworkParser(parse_bare_ip='both')
        
        # Test IPv4 bare IP
        results = parser.parse_line('192.0.2.1', context='input')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].network, IPv4Network('192.0.2.1/32'))
        
        # Test IPv6 bare IP
        results = parser.parse_line('::1', context='input')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].network, IPv6Network('::1/128'))
    
    def test_bare_ip_none_skips_bare(self):
        """With --parse-bare-ip=none, bare IPs should not be parsed."""
        parser = NetworkParser(parse_bare_ip='none')
        
        # Test IPv4 bare IP - should be skipped
        results = parser.parse_line('192.0.2.1', context='input')
        self.assertEqual(len(results), 0)
        
        # Test IPv6 bare IP - should be skipped
        results = parser.parse_line('::1', context='input')
        self.assertEqual(len(results), 0)
    
    def test_bare_ip_none_allows_explicit_prefix(self):
        """With --parse-bare-ip=none, explicit /32 or /128 should still work."""
        parser = NetworkParser(parse_bare_ip='none')
        
        # Test IPv4 with explicit /32 - should work (CIDR notation)
        results = parser.parse_line('192.0.2.1/32', context='input')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].network, IPv4Network('192.0.2.1/32'))
        
        # Test IPv6 with explicit /128 - should work (CIDR notation)
        results = parser.parse_line('::1/128', context='input')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].network, IPv6Network('::1/128'))
    
    def test_bare_ip_pattern_only_in_patterns(self):
        """With --parse-bare-ip=pattern, bare IPs should only be parsed in patterns."""
        parser = NetworkParser(parse_bare_ip='pattern')
        
        # In pattern context, bare IPs should be parsed
        results = parser.parse_line('192.0.2.1', context='pattern')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].network, IPv4Network('192.0.2.1/32'))
        
        # In input context, bare IPs should be skipped
        results = parser.parse_line('192.0.2.1', context='input')
        self.assertEqual(len(results), 0)
    
    def test_bare_ip_input_only_in_input(self):
        """With --parse-bare-ip=input, bare IPs should only be parsed in input files."""
        parser = NetworkParser(parse_bare_ip='input')
        
        # In input context, bare IPs should be parsed
        results = parser.parse_line('192.0.2.1', context='input')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].network, IPv4Network('192.0.2.1/32'))
        
        # In pattern context, bare IPs should be skipped
        results = parser.parse_line('192.0.2.1', context='pattern')
        self.assertEqual(len(results), 0)
    
    def test_bare_ip_does_not_affect_cidr(self):
        """--parse-bare-ip should not affect CIDR notation parsing."""
        parser_both = NetworkParser(parse_bare_ip='both')
        parser_none = NetworkParser(parse_bare_ip='none')
        
        # Both should parse CIDR notation
        results_both = parser_both.parse_line('192.0.2.0/24', context='input')
        results_none = parser_none.parse_line('192.0.2.0/24', context='input')
        
        self.assertEqual(len(results_both), 1)
        self.assertEqual(len(results_none), 1)
        self.assertEqual(results_both[0].network, IPv4Network('192.0.2.0/24'))
        self.assertEqual(results_none[0].network, IPv4Network('192.0.2.0/24'))
    
    def test_bare_ip_does_not_affect_ranges(self):
        """--parse-bare-ip should not affect range parsing."""
        parser_both = NetworkParser(parse_bare_ip='both')
        parser_none = NetworkParser(parse_bare_ip='none')
        
        # Both should parse ranges
        results_both = parser_both.parse_line('192.0.2.0-192.0.2.255', context='input')
        results_none = parser_none.parse_line('192.0.2.0-192.0.2.255', context='input')
        
        self.assertEqual(len(results_both), 1)
        self.assertEqual(len(results_none), 1)
    
    def test_bare_ip_does_not_affect_netmask(self):
        """--parse-bare-ip should not affect subnet mask parsing."""
        parser_both = NetworkParser(parse_bare_ip='both')
        parser_none = NetworkParser(parse_bare_ip='none')
        
        # Both should parse netmask format
        results_both = parser_both.parse_line('192.0.2.0 255.255.255.0', context='input')
        results_none = parser_none.parse_line('192.0.2.0 255.255.255.0', context='input')
        
        self.assertEqual(len(results_both), 1)
        self.assertEqual(len(results_none), 1)
        self.assertEqual(results_both[0].network, IPv4Network('192.0.2.0/24'))
        self.assertEqual(results_none[0].network, IPv4Network('192.0.2.0/24'))
    
    def test_bare_ip_multiple_addresses(self):
        """Test parse_bare_ip with multiple bare IPs on one line."""
        parser_both = NetworkParser(parse_bare_ip='both')
        parser_none = NetworkParser(parse_bare_ip='none')
        
        line = '192.0.2.1 10.0.0.1 172.16.0.1'
        
        # With parse_bare_ip=both, all should be parsed
        results_both = parser_both.parse_line(line, context='input')
        self.assertEqual(len(results_both), 3)
        
        # With parse_bare_ip=none, none should be parsed
        results_none = parser_none.parse_line(line, context='input')
        self.assertEqual(len(results_none), 0)
    
    def test_bare_ip_mixed_formats(self):
        """Test parse_bare_ip with mixed formats on same line."""
        parser_bare_ip_both = NetworkParser(parse_bare_ip='both', parse_cidr='both')
        parser_bare_ip_none = NetworkParser(parse_bare_ip='none', parse_cidr='both')
        
        line = '192.0.2.0/24 10.0.0.1 172.16.0.0/12'
        
        # With parse_bare_ip=both, should get 3 networks (CIDR + bare + CIDR)
        results_both = parser_bare_ip_both.parse_line(line, context='input')
        self.assertEqual(len(results_both), 3)
        
        # With parse_bare_ip=none, should get 2 networks (CIDR + CIDR, bare is skipped)
        results_none = parser_bare_ip_none.parse_line(line, context='input')
        self.assertEqual(len(results_none), 2)
        networks = [str(r.network) for r in results_none]
        self.assertIn('192.0.2.0/24', networks)
        self.assertIn('172.16.0.0/12', networks)
        self.assertNotIn('10.0.0.1/32', networks)


class TestParseBareIPIntegration(unittest.TestCase):
    """Integration tests for parse_bare_ip with other parse options."""
    
    def test_bare_ip_with_parse_cidr_none(self):
        """Test bare IP option combined with parse_cidr=none."""
        parser = NetworkParser(parse_cidr='none', parse_bare_ip='both')
        
        # CIDR should not be parsed
        results = parser.parse_line('192.0.2.0/24', context='input')
        self.assertEqual(len(results), 0)
        
        # But bare IP should be
        results = parser.parse_line('192.0.2.0', context='input')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].network, IPv4Network('192.0.2.0/32'))
    
    def test_bare_ip_pattern_vs_input_separation(self):
        """Test that pattern and input contexts are properly separated."""
        parser = NetworkParser(parse_bare_ip='pattern')
        
        line = '192.0.2.1'
        
        # Pattern context should work
        pattern_results = parser.parse_line(line, context='pattern')
        self.assertEqual(len(pattern_results), 1)
        
        # Input context should not work
        input_results = parser.parse_line(line, context='input')
        self.assertEqual(len(input_results), 0)
    
    def test_bare_ipv6_with_parse_bare_ip_none(self):
        """Test IPv6 bare addresses are properly gated."""
        parser_both = NetworkParser(parse_bare_ip='both')
        parser_none = NetworkParser(parse_bare_ip='none')
        
        ipv6_bare = '2001:db8::1'
        ipv6_explicit = '2001:db8::1/128'
        
        # parse_bare_ip=both should parse both
        results = parser_both.parse_line(ipv6_bare, context='input')
        self.assertEqual(len(results), 1)
        
        # parse_bare_ip=none should not parse bare
        results = parser_none.parse_line(ipv6_bare, context='input')
        self.assertEqual(len(results), 0)
        
        # But explicit notation should work regardless
        results = parser_none.parse_line(ipv6_explicit, context='input')
        self.assertEqual(len(results), 1)


class TestSNMPOIDHandling(unittest.TestCase):
    """
    Test SNMP OID detection and mixed-content line handling.
    
    CRITICAL: Per GREPNET-SPEC, lines should never be rejected wholesale.
    When SNMP OID patterns are detected, only bare IP extraction is skipped;
    other extractors (CIDR, ranges, etc.) continue running.
    """
    
    def test_snmp_oid_line_pure(self):
        """Pure SNMP OID line (no networks) should return empty list."""
        parser = NetworkParser()
        result = parser.parse_line('1.3.6.1.2.1.1.0')
        self.assertEqual(len(result), 0)
    
    def test_snmp_oid_line_with_cidr(self):
        """SNMP OID + CIDR should extract CIDR (bare IP extraction skipped)."""
        parser = NetworkParser()
        result = parser.parse_line('1.3.6.1.2.1.1.0 192.0.2.0/24')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].network, IPv4Network('192.0.2.0/24'))
    
    def test_snmp_oid_line_with_bare_ip(self):
        """SNMP OID + bare IP should NOT extract bare IP (would be suppressed)."""
        parser = NetworkParser()
        result = parser.parse_line('1.3.6.1.2.1.1.0 192.0.2.1')
        self.assertEqual(len(result), 0)
    
    def test_snmp_oid_line_with_range(self):
        """SNMP OID + range should extract range (only bare IP extraction affected)."""
        parser = NetworkParser()
        result = parser.parse_line('1.3.6.1.2.1.1.0 192.0.2.0-192.0.2.255')
        self.assertEqual(len(result), 1)
        # Range is returned as tuple (start_int, end_int), not a network
        self.assertIsNotNone(result[0].network)
    
    def test_normal_line_bare_ip_always_works(self):
        """Without SNMP OID, bare IPs should be extracted normally."""
        parser = NetworkParser()
        result = parser.parse_line('192.0.2.1')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].network, IPv4Network('192.0.2.1/32'))
    
    def test_comment_line_never_produces_networks(self):
        """Comment-only lines should return empty list."""
        parser = NetworkParser()
        result = parser.parse_line('# 1.3.6.1.2.1.1.0')
        self.assertEqual(len(result), 0)
    
    def test_empty_line_returns_empty_list(self):
        """Empty lines should return empty list."""
        parser = NetworkParser()
        result = parser.parse_line('')
        self.assertEqual(len(result), 0)
    
    def test_architectural_guarantee_no_line_rejection(self):
        """
        Verify the architectural guarantee: lines are never rejected
        based on line metadata, only based on extracted networks.
        """
        parser = NetworkParser()
        
        # These should all return SOME result (network or empty list)
        # but never raise an exception or reject the line:
        test_cases = [
            '1.3.6.1.2.1.1.0',                      # Pure SNMP OID
            '1.3.6.1.2.1.1.0 192.0.2.0/24',         # SNMP + CIDR
            '1.3.6.1.2.1.1.0 192.0.2.1',            # SNMP + bare IP
            '# comment 1.3.6.1.2.1.1.0',            # Comment
            '192.0.2.0/24 # comment',               # CIDR with comment
            '',                                      # Empty
        ]
        
        for line in test_cases:
            result = parser.parse_line(line)
            # Should always return a list (possibly empty), never None or raise
            self.assertIsInstance(result, list, f"Failed for line: {line}")


if __name__ == '__main__':
    unittest.main()
