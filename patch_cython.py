#!/usr/bin/env python3
"""
Patch Cython's _tempita.py to handle missing cgi module.

This script patches Cython 0.29.x source code to make it work without cgi.
"""
import os
import sys


def find_tempita():
    """Find the _tempita.py file in Cython installation."""
    try:
        import Cython
        cython_dir = os.path.dirname(Cython.__file__)
        tempita_path = os.path.join(cython_dir, 'Tempita', '_tempita.py')
        if os.path.exists(tempita_path):
            return tempita_path
    except ImportError:
        pass
    
    # Try in site-packages
    import site
    for site_dir in site.getsitepackages():
        candidate = os.path.join(site_dir, 'Cython', 'Tempita', '_tempita.py')
        if os.path.exists(candidate):
            return candidate
    
    return None


def patch_tempita():
    tempita_path = find_tempita()
    if not tempita_path:
        print("[patch_cython] _tempita.py not found")
        return False
    
    print(f"[patch_cython] Patching {tempita_path}")
    
    with open(tempita_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Original line 36: import cgi (or similar)
    # Replace with: import html as _cgi_html, then create fake cgi module
    if 'import cgi' in content and '# cgi_patched' not in content:
        # Find the import cgi line
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.strip() == 'import cgi':
                # Replace with shim
                new_lines = lines[:i]
                new_lines.append('# cgi_patched')
                new_lines.append('try:')
                new_lines.append('    import cgi  # noqa: F401')
                new_lines.append('except ImportError:')
                new_lines.append('    # cgi module was removed in Python 3.13')
                new_lines.append('    import html as cgi')
                new_lines.append('    if not hasattr(cgi, \'escape\'):')
                new_lines.append('        cgi.escape = html.escape')
                new_lines.append('    if not hasattr(cgi, \'parse_qs\'):')
                new_lines.append('        import urllib.parse')
                new_lines.append('        cgi.parse_qs = urllib.parse.parse_qs')
                new_lines.append(lines[i+1:])
                content = '\n'.join(new_lines)
                break
        
        with open(tempita_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"[patch_cython] Patched successfully")
        return True
    else:
        print(f"[patch_cython] Already patched or no 'import cgi' found")
        return False


if __name__ == '__main__':
    success = patch_tempita()
    sys.exit(0 if success else 1)