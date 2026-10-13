"""
Test suite for comment handling in grepnet.

Tests that comment markers are properly recognized and handled during extraction,
and that full original lines are output when they contain networks.
"""

import unittest
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from grepnet.parsing.comment_handler import CommentHandler


class TestCommentHandlerExtraction(unittest.TestCase):
    """Test comment filtering during network extraction phase."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.handler = CommentHandler()
    
    def test_comment_only_line_with_hash(self):
        """Comment-only lines with # should be completely filtered."""
        filtered, had_comments = self.handler.filter_comments('# Version1 192.0.2.2', filter_enabled=True)
        self.assertEqual(filtered, '')
        self.assertTrue(had_comments)
    
    def test_comment_only_line_with_exclamation(self):
        """Comment-only lines with ! should be completely filtered."""
        filtered, had_comments = self.handler.filter_comments('! Version1 192.0.2.2', filter_enabled=True)
        self.assertEqual(filtered, '')
        self.assertTrue(had_comments)
    
    def test_comment_only_line_with_double_slash(self):
        """Comment-only lines with // should be completely filtered."""
        filtered, had_comments = self.handler.filter_comments('// Version1 192.0.2.2', filter_enabled=True)
        self.assertEqual(filtered, '')
        self.assertTrue(had_comments)
    
    def test_comment_only_line_with_double_dash(self):
        """Comment-only lines with -- should be completely filtered."""
        filtered, had_comments = self.handler.filter_comments('-- Version1 192.0.2.2', filter_enabled=True)
        self.assertEqual(filtered, '')
        self.assertTrue(had_comments)
    
    def test_comment_only_line_with_semicolon(self):
        """Comment-only lines with ; should be completely filtered."""
        filtered, had_comments = self.handler.filter_comments('; Version1 192.0.2.2', filter_enabled=True)
        self.assertEqual(filtered, '')
        self.assertTrue(had_comments)
    
    def test_comment_marker_without_trailing_space_hash(self):
        """Comment markers do NOT require trailing whitespace (per spec)."""
        filtered, had_comments = self.handler.filter_comments('#anything', filter_enabled=True)
        self.assertEqual(filtered, '')
        self.assertTrue(had_comments)
    
    def test_comment_marker_without_trailing_space_exclamation(self):
        """Exclamation comment markers do NOT require trailing whitespace."""
        filtered, had_comments = self.handler.filter_comments('!anything', filter_enabled=True)
        self.assertEqual(filtered, '')
        self.assertTrue(had_comments)
    
    def test_inline_comment_hash_in_middle(self):
        """Inline # marker in middle of line should split at marker."""
        filtered, had_comments = self.handler.filter_comments('192.0.2.1#192.0.2.2', filter_enabled=True)
        self.assertEqual(filtered, '192.0.2.1')
        self.assertTrue(had_comments)
    
    def test_inline_comment_exclamation_in_middle(self):
        """Inline ! marker in middle of line should split at marker."""
        filtered, had_comments = self.handler.filter_comments('192.0.2.1!192.0.2.2', filter_enabled=True)
        self.assertEqual(filtered, '192.0.2.1')
        self.assertTrue(had_comments)
    
    def test_inline_comment_double_slash_in_middle(self):
        """Inline // marker in middle of line should split at marker."""
        filtered, had_comments = self.handler.filter_comments('192.0.2.1//192.0.2.2', filter_enabled=True)
        self.assertEqual(filtered, '192.0.2.1')
        self.assertTrue(had_comments)
    
    def test_inline_comment_double_dash_in_middle(self):
        """Inline -- marker in middle of line should split at marker."""
        filtered, had_comments = self.handler.filter_comments('192.0.2.1--192.0.2.2', filter_enabled=True)
        self.assertEqual(filtered, '192.0.2.1')
        self.assertTrue(had_comments)
    
    def test_inline_comment_semicolon_in_middle(self):
        """Inline ; marker in middle of line should split at marker."""
        filtered, had_comments = self.handler.filter_comments('192.0.2.1;192.0.2.2', filter_enabled=True)
        self.assertEqual(filtered, '192.0.2.1')
        self.assertTrue(had_comments)
    
    def test_inline_comment_with_trailing_space(self):
        """Inline comment with leading space should split at marker."""
        filtered, had_comments = self.handler.filter_comments('192.0.2.1 # comment', filter_enabled=True)
        self.assertEqual(filtered, '192.0.2.1')
        self.assertTrue(had_comments)
    
    def test_inline_comment_no_space_before_marker(self):
        """Inline comment marker without preceding space should still split."""
        filtered, had_comments = self.handler.filter_comments('192.0.2.1# comment', filter_enabled=True)
        self.assertEqual(filtered, '192.0.2.1')
        self.assertTrue(had_comments)
    
    def test_cisco_remark_keyword(self):
        """Cisco 'remark' keyword should filter line."""
        filtered, had_comments = self.handler.filter_comments('remark This is a comment', filter_enabled=True)
        self.assertEqual(filtered, '')
        self.assertTrue(had_comments)
    
    def test_cisco_rem_keyword(self):
        """Cisco 'rem' keyword (abbreviated) should filter line."""
        filtered, had_comments = self.handler.filter_comments('rem This is a comment', filter_enabled=True)
        self.assertEqual(filtered, '')
        self.assertTrue(had_comments)
    
    def test_cisco_description_keyword(self):
        """Cisco 'description' keyword should filter line."""
        filtered, had_comments = self.handler.filter_comments('description This is a comment', filter_enabled=True)
        self.assertEqual(filtered, '')
        self.assertTrue(had_comments)
    
    def test_cisco_desc_keyword(self):
        """Cisco 'desc' keyword (abbreviated) should filter line."""
        filtered, had_comments = self.handler.filter_comments('desc This is a comment', filter_enabled=True)
        self.assertEqual(filtered, '')
        self.assertTrue(had_comments)
    
    def test_cisco_remark_case_insensitive(self):
        """Cisco keywords should be case-insensitive."""
        filtered, had_comments = self.handler.filter_comments('REMARK This is a comment', filter_enabled=True)
        self.assertEqual(filtered, '')
        self.assertTrue(had_comments)
    
    def test_cisco_keyword_requires_leading_whitespace(self):
        """Cisco keywords must be preceded by whitespace to be recognized."""
        filtered, had_comments = self.handler.filter_comments('text101rem', filter_enabled=True)
        self.assertEqual(filtered, 'text101rem')
        self.assertFalse(had_comments)
    
    def test_cisco_keyword_with_leading_whitespace(self):
        """Cisco keywords with leading whitespace in config should work."""
        filtered, had_comments = self.handler.filter_comments('  remark This is a comment', filter_enabled=True)
        self.assertEqual(filtered, '')
        self.assertTrue(had_comments)
    
    def test_cisco_keyword_in_middle_with_leading_space(self):
        """Cisco keyword in middle of line with leading space should strip from keyword onward."""
        filtered, had_comments = self.handler.filter_comments('access-list 101 remark This is a comment', filter_enabled=True)
        self.assertEqual(filtered, 'access-list 101')
        self.assertTrue(had_comments)
    
    def test_cisco_keyword_without_trailing_space(self):
        """Cisco keyword at end of line should strip it."""
        filtered, had_comments = self.handler.filter_comments('text101 rem', filter_enabled=True)
        self.assertEqual(filtered, 'text101')
        self.assertTrue(had_comments)
    
    def test_block_comment_c_style(self):
        """C-style block comments /* ... */ should be removed."""
        filtered, had_comments = self.handler.filter_comments('192.0.2.1 /* comment */ 192.0.2.2', filter_enabled=True)
        # Networks should be extracted from before and after comment
        self.assertIn('192.0.2.1', filtered)
        self.assertIn('192.0.2.2', filtered)
        self.assertTrue(had_comments)
    
    def test_html_block_comment(self):
        """HTML/XML block comments <!-- ... --> should be removed."""
        filtered, had_comments = self.handler.filter_comments('192.0.2.1 <!-- comment --> 192.0.2.2', filter_enabled=True)
        # Networks should be extracted from before and after comment
        self.assertIn('192.0.2.1', filtered)
        self.assertIn('192.0.2.2', filtered)
        self.assertTrue(had_comments)
    
    def test_filter_disabled(self):
        """When filter_enabled=False, comments should not be removed."""
        filtered, had_comments = self.handler.filter_comments('192.0.2.1 # comment', filter_enabled=False)
        self.assertEqual(filtered, '192.0.2.1 # comment')
        self.assertFalse(had_comments)
    
    def test_first_marker_wins(self):
        """When multiple marker types present, first one in line wins."""
        # ! comes before #
        filtered, had_comments = self.handler.filter_comments('192.0.2.1!192.0.2.2#192.0.2.3', filter_enabled=True)
        self.assertEqual(filtered, '192.0.2.1')
        self.assertTrue(had_comments)
    
    def test_marker_precedence_hash_before_exclamation(self):
        """When # appears before !, hash takes precedence."""
        filtered, had_comments = self.handler.filter_comments('192.0.2.1 # comment ! more', filter_enabled=True)
        self.assertEqual(filtered, '192.0.2.1')
        self.assertTrue(had_comments)
    
    def test_marker_precedence_double_slash_before_semicolon(self):
        """When // appears before ;, double-slash takes precedence."""
        filtered, had_comments = self.handler.filter_comments('192.0.2.1 // comment ; more', filter_enabled=True)
        self.assertEqual(filtered, '192.0.2.1')
        self.assertTrue(had_comments)
    
    def test_marker_precedence_double_dash_before_hash(self):
        """When -- appears before #, double-dash takes precedence."""
        filtered, had_comments = self.handler.filter_comments('192.0.2.1 -- comment # more', filter_enabled=True)
        self.assertEqual(filtered, '192.0.2.1')
        self.assertTrue(had_comments)
    
    def test_block_comment_swallows_single_line_markers(self):
        """Block comment contains single-line markers without special meaning."""
        filtered, had_comments = self.handler.filter_comments('192.0.2.1 /* comment -- # ! */ 192.0.2.2', filter_enabled=True)
        # Block comment should be removed entirely, leaving both IPs
        self.assertIn('192.0.2.1', filtered)
        self.assertIn('192.0.2.2', filtered)
        self.assertNotIn('/*', filtered)
        self.assertTrue(had_comments)
    
    def test_html_block_comment_swallows_c_style_markers(self):
        """HTML block comment contains C-style markers without special meaning."""
        filtered, had_comments = self.handler.filter_comments('192.0.2.1 <!-- comment /* text --> 192.0.2.2', filter_enabled=True)
        # HTML comment should be removed entirely, leaving both IPs
        self.assertIn('192.0.2.1', filtered)
        self.assertIn('192.0.2.2', filtered)
        self.assertNotIn('<!--', filtered)
        self.assertTrue(had_comments)
    
    def test_no_comments(self):
        """Lines without comments should return unchanged."""
        filtered, had_comments = self.handler.filter_comments('192.0.2.1 192.0.2.2', filter_enabled=True)
        self.assertEqual(filtered, '192.0.2.1 192.0.2.2')
        self.assertFalse(had_comments)


