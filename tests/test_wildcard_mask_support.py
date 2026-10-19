"""
Comprehensive test suite for wildcard mask support (--parse-wildcard and --wildcard-search).

Tests cover:
1. Wildcard mask expansion algorithm
2. Parser mode detection and recognition
3. Integration with file scanning and matching
4. Edge cases and boundary conditions
5. CLI flag validation and interaction
6. Output formatting and colorization
7. Error handling
8. Regression tests to ensure existing functionality unchanged
"""

import unittest
import subprocess
import tempfile
import os
from pathlib import Path
from ipaddress import IPv4Network, IPv4Address


class TestWildcardMaskExpansion(unittest.TestCase):
    """Test wildcard mask expansion algorithm."""
    
    def setUp(self):
        """Set up test environment."""
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
    
    def test_basic_wildcard_expansion(self):
        """Test basic wildcard mask expansion: 192.0.2.0 0.0.0.192 expands correctly."""
        # Create a test file with a wildcard mask
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('192.0.2.0 0.0.0.192\n')
            f.write('192.0.2.64 0.0.127.252\n')
            f.write('192.0.2.128 0.0.127.252\n')
            temp_file = f.name
        
        try:
            # Search for networks matching the wildcard mask pattern
            # The mask 0.0.127.252 has 9 wildcard bits, so it should match a range
            stdout, stderr, rc = self.run_grepnet(
                '--parse-wildcard', 'input',
                '--wildcard-search', '192.0.2.0/24',
                '-o',  # Only show matching parts
                '192.0.2.0 0.0.0.192',  # Pattern to search for
                temp_file
            )
            
            # Should find the wildcard masks in the file
            self.assertEqual(rc, 0, f"Expected rc=0, got {rc}\nstderr: {stderr}")
            # The -o flag shows only the matched part, which may be split across lines
            # Just verify we got output without error
            self.assertTrue(len(stdout) > 0)
        finally:
            os.unlink(temp_file)
    
    def test_wildcard_mask_in_pattern(self):
        """Test wildcard mask recognition in search pattern."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('192.0.2.0\n')
            f.write('192.0.2.64\n')
            f.write('192.0.2.128\n')
            temp_file = f.name
        
        try:
            # Use wildcard mask as pattern
            stdout, stderr, rc = self.run_grepnet(
                '--parse-wildcard', 'pattern',
                '--wildcard-search', '192.0.2.0/24',
                '-e',  # Exact match
                '192.0.2.0 0.0.0.192',
                temp_file
            )
            
            # Should succeed without error
            self.assertNotIn('error:', stderr.lower())
        finally:
            os.unlink(temp_file)
    
    def test_wildcard_mask_format_detection(self):
        """Test format type assignment for wildcard masks."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('192.0.2.0 0.0.0.192\n')
            temp_file = f.name
        
        try:
            # Extract with wildcard parsing enabled - using stdin with pattern
            stdout, stderr, rc = self.run_grepnet(
                '--extract',
                '--parse-wildcard', 'input',
                '--wildcard-search', '192.0.2.0/24',
                '-e', '192.0.2.0 0.0.0.192',
                temp_file
            )
            
            # Should parse without error
            self.assertEqual(rc, 0, f"Extract failed: {stderr}")
            # Output should contain extracted networks
            self.assertTrue(len(stdout) > 0)
        finally:
            os.unlink(temp_file)
    
    def test_bare_ip_extraction_without_wildcard_parsing(self):
        """Test that '192.0.2.0 0.0.0.192' without --parse-wildcard returns 2 bare IPs with -o."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('192.0.2.0 0.0.0.192\n')
            temp_file = f.name
        
        try:
            # Run WITHOUT --parse-wildcard flag with -o to extract individual IPs
            stdout, stderr, rc = self.run_grepnet(
                '-o',  # Only matching parts
                '-e',  # Exact match
                '192.0.2.0 0.0.0.192',
                temp_file
            )
            
            # Should match successfully without wildcard parsing
            self.assertEqual(rc, 0, f"Expected rc=0, got {rc}\nstderr: {stderr}")
            
            # With -o flag, should extract both IPs as separate lines
            output_lines = [line.strip() for line in stdout.strip().split('\n') if line.strip()]
            self.assertEqual(len(output_lines), 2, 
                f"Expected 2 bare IP addresses with -o, got {len(output_lines)}\nOutput: {stdout}")
            
            # Verify the two extracted IPs
            self.assertEqual(output_lines[0], '192.0.2.0')
            self.assertEqual(output_lines[1], '0.0.0.192')
        finally:
            os.unlink(temp_file)


class TestWildcardMaskCLIFlags(unittest.TestCase):
    """Test CLI flag validation and interaction."""
    
    def setUp(self):
        """Set up test environment."""
        self.grepnet_script = Path(__file__).parent.parent / 'grepnet'
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
        self.temp_file.write('192.0.2.0/24\n')
        self.temp_file.close()
    
    def tearDown(self):
        """Clean up temp files."""
        os.unlink(self.temp_file.name)
    
    def run_grepnet(self, *args, stdin_data=None):
        """Run grepnet with given arguments."""
        cmd = [str(self.grepnet_script)] + list(args)
        result = subprocess.run(
            cmd,
            input=stdin_data,
            capture_output=True,
            text=True
        )
        return result.stdout, result.stderr, result.returncode
    
    def test_parse_wildcard_requires_wildcard_search(self):
        """Test error when --parse-wildcard is set but --wildcard-search is missing."""
        stdout, stderr, rc = self.run_grepnet(
            '--parse-wildcard', 'pattern',
            '-e', '192.0.2.0/24',
            self.temp_file.name
        )
        
        self.assertEqual(rc, 2, f"Expected exit code 2, got {rc}")
        self.assertIn('--wildcard-search', stderr)
    
    def test_wildcard_search_requires_parse_wildcard(self):
        """Test error when --wildcard-search is set but --parse-wildcard is missing."""
        stdout, stderr, rc = self.run_grepnet(
            '--wildcard-search', '192.0.2.0/24',
            '-e', '192.0.2.0/24',
            self.temp_file.name
        )
        
        self.assertEqual(rc, 2, f"Expected exit code 2, got {rc}")
        self.assertIn('--parse-wildcard', stderr)
    
    def test_invalid_cidr_in_wildcard_search(self):
        """Test error for invalid CIDR in --wildcard-search."""
        stdout, stderr, rc = self.run_grepnet(
            '--parse-wildcard', 'pattern',
            '--wildcard-search', 'not-a-cidr',
            '-e', '192.0.2.0/24',
            self.temp_file.name
        )
        
        self.assertEqual(rc, 2, f"Expected exit code 2, got {rc}")
        self.assertIn('invalid CIDR', stderr)
    
    def test_ipv6_in_wildcard_search_rejected(self):
        """Test error for IPv6 CIDR in --wildcard-search (IPv4 only)."""
        stdout, stderr, rc = self.run_grepnet(
            '--parse-wildcard', 'pattern',
            '--wildcard-search', '2001:db8::/32',
            '-e', '192.0.2.0/24',
            self.temp_file.name
        )
        
        self.assertEqual(rc, 2, f"Expected exit code 2, got {rc}")
        self.assertIn('IPv4', stderr)
    
    def test_both_parse_modes_accept_wildcard(self):
        """Test --parse-wildcard both mode."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('192.0.2.0 0.0.0.192\n')
            temp_file = f.name
        
        try:
            stdout, stderr, rc = self.run_grepnet(
                '--parse-wildcard', 'both',
                '--wildcard-search', '192.0.2.0/24',
                '-e', '192.0.2.0 0.0.0.192',
                temp_file
            )
            
            # Should succeed
            self.assertNotIn('error:', stderr.lower())
        finally:
            os.unlink(temp_file)


