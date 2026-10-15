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
    - Cisco keywords: remark, rem, description, desc (must be preceded/followed by whitespace)
    - Can be disabled with --no-filter-comments flag
    """
    
    # Regex for inline comments: # followed by space/tab
    INLINE_COMMENT_PATTERN = re.compile(r'\s+#\s')
    
    # Cisco keywords (case-insensitive, must be word-bounded)
    CISCO_KEYWORDS = re.compile(r'\b(remark|rem|description|desc)\b', re.IGNORECASE)
    
    def __init__(self):
        """Initialize with block comment state tracking."""
        self.in_block_comment = False
    
    def reset(self) -> None:
        """Reset block comment state (call between files)."""
        self.in_block_comment = False
    
    def filter_comments(self, line: str, filter_enabled: bool = True) -> Tuple[str, bool]:
        """
        Remove comments from line if filtering is enabled.
        
        Handles:
        - Full-line comments (lines starting with #, !, //, --, ;)
        - Cisco keywords (remark, rem, description, desc)
        - Inline single-line markers (# ! -- // ;) anywhere in line
        - Block comments (/* ... */ and <!-- ... -->)
        - Multi-line block comments (state tracked via self.in_block_comment)
        
        Args:
            line: Line text
            filter_enabled: If False, return line as-is
        
        Returns:
            Tuple of (filtered_line, had_comments)
        """
        if not filter_enabled:
            return line, False
        
        had_comments = False
        
        # Full-line comment markers (any of these at line start means full-line comment)
        stripped = line.lstrip()
        if stripped and stripped[0] in '#!;' or stripped.startswith('//') or stripped.startswith('--'):
            return '', True
        
        # Check for Cisco keywords at line start (full-line comment)
        if self.CISCO_KEYWORDS.match(stripped):
            return '', True
        
        # Handle multi-line block comments (already in block comment)
        if self.in_block_comment:
            # Look for end of block comment
            end_pos = line.find('*/')
            if end_pos != -1:
                # End of block found
                self.in_block_comment = False
                # Continue processing after the */
                remaining = line[end_pos + 2:].lstrip()
                # Recursively process the remaining part
                filtered, more_comments = self.filter_comments(remaining, filter_enabled=True)
                return filtered, True or more_comments
            else:
                # Still in block comment
                return '', True
        
        # Process line for block comments and inline comments
        filtered = line
        
        # Handle HTML-style block comments <!-- ... --> FIRST (more specific)
        while '<!--' in filtered:
            start_pos = filtered.find('<!--')
            end_pos = filtered.find('-->', start_pos + 4)
            
            if end_pos == -1:
                # HTML comment doesn't end on this line
                self.in_block_comment = True
                # Remove from <!-- to end of line
                filtered = filtered[:start_pos].rstrip()
                had_comments = True
                break
            else:
                # HTML comment ends on this line
                before = filtered[:start_pos]
                after = filtered[end_pos + 3:]
                filtered = before + after
                had_comments = True
        
        # Handle C-style block comments /* ... */ (after HTML comments)
        while '/*' in filtered:
            start_pos = filtered.find('/*')
            end_pos = filtered.find('*/', start_pos + 2)
            
            if end_pos == -1:
                # Block comment doesn't end on this line
                self.in_block_comment = True
                # Remove from /* to end of line
                filtered = filtered[:start_pos].rstrip()
                had_comments = True
                break
            else:
                # Block comment ends on this line
                before = filtered[:start_pos]
                after = filtered[end_pos + 2:]
                filtered = before + after
                had_comments = True
        
        # Find the FIRST comment marker (any of: #, !, //, --, ;)
        # These can appear anywhere in the line (no preceding whitespace required)
        first_marker_pos = len(filtered)
        marker_type = None
        
        # Check for single-char markers
        for marker in ['#', '!', ';']:
            pos = filtered.find(marker)
            if pos != -1 and pos < first_marker_pos:
                first_marker_pos = pos
                marker_type = marker
        
        # Check for two-char markers (// and --)
        for marker in ['//', '--']:
            pos = filtered.find(marker)
            if pos != -1 and pos < first_marker_pos:
                first_marker_pos = pos
                marker_type = marker
        
        # Check for Cisco keywords (must be surrounded by whitespace)
        cisco_match = self.CISCO_KEYWORDS.search(filtered)
        if cisco_match:
            # Check if preceded by whitespace (or at start)
            start_pos = cisco_match.start()
            if start_pos == 0 or filtered[start_pos - 1].isspace():
                # Check if followed by whitespace (or end of string)
                end_pos = cisco_match.end()
                if end_pos >= len(filtered) or filtered[end_pos].isspace():
                    # Valid Cisco keyword - check if it comes before other markers
                    if start_pos < first_marker_pos:
                        first_marker_pos = start_pos
                        marker_type = 'cisco'
        
        # Apply the first marker found
        if marker_type == 'cisco':
            # Cisco keyword: remove from keyword to end
            filtered = filtered[:first_marker_pos].rstrip()
            had_comments = True
        elif marker_type is not None:
            # Single-line marker: remove from marker to end
            filtered = filtered[:first_marker_pos].rstrip()
            had_comments = True
        
        return filtered.rstrip(), had_comments
    
    @classmethod
    def is_comment_line(cls, line: str) -> bool:
        """Check if entire line is a comment.
        
        Returns True if line starts with any comment marker:
        - Full-line markers: #, !, //, --, ;
        - Cisco keywords: remark, rem, description, desc
        """
        stripped = line.lstrip()
        if not stripped:
            return False
        
        # Check for single-char markers
        if stripped[0] in '#!;':
            return True
        
        # Check for two-char markers
        if stripped.startswith('//') or stripped.startswith('--'):
            return True
        
        # Check for Cisco keywords
        if cls.CISCO_KEYWORDS.match(stripped):
            return True
        
        return False
