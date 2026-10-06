"""
Comment handling for network extraction.

Removes comments from lines before extraction, with optional --no-filter-comments flag.
"""

import re
from typing import Tuple


class CommentHandler:
    """
    Handles comment removal from lines.
    
    Rules:
    - Lines starting with '#' are full-line comments
    - Inline comments: '#' followed by whitespace
    - Block comments: /* ... */ (multi-line)
    - Can be disabled with --no-filter-comments flag
    """
    
    # Regex for inline comments: # followed by space/tab
    INLINE_COMMENT_PATTERN = re.compile(r'\s+#\s')
    
    def __init__(self):
        """Initialize with block comment state tracking."""
        self.in_block_comment = False
    
    def reset(self) -> None:
        """Reset block comment state (call between files)."""
        self.in_block_comment = False
    
    def filter_comments(self, line: str, filter_enabled: bool = True) -> Tuple[str, bool]:
        """
        Remove comments from line if filtering is enabled.
        
        Args:
            line: Line text
            filter_enabled: If False, return line as-is
        
        Returns:
            Tuple of (filtered_line, had_comments)
        """
        if not filter_enabled:
            return line, False
        
        had_comments = False
        original_line = line
        
        # Full-line comment
        stripped = line.lstrip()
        if stripped.startswith('#'):
            return '', True
        
        # Block comment handling
        while '/*' in line or self.in_block_comment:
            if self.in_block_comment:
                # We're inside a block comment, look for the end
                end_pos = line.find('*/')
                if end_pos != -1:
                    # Found end of block comment
                    line = line[end_pos + 2:]  # Remove everything up to and including */
                    self.in_block_comment = False
                    had_comments = True
                    # Continue loop in case there's more content after the comment
                else:
                    # Entire line is part of block comment
                    return '', True
            else:
                # Look for start of block comment
                start_pos = line.find('/*')
                if start_pos != -1:
                    # Found start of block comment
                    end_pos = line.find('*/', start_pos + 2)
                    if end_pos != -1:
                        # Block comment ends on same line
                        line = line[:start_pos] + line[end_pos + 2:]
                        had_comments = True
                        # Continue loop in case there's more content after the comment
                    else:
                        # Block comment starts but doesn't end on this line
                        line = line[:start_pos]
                        self.in_block_comment = True
                        had_comments = True
                        break  # Stop processing this line, state is saved for next line
                else:
                    # No block comment found
                    break
        
        # Inline comment: find ' #' pattern
        match = self.INLINE_COMMENT_PATTERN.search(line)
        if match:
            # Remove from the space before # onward
            line = line[:match.start()]
            line = line.rstrip()
            had_comments = True
        
        return line, had_comments
    
    @classmethod
    def is_comment_line(cls, line: str) -> bool:
        """Check if entire line is a comment."""
        return line.lstrip().startswith('#')