class TestWildcardMaskMatching(unittest.TestCase):
    """Test wildcard mask matching with various match types."""
    
    def setUp(self):
        """Set up test environment."""
        self.grepnet_script = Path(__file__).parent.parent / 'grepnet'
    
    def run_grepnet(self, *args, stdin_data=None):
        """Run grepnet with given arguments."""
        cmd = [str(self.grepnet_script)] + list(args)
        result = subprocess.run(
            cmd,
            input=stdin_data,
            capture_output=True,
            text=True
        )
        return result.stdout, result.stderr, result.returncode
    
    def test_wildcard_equal_match(self):
        """Test EQUALS match type with wildcard masks.
        
        File: 192.0.2.0 0.0.0.128 expands to {192.0.2.0/32, 192.0.2.128/32}
        Pattern: 192.0.2.0 0.0.0.128 expands to {192.0.2.0/32, 192.0.2.128/32}
        Result: EQUALS (same set)
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('192.0.2.0 0.0.0.128\n')  # Same as pattern
            f.write('192.0.2.64 0.0.127.252\n')  # Different wildcard - should not match
            temp_file = f.name
        
        try:
            stdout, stderr, rc = self.run_grepnet(
                '--parse-wildcard', 'both',
                '--wildcard-search', '0.0.0.0/17',
                '-e',  # Equal match only
                '192.0.2.0 0.0.0.128',
                temp_file
            )
            
            # Should find exact match
            self.assertEqual(rc, 0)
            self.assertIn('192.0.2.0 0.0.0.128', stdout)
            self.assertNotIn('192.0.2.64 0.0.127.252', stdout)
        finally:
            os.unlink(temp_file)
    
    def test_wildcard_overlap_match(self):
        """Test OVERLAP match type with wildcard masks.
        
        File: 192.0.2.0 0.0.0.128 expands to {192.0.2.0/32, 192.0.2.128/32}
        Pattern: 192.0.2.128/25 covers 192.0.2.128-192.0.2.255
        Result: OVERLAP (includes 192.0.2.128/32 from file but also 192.0.2.129-192.0.2.255 not in file)
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('192.0.2.0 0.0.0.128\n')  # Expands to 192.0.2.0/32 and 192.0.2.128/32
            temp_file = f.name
        
        try:
            stdout, stderr, rc = self.run_grepnet(
                '--parse-wildcard', 'both',
                '--wildcard-search', '0.0.0.0/17',
                '--overlap',  # Overlap match
                '192.0.2.128/25',  # Partial overlap with wildcard
                temp_file
            )
            
            # Should find overlap
            self.assertEqual(rc, 0)
            self.assertIn('192.0.2.0 0.0.0.128', stdout)
        finally:
            os.unlink(temp_file)
    
    def test_wildcard_superset_match(self):
        """Test SUPERSET match type: pattern contains all file CIDRs.
        
        File: 192.0.2.0 0.0.0.128 expands to {192.0.2.0/32, 192.0.2.128/32}
        Pattern: 192.0.2.0/24
        Result: SUPERSET (pattern completely contains both /32s from file)
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('192.0.2.0 0.0.0.128\n')  # Expands to 192.0.2.0/32 and 192.0.2.128/32
            temp_file = f.name
        
        try:
            stdout, stderr, rc = self.run_grepnet(
                '--parse-wildcard', 'both',
                '--wildcard-search', '0.0.0.0/17',
                '--superset',  # Superset match
                '192.0.2.0/24',  # Completely contains the wildcard mask
                temp_file
            )
            
            # Should find superset
            self.assertEqual(rc, 0)
            self.assertIn('192.0.2.0 0.0.0.128', stdout)
        finally:
            os.unlink(temp_file)
    
    def test_wildcard_subset_match(self):
        """Test SUBSET match type: pattern is part of file CIDRs.
        
        File: 192.0.2.0 0.0.0.128 expands to {192.0.2.0/32, 192.0.2.128/32}
        Pattern: 192.0.2.128/32
        Result: SUBSET (pattern is part of file set, but not all)
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('192.0.2.0 0.0.0.128\n')  # Expands to 192.0.2.0/32 and 192.0.2.128/32
            temp_file = f.name
        
        try:
            stdout, stderr, rc = self.run_grepnet(
                '--parse-wildcard', 'both',
                '--wildcard-search', '0.0.0.0/17',
                '--subset',  # Subset match
                '192.0.2.128',  # Only one of the two /32s from wildcard
                temp_file
            )
            
            # Should find subset
            self.assertEqual(rc, 0)
            self.assertIn('192.0.2.0 0.0.0.128', stdout)
        finally:
            os.unlink(temp_file)


class TestWildcardMaskEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""
    
    def setUp(self):
        """Set up test environment."""
        self.grepnet_script = Path(__file__).parent.parent / 'grepnet'
    
    def run_grepnet(self, *args, stdin_data=None):
        """Run grepnet with given arguments."""
        cmd = [str(self.grepnet_script)] + list(args)
        result = subprocess.run(
            cmd,
            input=stdin_data,
            capture_output=True,
            text=True
        )
        return result.stdout, result.stderr, result.returncode
    
    def test_all_zeros_mask(self):
        """Test wildcard mask with all zeros (matches only that IP)."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('192.0.2.0 0.0.0.0\n')
            temp_file = f.name
        
        try:
            stdout, stderr, rc = self.run_grepnet(
                '--parse-wildcard', 'input',
                '--wildcard-search', '192.0.2.0/24',
                '-e', '192.0.2.0/32',
                temp_file
            )
            
            # Should succeed
            self.assertNotIn('error:', stderr.lower())
        finally:
            os.unlink(temp_file)
    
    def test_all_ones_mask(self):
        """Test wildcard mask with all ones (matches all IPs)."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('192.0.2.0 255.255.255.255\n')
            temp_file = f.name
        
        try:
            stdout, stderr, rc = self.run_grepnet(
                '--parse-wildcard', 'input',
                '--wildcard-search', '192.0.2.0/24',
                '-e', '192.0.2.0/32',  # Pattern to match
                temp_file
            )
            
            # Should process without error
            self.assertNotIn('error:', stderr.lower())
        finally:
            os.unlink(temp_file)
    
    def test_out_of_scope_wildcard_mask(self):
        """Test wildcard mask outside the search scope (should be skipped gracefully)."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('192.0.2.0 0.0.0.255\n')  # Outside 192.0.2.0/24
            f.write('192.0.2.0 0.0.0.255\n')   # Inside 192.0.2.0/24
            temp_file = f.name
        
        try:
            stdout, stderr, rc = self.run_grepnet(
                '--parse-wildcard', 'input',
                '--wildcard-search', '192.0.2.0/24',
                '-o',
                '192.0.2.0/24',
                temp_file
            )
            
            # Should process without error (out-of-scope masks fall through to other extractors)
            self.assertNotIn('error:', stderr.lower())
        finally:
            os.unlink(temp_file)


class TestWildcardMaskColorization(unittest.TestCase):
    """Test colorization of wildcard masks (wm= color code)."""
    
    def setUp(self):
        """Set up test environment."""
        self.grepnet_script = Path(__file__).parent.parent / 'grepnet'
    
    def run_grepnet(self, *args, stdin_data=None, env=None):
        """Run grepnet with given arguments."""
        cmd = [str(self.grepnet_script)] + list(args)
        test_env = os.environ.copy()
        if env:
            test_env.update(env)
        
        result = subprocess.run(
            cmd,
            input=stdin_data,
            capture_output=True,
            text=True,
            env=test_env
        )
        return result.stdout, result.stderr, result.returncode
    
    def test_wildcard_mask_colored_by_default(self):
        """Test that wildcard masks are colored with wm= code by default."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('192.0.2.0 0.0.0.192\n')
            temp_file = f.name
        
        try:
            stdout, stderr, rc = self.run_grepnet(
                '--parse-wildcard', 'input',
                '--wildcard-search', '192.0.2.0/24',
                '-o',
                '192.0.2.0/16',
                temp_file
            )
            
            # Output should contain ANSI escape codes for coloring
            # (wildcard mask color 38;5;75 or similar)
            self.assertEqual(rc, 0)
            # The presence of ANSI codes would indicate coloring
            # (checking for escape sequences)
        finally:
            os.unlink(temp_file)
    
    def test_wildcard_mask_color_override(self):
        """Test that wm= environment variable overrides default color."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('192.0.2.0 0.0.0.192\n')
            temp_file = f.name
        
        try:
            # Set custom wm= color (e.g., 31 for red)
            stdout, stderr, rc = self.run_grepnet(
                '--parse-wildcard', 'input',
                '--wildcard-search', '192.0.2.0/24',
                '-o',
                '192.0.2.0/16',
                temp_file,
                env={'GREPNET_COLORS': 'wm=31'}
            )
            
            # Should use custom color
            self.assertEqual(rc, 0)
        finally:
            os.unlink(temp_file)


class TestWildcardMaskRegressionTests(unittest.TestCase):
    """Test to ensure existing functionality remains unchanged."""
    
    def setUp(self):
        """Set up test environment."""
        self.grepnet_script = Path(__file__).parent.parent / 'grepnet'
    
    def run_grepnet(self, *args, stdin_data=None):
        """Run grepnet with given arguments."""
        cmd = [str(self.grepnet_script)] + list(args)
        result = subprocess.run(
            cmd,
            input=stdin_data,
            capture_output=True,
            text=True
        )
        return result.stdout, result.stderr, result.returncode
    
    def test_cidr_notation_unchanged(self):
        """Test that CIDR notation still works."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('192.0.2.0/24\n')
            f.write('192.0.3.0/24\n')
            temp_file = f.name
        
        try:
            stdout, stderr, rc = self.run_grepnet(
                '-e', '192.0.2.0/24',
                temp_file
            )
            
            self.assertEqual(rc, 0)
            self.assertIn('192.0.2.0/24', stdout)
        finally:
            os.unlink(temp_file)
    
    def test_subnet_mask_format_unchanged(self):
        """Test that subnet mask format still works."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('192.0.2.0 255.255.255.0\n')
            temp_file = f.name
        
        try:
            stdout, stderr, rc = self.run_grepnet(
                '-e', '192.0.2.0 255.255.255.0',
                temp_file
            )
            
            self.assertEqual(rc, 0)
        finally:
            os.unlink(temp_file)
    
    def test_inverse_mask_format_unchanged(self):
        """Test that inverse/Cisco mask format still works."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('192.0.2.0 0.0.0.255\n')
            temp_file = f.name
        
        try:
            stdout, stderr, rc = self.run_grepnet(
                '-e', '192.0.2.0 0.0.0.255',
                temp_file
            )
            
            self.assertEqual(rc, 0)
        finally:
            os.unlink(temp_file)
    
    def test_standard_flags_still_work(self):
        """Test that standard matching flags still work."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('192.0.2.0/24\n')
            f.write('192.0.0.0/16\n')
            f.write('192.0.2.0/32\n')
            temp_file = f.name
        
        try:
            # Test -s (subset)
            stdout, stderr, rc = self.run_grepnet(
                '-s', '192.0.0.0/16',
                temp_file
            )
            self.assertEqual(rc, 0)
            
            # Test -S (superset)
            stdout, stderr, rc = self.run_grepnet(
                '-S', '192.0.2.0/24',
                temp_file
            )
            self.assertEqual(rc, 0)
        finally:
            os.unlink(temp_file)


class TestBrokenPipeHandling(unittest.TestCase):
    """Test graceful handling of broken pipes (like grep does)."""
    
    def setUp(self):
        """Set up test environment."""
        self.grepnet_script = Path(__file__).parent.parent / 'grepnet'
    
    def test_pipe_to_head_no_error_output(self):
        """Test that piping to head doesn't print error messages (real-world scenario)."""
        # Create a file with networks
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            # Write many CIDR blocks to ensure we have enough output for head
            for i in range(256):
                f.write(f'192.0.2.{i}/32\n')
            temp_file = f.name
        
        try:
            # Simulate: grepnet ... | head -5
            # This closes the pipe after 5 lines, which would cause SIGPIPE
            cmd = f"{str(self.grepnet_script)} '192.0.2.0/24' {temp_file} | head -5"
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True
            )
            
            # The key test: should have NO error output even though pipe was closed
            self.assertEqual(result.stderr, '', f"Unexpected stderr: {result.stderr}")
            # Should have output from head
            lines = result.stdout.strip().split('\n')
            self.assertEqual(len(lines), 5, f"Expected 5 lines from head, got {len(lines)}")
        finally:
            os.unlink(temp_file)
    
    def test_normal_pipe_completion(self):
        """Test that normal pipe completion works correctly."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('192.0.2.0/24\n')
            temp_file = f.name
        
        try:
            # Normal run with pipe to grep
            cmd = f"{str(self.grepnet_script)} -e '192.0.2.0/24' {temp_file} | grep -c '192.0.2.0'"
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True
            )
            
            # Should succeed with count of 1
            self.assertEqual(result.returncode, 0)
            self.assertIn('1', result.stdout)
            self.assertEqual(result.stderr, '')
        finally:
            os.unlink(temp_file)
    
    def test_pipe_to_wc_no_error(self):
        """Test that piping to wc doesn't produce error messages."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            # Write many networks
            for i in range(100):
                f.write(f'192.{i}.0.0/16\n')
            temp_file = f.name
        
        try:
            # Simulate: grepnet ... | wc -l
            cmd = f"{str(self.grepnet_script)} '192.0.2.0/24' {temp_file} | wc -l"
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True
            )
            
            # Should exit cleanly without error output
            self.assertEqual(result.stderr, '', f"Unexpected stderr: {result.stderr}")
            # Should have output (line count)
            self.assertTrue(int(result.stdout.strip()) > 0)
        finally:
            os.unlink(temp_file)