class TestCommentHandlerIsCommentLine(unittest.TestCase):
    """Test is_comment_line class method."""
    
    def test_hash_comment_line(self):
        """Hash-prefixed lines should be identified as comments."""
        self.assertTrue(CommentHandler.is_comment_line('# comment'))
    
    def test_exclamation_comment_line(self):
        """Exclamation-prefixed lines should be identified as comments."""
        self.assertTrue(CommentHandler.is_comment_line('! comment'))
    
    def test_double_slash_comment_line(self):
        """Double-slash-prefixed lines should be identified as comments."""
        self.assertTrue(CommentHandler.is_comment_line('// comment'))
    
    def test_double_dash_comment_line(self):
        """Double-dash-prefixed lines should be identified as comments."""
        self.assertTrue(CommentHandler.is_comment_line('-- comment'))
    
    def test_semicolon_comment_line(self):
        """Semicolon-prefixed lines should be identified as comments."""
        self.assertTrue(CommentHandler.is_comment_line('; comment'))
    
    def test_cisco_remark_line(self):
        """Cisco remark keyword line should be identified as comment."""
        self.assertTrue(CommentHandler.is_comment_line('remark This is a comment'))
    
    def test_non_comment_line(self):
        """Regular lines should not be identified as comments."""
        self.assertFalse(CommentHandler.is_comment_line('192.0.2.1 some text'))
    
    def test_non_comment_line_with_embedded_marker(self):
        """Lines with embedded markers should not be identified as full comments."""
        self.assertFalse(CommentHandler.is_comment_line('192.0.2.1#192.0.2.2'))


if __name__ == '__main__':
    unittest.main()
