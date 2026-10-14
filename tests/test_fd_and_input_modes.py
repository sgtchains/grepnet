"""
Test suite for file descriptor (FD) and advanced input mode handling.

Tests FD input via /dev/fd/N syntax, process substitution, pipes, and 
comprehensive input source handling as documented in GREPNET-SPEC.
"""

import unittest
import subprocess
import tempfile
import os
from pathlib import Path


class TestFDDirectInput(unittest.TestCase):
    """Test file descriptor input via /dev/fd/N syntax."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.grepnet_script = Path(__file__).parent.parent / 'grepnet'
    
    def test_dev_fd_input(self):
        """Test /dev/fd/N syntax for file descriptor input."""
        # Use bash to create and pass FDs
        cmd = [
            'bash', '-c',
            f'{self.grepnet_script} "0.0.0.0/0" /dev/fd/3 3<<< "192.0.2.1\n10.0.0.1\n"'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertIn('192.0.2.1', result.stdout)
        self.assertIn('10.0.0.1', result.stdout)
    
    def test_process_substitution_input(self):
        """Test process substitution with <() syntax."""
        cmd = [
            'bash', '-c',
            f'{self.grepnet_script} "0.0.0.0/0" <(echo -e "192.0.2.1\n10.0.0.1\n172.16.0.0/24")'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertIn('192.0.2.1', result.stdout)
        self.assertIn('10.0.0.1', result.stdout)
        self.assertIn('172.16.0.0/24', result.stdout)
    
    def test_named_pipe_input(self):
        """Test named pipe (FIFO) input."""
        temp_dir = tempfile.TemporaryDirectory()
        fifo_path = Path(temp_dir.name) / 'test.fifo'
        
        try:
            os.mkfifo(fifo_path)
            
            # Run writer in background and grepnet in foreground
            cmd = [
                'bash', '-c',
                f'(echo -e "192.0.2.1\n10.0.0.1") > {fifo_path} & '
                f'{self.grepnet_script} "0.0.0.0/0" {fifo_path}'
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            
            self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
            self.assertIn('192.0.2.1', result.stdout)
        finally:
            temp_dir.cleanup()
    
    def test_dev_stdin_as_argument(self):
        """Test /dev/stdin as explicit argument."""
        cmd = [
            'bash', '-c',
            f'echo "192.0.2.1" | {self.grepnet_script} "0.0.0.0/0" /dev/stdin'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertIn('192.0.2.1', result.stdout)
    
    def test_fd_with_label_flag(self):
        """Test /dev/fd with --label flag for custom naming."""
        cmd = [
            'bash', '-c',
            f'{self.grepnet_script} "0.0.0.0/0" --label=custom_fd -H /dev/fd/3 3<<< "192.0.2.1"'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertIn('custom_fd:', result.stdout)
        self.assertIn('192.0.2.1', result.stdout)
    
    def test_fd_with_binary_detection(self):
        """Test that binary detection works with FD input."""
        # Create binary and text FDs
        cmd = [
            'bash', '-c',
            # Create text FD and binary FD
            f'{self.grepnet_script} "192.0.2.1" /dev/fd/3 /dev/fd/4 '
            f'3<<< "192.0.2.1" '
            f'4<<< $(printf "\\x00\\x01\\x02\\x03")'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Should warn about binary file (FD 4) but still process text (FD 3)
        self.assertIn('192.0.2.1', result.stdout)
    
    def test_fd_peek_buffer_integration(self):
        """Test that peek buffer strategy works with FD input."""
        # Peek buffer should cache first 8KB and not lose data
        large_data = ('192.0.2.0/24\n' * 1000)  # > 8KB
        
        cmd = [
            'bash', '-c',
            f'{self.grepnet_script} "192.0.2.0/24" /dev/fd/3 3<<< {repr(large_data)}'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        # Should find all matches (no data loss from peek buffer)
        line_count = len([l for l in result.stdout.strip().split('\n') if l])
        self.assertGreater(line_count, 10, "Should find multiple matches in large FD input")


class TestPipeInput(unittest.TestCase):
    """Test piped input via stdin."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.grepnet_script = Path(__file__).parent.parent / 'grepnet'
    
    def test_simple_pipe(self):
        """Test simple pipe input."""
        cmd = [
            'bash', '-c',
            f'echo "192.0.2.1" | {self.grepnet_script} "0.0.0.0/0"'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertIn('192.0.2.1', result.stdout)
    
    def test_cat_pipe(self):
        """Test piped input via cat."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
        temp_file.write('192.0.2.1\n10.0.0.1\n172.16.0.0/24\n')
        temp_file.close()
        
        try:
            cmd = [
                'bash', '-c',
                f'cat {temp_file.name} | {self.grepnet_script} "0.0.0.0/0"'
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
            self.assertIn('192.0.2.1', result.stdout)
        finally:
            os.unlink(temp_file.name)
    
    def test_multi_file_pipe(self):
        """Test piped input with multiple files."""
        temp_files = []
        try:
            for i in range(2):
                temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
                temp_file.write(f'192.0.{i}.0/24\n')
                temp_file.close()
                temp_files.append(temp_file.name)
            
            cmd = [
                'bash', '-c',
                f'cat {" ".join(temp_files)} | {self.grepnet_script} "0.0.0.0/0"'
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
            self.assertIn('192.0.0.0/24', result.stdout)
            self.assertIn('192.0.1.0/24', result.stdout)
        finally:
            for temp_file in temp_files:
                os.unlink(temp_file)
    
    def test_grep_pipe_to_grepnet(self):
        """Test grep pipe to grepnet."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
        temp_file.write('192.0.2.1 some comment\n10.0.0.1 other\n172.16.0.0/24 network\n')
        temp_file.close()
        
        try:
            cmd = [
                'bash', '-c',
                f'grep "^1" {temp_file.name} | {self.grepnet_script} "0.0.0.0/0"'
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
            # Should only get lines matching "^1"
            self.assertIn('192.0.2.1', result.stdout)
            self.assertIn('10.0.0.1', result.stdout)
        finally:
            os.unlink(temp_file.name)
    
    def test_xargs_pipe_to_grepnet(self):
        """Test xargs piped to grepnet."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
        temp_file.write('192.0.2.1\n10.0.0.1\n')
        temp_file.close()
        
        try:
            cmd = [
                'bash', '-c',
                f'cat {temp_file.name} | xargs -I {{}} echo {{}} | {self.grepnet_script} "0.0.0.0/0"'
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
            self.assertIn('192.0.2.1', result.stdout)
        finally:
            os.unlink(temp_file.name)


class TestStreamingBehavior(unittest.TestCase):
    """Test streaming input behavior (line-by-line processing)."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.grepnet_script = Path(__file__).parent.parent / 'grepnet'
    
    def test_streaming_stdin_no_full_buffering(self):
        """Test that stdin is processed line-by-line without full buffering."""
        # Large input that should not require full buffering
        large_input = '192.0.2.1\n' * 10000  # 10k lines
        
        cmd = [str(self.grepnet_script), '0.0.0.0/0']
        result = subprocess.run(
            cmd,
            input=large_input,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        self.assertEqual(result.returncode, 0)
        # Should output all matches
        output_lines = len([l for l in result.stdout.strip().split('\n') if l])
        self.assertGreater(output_lines, 100, "Should process large stream")
    
    def test_infinite_stream_with_max_matches(self):
        """Test that -m N stops after N matches even with infinite stream."""
        cmd = [
            'bash', '-c',
            f'yes "192.0.2.1" | {self.grepnet_script} -m 5 "0.0.0.0/0"'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        
        self.assertEqual(result.returncode, 0)
        lines = [l for l in result.stdout.strip().split('\n') if l]
        self.assertEqual(len(lines), 5, "Should stop after -m N matches")
    
    def test_streaming_with_context_lines(self):
        """Test streaming behavior with context flags (-B/-A/-C)."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
        content = '\n'.join([f'line {i}' if i % 10 != 5 else f'192.0.2.{i%256}' 
                            for i in range(100)])
        temp_file.write(content)
        temp_file.close()
        
        try:
            cmd = [str(self.grepnet_script), '-A', '2', '192.0.2.', str(temp_file.name)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            
            # Should include matches and context
            self.assertIn('192.0.2.', result.stdout)
        finally:
            os.unlink(temp_file.name)


class TestBinaryDetection(unittest.TestCase):
    """Test binary file detection in various input modes."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.grepnet_script = Path(__file__).parent.parent / 'grepnet'
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
    
    def tearDown(self):
        """Clean up."""
        self.temp_dir.cleanup()
    
    def test_binary_file_detection(self):
        """Test that binary files are detected and skipped."""
        binary_file = self.temp_path / 'binary.bin'
        binary_file.write_bytes(b'\x00\x01\x02\x03\xff\xfe\xfd\xfc')
        
        text_file = self.temp_path / 'text.txt'
        text_file.write_text('192.0.2.1\n')
        
        cmd = [str(self.grepnet_script), '0.0.0.0/0', 
               str(binary_file), str(text_file)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Should match text file
        self.assertIn('192.0.2.1', result.stdout)
        # Should warn about binary file
        if result.stderr:
            self.assertIn('binary', result.stderr.lower())
    
    def test_binary_detection_via_fd(self):
        """Test binary detection with FD input."""
        cmd = [
            'bash', '-c',
            f'{self.grepnet_script} "192.0.2.1" /dev/fd/3 3<<< $(printf "\\x00\\x01\\x02")'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Binary FD should be skipped
        self.assertNotEqual(result.returncode, 0)  # No matches in binary
    
    def test_peek_buffer_binary_detection(self):
        """Test that peek buffer doesn't lose data when detecting binary."""
        # File starting with non-binary but containing null bytes later
        text_file = self.temp_path / 'mostly_text.txt'
        content = '192.0.2.1\n' + 'a' * 10000 + '\x00binary\n' + '10.0.0.1\n'
        text_file.write_bytes(content.encode('utf-8', errors='replace'))
        
        cmd = [str(self.grepnet_script), '0.0.0.0/0', str(text_file)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Should process at least the beginning
        self.assertIn('192.0.2.1', result.stdout)


class TestInputSourceAbstraction(unittest.TestCase):
    """Test that InputSource abstraction correctly handles different input types."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.grepnet_script = Path(__file__).parent.parent / 'grepnet'
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
    
    def tearDown(self):
        """Clean up."""
        self.temp_dir.cleanup()
    
    def test_stdin_dash_vs_no_args(self):
        """Test that '-' and no args both read from stdin."""
        data = '192.0.2.1\n'
        
        # Test with '-'
        cmd1 = [str(self.grepnet_script), '0.0.0.0/0', '-']
        result1 = subprocess.run(cmd1, input=data, capture_output=True, text=True)
        
        # Test without files (implicit stdin)
        cmd2 = [str(self.grepnet_script), '0.0.0.0/0']
        result2 = subprocess.run(cmd2, input=data, capture_output=True, text=True)
        
        # Both should produce same output
        self.assertEqual(result1.returncode, result2.returncode)
        self.assertEqual(result1.stdout, result2.stdout)
    
    def test_explicit_files_vs_stdin(self):
        """Test that explicit files are used when provided."""
        file1 = self.temp_path / 'file1.txt'
        file1.write_text('192.0.2.1\n')
        
        # With explicit file
        cmd1 = [str(self.grepnet_script), '0.0.0.0/0', str(file1)]
        result1 = subprocess.run(cmd1, capture_output=True, text=True)
        
        # stdin should be ignored when explicit file given
        stdin_data = '10.0.0.1\n'
        cmd2 = [str(self.grepnet_script), '0.0.0.0/0', str(file1)]
        result2 = subprocess.run(cmd2, input=stdin_data, capture_output=True, text=True)
        
        # Both should use file1.txt
        self.assertEqual(result1.stdout, result2.stdout)
        # stdin data should be ignored
        self.assertNotIn('10.0.0.1', result2.stdout)
    
    def test_multiple_input_sources_unified_path(self):
        """Test that multiple input sources go through unified processing."""
        file1 = self.temp_path / 'file1.txt'
        file1.write_text('192.0.2.0/24\n')
        
        file2 = self.temp_path / 'file2.txt'
        file2.write_text('10.0.0.0/8\n')
        
        # Multiple files
        cmd = [str(self.grepnet_script), '0.0.0.0/0', str(file1), str(file2)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        self.assertEqual(result.returncode, 0)
        # Should process both files
        self.assertIn('192.0.2.0/24', result.stdout)
        self.assertIn('10.0.0.0/8', result.stdout)
    
    def test_input_source_display_name(self):
        """Test that input sources have appropriate display names."""
        file1 = self.temp_path / 'test.txt'
        file1.write_text('192.0.2.1\n')
        
        # File should show filename
        cmd1 = [str(self.grepnet_script), '0.0.0.0/0', '-H', str(file1)]
        result1 = subprocess.run(cmd1, capture_output=True, text=True)
        self.assertIn('test.txt:', result1.stdout)
        
        # stdin with label should show label
        cmd2 = [str(self.grepnet_script), '0.0.0.0/0', '-H', '--label=stdin_label', '-']
        result2 = subprocess.run(cmd2, input='192.0.2.1\n', capture_output=True, text=True)
        self.assertIn('stdin_label:', result2.stdout)
    
    def test_byte_offset_for_different_sources(self):
        """Test that byte offsets work correctly for all input sources."""
        file1 = self.temp_path / 'test.txt'
        file1.write_text('192.0.2.0/24\n10.0.0.1\n172.16.0.0/12\n')
        
        # With file: byte offset should be accurate
        cmd1 = [str(self.grepnet_script), '0.0.0.0/0', '-b', str(file1)]
        result1 = subprocess.run(cmd1, capture_output=True, text=True)
        
        # First match should have offset 0
        first_line = result1.stdout.split('\n')[0]
        self.assertTrue(first_line.startswith('0:'), 
                       f"First line should have offset 0, got: {first_line}")
        
        # With stdin: byte offset should be 0 for all (streams don't have positions)
        cmd2 = [str(self.grepnet_script), '0.0.0.0/0', '-b', '-']
        result2 = subprocess.run(cmd2, input='192.0.2.1\n', capture_output=True, text=True)
        
        # stdin should have offset 0
        self.assertIn('0:', result2.stdout)


if __name__ == '__main__':
    unittest.main()
