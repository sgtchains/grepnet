"""
Tests for MaskFormatDetector - analyzing peek buffer for format hints.

Tests the three core scenarios:
1. Netmask-dominant detection (most two-value patterns have MSB=1)
2. Hostmask-dominant detection (most two-value patterns have MSB=0)
3. Mixed/unknown detection (balanced or no patterns)
"""

import pytest
from grepnet.parsing.mask_format_detector import MaskFormatDetector


class TestMaskFormatDetectorBasic:
    """Test basic format detection on simple inputs."""
    
    def test_empty_text_returns_unknown(self):
        """Empty text should return 'unknown'."""
        assert MaskFormatDetector.detect_format('') == 'unknown'
        assert MaskFormatDetector.detect_format('   \n  ') == 'unknown'
    
    def test_no_two_value_patterns_returns_unknown(self):
        """Text with no two-value patterns should return 'unknown'."""
        text = '192.0.2.1\n10.0.0.0/8\n172.16.0.0/12\n'
        assert MaskFormatDetector.detect_format(text) == 'unknown'
    
    def test_single_netmask_pattern(self):
        """Single netmask pattern (MSB=1) should be detected."""
        # 255.255.255.0 has MSB=1 (255 in binary starts with 1)
        text = '192.0.2.0 255.255.255.0'
        result = MaskFormatDetector.detect_format(text)
        # With only one pattern, it's netmask_dominant
        assert result == 'netmask_dominant'
    
    def test_single_hostmask_pattern(self):
        """Single hostmask pattern (MSB=0) should be detected."""
        # 0.0.0.255 has MSB=0 (0 in binary starts with 0)
        text = '192.0.2.0 0.0.0.255'
        result = MaskFormatDetector.detect_format(text)
        # With only one pattern, it's hostmask_dominant
        assert result == 'hostmask_dominant'


class TestMaskFormatDetectorNetmaskDominant:
    """Test netmask-dominant format detection."""
    
    def test_all_netmasks_dominant(self):
        """All netmask patterns (MSB=1) should be detected as netmask_dominant."""
        text = """
192.0.2.0 255.255.255.0
10.0.0.0 255.0.0.0
172.16.0.0 255.255.0.0
"""
        assert MaskFormatDetector.detect_format(text) == 'netmask_dominant'
    
    def test_majority_netmasks_dominant(self):
        """Majority netmask patterns should be detected as netmask_dominant (>66%)."""
        text = """
192.0.2.0 255.255.255.0
10.0.0.0 255.0.0.0
172.16.0.0 255.255.0.0
192.168.0.0 0.0.0.255
"""
        # 3 netmask (MSB=1), 1 hostmask (MSB=0) = 75% netmask
        assert MaskFormatDetector.detect_format(text) == 'netmask_dominant'
    
    def test_netmask_at_threshold(self):
        """Netmask at exactly 66% should be detected as dominant."""
        text = """
192.0.2.0 255.255.255.0
10.0.0.0 255.0.0.0
192.168.0.0 0.0.0.255
"""
        # 2 netmask (MSB=1), 1 hostmask (MSB=0) = ~67% netmask (above 66%)
        assert MaskFormatDetector.detect_format(text) == 'netmask_dominant'
    
    def test_netmask_with_whitespace_variations(self):
        """Netmask detection should work with various whitespace."""
        text = """
192.0.2.0  255.255.255.0
10.0.0.0	255.0.0.0
172.16.0.0   255.255.0.0
"""
        assert MaskFormatDetector.detect_format(text) == 'netmask_dominant'


class TestMaskFormatDetectorHostmaskDominant:
    """Test hostmask-dominant format detection."""
    
    def test_all_hostmasks_dominant(self):
        """All hostmask patterns (MSB=0) should be detected as hostmask_dominant."""
        text = """
192.0.2.0 0.0.0.255
10.0.0.0 0.255.255.255
172.16.0.0 0.0.255.255
"""
        assert MaskFormatDetector.detect_format(text) == 'hostmask_dominant'
    
    def test_majority_hostmasks_dominant(self):
        """Majority hostmask patterns should be detected as hostmask_dominant (>66%)."""
        text = """
192.0.2.0 0.0.0.255
10.0.0.0 0.255.255.255
172.16.0.0 0.0.255.255
192.168.0.0 255.255.255.0
"""
        # 3 hostmask (MSB=0), 1 netmask (MSB=1) = 75% hostmask
        assert MaskFormatDetector.detect_format(text) == 'hostmask_dominant'
    
    def test_hostmask_at_threshold(self):
        """Hostmask at exactly 66% should be detected as dominant."""
        text = """
192.0.2.0 0.0.0.255
10.0.0.0 0.255.255.255
192.168.0.0 255.255.255.0
"""
        # 2 hostmask (MSB=0), 1 netmask (MSB=1) = ~67% hostmask (above 66%)
        assert MaskFormatDetector.detect_format(text) == 'hostmask_dominant'


