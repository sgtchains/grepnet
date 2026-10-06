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
    - Lines starting with '#' are full-line comments (Unix/Python/shell)
    - Lines starting with '!' are Cisco full-line comments
    - Lines starting with '--' are SQL/Lua full-line comments
    - Lines starting with '//' are C-style full-line comments
    - Lines starting with ';' are INI/Lisp full-line comments
    - Lines starting with 'remark', 'rem', 'description', or 'desc' are Cisco descriptions (case-insensitive)
    - Inline comments: '#' followed by whitespace
    - Block comments: /* ... */ (multi-line C-style)
    - Block comments: <!-- ... --> (multi-line HTML/XML)
    - Can be disabled with --no-filter-comments flag
    """
    
    # Regex for inline comments: # followed by space/tab (no leading space required)
    INLINE_COMMENT_PATTERN = re.compile(r'#\s')
    # Regex for inline // comments: // followed by space/tab
    INLINE_CSTYLE_COMMENT_PATTERN = re.compile(r'//\s')
    # Regex for inline -- comments: -- followed by space/tab
    INLINE_SQL_COMMENT_PATTERN = re.compile(r'--\s')
    # Regex for inline ; comments: ; followed by space/tab
    INLINE_SEMI_COMMENT_PATTERN = re.compile(r';\s')
    
    # Regex for Cisco keywords (case-insensitive)
    CISCO_KEYWORD_PATTERN = re.compile(r'^\s*(remark|rem|description|desc)\s', re.IGNORECASE)
    
    def __init__(self):
        """Initialize with block comment state tracking."""
        self.in_block_comment = False
        self.in_html_comment = False
    
    def reset(self) -> None:
        """Reset block comment state (call between files)."""
        self.in_block_comment = False
        self.in_html_comment = False
    
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
        
        # HTML/XML block comment handling: <!-- ... --> (check BEFORE SQL comments)
        # This must come before SQL comment checks since "-->" starts with "--"
        while '<!--' in line or (hasattr(self, 'in_html_comment') and self.in_html_comment):
            if hasattr(self, 'in_html_comment') and self.in_html_comment:
                # We're inside an HTML comment, look for the end
                end_pos = line.find('-->')
                if end_pos != -1:
                    # Found end of HTML comment
                    line = line[end_pos + 3:]  # Remove everything up to and including -->
                    self.in_html_comment = False
                    had_comments = True
                    # If line is now empty, exit loop
                    if not line:
                        break
                    # Continue loop in case there's more content after the comment
                else:
                    # Entire line is part of HTML comment
                    return '', True
            else:
                # Look for start of HTML comment
                start_pos = line.find('<!--')
                if start_pos != -1:
                    # Found start of HTML comment
                    end_pos = line.find('-->', start_pos + 4)
                    if end_pos != -1:
                        # HTML comment ends on same line
                        line = line[:start_pos] + line[end_pos + 3:]
                        had_comments = True
                        # Continue loop in case there's more content after the comment
                    else:
                        # HTML comment starts but doesn't end on this line
                        line = line[:start_pos]
                        self.in_html_comment = True
                        had_comments = True
                        break  # Stop processing this line, state is saved for next line
                else:
                    # No HTML comment found
                    break
        
        # Full-line comments: #, !, --, //, ;
        stripped = line.lstrip()
        if stripped.startswith('#') or stripped.startswith('!') or \
           stripped.startswith('--') or stripped.startswith('//') or \
           stripped.startswith(';'):
            return '', True
        
        # Cisco keywords: remark, rem, description, desc (case-insensitive)
        if self.CISCO_KEYWORD_PATTERN.match(line):
            return '', True
        
        # C-style block comment handling: /* ... */
        while '/*' in line or self.in_block_comment:
            if self.in_block_comment:
                # We're inside a block comment, look for the end
                end_pos = line.find('*/')
                if end_pos != -1:
                    # Found end of block comment
                    line = line[end_pos + 2:]  # Remove everything up to and including */
                    self.in_block_comment = False
                    had_comments = True
                    # If line is now empty, exit loop
                    if not line:
                        break
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
        
        # Inline comments: check for #, //, --, ; followed by whitespace
        for pattern in [self.INLINE_COMMENT_PATTERN, 
                       self.INLINE_CSTYLE_COMMENT_PATTERN,
                       self.INLINE_SQL_COMMENT_PATTERN,
                       self.INLINE_SEMI_COMMENT_PATTERN]:
            match = pattern.search(line)
            if match:
                # Remove from the space before comment char onward
                line = line[:match.start()]
                line = line.rstrip()
                had_comments = True
                break  # Only one inline comment type per line
        
        return line, had_comments
    
    @classmethod
    def is_comment_line(cls, line: str) -> bool:
        """Check if entire line is a comment."""
        stripped = line.lstrip()
        # Check all single-line comment prefixes
        if stripped.startswith('#') or stripped.startswith('!') or \
           stripped.startswith('--') or stripped.startswith('//') or \
           stripped.startswith(';'):
            return True
        # Check for Cisco keywords
        return bool(re.match(r'^(remark|rem|description|desc)\s', stripped, re.IGNORECASE))
