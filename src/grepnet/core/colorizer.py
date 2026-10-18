"""
Colorizer: Generate ANSI color codes at startup, apply during matching.

Follows tight coupling requirement: colors determined at match time (when content
is available), not during output phase. Pre-renders colored content in MatchResult.
"""

import os
from typing import Dict, Optional


class ColorCode:
    """ANSI color code for a single attribute."""
    
    def __init__(self, code: str):
        """
        Args:
            code: ANSI SGR code (e.g., '31' for red, '0' for reset)
        """
        self.code = code
    
    def render(self, text: str) -> str:
        """Apply this color code to text."""
        if not self.code or self.code == '0':
            return text
        return f'\x1b[{self.code}m{text}\x1b[0m'
    
    def __str__(self):
        return f'\x1b[{self.code}m' if self.code else ''


class Colorizer:
    """
    ANSI color code generator and applier.
    
    Initialized once at startup by parsing GREPNET_COLORS environment variable.
    Defaults provide color highlighting for network match types and CIDR normalization.
    
    Used during matching to colorize content before creating MatchResult.
    Pre-rendered colored content stored in MatchResult.content_colored.
    """
    
    # Default SGR codes
    DEFAULTS = {
        'file': '35',      # fn= (filename - magenta, grep-compatible)
        'line': '32',      # ln= (line number - green, grep-compatible)
        'byte': '32',      # bn= (byte offset - green, grep-compatible)
        'sep': '36',       # se= (separator - cyan, grep-compatible)
        'selected': '0',   # sl= (selected line background)
        'match_equals': '01;32',     # me= (bright green for EQUALS)
        'match_subset': '01;34',     # mb= (bright blue for SUBSET)
        'match_superset': '01;33',   # mS= (bright yellow for SUPERSET)
        'match_overlap': '01;31',    # mo= (bright red for OVERLAP)
        'match_unmatched': '0',      # mu= (no color for UNMATCHED)
        'match_text': '0',           # mt= (match text color)
        'normalized': '04',          # mn= (underline for normalized CIDR)
        'wildcard_mask': '4:3',  # wm= (curly underline for wildcard mask format)
    }
    
    # Code name mappings for environment variables
    CODE_NAMES = {
        'mt': 'match_text',
        'ms': 'match_separator',
        'mc': 'match_colon',  # Compatibility with grep
        'fn': 'file',
        'ln': 'line',
        'bn': 'byte',
        'se': 'sep',
        'sl': 'selected',
        'cx': 'context',
        'me': 'match_equals',
        'mb': 'match_subset',
        'mS': 'match_superset',
        'mo': 'match_overlap',
        'mu': 'match_unmatched',
        'mn': 'normalized',
        'wm': 'wildcard_mask',  # Wildcard mask format color
    }
    
    def __init__(self, enable_colors: bool = True):
        """
        Initialize colorizer from GREPNET_COLORS environment variable.
        
        Args:
            enable_colors: If False, all colors disabled (all codes become '0')
        """
        self.colors: Dict[str, str] = self.DEFAULTS.copy()
        
        if enable_colors:
            self._parse_grepnet_colors()
    
    def _parse_grepnet_colors(self):
        """Parse GREPNET_COLORS environment variable (highest priority)."""
        colors_str = os.environ.get('GREPNET_COLORS', '')
        if not colors_str:
            return
        
        self._parse_color_string(colors_str)
    
    def _parse_color_string(self, color_string: str):
        """
        Parse color string in format: code1=value1:code2=value2:...
        
        Args:
            color_string: colon-separated key=value pairs
        """
        pairs = color_string.split(':')
        for pair in pairs:
            if '=' not in pair:
                continue
            key, value = pair.split('=', 1)
            key = key.strip()
            value = value.strip()
            
            # Map key to internal name
            if key in self.CODE_NAMES:
                internal_name = self.CODE_NAMES[key]
                self.colors[internal_name] = value
            elif key in self.colors:
                # Direct match (e.g., 'match_text')
                self.colors[key] = value
    
    def markup_network_in_line(
        self,
        line_content: str,
        network_text: str,
        match_type: 'MatchType',
        obj_type: str,
        was_normalized: bool = False,
    ) -> str:
        """
        Add internal markup to a network within a line.
        
        Markup uses Unicode Private Use Area (U+E000, U+E001) that never appear in network data.
        Format: ◀TYPE:MATCH_TYPE|OBJ:OBJECT_TYPE|NORM:WAS_NORMALIZED▶network_text◀/TYPE▶
        
        Args:
            line_content: Full line text
            network_text: The network text to find and markup
            match_type: MatchType (EQUALS, SUBSET, SUPERSET, OVERLAP, UNMATCHED)
            obj_type: Object type (CIDR, BARE_IP, RANGE, SUBNET_MASK, INVERSE_MASK)
            was_normalized: If True, indicates CIDR was corrected from non-strict mode
        
        Returns:
            Full line with network wrapped in markup
        """
        from .network_objects import MatchType
        
        # Get match type name
        match_type_name = match_type.name
        
        # Format: ◀TYPE:EQUALS|OBJ:CIDR|NORM:true▶network_text◀/TYPE▶
        markup_start = f'\uE000TYPE:{match_type_name}|OBJ:{obj_type}|NORM:{str(was_normalized).lower()}\uE001'
        markup_end = '\uE000/TYPE\uE001'
        
        marked_network = f'{markup_start}{network_text}{markup_end}'
        
        # Find and replace first occurrence of network_text, but NOT if it's inside existing markup
        import re
        escaped_network = re.escape(network_text)
        
        # Use a regex that matches the network text but not inside markup blocks
        # Markup blocks have the structure: \uE000...\uE001CONTENT\uE000/TYPE\uE001
        # We need to find a match that is NOT inside such a block
        
        matches = list(re.finditer(escaped_network, line_content))
        if not matches:
            return line_content
        
        # Find the first match that's NOT inside a markup block
        # A position is inside markup if there's an unmatched \uE000...\uE001CONTENT sequence before it
        for match in matches:
            start, end = match.span()
            # Check if this position is inside a markup block
            before_text = line_content[:start]
            
            # Find all markup blocks that haven't closed yet
            # A markup block starts with \uE000 and ends with \uE001CONTENT\uE000/TYPE\uE001
            # Simpler approach: look for open markup markers
            inside_markup = False
            
            # Track depth of markup
            depth = 0
            i = 0
            while i < len(before_text):
                if before_text[i:i+1] == '\uE000':
                    # Check if this starts a new markup or ends one
                    if before_text[i:i+6] == '\uE000/TYPE':
                        depth -= 1
                    else:
                        depth += 1
                    i += 1
                elif before_text[i:i+1] == '\uE001':
                    i += 1
                else:
                    i += 1
            
            inside_markup = depth > 0
            
            if inside_markup:
                # This match is inside markup, skip it
                continue
            
            # This match is not inside markup, use it
            result = line_content[:start] + marked_network + line_content[end:]
            return result
        
        # No valid match found, return unchanged
        return line_content
    
    def finalize_markup(self, content_marked: str, enable_colors: bool = True) -> str:
        """
        Convert internal markup to ANSI codes (or strip if colors disabled).
        
        Args:
            content_marked: Line with internal markup
            enable_colors: If True, convert to ANSI codes; else strip markup
        
        Returns:
            Line with ANSI codes or plain text
        """
        import re
        
        pattern = r'\uE000TYPE:([A-Z_]+)\|OBJ:([A-Z_]+)\|NORM:(\w+)\uE001(.*?)\uE000/TYPE\uE001'
        
        if not enable_colors:
            # Strip markup entirely
            return re.sub(pattern, r'\4', content_marked)
        
        # Convert markup to ANSI codes
        def replace_markup(match):
            match_type_str = match.group(1)  # EQUALS, SUBSET, etc.
            obj_type = match.group(2)        # CIDR, BARE_IP, WILDCARD_MASK, etc.
            was_normalized = match.group(3) == 'true'
            network_text = match.group(4)
            
            # Special handling for WILDCARD_MASK format
            if obj_type == 'WILDCARD_MASK':
                # Use wildcard_mask color code (wm=) instead of match type colors
                wm_code = self.colors.get('wildcard_mask', '0')
                if wm_code == '0':
                    return network_text
                return f'\x1b[{wm_code}m{network_text}\x1b[0m'
            
            # Standard match type colors for other OBJ types
            color_map = {
                'EQUALS': self.colors.get('match_equals', '0'),
                'SUBSET': self.colors.get('match_subset', '0'),
                'SUPERSET': self.colors.get('match_superset', '0'),
                'OVERLAP': self.colors.get('match_overlap', '0'),
                'UNMATCHED': self.colors.get('match_unmatched', '0'),
            }
            
            base_code = color_map.get(match_type_str, '0')
            
            # Stack with normalization code if applicable
            if was_normalized:
                norm_code = self.colors.get('normalized', '0')
                if base_code != '0' and norm_code != '0':
                    # Combine codes: e.g., "01;32;04" for green + underline
                    combined_code = f"{base_code};{norm_code}"
                elif norm_code != '0':
                    combined_code = norm_code
                else:
                    combined_code = base_code
            else:
                combined_code = base_code
            
            # No color needed
            if combined_code == '0':
                return network_text
            
            return f'\x1b[{combined_code}m{network_text}\x1b[0m'
        
        result = re.sub(pattern, replace_markup, content_marked)
        return result
    
    def colorize_network_in_line(
        self, 
        line_content: str, 
        network_text: str, 
        match_type: 'MatchType',
        was_normalized: bool = False,
    ) -> str:
        """
        Colorize a network within a full line (only the network text is colored).
        
        Spec requirement: "Apply color escape codes to the matched pattern (first occurrence only)"
        Multiple networks on the same line each get their own colorized version.
        
        Args:
            line_content: Full line text
            network_text: The network text to find and colorize (from original_text)
            match_type: MatchType (EQUALS, SUBSET, SUPERSET, OVERLAP, UNMATCHED)
            was_normalized: If True, include normalization flag in color stacking
        
        Returns:
            Full line with only the matched network colorized
        """
        from .network_objects import MatchType
        
        code_map = {
            MatchType.EQUALS: self.colors.get('match_equals', '0'),
            MatchType.SUBSET: self.colors.get('match_subset', '0'),
            MatchType.SUPERSET: self.colors.get('match_superset', '0'),
            MatchType.OVERLAP: self.colors.get('match_overlap', '0'),
            MatchType.UNMATCHED: self.colors.get('match_unmatched', '0'),
        }
        
        base_code = code_map.get(match_type, '0')
        
        # Stack with normalization code if applicable
        if was_normalized:
            norm_code = self.colors.get('normalized', '0')
            if base_code != '0' and norm_code != '0':
                # Combine codes: e.g., "01;32;04" for green + underline
                combined_code = f"{base_code};{norm_code}"
            elif norm_code != '0':
                combined_code = norm_code
            else:
                combined_code = base_code
        else:
            combined_code = base_code
        
        # No color needed
        if combined_code == '0':
            return line_content
        
        # Find and colorize first occurrence of network_text
        # Escape special regex chars in the network text
        import re
        escaped_network = re.escape(network_text)
        pattern = escaped_network
        
        # Replace first occurrence only
        colored_network = f'\x1b[{combined_code}m{network_text}\x1b[0m'
        result = re.sub(pattern, colored_network, line_content, count=1)
        
        return result
    
    def colorize_match(self, text: str, match_type: 'MatchType') -> str:
        """
        Colorize text based on match type.
        
        Args:
            text: Text to colorize
            match_type: MatchType (EQUALS, SUBSET, SUPERSET, OVERLAP, UNMATCHED)
        
        Returns:
            Colored text with ANSI codes
        """
        from .network_objects import MatchType
        
        code_map = {
            MatchType.EQUALS: self.colors.get('match_equals', '0'),
            MatchType.SUBSET: self.colors.get('match_subset', '0'),
            MatchType.SUPERSET: self.colors.get('match_superset', '0'),
            MatchType.OVERLAP: self.colors.get('match_overlap', '0'),
            MatchType.UNMATCHED: self.colors.get('match_unmatched', '0'),
        }
        
        code = code_map.get(match_type, '0')
        if code == '0':
            return text
        
        return f'\x1b[{code}m{text}\x1b[0m'
    
    def colorize_by_name(self, text: str, color_name: str) -> str:
        """
        Colorize text by color name (e.g., 'match_text', 'normalized').
        
        Args:
            text: Text to colorize
            color_name: Color name (key in self.colors)
        
        Returns:
            Colored text with ANSI codes
        """
        code = self.colors.get(color_name, '0')
        if code == '0':
            return text
        
        return f'\x1b[{code}m{text}\x1b[0m'
    
    def colorize_filename(self, filename: str) -> str:
        """Colorize filename using 'file' color code."""
        return self.colorize_by_name(filename, 'file')
    
    def colorize_line_number(self, line_num: str) -> str:
        """Colorize line number using 'line' color code."""
        return self.colorize_by_name(line_num, 'line')
    
    def colorize_byte_offset(self, byte_offset: str) -> str:
        """Colorize byte offset using 'byte' color code."""
        return self.colorize_by_name(byte_offset, 'byte')
    
    def colorize_separator(self, sep: str) -> str:
        """Colorize separator using 'sep' color code."""
        return self.colorize_by_name(sep, 'sep')