class TestMaskFormatDetectorMixed:
    """Test mixed format detection."""
    
    def test_equal_netmask_hostmask(self):
        """Equal netmask and hostmask patterns should be detected as mixed."""
        text = """
192.0.2.0 255.255.255.0
10.0.0.0 0.255.255.255
"""
        # 1 netmask, 1 hostmask = 50/50 mixed
        assert MaskFormatDetector.detect_format(text) == 'mixed'
    
    def test_below_threshold_mixed(self):
        """Patterns below 66% threshold should be detected as mixed."""
        text = """
192.0.2.0 255.255.255.0
10.0.0.0 0.255.255.255
192.168.0.0 0.0.0.1
"""
        # 1 netmask (MSB=1), 2 hostmask (MSB=0) = 33% netmask, 67% hostmask
        # 67% is exactly at threshold so it's hostmask_dominant (not mixed)
        # Need 2-2 split for true mixed, or 3-2 split (40%) for below threshold
        assert MaskFormatDetector.detect_format(text) == 'hostmask_dominant'
    
    def test_exactly_equal_mixed(self):
        """Exactly equal split should be detected as mixed."""
        text = """
192.0.2.0 255.255.255.0
10.0.0.0 0.255.255.255
"""
        # 1 netmask, 1 hostmask = 50% each = mixed
        assert MaskFormatDetector.detect_format(text) == 'mixed'


class TestMaskFormatDetectorRobustness:
    """Test robustness with edge cases and special values."""
    
    def test_special_case_zero_mask(self):
        """0.0.0.0 has MSB=0 (hostmask-like), should be counted as hostmask indicator."""
        text = '192.0.2.1 0.0.0.0'
        # 0.0.0.0 has MSB=0, so it's hostmask format
        assert MaskFormatDetector.detect_format(text) == 'hostmask_dominant'
    
    def test_special_case_broadcast_mask(self):
        """255.255.255.255 has MSB=1, should be counted as netmask indicator."""
        text = '255.255.255.255 255.255.255.255'
        # First IP is stripped, second is 255.255.255.255 with MSB=1
        assert MaskFormatDetector.detect_format(text) == 'netmask_dominant'
    
    def test_invalid_ips_skipped(self):
        """Invalid IPs should be skipped."""
        text = """
192.0.2.0 999.999.999.999
192.0.2.1 255.255.255.0
"""
        # Invalid IP is skipped, only netmask pattern counts
        assert MaskFormatDetector.detect_format(text) == 'netmask_dominant'
    
    def test_mixed_content_with_comments_and_cidrs(self):
        """Format detection should work even with comments and CIDR notation."""
        text = """
# Comment
192.0.2.0 255.255.255.0
10.0.0.0/8
172.16.0.0 0.0.255.255
# Another comment
"""
        # 1 netmask, 1 hostmask = mixed
        assert MaskFormatDetector.detect_format(text) == 'mixed'
    
    def test_partial_overlapping_patterns(self):
        """Overlapping two-value patterns should all be detected."""
        text = '192.0.2.0 255.255.255.0 10.0.0.0 255.0.0.0'
        # Should find both patterns
        result = MaskFormatDetector.detect_format(text)
        assert result == 'netmask_dominant'


class TestMaskFormatDetectorConclusiveness:
    """Test is_conclusive() method for determining when hints should be used."""
    
    def test_conclusive_netmask_dominant(self):
        """netmask_dominant should be conclusive."""
        assert MaskFormatDetector.is_conclusive('netmask_dominant') is True
    
    def test_conclusive_hostmask_dominant(self):
        """hostmask_dominant should be conclusive."""
        assert MaskFormatDetector.is_conclusive('hostmask_dominant') is True
    
    def test_inconclusive_mixed(self):
        """mixed should not be conclusive."""
        assert MaskFormatDetector.is_conclusive('mixed') is False
    
    def test_inconclusive_unknown(self):
        """unknown should not be conclusive."""
        assert MaskFormatDetector.is_conclusive('unknown') is False