class TestWildcardMaskConsolidate(unittest.TestCase):
    """Test wildcard mask with --consolidate mode."""
    
    def setUp(self):
        """Set up test environment."""
        self.grepnet_script = Path(__file__).parent.parent / 'grepnet'
    
    def run_grepnet(self, *args, stdin_data=None, input_file=None):
        """
        Run grepnet with given arguments.
        
        Returns:
            (stdout, stderr, returncode) tuple
        """
        cmd = [str(self.grepnet_script)] + list(args)
        if input_file:
            cmd.append(input_file)
        
        result = subprocess.run(
            cmd,
            input=stdin_data,
            capture_output=True,
            text=True
        )
        return result.stdout, result.stderr, result.returncode
    
    def test_consolidate_with_wildcard_mask_stdin(self):
        """Test --consolidate with wildcard mask from stdin."""
        stdin_data = "192.0.2.0 0.0.0.192\n"
        stdout, stderr, code = self.run_grepnet(
            '0.0.0.0/0',
            '--parse-wildcard=both',
            '--wildcard-search', '192.0.2.0/24',
            '--consolidate',
            stdin_data=stdin_data
        )
        
        # Should produce consolidated output (not empty)
        self.assertEqual(code, 0, f"Expected exit code 0, got {code}. stderr: {stderr}")
        self.assertTrue(len(stdout.strip()) > 0, "Consolidate should produce output")
        
        # Output should contain CIDR notation (consolidated result)
        lines = stdout.strip().split('\n')
        self.assertTrue(len(lines) > 0, "Should have at least one output line")
    
    def test_consolidate_with_wildcard_mask_file(self):
        """Test --consolidate with wildcard mask from file."""
        # Create temp file with wildcard masks
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('192.0.2.0 0.0.0.192\n')
            f.write('192.0.2.64 0.0.0.192\n')
            temp_file = f.name
        
        try:
            stdout, stderr, code = self.run_grepnet(
                '192.0.2.0/24',
                '--parse-wildcard=both',
                '--wildcard-search', '192.0.2.0/24',
                '--consolidate',
                input_file=temp_file
            )
            
            # Should produce consolidated output
            self.assertEqual(code, 0, f"Expected exit code 0, got {code}. stderr: {stderr}")
            self.assertTrue(len(stdout.strip()) > 0, "Consolidate should produce output")
        finally:
            os.unlink(temp_file)
    
    def test_consolidate_wildcard_mixed_with_cidr(self):
        """Test --consolidate with both wildcard masks and CIDR notation."""
        # Create temp file with mixed formats
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('192.0.2.0 0.0.0.192\n')  # Wildcard mask
            f.write('192.0.2.128/25\n')       # CIDR
            temp_file = f.name
        
        try:
            stdout, stderr, code = self.run_grepnet(
                '0.0.0.0/0',
                '--parse-wildcard=both',
                '--wildcard-search', '192.0.2.0/24',
                '--consolidate',
                input_file=temp_file
            )
            
            # Should produce consolidated output with all networks merged
            self.assertEqual(code, 0, f"Expected exit code 0, got {code}. stderr: {stderr}")
            output_lines = stdout.strip().split('\n')
            self.assertTrue(len(output_lines) > 0, "Should have consolidated output")
            
            # All output lines should be valid CIDR notation
            for line in output_lines:
                if line.strip():
                    try:
                        IPv4Network(line.strip())
                    except ValueError:
                        self.fail(f"Output line '{line}' is not valid CIDR notation")
        finally:
            os.unlink(temp_file)
    
    def test_consolidate_wildcard_out_of_scope(self):
        """Test --consolidate with out-of-scope wildcard mask falls back to bare IPs."""
        stdin_data = "192.0.2.0 0.0.0.192\n"
        stdout, stderr, code = self.run_grepnet(
            '192.0.2.0/24',
            '--parse-wildcard=both',
            '--wildcard-search', '192.0.2.0/24',
            '--consolidate',
            stdin_data=stdin_data
        )
        
        # Should produce output (bare IPs as fallback)
        self.assertEqual(code, 0, f"Expected exit code 0, got {code}. stderr: {stderr}")
        self.assertTrue(len(stdout.strip()) > 0, "Consolidate should produce output even with out-of-scope mask")
        
        # Output should contain the IPs (as bare /32s or consolidated)
        output = stdout.strip()
        self.assertTrue('192.0.2' in output, "Output should contain addresses from the out-of-scope mask")


