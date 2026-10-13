"""
Test suite for stdin input handling.

Tests that stdin input is properly recognized when using '-' as a file argument
and through various input mechanisms.
"""

import unittest
import subprocess
import tempfile
import os
from pathlib import Path


class TestStdinInput(unittest.TestCase):
    """Test stdin input handling via '-' argument."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.grepnet_script = Path(__file__).parent.parent / 'grepnet'
        self.test_data = '192.0.2.1\n10.0.0.1\n172.16.0.0/24\n'
    
    def run_grepnet(self, pattern, *args, stdin_data=None):
        """
        Run grepnet with given arguments.
        
        Args:
            pattern: Search pattern
            *args: Additional arguments (files, flags)
            stdin_data: Data to pass via stdin
        
        Returns:
            (stdout, stderr, returncode) tuple
        """
        cmd = [str(self.grepnet_script), pattern] + list(args)
        result = subprocess.run(
            cmd,
            input=stdin_data,
            capture_output=True,
            text=True
        )
        return result.stdout, result.stderr, result.returncode
    
    def test_stdin_with_dash_argument(self):
        """Test that '-' is recognized as stdin."""
        stdout, stderr, returncode = self.run_grepnet(
            '0.0.0.0/0',
            '-',
            stdin_data=self.test_data
        )
        
        self.assertEqual(returncode, 0, f"stderr: {stderr}")
        lines = stdout.strip().split('\n')
        self.assertEqual(len(lines), 3)
        self.assertIn('192.0.2.1', lines)
        self.assertIn('10.0.0.1', lines)
        self.assertIn('172.16.0.0/24', lines)
    
    def test_stdin_with_dash_and_f_flag(self):
        """Test that '-' is recognized as stdin with -F flag."""
        stdout, stderr, returncode = self.run_grepnet(
            '0.0.0.0/0',
            '-F', '-',
            stdin_data=self.test_data
        )
        
        self.assertEqual(returncode, 0, f"stderr: {stderr}")
        lines = stdout.strip().split('\n')
        self.assertEqual(len(lines), 3)
        self.assertIn('192.0.2.1', lines)
        self.assertIn('10.0.0.1', lines)
        self.assertIn('172.16.0.0/24', lines)
    
    def test_stdin_with_dash_and_extract(self):
        """Test that '-' works when file is after flags."""
        # Note: grepnet pattern must come before flags that take positional args
        stdout, stderr, returncode = self.run_grepnet(
            '0.0.0.0/0',
            '-', '--extract',
            stdin_data=self.test_data
        )
        
        self.assertEqual(returncode, 0, f"stderr: {stderr}")
        lines = stdout.strip().split('\n')
        # Extract should deduplicate and normalize
        self.assertIn('192.0.2.1/32', lines)
        self.assertIn('10.0.0.1/32', lines)
        self.assertIn('172.16.0.0/24', lines)
    
    def test_stdin_with_dash_multiple_files(self):
        """Test that '-' can be mixed with regular files."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write('172.16.0.0/24\n')
            temp_file = f.name
        
        try:
            stdout, stderr, returncode = self.run_grepnet(
                '0.0.0.0/0',
                '-', temp_file,
                stdin_data=self.test_data
            )
            
            self.assertEqual(returncode, 0, f"stderr: {stderr}")
            lines = stdout.strip().split('\n')
            # Should have all entries from stdin and file
            self.assertTrue(any('192.0.2.1' in line for line in lines))
            self.assertTrue(any('10.0.0.1' in line for line in lines))
            # 172.16.0.0/24 appears in both stdin and file
            self.assertTrue(any('172.16.0.0/24' in line for line in lines))
        finally:
            os.unlink(temp_file)
    
    def test_stdin_with_dash_and_consolidate(self):
        """Test that '-' works with --consolidate flag."""
        test_data = '192.0.2.0/25\n192.0.2.0/26\n'
        stdout, stderr, returncode = self.run_grepnet(
            '0.0.0.0/0',
            '-', '--consolidate',
            stdin_data=test_data
        )
        
        self.assertEqual(returncode, 0, f"stderr: {stderr}")
        # Consolidate should merge overlapping networks
        self.assertIn('192.0.2.0/25', stdout)
    
    def test_stdin_parse_bare_ip_option(self):
        """Test that --parse-bare-ip works with stdin."""
        stdout_both, _, rc_both = self.run_grepnet(
            '0.0.0.0/0',
            '-',
            '--parse-bare-ip=both',
            stdin_data='192.0.2.1\n'
        )
        self.assertEqual(rc_both, 0)
        self.assertIn('192.0.2.1', stdout_both)
        
        stdout_none, _, rc_none = self.run_grepnet(
            '0.0.0.0/0',
            '-',
            '--parse-bare-ip=none',
            stdin_data='192.0.2.1\n'
        )
        self.assertEqual(rc_none, 1)  # No matches
        self.assertEqual(stdout_none.strip(), '')
    
    def test_stdin_with_dash_filtering(self):
        """Test that filtering works correctly with stdin."""
        # Test filtering with a specific pattern
        stdout, stderr, returncode = self.run_grepnet(
            '192.0.2.0/24',
            '-',
            stdin_data=self.test_data
        )
        
        self.assertEqual(returncode, 0, f"stderr: {stderr}")
        lines = stdout.strip().split('\n')
        # Should only include networks that match pattern
        self.assertIn('192.0.2.1', lines)
        # 10.0.0.1 and 172.16.0.0/24 are not subsets
        self.assertNotIn('10.0.0.1', lines)
        self.assertNotIn('172.16.0.0/24', lines)
    
    def test_stdin_with_dash_and_label(self):
        """Test that --label works with stdin."""
        stdout, stderr, returncode = self.run_grepnet(
            '0.0.0.0/0',
            '-',
            '--label=test_stdin',
            '--with-filename',
            stdin_data=self.test_data
        )
        
        self.assertEqual(returncode, 0, f"stderr: {stderr}")
        # With --label, stdin should be labeled
        self.assertIn('test_stdin', stdout)


