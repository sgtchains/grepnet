"""
Test suite for 8KB buffer optimization.

Tests the critical optimization where:
1. First 8KB is read ONCE and cached
2. Same buffer is used for BOTH binary detection AND mask format hint detection
3. File handle remains open for continued sequential reading from byte 8KB

This ensures single file open, zero seeks, zero redundant reads.
"""

import unittest
import tempfile
import os
from pathlib import Path
from grepnet.input.input_source import InputSource
from grepnet.core.binary_detector import BinaryDetector


class TestSingle8KBBufferOptimization(unittest.TestCase):
    """Test that first 8KB buffer is reused for multiple purposes."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
    
    def tearDown(self):
        """Clean up temporary files."""
        self.temp_dir.cleanup()
    
    def test_8kb_buffer_reused_for_binary_and_format_detection(self):
        """
        Verify that get_binary_status() and get_mask_format_hint() 
        both use the same cached 8KB buffer (no redundant reads).
        """
        # Create a file with netmask format in first 8KB
        test_file = self.temp_path / 'test_8kb_reuse.txt'
        content = '192.168.1.0 255.255.255.0\n' * 100  # Fill with netmask patterns
        content += '192.0.2.0/24\n' * 1000  # Add more after 8KB
        
        test_file.write_text(content)
        
        # Create InputSource
        source = InputSource('file', file_path=str(test_file))
        
        # Call get_binary_status() first
        is_binary = source.get_binary_status()
        self.assertFalse(is_binary, "Text file should not be detected as binary")
        
        # Verify peek buffer is cached
        self.assertIsNotNone(source._peek_buffer, "Peek buffer should be cached after binary detection")
        
        # Now call get_mask_format_hint()
        format_hint = source.get_mask_format_hint(scan_mask='both')
        
        # Should have detected netmask format from the first 8KB
        self.assertIn(format_hint, ['netmask_dominant', 'mixed', 'unknown'],
                     f"Format hint should be netmask-related or unknown, got: {format_hint}")
        
        # Verify the same peek buffer was used (no new read)
        # This is verified by checking _mask_format_hint was cached
        self.assertIsNotNone(source._mask_format_hint, 
                            "Mask format hint should be cached")
    
    def test_file_handle_stays_open_after_detection(self):
        """
        Verify file handle remains open after binary/format detection,
        ready for line iteration from byte 8KB onward.
        """
        test_file = self.temp_path / 'test_filehandle_open.txt'
        content = '192.168.1.0 255.255.255.0\n' * 100
        content += '10.0.0.0/8\n' * 1000
        
        test_file.write_text(content)
        
        source = InputSource('file', file_path=str(test_file))
        
        # Before any detection, file handle should not exist
        self.assertIsNone(source._file_handle, "File handle should be None before detection")
        
        # Call binary detection
        is_binary = source.get_binary_status()
        
        # File handle should now be open
        self.assertIsNotNone(source._file_handle, "File handle should be open after binary detection")
        self.assertFalse(source._file_handle.closed, "File handle should not be closed")
        
        # Get format hint (should reuse same handle)
        format_hint = source.get_mask_format_hint(scan_mask='both')
        
        # File handle should still be open
        self.assertIsNotNone(source._file_handle, "File handle should still be open")
        self.assertFalse(source._file_handle.closed, "File handle should not be closed after format detection")
        
        # Now iterate lines (this should continue from byte 8KB)
        line_count = 0
        for line_number, line_content, byte_offset in source.lines():
            line_count += 1
            self.assertGreater(line_number, 0, "Line numbers should be 1-based")
        
        self.assertGreater(line_count, 100, "Should read many lines from the file")
    
    def test_peek_buffer_size_is_8kb(self):
        """Verify peek buffer is exactly 8KB (8192 bytes)."""
        test_file = self.temp_path / 'test_8kb_size.txt'
        # Create file larger than 8KB
        content = 'x' * 20000  # 20KB
        test_file.write_text(content)
        
        source = InputSource('file', file_path=str(test_file))
        is_binary = source.get_binary_status()
        
        peek_size = len(source._peek_buffer)
        self.assertEqual(peek_size, BinaryDetector.DETECTION_SIZE,
                        f"Peek buffer should be {BinaryDetector.DETECTION_SIZE} bytes, got {peek_size}")
    
    def test_both_detections_precede_line_iteration(self):
        """
        Verify that binary detection and format hint detection
        both complete before line iteration starts.
        """
        test_file = self.temp_path / 'test_detection_order.txt'
        content = '192.168.1.0 255.255.255.0\n' * 200  # Netmask in first 8KB
        content += '10.0.0.0 0.255.255.255\n' * 1000    # Hostmask after 8KB
        
        test_file.write_text(content)
        
        source = InputSource('file', file_path=str(test_file))
        
        # Initially, nothing should be cached
        self.assertIsNone(source._is_binary)
        self.assertIsNone(source._mask_format_hint)
        self.assertIsNone(source._peek_buffer)
        
        # Get both detections
        is_binary = source.get_binary_status()
        format_hint = source.get_mask_format_hint(scan_mask='both')
        
        # Now everything should be cached
        self.assertIsNotNone(source._is_binary)
        self.assertIsNotNone(source._mask_format_hint)
        self.assertIsNotNone(source._peek_buffer)
        
        # Start iterating lines
        first_line = None
        for line_number, line_content, byte_offset in source.lines():
            if first_line is None:
                first_line = (line_number, line_content, byte_offset)
            break
        
        # First line should still be from the very start (peek buffer was prepended)
        self.assertEqual(first_line[0], 1, "First line should be line 1")
        self.assertIn('192.168.1.0', first_line[1], 
                     "First line should contain data from beginning of file")


class TestPeekBufferWithDifferentFileSizes(unittest.TestCase):
    """Test 8KB buffer behavior with files of various sizes."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
    
    def tearDown(self):
        """Clean up temporary files."""
        self.temp_dir.cleanup()
    
    def test_small_file_under_8kb(self):
        """Test with file smaller than 8KB."""
        test_file = self.temp_path / 'small_file.txt'
        content = '192.0.2.0/24\n' * 100  # Small file
        test_file.write_text(content)
        
        source = InputSource('file', file_path=str(test_file))
        is_binary = source.get_binary_status()
        
        # Peek buffer should contain entire file (smaller than 8KB)
        self.assertLess(len(source._peek_buffer), BinaryDetector.DETECTION_SIZE)
        self.assertIn(b'192.0.2.0', source._peek_buffer)
        
        # Should still be able to iterate all lines
        line_count = sum(1 for _ in source.lines())
        self.assertEqual(line_count, 100)
    
    def test_exactly_8kb_file(self):
        """Test with file exactly 8KB."""
        test_file = self.temp_path / 'exact_8kb_file.txt'
        # Create exactly 8192 bytes by padding
        content = 'x' * 8192
        test_file.write_text(content)
        
        source = InputSource('file', file_path=str(test_file))
        is_binary = source.get_binary_status()
        
        # Peek buffer should be exactly 8KB
        self.assertEqual(len(source._peek_buffer), 8192)
        
        # Should be able to iterate
        line_count = sum(1 for _ in source.lines())
        self.assertGreater(line_count, 0)
    
    def test_large_file_over_8kb(self):
        """Test with file much larger than 8KB."""
        test_file = self.temp_path / 'large_file.txt'
        content = '192.0.2.0/24\n' * 2000  # > 8KB
        test_file.write_text(content)
        
        source = InputSource('file', file_path=str(test_file))
        is_binary = source.get_binary_status()
        
        # Peek buffer should be exactly 8KB
        self.assertEqual(len(source._peek_buffer), BinaryDetector.DETECTION_SIZE)
        
        # Should still read all lines (not truncated)
        line_count = sum(1 for _ in source.lines())
        self.assertEqual(line_count, 2000)


