#!/usr/bin/env python3
"""
Build grepnet-bundled: Single-file executable combining all modules.
"""

import os
import re
from pathlib import Path


def get_module_order():
    """Return the correct order to concatenate modules."""
    return [
        # Core modules first (no dependencies)
        'src/grepnet/core/__init__.py',
        'src/grepnet/core/network_objects.py',
        'src/grepnet/core/binary_detector.py',
        'src/grepnet/core/colorizer.py',
        
        # Input modules
        'src/grepnet/input/__init__.py',
        'src/grepnet/input/input_source.py',
        
        # Matching modules
        'src/grepnet/matching/__init__.py',
        'src/grepnet/matching/cidr_matcher.py',
        'src/grepnet/matching/range_matcher.py',
        
        # Parsing modules (extractors first, then others)
        'src/grepnet/parsing/__init__.py',
        'src/grepnet/parsing/extractors/__init__.py',
        'src/grepnet/parsing/extractors/cidr_extractor.py',
        'src/grepnet/parsing/extractors/ip_only_extractor.py',
        'src/grepnet/parsing/extractors/ip_range_extractor.py',
        'src/grepnet/parsing/extractors/subnet_mask_extractor.py',
        'src/grepnet/parsing/extractors/inverse_mask_extractor.py',
        'src/grepnet/parsing/extractors/wildcard_mask_extractor.py',
        'src/grepnet/parsing/extractors/ipv6_extractor.py',
        'src/grepnet/parsing/mask_format_detector.py',
        'src/grepnet/parsing/comment_handler.py',
        'src/grepnet/parsing/network_parser.py',
        
        # Main modules last
        'src/grepnet/grepnet.py',
        'src/grepnet/__init__.py',
        'src/grepnet/cli.py',
    ]


def clean_imports(content, module_path):
    """Remove internal imports but keep class/function references available."""
    lines = content.split('\n')
    cleaned = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Skip grepnet internal absolute imports - they become local references
        # Pattern: from grepnet.XXX import YYY -> removed, YYY is now in same scope
        if re.match(r'^\s*from grepnet\.', line):
            i += 1
            continue
        if re.match(r'^\s*import grepnet\.', line):
            i += 1
            continue
        
        # For: import grepnet as grepnet_module
        # Replace with pass - the module is now everything in this file
        if re.match(r'^\s*import grepnet(\s+as\s+\w+)?(\s*#.*)?$', line):
            # Skip this line - grepnet is now the current namespace
            i += 1
            continue
        
        # Handle multi-line relative imports: from .module import (...)
        # These should be skipped entirely since all modules are in one file
        if re.match(r'^\s*from \.', line) and 'import' in line:
            # Find the end of this import statement
            if '(' in line:
                open_count = line.count('(')
                close_count = line.count(')')
                i += 1
                while open_count > close_count and i < len(lines):
                    open_count += lines[i].count('(')
                    close_count += lines[i].count(')')
                    i += 1
            else:
                i += 1
            continue
        
        # Skip __all__ declarations (multi-line support)
        if re.match(r'^\s*__all__\s*=', line):
            # Find the end of this assignment
            if '[' in line or '(' in line:
                open_count = line.count('[') + line.count('(')
                close_count = line.count(']') + line.count(')')
                i += 1
                while open_count > close_count and i < len(lines):
                    open_count += lines[i].count('[') + lines[i].count('(')
                    close_count += lines[i].count(']') + lines[i].count(')')
                    i += 1
            else:
                i += 1
            continue
        
        cleaned.append(line)
        i += 1
    
    return '\n'.join(cleaned)


def build_bundle():
    """Build the grepnet-bundled executable."""
    
    # Start with shebang and version
    header = '''#!/usr/bin/env python3
"""GrepNet - Network-aware grep (single file executable)

Version: 5.0.0
"""

'''
    
    parts = [header]
    module_order = get_module_order()
    
    print("Building grepnet-bundled...")
    print()
    
    for module_path in module_order:
        if not os.path.exists(module_path):
            print(f"⚠ Skipping missing: {module_path}")
            continue
        
        with open(module_path, 'r') as f:
            content = f.read()
        
        # Add separator comment
        parts.append(f"\n# {module_path}\n")
        
        # Clean the content
        content = clean_imports(content, module_path)
        
        # Remove shebang if present
        if content.startswith('#!'):
            lines = content.split('\n')
            content = '\n'.join(lines[1:])
        
        parts.append(content)
        print(f"✓ {module_path}")
    
    # Combine all parts
    bundled = ''.join(parts)
    
    # Write to grepnet-bundled
    output_path = 'grepnet-bundled'
    with open(output_path, 'w') as f:
        f.write(bundled)
    
    # Make executable
    os.chmod(output_path, 0o755)
    
    # Get stats
    lines = bundled.count('\n')
    size_kb = len(bundled) / 1024
    
    print()
    print(f"✓ Built {output_path}")
    print(f"  Size: {size_kb:.1f} KB")
    print(f"  Lines: {lines:,}")
    print()
    
    return bundled


if __name__ == '__main__':
    build_bundle()

