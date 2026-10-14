"""
Unified Input Source abstraction.

Single InputSource class handles all input types:
- Files (local files on disk)
- stdin (piped data)
- File descriptors (process substitution)

All sources yield identical (line_number, line_content, byte_offset) tuples.
First 8KB is cached for binary detection before line iteration begins.
"""

import sys
import os
from typing import Iterator, Tuple, Optional

from grepnet.core.binary_detector import BinaryDetector
from grepnet.parsing.mask_format_detector import MaskFormatDetector


class InputSource:
    """
    Unified input source for all input types.
    
    Handles files, stdin, and file descriptors with a single interface.
    All sources yield identical (line_number, line_content, byte_offset) tuples.
    Line numbers are 1-based.
    
    For stdin/fd: First 8KB is read and cached before iteration to support binary detection
    without consuming the stream. The cached buffer is prepended during line iteration.
    """
    
    def __init__(
        self,
        source_type: str,
        file_path: Optional[str] = None,
        fd: Optional[int] = None,
        label: Optional[str] = None,
        null_delimited: bool = False,
    ):
        """
        Initialize InputSource.
        
        Args:
            source_type: One of 'file', 'stdin', 'fd'
            file_path: Path to file (required if source_type='file')
            fd: File descriptor number (required if source_type='fd')
            label: Custom display label (from --label flag, used with stdin or fd)
            null_delimited: If True, split on NUL byte instead of newline (for -z flag)
        """
        if source_type not in ('file', 'stdin', 'fd'):
            raise ValueError(f"Invalid source_type: {source_type}")
        
        self.source_type = source_type
        self.file_path = file_path
        self.fd = fd
        self._label = label
        self.null_delimited = null_delimited
        self.record_delimiter = b'\0' if null_delimited else b'\n'
        self._is_binary = None  # Cache binary status
        self._file_handle = None
        self._peek_buffer = None  # First 8KB cached for binary detection (stdin/fd only)
        self._mask_format_hint = None  # Format hint cached from peek buffer analysis
    
    @property
    def file_type(self) -> str:
        """Type of input source: 'file', 'stdin', or 'fd'."""
        return self.source_type
    
    @property
    def display_name(self) -> Optional[str]:
        """
        Display name for use in -H/--with-filename output.
        
        Returns:
            - For files: the file path
            - For stdin/fd: the custom label (if --label was provided), or None
        """
        if self.source_type == 'file':
            return self.file_path
        else:
            # stdin or fd: return label only if explicitly set
            return self._label
    
    def get_binary_status(self) -> bool:
        """
        Check if source contains binary data.
        
        Lazy evaluation: checks only once and caches result.
        For all sources: reads and caches first 8KB for analysis and format detection.
        
        Returns:
            True if source appears to be binary
        """
        if self._is_binary is None:
            if self.source_type == 'file':
                # For files, read first 8KB for binary detection
                try:
                    with open(self.file_path, 'rb') as f:
                        self._peek_buffer = f.read(BinaryDetector.DETECTION_SIZE)
                    self._is_binary = BinaryDetector.is_binary_from_buffer(self._peek_buffer)
                except (IOError, OSError):
                    self._is_binary = False
            else:
                # stdin or fd: read and cache first 8KB for binary detection
                self._peek_buffer = self._read_peek_buffer()
                self._is_binary = BinaryDetector.is_binary_from_buffer(self._peek_buffer)
        return self._is_binary
    
    def get_mask_format_hint(self, scan_mask: str = 'both') -> Optional[str]:
        """
        Get cached mask format hint from peek buffer analysis.
        
        Lazy evaluation: scans only once and caches result.
        For files: reads first 8KB to detect format.
        For stdin/fd: reuses peek buffer from binary detection.
        
        Args:
            scan_mask: Control flag ('both', 'input', 'pattern', 'none')
                      Only used if scan_mask != 'none'
        
        Returns:
            Format hint: 'netmask_dominant', 'hostmask_dominant', 'mixed', 'unknown'
            or None if scan_mask is 'none'
        """
        if scan_mask == 'none':
            return None
        
        if self._mask_format_hint is not None:
            return self._mask_format_hint
        
        # Ensure peek buffer is loaded
        if self.source_type == 'file':
            # For files, read first 8KB
            try:
                with open(self.file_path, 'rb') as f:
                    peek_bytes = f.read(BinaryDetector.DETECTION_SIZE)
            except (IOError, OSError):
                self._mask_format_hint = 'unknown'
                return self._mask_format_hint
        else:
            # For stdin/fd, ensure peek buffer exists from binary detection
            if self._peek_buffer is None:
                # Binary detection wasn't called yet, read it now
                self._peek_buffer = self._read_peek_buffer()
            peek_bytes = self._peek_buffer
        
        # Decode peek buffer to text
        try:
            peek_text = peek_bytes.decode('utf-8', errors='replace')
        except:
            peek_text = peek_bytes.decode('latin-1', errors='replace')
        
        # Scan for format
        self._mask_format_hint = MaskFormatDetector.detect_format(peek_text)
        return self._mask_format_hint
    
    def _read_peek_buffer(self) -> bytes:
        """
        Read first 8KB from stdin or FD for binary detection.
        Buffer is cached and will be prepended during line reading.
        """
        try:
            if self.source_type == 'stdin':
                return sys.stdin.buffer.read(BinaryDetector.DETECTION_SIZE)
            else:  # fd
                return os.read(self.fd, BinaryDetector.DETECTION_SIZE)
        except (OSError, IOError, AttributeError):
            return b''
    
    def lines(self) -> Iterator[Tuple[int, str, int]]:
        """
        Iterate over lines from source.
        
        Yields:
            (line_number, line_content, byte_offset) tuples
            line_number: 1-based
            line_content: line without trailing newline
            byte_offset: 0-based byte position of line start (0 for stdin/fd)
        """
        try:
            if self.source_type == 'file':
                yield from self._lines_from_file()
            elif self.source_type == 'stdin':
                yield from self._lines_from_stdin()
            else:  # fd
                yield from self._lines_from_fd()
        finally:
            self.close()
    
    def _lines_from_file(self) -> Iterator[Tuple[int, str, int]]:
        """
        Read lines/records from file with byte offset tracking.
        
        Uses cached peek buffer if available (from binary detection),
        ensuring uniform "All Input Is Input" behavior with stdin/fd.
        """
        try:
            if self.null_delimited:
                # NUL-delimited record processing
                # Reuse peek buffer if available, then continue reading rest of file
                content = b''
                
                if self._peek_buffer:
                    content = self._peek_buffer
                
                # Read remaining content from file (seek past the peek buffer if possible)
                try:
                    self._file_handle = open(self.file_path, 'rb')
                    # Try to seek past the peek buffer to avoid re-reading it
                    if self._peek_buffer:
                        try:
                            self._file_handle.seek(len(self._peek_buffer))
                        except (OSError, IOError):
                            # File/stream not seekable (e.g., /dev/stdin), can't continue
                            pass
                    content += self._file_handle.read()
                except IOError:
                    # If we can't open file but have peek buffer, use just that
                    if not content:
                        raise
                
                records = content.split(b'\0')
                
                line_num = 1
                byte_offset = 0
                
                for i, record_bytes in enumerate(records):
                    # Skip empty records except if it's the last one and file doesn't end with NUL
                    if not record_bytes and i < len(records) - 1:
                        byte_offset += 1  # Account for the NUL delimiter
                        continue
                    
                    # Decode record
                    try:
                        record_str = record_bytes.decode('utf-8', errors='replace')
                    except:
                        record_str = record_bytes.decode('latin-1', errors='replace')
                    
                    # Yield with byte offset of this record
                    if record_str or i == len(records) - 1:  # Yield empty last record only if file doesn't end with NUL
                        yield line_num, record_str, byte_offset
                        line_num += 1
                    
                    # Update byte offset for next record
                    byte_offset += len(record_bytes) + 1  # +1 for NUL delimiter
            else:
                # Newline-delimited logic with unified peek buffer handling
                line_num = 1
                byte_offset = 0
                partial_line = None
                
                # If peek buffer exists, process it first (unified "All Input Is Input" approach)
                if self._peek_buffer:
                    buffer_lines = self._peek_buffer.split(b'\n')
                    
                    # Process all complete lines from buffer (all except the last)
                    for line_bytes in buffer_lines[:-1]:
                        line = line_bytes.decode('utf-8', errors='replace')
                        line_content = line.rstrip('\r')
                        yield line_num, line_content, byte_offset
                        byte_offset += len(line_bytes) + 1  # +1 for newline
                        line_num += 1
                    
                    # Last line from buffer: if non-empty, it was incomplete (no trailing \n)
                    if buffer_lines[-1]:
                        partial_line = buffer_lines[-1]
                        byte_offset += len(partial_line)  # Account for the incomplete line
                
                # Now open file and read remaining content
                self._file_handle = open(self.file_path, 'rb')
                
                # Try to seek past the peek buffer to avoid re-reading it
                # Some sources (like /dev/stdin) are not seekable, so handle gracefully
                if self._peek_buffer:
                    try:
                        self._file_handle.seek(len(self._peek_buffer))
                    except (OSError, IOError):
                        # File/stream not seekable, we'll just use peek buffer and skip rest
                        # Don't read from file_handle in this case
                        if partial_line:
                            line = partial_line.decode('utf-8', errors='replace')
                            line_content = line.rstrip('\r')
                            yield line_num, line_content, byte_offset
                        return
                
                # If we have a partial line from peek buffer, prepend it to first read
                for line_bytes in self._file_handle:
                    if partial_line:
                        line_bytes = partial_line + line_bytes
                        partial_line = None
                    
                    # Decode line
                    try:
                        line = line_bytes.decode('utf-8', errors='replace')
                    except:
                        line = line_bytes.decode('latin-1', errors='replace')
                    
                    # Remove trailing newline
                    line_content = line.rstrip('\n\r')
                    
                    # Yield with byte offset of this line
                    yield line_num, line_content, byte_offset
                    
                    # Update byte offset for next line
                    byte_offset += len(line_bytes)
                    line_num += 1
                
                # Handle any remaining partial line
                if partial_line:
                    line = partial_line.decode('utf-8', errors='replace')
                    line_content = line.rstrip('\r')
                    yield line_num, line_content, byte_offset
        except IOError as e:
            raise IOError(f"Cannot read {self.file_path}: {e}")
    
    def _lines_from_stdin(self) -> Iterator[Tuple[int, str, int]]:
        """Read lines/records from stdin, using cached peek buffer if available."""
        line_num = 1
        partial_line = None
        
        if self.null_delimited:
            # NUL-delimited record processing with chunked reading
            chunk_size = 8192
            
            # Start with peek buffer if available
            if self._peek_buffer:
                buffer = self._peek_buffer
            else:
                buffer = b''
            
            try:
                while True:
                    # Read next chunk
                    chunk = sys.stdin.buffer.read(chunk_size)
                    if not chunk:
                        # Handle final partial record
                        if buffer:
                            record_str = buffer.decode('utf-8', errors='replace')
                            yield line_num, record_str, 0
                        break
                    
                    # Combine with buffer
                    buffer += chunk
                    records = buffer.split(b'\0')
                    
                    # Last element might be incomplete - save for next iteration
                    buffer = records[-1]
                    
                    # Process complete records
                    for record_bytes in records[:-1]:
                        record_str = record_bytes.decode('utf-8', errors='replace')
                        yield line_num, record_str, 0
                        line_num += 1
            except (UnicodeDecodeError, AttributeError):
                print('grepnet: error: stdin contains invalid UTF-8 data', file=sys.stderr)
                raise
        else:
            # Original newline-delimited logic
            # If peek buffer exists (from binary detection), process it first
            if self._peek_buffer:
                buffer_lines = self._peek_buffer.split(b'\n')
                # Process all lines except the last (split artifact)
                for line_bytes in buffer_lines[:-1]:
                    line = line_bytes.decode('utf-8', errors='replace')
                    line_content = line.rstrip('\r')
                    yield line_num, line_content, 0
                    line_num += 1
                
                # Last line from buffer: if non-empty, it was incomplete (no trailing \n)
                if buffer_lines[-1]:
                    partial_line = buffer_lines[-1]
            
            # Read remaining lines from stdin, combining with partial line if needed
            try:
                for line_bytes in sys.stdin.buffer:
                    # If we have a partial line from peek buffer, prepend it to first chunk
                    if partial_line:
                        line_bytes = partial_line + line_bytes
                        partial_line = None
                    
                    line = line_bytes.decode('utf-8', errors='replace')
                    line_content = line.rstrip('\n\r')
                    yield line_num, line_content, 0  # byte_offset always 0 for stdin
                    line_num += 1
            except (UnicodeDecodeError, AttributeError):
                # If sys.stdin.buffer is not available, fall back to text mode
                try:
                    for line in sys.stdin:
                        line_content = line.rstrip('\n\r')
                        yield line_num, line_content, 0
                        line_num += 1
                except UnicodeDecodeError:
                    print('grepnet: error: stdin contains invalid UTF-8 data', file=sys.stderr)
                    raise
                finally:
                    # If partial_line still exists, yield it
                    if partial_line:
                        line = partial_line.decode('utf-8', errors='replace')
                        line_content = line.rstrip('\r')
                        yield line_num, line_content, 0
                        line_num += 1
            finally:
                # If partial_line still exists after all reads, yield it
                if partial_line:
                    line = partial_line.decode('utf-8', errors='replace')
                    line_content = line.rstrip('\r')
                    yield line_num, line_content, 0
    
    def _lines_from_fd(self) -> Iterator[Tuple[int, str, int]]:
        """Read lines/records from file descriptor, using cached peek buffer if available."""
        line_num = 1
        partial_line = None
        
        try:
            self._file_handle = os.fdopen(self.fd, 'rb')
            
            if self.null_delimited:
                # NUL-delimited record processing with chunked reading
                chunk_size = 8192
                
                # Start with peek buffer if available
                if self._peek_buffer:
                    buffer = self._peek_buffer
                else:
                    buffer = b''
                
                try:
                    while True:
                        # Read next chunk
                        chunk = self._file_handle.read(chunk_size)
                        if not chunk:
                            # Handle final partial record
                            if buffer:
                                record_str = buffer.decode('utf-8', errors='replace')
                                yield line_num, record_str, 0
                            break
                        
                        # Combine with buffer
                        buffer += chunk
                        records = buffer.split(b'\0')
                        
                        # Last element might be incomplete - save for next iteration
                        buffer = records[-1]
                        
                        # Process complete records
                        for record_bytes in records[:-1]:
                            record_str = record_bytes.decode('utf-8', errors='replace')
                            yield line_num, record_str, 0
                            line_num += 1
                except (UnicodeDecodeError, AttributeError):
                    print('grepnet: error: FD contains invalid UTF-8 data', file=sys.stderr)
                    raise
            else:
                # Original newline-delimited logic
                # If peek buffer exists (from binary detection), process it first
                if self._peek_buffer:
                    buffer_lines = self._peek_buffer.split(b'\n')
                    # Process all lines except the last (split artifact)
                    for line_bytes in buffer_lines[:-1]:
                        line = line_bytes.decode('utf-8', errors='replace')
                        line_content = line.rstrip('\r')
                        yield line_num, line_content, 0
                        line_num += 1
                    
                    # Handle last line from buffer: if non-empty, it was incomplete
                    if buffer_lines[-1]:
                        partial_line = buffer_lines[-1]
                
                for line_bytes in self._file_handle:
                    # If we have a partial line, prepend it to first chunk
                    if partial_line:
                        line_bytes = partial_line + line_bytes
                        partial_line = None
                    
                    line = line_bytes.decode('utf-8', errors='replace')
                    line_content = line.rstrip('\n\r')
                    yield line_num, line_content, 0  # byte_offset always 0 for FD
                    line_num += 1
                
                # If partial_line still exists after all reads, yield it
                if partial_line:
                    line = partial_line.decode('utf-8', errors='replace')
                    line_content = line.rstrip('\r')
                    yield line_num, line_content, 0
        except IOError as e:
            raise IOError(f"Cannot read from FD {self.fd}: {e}")
    
    def close(self) -> None:
        """Close file handle if open. Safe to call multiple times."""
        if self._file_handle is not None:
            try:
                self._file_handle.close()
            except:
                pass  # Already closed or error closing
            self._file_handle = None