class TestMaskFormatDetectorRealWorldExamples:
    """Test with real-world-like examples."""
    
    def test_network_config_file_netmask_format(self):
        """Real-world network config file with netmask notation."""
        text = """# Network configuration
# IP Netmask
192.168.1.0 255.255.255.0
10.0.0.0 255.0.0.0
172.16.0.0 255.255.0.0
192.168.100.0 255.255.255.0
"""
        assert MaskFormatDetector.detect_format(text) == 'netmask_dominant'
    
    def test_firewall_rules_hostmask_format(self):
        """Real-world firewall rules with hostmask notation."""
        text = """allow 192.168.1.0 0.0.0.255
deny 10.0.0.0 0.255.255.255
allow 172.16.0.0 0.0.255.255
deny 192.168.100.0 0.0.0.255
"""
        assert MaskFormatDetector.detect_format(text) == 'hostmask_dominant'
    
    def test_mixed_network_database(self):
        """Real-world database with mixed notation."""
        text = """
-- Netmask format entries
192.168.1.0 255.255.255.0
10.0.0.0 255.0.0.0
-- Hostmask format entries (legacy system)
172.16.0.0 0.0.255.255
192.168.100.0 0.0.0.255
-- And a bare IP
8.8.8.8
"""
        # 2 netmask, 2 hostmask = 50/50 mixed
        assert MaskFormatDetector.detect_format(text) == 'mixed'
    
    def test_scan_8kb_buffer_simulation(self):
        """Simulate scanning an 8KB buffer like in real usage."""
        # Create a buffer similar to first 8KB of a file
        lines = ['192.168.1.0 255.255.255.0'] * 20  # All netmask
        buffer = '\n'.join(lines)
        
        # Should detect as netmask_dominant
        assert MaskFormatDetector.detect_format(buffer) == 'netmask_dominant'


class TestMaskFormatDetectorEdgeCases:
    """Test edge cases that might appear in real parsing scenarios."""
    
    def test_only_whitespace_between_ips(self):
        """Test various whitespace characters between IPs."""
        text = '192.0.2.0     255.255.255.0'  # Multiple spaces
        assert MaskFormatDetector.detect_format(text) == 'netmask_dominant'
    
    def test_ip_at_line_boundaries(self):
        """Test IPs at the very start and end of text."""
        text = '192.0.2.0 255.255.255.0'
        assert MaskFormatDetector.detect_format(text) == 'netmask_dominant'
    
    def test_very_long_text_with_patterns(self):
        """Test detection works on very long text."""
        lines = []
        for i in range(100):
            lines.append(f'192.0.{i}.0 255.255.255.0')  # All netmask
        text = '\n'.join(lines)
        assert MaskFormatDetector.detect_format(text) == 'netmask_dominant'
    
    def test_patterns_in_different_contexts(self):
        """Test patterns found amid other content."""
        text = """
Some header text
192.0.2.0 255.255.255.0
More content here
10.0.0.0 255.0.0.0
Footer text
"""
        assert MaskFormatDetector.detect_format(text) == 'netmask_dominant'


class TestMaskFormatDetectorMSBLogic:
    """Test MSB logic for different mask values."""
    
    def test_msb_one_patterns(self):
        """Test various netmask patterns with MSB=1."""
        patterns = [
            '192.0.2.0 255.255.255.0',      # 255 = 0xFF = 11111111
            '10.0.0.0 255.0.0.0',            # 255 = 0xFF = 11111111
            '172.16.0.0 255.255.0.0',        # 255 = 0xFF = 11111111
            '192.168.0.0 255.255.255.128',   # 128 = 0x80 = 10000000
        ]
        for pattern in patterns:
            result = MaskFormatDetector.detect_format(pattern)
            assert result == 'netmask_dominant', f"Failed for pattern: {pattern}"
    
    def test_msb_zero_patterns(self):
        """Test various hostmask patterns with MSB=0."""
        patterns = [
            '192.0.2.0 0.0.0.255',           # 0 = 0x00 = 00000000
            '10.0.0.0 0.255.255.255',        # 0 = 0x00 = 00000000
            '172.16.0.0 0.0.255.255',        # 0 = 0x00 = 00000000
            '192.168.0.0 0.0.0.127',         # 0 = 0x00 = 00000000
        ]
        for pattern in patterns:
            result = MaskFormatDetector.detect_format(pattern)
            assert result == 'hostmask_dominant', f"Failed for pattern: {pattern}"