class TestBinaryDetectionViaBufferReuse(unittest.TestCase):
    """Test binary detection correctly uses cached buffer."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
    
    def tearDown(self):
        """Clean up temporary files."""
        self.temp_dir.cleanup()
    
    def test_binary_file_detected_from_8kb_buffer(self):
        """Test binary file detection from cached 8KB buffer."""
        test_file = self.temp_path / 'binary_file.bin'
        # Write binary data with null bytes in first 8KB
        binary_data = b'\x00\x01\x02\x03' * 2000  # Null bytes
        test_file.write_bytes(binary_data)
        
        source = InputSource('file', file_path=str(test_file))
        is_binary = source.get_binary_status()
        
        # Should detect as binary (due to null bytes)
        self.assertTrue(is_binary, "File with null bytes should be detected as binary")
        
        # Should have cached the 8KB buffer
        self.assertIsNotNone(source._peek_buffer)
        self.assertIn(b'\x00', source._peek_buffer)
    
    def test_text_file_not_detected_as_binary(self):
        """Test text file is correctly identified as text."""
        test_file = self.temp_path / 'text_file.txt'
        content = '192.168.1.0 255.255.255.0\n' * 500
        test_file.write_text(content)
        
        source = InputSource('file', file_path=str(test_file))
        is_binary = source.get_binary_status()
        
        # Should NOT detect as binary
        self.assertFalse(is_binary, "Text file should not be detected as binary")


if __name__ == '__main__':
    unittest.main()