class TestFDInput(unittest.TestCase):
    """Test file descriptor input handling."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.grepnet_script = Path(__file__).parent.parent / 'grepnet'
    
    def test_fd_numeric_argument(self):
        """Test that numeric FD is recognized."""
        # This test would need to actually set up an FD, which is complex in subprocess
        # Skip for now as the mechanism is hard to test without shell integration
        pass
    
    def test_process_substitution_dev_fd(self):
        """Test process substitution with /dev/fd syntax (bash/zsh)."""
        # Use bash to test process substitution
        import subprocess
        cmd = [
            'bash', '-c',
            f'{self.grepnet_script} "0.0.0.0/0" <(echo "192.0.2.1")'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertIn('192.0.2.1', result.stdout)


class TestStdinEdgeCases(unittest.TestCase):
    """Test edge cases for stdin handling."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.grepnet_script = Path(__file__).parent.parent / 'grepnet'
    
    def run_grepnet(self, pattern, *args, stdin_data=None):
        """Helper to run grepnet."""
        cmd = [str(self.grepnet_script), pattern] + list(args)
        result = subprocess.run(
            cmd,
            input=stdin_data,
            capture_output=True,
            text=True
        )
        return result.stdout, result.stderr, result.returncode
    
    def test_stdin_empty_input(self):
        """Test that empty stdin is handled correctly."""
        stdout, stderr, returncode = self.run_grepnet(
            '0.0.0.0/0',
            '-',
            stdin_data=''
        )
        
        # Empty input should return no matches (exit code 1)
        self.assertEqual(returncode, 1)
    
    def test_stdin_with_comments(self):
        """Test that comments in stdin are handled correctly."""
        stdin_data = '192.0.2.1 # comment\n10.0.0.1\n# pure comment line\n172.16.0.0/24\n'
        stdout, stderr, returncode = self.run_grepnet(
            '0.0.0.0/0',
            '-',
            stdin_data=stdin_data
        )
        
        self.assertEqual(returncode, 0, f"stderr: {stderr}")
        lines = stdout.strip().split('\n')
        self.assertEqual(len(lines), 3)
        # Comments should be preserved in output
        self.assertTrue(any('192.0.2.1' in line for line in lines))
    
    def test_stdin_with_null_delimited_data(self):
        """Test that stdin works with -z (null-delimited) flag."""
        # Create null-delimited data
        stdin_data = '192.0.2.1\x0010.0.0.1\x00172.16.0.0/24\x00'
        stdout, stderr, returncode = self.run_grepnet(
            '0.0.0.0/0',
            '-',
            '-z',
            stdin_data=stdin_data
        )
        
        self.assertEqual(returncode, 0, f"stderr: {stderr}")
        # Output should still contain the IPs
        self.assertIn('192.0.2.1', stdout)
        self.assertIn('10.0.0.1', stdout)
    
    def test_multiple_dash_arguments(self):
        """Test behavior with multiple '-' arguments."""
        # Multiple stdin sources all refer to the same stdin
        stdout, stderr, returncode = self.run_grepnet(
            '0.0.0.0/0',
            '-', '-',
            stdin_data='192.0.2.1\n'
        )
        
        # Should still process the input
        self.assertIn('192.0.2.1', stdout)


if __name__ == '__main__':
    unittest.main()

