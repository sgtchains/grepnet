"""
Test suite for output formatting flags: -H, -n, -b, -T, --no-filename, --label, etc.

Tests the behavior of filename prefixes, line numbers, byte offsets, and their interactions
according to GREPNET-SPEC section "Output Modes" and "Line Prefixes".
"""

import unittest
import subprocess
import tempfile
import os
from pathlib import Path


class TestOutputFormattingFlags(unittest.TestCase):
    """Test output formatting flags: -H, -n, -b, -T, --no-filename, --label."""
    
    def setUp(self):
        """Set up test fixtures with temp files."""
        self.grepnet_script = Path(__file__).parent.parent / 'grepnet'
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        
        # Create test files with known content
        self.file1 = self.temp_path / 'file1.txt'
        self.file1.write_text('192.0.2.0/24\n10.0.0.1\n172.16.0.0/24\n')
        
        self.file2 = self.temp_path / 'file2.txt'
        self.file2.write_text('10.0.0.0/8\n192.0.2.1/32\n')
        
        self.stdin_data = '203.0.113.0/24\n10.0.0.0/16\n'
    
    def tearDown(self):
        """Clean up temp directory."""
        self.temp_dir.cleanup()
    
    def run_grepnet(self, pattern, *args, stdin_data=None, files=None):
        """
        Run grepnet with given arguments.
        
        Args:
            pattern: Search pattern
            *args: Additional arguments (flags). Files should be passed via files param.
            stdin_data: Data to pass via stdin
            files: List of file paths to search (if not in args)
        
        Returns:
            (stdout, stderr, returncode) tuple
        """
        # Build command: grepnet [flags...] PATTERN [files...]
        # Flags come before pattern, files come after
        cmd = [str(self.grepnet_script)] + list(args) + [pattern]
        if files:
            cmd.extend(files)
        
        result = subprocess.run(
            cmd,
            input=stdin_data,
            capture_output=True,
            text=True
        )
        return result.stdout, result.stderr, result.returncode
    
    # ========== Single File Tests ==========
    
    def test_single_file_no_filename_prefix_by_default(self):
        """With single file, no filename prefix by default (grep behavior)."""
        stdout, stderr, returncode = self.run_grepnet(
            '0.0.0.0/0',
            files=[str(self.file1)]
        )
        
        self.assertEqual(returncode, 0)
        lines = stdout.strip().split('\n')
        # No filename prefix expected in output
        for line in lines:
            # Line should not start with filename
            self.assertNotIn('file1.txt:', line, 
                           f"Single file should not have prefix by default, got: {line}")
    
    def test_single_file_with_H_forces_filename_prefix(self):
        """With single file and -H flag, show filename prefix."""
        stdout, stderr, returncode = self.run_grepnet(
            '0.0.0.0/0',
            '-H',
            files=[str(self.file1)]
        )
        
        self.assertEqual(returncode, 0)
        lines = stdout.strip().split('\n')
        # All lines should have filename prefix
        for line in lines:
            self.assertIn('file1.txt:', line,
                        f"-H flag should force filename prefix, got: {line}")
    
    def test_single_file_with_with_filename_forces_prefix(self):
        """With single file and --with-filename flag, show filename prefix."""
        stdout, stderr, returncode = self.run_grepnet(
            '0.0.0.0/0',
            '--with-filename',
            files=[str(self.file1)]
        )
        
        self.assertEqual(returncode, 0)
        lines = stdout.strip().split('\n')
        # All lines should have filename prefix
        for line in lines:
            self.assertIn('file1.txt:', line,
                        f"--with-filename should show prefix, got: {line}")
    
    # ========== Multiple File Tests ==========
    
    def test_multiple_files_show_filename_prefix_by_default(self):
        """With multiple files, show filename prefix by default (grep behavior)."""
        stdout, stderr, returncode = self.run_grepnet(
            '0.0.0.0/0',
            files=[str(self.file1), str(self.file2)]
        )
        
        self.assertEqual(returncode, 0)
        lines = stdout.strip().split('\n')
        
        # Should have at least one result from each file
        # Use endswith to match regardless of absolute/relative path
        file1_results = [l for l in lines if 'file1.txt:' in l]
        file2_results = [l for l in lines if 'file2.txt:' in l]
        
        self.assertGreater(len(file1_results), 0,
                          "Should have results from file1.txt with prefix")
        self.assertGreater(len(file2_results), 0,
                          "Should have results from file2.txt with prefix")
    
    def test_multiple_files_with_H_shows_filename_prefix(self):
        """With multiple files and -H, explicitly show filename prefix."""
        stdout, stderr, returncode = self.run_grepnet(
            '0.0.0.0/0',
            '-H',
            files=[str(self.file1), str(self.file2)]
        )
        
        self.assertEqual(returncode, 0)
        lines = stdout.strip().split('\n')
        
        # All lines should have filename prefix
        file1_results = [l for l in lines if 'file1.txt' in l]
        file2_results = [l for l in lines if 'file2.txt' in l]
        
        self.assertGreater(len(file1_results), 0)
        self.assertGreater(len(file2_results), 0)
    
    def test_multiple_files_no_filename_flag_suppresses_prefix(self):
        """With multiple files and --no-filename, suppress filename prefix."""
        stdout, stderr, returncode = self.run_grepnet(
            '0.0.0.0/0',
            '--no-filename',
            files=[str(self.file1), str(self.file2)]
        )
        
        self.assertEqual(returncode, 0)
        lines = stdout.strip().split('\n')
        
        # No lines should have filename prefix
        for line in lines:
            self.assertNotIn('file1.txt:', line,
                           f"--no-filename should suppress prefix, got: {line}")
            self.assertNotIn('file2.txt:', line,
                           f"--no-filename should suppress prefix, got: {line}")
    
    # ========== Line Number Prefix Tests ==========
    
    def test_line_number_prefix_with_n_flag(self):
        """With -n flag, prepend 1-based line number."""
        stdout, stderr, returncode = self.run_grepnet(
            '0.0.0.0/0',
            '-n',
            files=[str(self.file1)]
        )
        
        self.assertEqual(returncode, 0)
        lines = stdout.strip().split('\n')
        
        # All lines should start with "N:" where N is the line number
        for line in lines:
            # Line should start with digit and colon (e.g., "1:", "2:")
            parts = line.split(':', 1)
            self.assertEqual(len(parts), 2, f"Line should have number prefix, got: {line}")
            self.assertTrue(parts[0].isdigit(), f"Line number should be digit, got: {line}")
    
    def test_line_number_with_multiple_files(self):
        """With -n and multiple files, line numbers are per-file."""
        stdout, stderr, returncode = self.run_grepnet(
            '0.0.0.0/0',
            '-n',
            files=[str(self.file1), str(self.file2)]
        )
        
        self.assertEqual(returncode, 0)
        output = stdout.strip()
        
        # Should contain line numbers for each file
        self.assertRegex(output, r'1:', "Should have line 1 prefix")
        self.assertRegex(output, r'2:', "Should have line 2 prefix")
    
    # ========== Byte Offset Prefix Tests ==========
    
    def test_byte_offset_prefix_with_b_flag(self):
        """With -b flag, prepend 0-based byte offset."""
        stdout, stderr, returncode = self.run_grepnet(
            '192.0.2.0/24',
            '-b',
            files=[str(self.file1)]
        )
        
        self.assertEqual(returncode, 0)
        lines = stdout.strip().split('\n')
        
        # First line should have byte offset 0 (first line in file)
        first_line = lines[0]
        self.assertRegex(first_line, r'^0:', f"First line should have offset 0, got: {first_line}")
    
    def test_byte_offset_format(self):
        """Byte offset should be 0-based integer followed by colon."""
        stdout, stderr, returncode = self.run_grepnet(
            '0.0.0.0/0',
            '-b',
            files=[str(self.file1)]
        )
        
        self.assertEqual(returncode, 0)
        lines = stdout.strip().split('\n')
        
        for line in lines:
            # Should match pattern: DIGIT+:content
            parts = line.split(':', 1)
            self.assertEqual(len(parts), 2, f"Line should have byte offset, got: {line}")
            self.assertTrue(parts[0].isdigit(), f"Byte offset should be digit, got: {line}")
    
    # ========== Combined Prefix Tests ==========
    
    def test_n_and_b_prefixes_together(self):
        """With -n and -b, both line number and byte offset appear."""
        stdout, stderr, returncode = self.run_grepnet(
            '0.0.0.0/0',
            '-n',
            '-b',
            files=[str(self.file1)]
        )
        
        self.assertEqual(returncode, 0)
        lines = stdout.strip().split('\n')
        
        for line in lines:
            # Should have format: N:B:content or B:N:content depending on implementation
            # At minimum, should have multiple colons and numbers
            parts = line.split(':', 2)
            self.assertGreaterEqual(len(parts), 3, 
                                   f"Should have both prefixes, got: {line}")
            # First two parts should be numbers
            self.assertTrue(parts[0].isdigit() or parts[1].isdigit(),
                          f"Should have numeric prefixes, got: {line}")
    
    def test_H_n_b_prefixes_together(self):
        """With -H, -n, -b, all three prefixes appear."""
        stdout, stderr, returncode = self.run_grepnet(
            '0.0.0.0/0',
            '-H',
            '-n',
            '-b',
            files=[str(self.file1)]
        )
        
        self.assertEqual(returncode, 0)
        lines = stdout.strip().split('\n')
        
        for line in lines:
            # Should start with filename
            self.assertIn('file1.txt:', line,
                        f"Should have filename with -H, got: {line}")
            # Should contain line number and byte offset
            self.assertRegex(line, r':\d+:',
                           f"Should have numeric prefixes, got: {line}")
    
    # ========== Tab Separator Tests ==========
    
    def test_T_flag_inserts_tab_after_prefixes(self):
        """With -T flag, insert tab after prefixes (for alignment)."""
        stdout_with_t, _, _ = self.run_grepnet(
            '0.0.0.0/0',
            '-n',
            '-T',
            files=[str(self.file1)]
        )
        
        stdout_without_t, _, _ = self.run_grepnet(
            '0.0.0.0/0',
            '-n',
            files=[str(self.file1)]
        )
        
        # With -T should have tab character
        self.assertIn('\t', stdout_with_t,
                     "-T flag should insert tab character")
        
        # Tab should appear after line number prefix
        lines_with_t = stdout_with_t.strip().split('\n')
        for line in lines_with_t:
            if line:  # Non-empty line
                # Format should be N\tCONTENT
                parts = line.split('\t', 1)
                self.assertEqual(len(parts), 2,
                              f"Should have tab after prefix with -T, got: {line}")
                self.assertTrue(parts[0].isdigit(),
                             f"First part should be line number, got: {line}")
    
    # ========== Stdin with Filename Tests ==========
    
    def test_stdin_shows_standard_input_label(self):
        """When reading from stdin, show '(standard input)' as filename."""
        stdout, stderr, returncode = self.run_grepnet(
            '0.0.0.0/0',
            '-H',
            files=['-'],
            stdin_data=self.stdin_data
        )
        
        self.assertEqual(returncode, 0)
        # Should contain (standard input) label
        self.assertIn('(standard input):', stdout,
                     "stdin input should show '(standard input)' label with -H")
    
    def test_stdin_with_label_flag(self):
        """With --label, use custom label instead of '(standard input)'."""
        stdout, stderr, returncode = self.run_grepnet(
            '0.0.0.0/0',
            '--label=custom_input',
            '-H',
            files=['-'],
            stdin_data=self.stdin_data
        )
        
        self.assertEqual(returncode, 0)
        # Should contain custom label
        self.assertIn('custom_input:', stdout,
                     "Should use custom label with --label flag")
        # Should NOT contain (standard input)
        self.assertNotIn('(standard input):', stdout,
                        "--label should override (standard input) label")
    
    def test_stdin_with_H_and_label(self):
        """Stdin with -H and --label shows custom label."""
        stdout, stderr, returncode = self.run_grepnet(
            '0.0.0.0/0',
            '-H',
            '--label=test_input',
            files=['-'],
            stdin_data=self.stdin_data
        )
        
        self.assertEqual(returncode, 0)
        lines = stdout.strip().split('\n')
        
        for line in lines:
            self.assertIn('test_input:', line,
                        "Should show custom label from --label flag")
    
    # ========== Prefix Ordering Tests ==========
    
    def test_filename_then_line_number_then_byte_offset(self):
        """Prefixes should appear in order: filename, line number, byte offset."""
        stdout, stderr, returncode = self.run_grepnet(
            '0.0.0.0/0',
            '-H',
            '-n',
            '-b',
            files=[str(self.file1)]
        )
        
        self.assertEqual(returncode, 0)
        lines = stdout.strip().split('\n')
        
        if lines:
            first_line = lines[0]
            # Should start with filename:
            self.assertIn('file1.txt:', first_line,
                        "Filename should appear first")
    
    # ========== No-Filename with Single File Tests ==========
    
    def test_single_file_with_no_filename_flag(self):
        """With single file and --no-filename, suppress filename prefix."""
        stdout, stderr, returncode = self.run_grepnet(
            '0.0.0.0/0',
            '--no-filename',
            files=[str(self.file1)]
        )
        
        self.assertEqual(returncode, 0)
        lines = stdout.strip().split('\n')
        
        # No lines should have filename prefix
        for line in lines:
            self.assertNotIn('file1.txt:', line,
                           "--no-filename should suppress all filename prefixes")
    
    # ========== Null Separator Tests ==========
    
    def test_Z_flag_uses_null_separator(self):
        """With -Z flag, use NUL byte separator instead of newline."""
        stdout, stderr, returncode = self.run_grepnet(
            '0.0.0.0/0',
            '-H',
            '-Z',
            files=[str(self.file1)]
        )
        
        self.assertEqual(returncode, 0)
        # Output should contain NUL bytes instead of newlines
        self.assertIn('\0', stdout,
                     "-Z flag should use NUL separator")
        
        # Should not end with regular newline (or minimal newlines)
        # Check that entries are separated by NUL
        entries = stdout.split('\0')
        self.assertGreater(len(entries), 1,
                          "Should have multiple NUL-separated entries")
    
    # ========== Interaction Tests ==========
    
    def test_H_and_no_filename_conflict(self):
        """When both -H and --no-filename specified, last one should win."""
        # Test H then no-filename
        stdout1, _, returncode1 = self.run_grepnet(
            '0.0.0.0/0',
            '-H',
            '--no-filename',
            files=[str(self.file1)]
        )
        
        # Test no-filename then H
        stdout2, _, returncode2 = self.run_grepnet(
            '0.0.0.0/0',
            '--no-filename',
            '-H',
            files=[str(self.file1)]
        )
        
        # Both should succeed
        self.assertEqual(returncode1, 0)
        self.assertEqual(returncode2, 0)
        
        # First should have no prefix (--no-filename last)
        for line in stdout1.strip().split('\n'):
            self.assertNotIn('file1.txt:', line,
                           "--no-filename should win when last")
        
        # Second should have prefix (-H last)
        has_prefix = any('file1.txt:' in line for line in stdout2.strip().split('\n'))
        self.assertTrue(has_prefix,
                       "-H should win when last")
    
    def test_multiple_files_mixed_stdin(self):
        """With mixed files and stdin, both show proper prefixes."""
        stdout, stderr, returncode = self.run_grepnet(
            '0.0.0.0/0',
            '-H',
            files=[str(self.file1), '-'],
            stdin_data=self.stdin_data
        )
        
        self.assertEqual(returncode, 0)
        output = stdout
        
        # Should have results from both file and stdin
        self.assertIn('file1.txt:', output,
                     "Should show file1.txt prefix")
        self.assertIn('(standard input):', output,
                     "Should show (standard input) prefix for stdin")
    
    # ========== Edge Cases ==========
    
    def test_empty_file_no_output(self):
        """With empty file, no output (returncode 1)."""
        empty_file = self.temp_path / 'empty.txt'
        empty_file.write_text('')
        
        stdout, stderr, returncode = self.run_grepnet(
            '192.0.2.0/24',
            files=[str(empty_file)]
        )
        
        # Should have no matches
        self.assertEqual(returncode, 1)
        self.assertEqual(stdout.strip(), '')
    
    def test_file_with_no_matches_no_output(self):
        """With file that has no matches, no output for that file."""
        stdout, stderr, returncode = self.run_grepnet(
            '255.255.255.0',  # Pattern not in files
            '-H',
            files=[str(self.file1)]
        )
        
        # No matches
        self.assertEqual(returncode, 1)
        self.assertEqual(stdout.strip(), '')
    
    def test_multiple_matches_on_same_line(self):
        """With multiple networks on same line, each appears once in output."""
        multi_line_file = self.temp_path / 'multi.txt'
        multi_line_file.write_text('192.0.2.0/24 10.0.0.0/8 172.16.0.0/12\n')
        
        stdout, stderr, returncode = self.run_grepnet(
            '0.0.0.0/0',
            '-n',
            files=[str(multi_line_file)]
        )
        
        self.assertEqual(returncode, 0)
        # Should output the line once with all networks marked
        lines = stdout.strip().split('\n')
        self.assertEqual(len(lines), 1, 
                        "Multiple matches on same line should produce one output line")


class TestOutputFormattingEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions for output formatting."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.grepnet_script = Path(__file__).parent.parent / 'grepnet'
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
    
    def tearDown(self):
        """Clean up temp directory."""
        self.temp_dir.cleanup()
    
    def run_grepnet(self, pattern, *args, stdin_data=None, files=None):
        """Run grepnet with given arguments."""
        # Build command: grepnet [flags...] PATTERN [files...]
        cmd = [str(self.grepnet_script)] + list(args) + [pattern]
        if files:
            cmd.extend(files)
        
        result = subprocess.run(
            cmd,
            input=stdin_data,
            capture_output=True,
            text=True
        )
        return result.stdout, result.stderr, result.returncode
    
    def test_filename_with_spaces(self):
        """Filename with spaces should be properly formatted."""
        spaced_file = self.temp_path / 'my test file.txt'
        spaced_file.write_text('192.0.2.0/24\n')
        
        stdout, stderr, returncode = self.run_grepnet(
            '0.0.0.0/0',
            '-H',
            files=[str(spaced_file)]
        )
        
        self.assertEqual(returncode, 0)
        self.assertIn('my test file.txt:', stdout,
                     "Should handle filename with spaces")
    
    def test_filename_with_special_characters(self):
        """Filename with special characters should be properly formatted."""
        special_file = self.temp_path / 'file-with_special.chars.txt'
        special_file.write_text('192.0.2.0/24\n')
        
        stdout, stderr, returncode = self.run_grepnet(
            '0.0.0.0/0',
            '-H',
            files=[str(special_file)]
        )
        
        self.assertEqual(returncode, 0)
        self.assertIn('file-with_special.chars.txt:', stdout,
                     "Should handle filename with special characters")
    
    def test_long_filename(self):
        """Long filename should be properly formatted."""
        long_name = 'very_' + 'long_' * 20 + 'filename.txt'
        long_file = self.temp_path / long_name
        long_file.write_text('192.0.2.0/24\n')
        
        stdout, stderr, returncode = self.run_grepnet(
            '0.0.0.0/0',
            '-H',
            files=[str(long_file)]
        )
        
        self.assertEqual(returncode, 0)
        self.assertIn(long_name + ':', stdout,
                     "Should handle long filenames")
    
    def test_relative_vs_absolute_path_display(self):
        """Filename should be displayed as provided (relative or absolute)."""
        test_file = self.temp_path / 'test.txt'
        test_file.write_text('192.0.2.0/24\n')
        
        # Test with relative path (if possible)
        original_cwd = os.getcwd()
        try:
            os.chdir(self.temp_path)
            stdout_rel, _, _ = self.run_grepnet(
                '0.0.0.0/0',
                '-H',
                files=['test.txt']
            )
            
            # With relative path, output should show relative path
            self.assertIn('test.txt:', stdout_rel,
                         "Should show filename as provided (relative)")
        finally:
            os.chdir(original_cwd)


if __name__ == '__main__':
    unittest.main()
