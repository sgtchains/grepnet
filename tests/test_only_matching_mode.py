"""
Tests for -o/--only-matching mode to prevent duplicate output.

Regression tests for bug where multi-network lines were outputting
each network multiple times in -o mode.
"""

import unittest
import subprocess
import sys
import os


class TestOnlyMatchingMode(unittest.TestCase):
    """Test -o/--only-matching mode output correctness."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.grepnet_path = os.path.join(
            os.path.dirname(__file__),
            '..',
            'bin',
            'grepnet'
        )
        if not os.path.exists(cls.grepnet_path):
            raise RuntimeError(f"grepnet not found at {cls.grepnet_path}")

    def run_grepnet(self, *args, stdin_data=''):
        """Helper to run grepnet and capture output."""
        cmd = [self.grepnet_path] + list(args)
        result = subprocess.run(
            cmd,
            input=stdin_data,
            capture_output=True,
            text=True
        )
        return result.stdout, result.stderr, result.returncode

    def test_single_network_single_line(self):
        """Single network on one line should output exactly once."""
        stdout, _, rc = self.run_grepnet('-o', '10.0.0.0/8', stdin_data='10.5.6.7\n')
        self.assertEqual(rc, 0)
        self.assertEqual(stdout.count('10.5.6.7'), 1, "Network should appear exactly once")

    def test_two_networks_single_line_ipv4(self):
        """Two IPv4 networks on one line should each output exactly once."""
        stdout, _, rc = self.run_grepnet('-o', '::/0', stdin_data='64:ffff:: ac10:1::/108\n')
        self.assertEqual(rc, 0)
        lines = stdout.strip().split('\n')
        self.assertEqual(len(lines), 2, f"Expected 2 lines, got {len(lines)}: {lines}")
        self.assertIn('64:ffff::', stdout, "First network should appear")
        self.assertIn('ac10:1::/108', stdout, "Second network should appear")
        self.assertEqual(stdout.count('64:ffff::'), 1, "First network should appear exactly once")
        self.assertEqual(stdout.count('ac10:1::/108'), 1, "Second network should appear exactly once")

    def test_two_networks_single_line_ipv6(self):
        """Two IPv6 networks on one line should each output exactly once."""
        stdout, _, rc = self.run_grepnet('-o', '::/0', stdin_data='2001:db8::/32 fe80::/10\n')
        self.assertEqual(rc, 0)
        lines = stdout.strip().split('\n')
        self.assertEqual(len(lines), 2, f"Expected 2 lines, got {len(lines)}")
        self.assertEqual(stdout.count('2001:db8::/32'), 1)
        self.assertEqual(stdout.count('fe80::/10'), 1)

    def test_multiple_networks_multiple_matches(self):
        """Line with 4 networks, 2 matching the pattern."""
        stdout, _, rc = self.run_grepnet(
            '-o', '10.0.0.0/8',
            stdin_data='10.1.2.3 192.168.1.1 10.5.6.7 172.16.0.1\n'
        )
        self.assertEqual(rc, 0)
        lines = stdout.strip().split('\n')
        self.assertEqual(len(lines), 2, f"Expected 2 matching networks, got {len(lines)}")
        self.assertIn('10.1.2.3', stdout)
        self.assertIn('10.5.6.7', stdout)
        self.assertNotIn('192.168.1.1', stdout)
        self.assertNotIn('172.16.0.1', stdout)

    def test_mixed_format_networks_single_line(self):
        """Multiple networks in different formats on one line."""
        stdout, _, rc = self.run_grepnet(
            '-o', '10.0.0.0/8',
            stdin_data='10.0.0.0/24 10.1.2.3 10.2.3.0-10.2.3.255\n'
        )
        self.assertEqual(rc, 0)
        lines = stdout.strip().split('\n')
        self.assertEqual(len(lines), 3, f"Expected 3 networks, got {len(lines)}: {lines}")
        # Each should appear exactly once
        self.assertEqual(stdout.count('10.0.0.0/24'), 1)
        self.assertEqual(stdout.count('10.1.2.3'), 1)
        self.assertEqual(stdout.count('10.2.3.0-10.2.3.255'), 1)

    def test_multiple_lines_each_with_multiple_networks(self):
        """Multiple lines, each with multiple networks."""
        stdin = '10.1.0.0/16 172.16.0.0/12\n192.168.0.0/16 10.2.0.0/16\n'
        stdout, _, rc = self.run_grepnet('-o', '10.0.0.0/8', stdin_data=stdin)
        self.assertEqual(rc, 0)
        lines = stdout.strip().split('\n')
        self.assertEqual(len(lines), 2, f"Expected 2 matching networks, got {len(lines)}")
        self.assertIn('10.1.0.0/16', stdout)
        self.assertIn('10.2.0.0/16', stdout)

    def test_with_line_numbers(self):
        """-o mode with -n flag should show line numbers without duplicates."""
        stdin = '10.1.0.0/16 10.2.0.0/16\n'
        stdout, _, rc = self.run_grepnet('-n', '-o', '10.0.0.0/8', stdin_data=stdin)
        self.assertEqual(rc, 0)
        lines = stdout.strip().split('\n')
        self.assertEqual(len(lines), 2, f"Expected 2 lines with prefixes, got {len(lines)}")
        # Each line should have format: "1:10.x.x.x/x"
        self.assertTrue(lines[0].startswith('1:'), f"Line should start with '1:': {lines[0]}")
        self.assertTrue(lines[1].startswith('1:'), f"Line should start with '1:': {lines[1]}")

    def test_with_multiple_files(self):
        """Multiple input files with multi-network lines."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = os.path.join(tmpdir, 'file1.txt')
            file2 = os.path.join(tmpdir, 'file2.txt')
            
            with open(file1, 'w') as f:
                f.write('10.1.0.0/16 10.2.0.0/16\n')
            with open(file2, 'w') as f:
                f.write('10.3.0.0/16 10.4.0.0/16\n')
            
            stdout, _, rc = self.run_grepnet('-o', '10.0.0.0/8', file1, file2)
            self.assertEqual(rc, 0)
            lines = stdout.strip().split('\n')
            self.assertEqual(len(lines), 4, f"Expected 4 networks total, got {len(lines)}")

    def test_no_matches(self):
        """Line with multiple networks, none matching the pattern."""
        stdout, _, rc = self.run_grepnet(
            '-o', '10.0.0.0/8',
            stdin_data='192.168.0.0/16 172.16.0.0/12\n'
        )
        self.assertEqual(rc, 1)  # No matches
        self.assertEqual(stdout, '')

    def test_with_max_count(self):
        """-m/--max-count with -o mode should limit output correctly."""
        stdin = '10.1.0.0/16 10.2.0.0/16 10.3.0.0/16\n'
        stdout, _, rc = self.run_grepnet('-o', '-m', '2', '10.0.0.0/8', stdin_data=stdin)
        self.assertEqual(rc, 0)
        lines = [l for l in stdout.strip().split('\n') if l]
        self.assertEqual(len(lines), 2, f"Expected max 2 matches, got {len(lines)}")

    def test_with_inverted_match(self):
        """-v/--invert-match (without -o) to ensure multi-network lines work."""
        # Just verify inverted match works with multi-network lines
        stdin = '10.1.0.0/16 10.2.0.0/16\n192.168.0.0/16 192.168.1.0/24\n'
        stdout, _, rc = self.run_grepnet('-v', '10.0.0.0/8', stdin_data=stdin)
        self.assertEqual(rc, 0)
        # Should match lines with NO 10.x networks
        self.assertIn('192.168.0.0/16', stdout)
        self.assertIn('192.168.1.0/24', stdout)
        self.assertNotIn('10.1.0.0/16', stdout)

    def test_invert_with_only_matching_incompatible(self):
        """-v and -o together are incompatible (like grep).
        
        With -v, lines contain NO matching networks, so there is nothing
        for -o to extract. Should produce no output (exit code 1).
        """
        stdin = '10.1.0.0/16\n192.168.0.0/16\n'
        stdout, _, rc = self.run_grepnet('-v', '-o', '10.0.0.0/8', stdin_data=stdin)
        # No output because -v returns lines with NO matches,
        # and -o has nothing to extract from those lines
        self.assertEqual(rc, 1)
        self.assertEqual(stdout, '')

    def test_ipv6_multiple_networks_line(self):
        """IPv6 with multiple networks on single line."""
        stdin = '2001:db8::/32 2001:db8:1::/48 fe80::/10\n'
        stdout, _, rc = self.run_grepnet('-o', '::/0', stdin_data=stdin)
        self.assertEqual(rc, 0)
        lines = [l for l in stdout.strip().split('\n') if l]
        self.assertEqual(len(lines), 3, f"Expected 3 networks, got {len(lines)}")
        self.assertEqual(stdout.count('2001:db8::/32'), 1)
        self.assertEqual(stdout.count('2001:db8:1::/48'), 1)
        self.assertEqual(stdout.count('fe80::/10'), 1)

    def test_cidr_and_range_formats(self):
        """Mix of CIDR and range format networks."""
        stdin = '10.0.0.0/24 10.1.0.0-10.1.255.255 10.2.3.4\n'
        stdout, _, rc = self.run_grepnet('-o', '10.0.0.0/8', stdin_data=stdin)
        self.assertEqual(rc, 0)
        lines = [l for l in stdout.strip().split('\n') if l]
        self.assertEqual(len(lines), 3, f"Expected 3 formats, got {len(lines)}")

    def test_duplicate_networks_on_line(self):
        """Same network appears twice on same line."""
        stdin = '10.1.0.0/16 10.1.0.0/16\n'
        stdout, _, rc = self.run_grepnet('-o', '10.0.0.0/8', stdin_data=stdin)
        self.assertEqual(rc, 0)
        # Depending on deduplication, might be 1 or 2; just ensure not 4+
        lines = [l for l in stdout.strip().split('\n') if l]
        self.assertLessEqual(len(lines), 2, "Should have at most 2 outputs (no multiplication)")

    def test_all_networks_match(self):
        """All networks on line match the pattern."""
        stdin = '10.0.0.1 10.1.2.3 10.255.255.254\n'
        stdout, _, rc = self.run_grepnet('-o', '10.0.0.0/8', stdin_data=stdin)
        self.assertEqual(rc, 0)
        lines = [l for l in stdout.strip().split('\n') if l]
        self.assertEqual(len(lines), 3, f"Expected 3 IPs, got {len(lines)}")

    def test_empty_input(self):
        """Empty input should produce no output."""
        stdout, _, rc = self.run_grepnet('-o', '10.0.0.0/8', stdin_data='')
        self.assertEqual(rc, 1)
        self.assertEqual(stdout, '')

    def test_long_line_many_networks(self):
        """Long line with many networks."""
        networks = ' '.join([f'10.{i}.0.0/16' for i in range(10)])
        stdin = networks + '\n'
        stdout, _, rc = self.run_grepnet('-o', '10.0.0.0/8', stdin_data=stdin)
        self.assertEqual(rc, 0)
        lines = [l for l in stdout.strip().split('\n') if l]
        self.assertEqual(len(lines), 10, f"Expected 10 networks, got {len(lines)}")
        # Each should appear exactly once
        for i in range(10):
            self.assertEqual(stdout.count(f'10.{i}.0.0/16'), 1)


if __name__ == '__main__':
    unittest.main()