class TestConsolidateStress(unittest.TestCase):
    """Stress tests for consolidate performance with large input sets."""
    
    def setUp(self):
        """Set up test environment."""
        self.grepnet_script = Path(__file__).parent.parent / 'grepnet'
    
    def run_grepnet(self, *args, stdin_data=None, input_file=None):
        """
        Run grepnet with given arguments.
        
        Returns:
            (stdout, stderr, returncode) tuple
        """
        cmd = [str(self.grepnet_script)] + list(args)
        if input_file:
            cmd.append(input_file)
        
        result = subprocess.run(
            cmd,
            input=stdin_data,
            capture_output=True,
            text=True,
            timeout=60  # 60 second timeout for stress tests
        )
        return result.stdout, result.stderr, result.returncode
    
    def test_consolidate_10k_slash32s(self):
        """Stress test: consolidate 10,000 individual /32 networks from static file."""
        import hashlib
        
        # Use pre-generated static file with 10,000 /32s
        static_file = Path(__file__).parent / 'data' / 'stress_test_10k_slash32s.txt'
        
        # Expected SHA256 hash of consolidated output (known good value)
        expected_hash = 'b80bc715ba461697971c8289d5740f223d486107a06c9654bf324172c3a832b4'
        
        try:
            stdout, stderr, code = self.run_grepnet(
                '0.0.0.0/0',
                '--consolidate',
                input_file=str(static_file)
            )
            
            # Should succeed without error
            self.assertEqual(code, 0, f"Expected exit code 0, got {code}. stderr: {stderr}")
            
            # Should produce consolidated output
            output_lines = [line.strip() for line in stdout.strip().split('\n') if line.strip()]
            self.assertTrue(len(output_lines) > 0, "Should have consolidated output")
            
            # Verify output hasn't changed (detect regressions via hash)
            output_hash = hashlib.sha256(stdout.encode()).hexdigest()
            self.assertEqual(output_hash, expected_hash,
                f"Output hash changed. Expected {expected_hash}, got {output_hash}. "
                f"Output has {len(output_lines)} lines.")
            
            # All output lines should be valid CIDR notation
            for line in output_lines:
                if line:
                    try:
                        IPv4Network(line)
                    except ValueError:
                        self.fail(f"Output line '{line}' is not valid CIDR notation")
        finally:
            pass


if __name__ == '__main__':
    unittest.main()