class InputDiscovery:
    """
    Determine input sources based on arguments and environment.
    
    Priority:
    1. Stdin: If no files specified and stdin is not a terminal
    2. Explicit file list: Files from positional args or -F flags
    3. Directory recursion: If --recursive or --dereference-recursive
    """
    
    @staticmethod
    def get_sources(
        files: Optional[list] = None,
        use_stdin: bool = False,
        recursive: bool = False,
        dereference_recursive: bool = False,
        include_patterns: Optional[list] = None,
        exclude_patterns: Optional[list] = None,
        exclude_dirs: Optional[list] = None,
        stdin_label: Optional[str] = None,
        null_delimited: bool = False,
    ) -> list:
        """
        Get list of input sources.
        
        Args:
            files: List of file paths
            use_stdin: If True, read from stdin
            recursive: If True, recursively discover files from directories (don't follow symlinks)
            dereference_recursive: If True, recursively discover files and follow symlinks
            include_patterns: List of glob patterns to include (empty = include all)
            exclude_patterns: List of glob patterns to exclude
            exclude_dirs: List of glob patterns for directories to exclude
            stdin_label: Optional custom label for stdin input (from --label flag)
            null_delimited: If True, split records on NUL byte instead of newline (for -z flag)
        
        Returns:
            List of InputSource instances
        """
        import fnmatch
        
        sources = []
        
        def matches_patterns(path: str, patterns: Optional[list]) -> bool:
            """Check if path matches any of the patterns."""
            if not patterns:
                return True
            return any(fnmatch.fnmatch(path, p) for p in patterns)
        
        def should_exclude_dir(path: str) -> bool:
            """Check if directory should be excluded."""
            if not exclude_dirs:
                return False
            dir_name = os.path.basename(path)
            return any(fnmatch.fnmatch(dir_name, p) for p in exclude_dirs)
        
        if use_stdin:
            sources.append(InputSource('stdin', label=stdin_label, null_delimited=null_delimited))
        elif files:
            for file_path in files:
                # Support '-' as stdin
                if file_path == '-':
                    sources.append(InputSource('stdin', label=stdin_label, null_delimited=null_delimited))
                # Support FD numbers (e.g., 3, 4 from process substitution)
                elif file_path.isdigit():
                    fd = int(file_path)
                    sources.append(InputSource('fd', fd=fd, label=stdin_label, null_delimited=null_delimited))
                # Support /dev/fd/N and /proc/*/fd/N patterns (process substitution)
                elif file_path.startswith('/dev/fd/') and file_path[8:].isdigit():
                    fd = int(file_path[8:])
                    sources.append(InputSource('fd', fd=fd, label=stdin_label, null_delimited=null_delimited))
                elif '/proc/' in file_path and file_path.endswith(('/fd/0', '/fd/1', '/fd/2')):
                    # Standard streams via /proc
                    fd = int(file_path[-1])
                    sources.append(InputSource('fd', fd=fd, label=stdin_label, null_delimited=null_delimited))
                elif '/proc/' in file_path and '/fd/' in file_path:
                    # Try to extract FD number from /proc paths
                    try:
                        fd_str = file_path.split('/fd/')[-1]
                        if fd_str.isdigit():
                            fd = int(fd_str)
                            sources.append(InputSource('fd', fd=fd, label=stdin_label, null_delimited=null_delimited))
                        else:
                            # Not an FD path, treat as regular file
                            if not matches_patterns(file_path, include_patterns):
                                continue
                            if exclude_patterns and matches_patterns(file_path, exclude_patterns):
                                continue
                            sources.append(InputSource('file', file_path=file_path, null_delimited=null_delimited))
                    except (ValueError, IndexError):
                        # If extraction fails, treat as regular file
                        if not matches_patterns(file_path, include_patterns):
                            continue
                        if exclude_patterns and matches_patterns(file_path, exclude_patterns):
                            continue
                        sources.append(InputSource('file', file_path=file_path, null_delimited=null_delimited))
                elif os.path.isdir(file_path) and (recursive or dereference_recursive):
                    # Recursively discover files
                    follow_symlinks = dereference_recursive
                    for root, dirs, filenames in os.walk(file_path, followlinks=follow_symlinks):
                        # Filter out excluded directories
                        dirs[:] = [d for d in dirs if not should_exclude_dir(d)]
                        
                        for filename in sorted(filenames):
                            full_path = os.path.join(root, filename)
                            rel_path = os.path.relpath(full_path)
                            
                            # Apply include/exclude patterns
                            if not matches_patterns(rel_path, include_patterns):
                                continue
                            if exclude_patterns and matches_patterns(rel_path, exclude_patterns):
                                continue
                            
                            sources.append(InputSource('file', file_path=full_path, null_delimited=null_delimited))
                else:
                    # Single file - check if it matches patterns
                    if not matches_patterns(file_path, include_patterns):
                        continue
                    if exclude_patterns and matches_patterns(file_path, exclude_patterns):
                        continue
                    sources.append(InputSource('file', file_path=file_path, null_delimited=null_delimited))
        else:
            # Default: stdin if not a terminal
            if not sys.stdin.isatty():
                sources.append(InputSource('stdin', label=stdin_label, null_delimited=null_delimited))
        
        return sources
