"""
Binary file detection and VTY protection.

Detects binary/non-UTF8 files to prevent terminal corruption from control sequences.
Three modes: binary (skip), text (process), without-match (report "Binary file X matches").
"""

import os
from typing import Tuple


class BinaryDetector:
    """
    Detects binary/non-text files to protect terminal (VTY protection).
    
    Strategy:
    1. Read first 8KB of file
    2. Check for null bytes (strong indicator of binary)
    3. Check proportion of non-printable characters
    4. Threshold: >30% non-printable = binary
    """
    
    # First 8KB for detection
    DETECTION_SIZE = 8192
    
    # Printable characters (ASCII 32-126, plus whitespace)
    PRINTABLE_BYTES = set(range(32, 127)) | {9, 10, 13}  # tab, LF, CR
    
    # Threshold for binary classification
    NONPRINTABLE_THRESHOLD = 0.30  # 30%
    
    @classmethod
    def is_binary(cls, file_path: str) -> bool:
        """
        Determine if file is binary/non-text.
        
        Args:
            file_path: Path to file to check
        
        Returns:
            True if file appears to be binary
        """
        try:
            with open(file_path, 'rb') as f:
                sample = f.read(cls.DETECTION_SIZE)
            
            if not sample:
                # Empty file = text
                return False
            
            # Null bytes indicate binary
            if b'\x00' in sample:
                return True
            
            # Count non-printable bytes
            non_printable = sum(
                1 for byte in sample
                if byte not in cls.PRINTABLE_BYTES
            )
            
            proportion = non_printable / len(sample)
            return proportion > cls.NONPRINTABLE_THRESHOLD
        
        except (IOError, OSError):
            # If can't read, assume text (will fail later with more context)
            return False
    
    @classmethod
    def check_line_binary(cls, line_content: bytes) -> Tuple[bool, str]:
        """
        Check if a single line contains binary/control content.
        
        Args:
            line_content: Line bytes
        
        Returns:
            Tuple of (is_binary, reason)
        """
        # Null bytes in line
        if b'\x00' in line_content:
            return True, 'null byte'
        
        # Count non-printable
        non_printable = sum(
            1 for byte in line_content
            if byte not in cls.PRINTABLE_BYTES
        )
        
        if len(line_content) > 0:
            proportion = non_printable / len(line_content)
            if proportion > cls.NONPRINTABLE_THRESHOLD:
                return True, 'non-printable characters'
        
        return False, ''
    
    @classmethod
    def is_binary_from_buffer(cls, buffer: bytes) -> bool:
        """
        Determine if a buffer contains binary/non-text data.
        
        Uses same algorithm as is_binary() but operates on already-read buffer.
        This is used after peeking the first 8KB of stdin/fd.
        
        Args:
            buffer: Byte buffer to check
        
        Returns:
            True if appears to be binary
        """
        if not buffer:
            # Empty = text
            return False
        
        # Null bytes indicate binary
        if b'\x00' in buffer:
            return True
        
        # Count non-printable bytes
        non_printable = sum(
            1 for byte in buffer
            if byte not in cls.PRINTABLE_BYTES
        )
        
        proportion = non_printable / len(buffer)
        return proportion > cls.NONPRINTABLE_THRESHOLD
    
    @classmethod
    def is_binary_fd(cls, fd_or_file) -> bool:
        """
        Determine if file descriptor or file object contains binary data.
        
        Args:
            fd_or_file: File descriptor (int), file object, or sys.stdin
        
        Returns:
            True if appears to be binary
        """
        try:
            # Handle file objects (like sys.stdin)
            if hasattr(fd_or_file, 'fileno'):
                actual_fd = fd_or_file.fileno()
            else:
                actual_fd = fd_or_file
            
            # Try to read 8KB from the file descriptor
            sample = os.read(actual_fd, cls.DETECTION_SIZE)
            
            if not sample:
                # Empty = text
                return False
            
            # Null bytes indicate binary
            if b'\x00' in sample:
                return True
            
            # Count non-printable bytes
            non_printable = sum(
                1 for byte in sample
                if byte not in cls.PRINTABLE_BYTES
            )
            
            proportion = non_printable / len(sample)
            return proportion > cls.NONPRINTABLE_THRESHOLD
        
        except (OSError, IOError, ValueError):
            # If can't read from FD, assume text
            return False
