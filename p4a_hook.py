#!/usr/bin/env python3
"""
P4A pre-build hook that patches Cython's _tempita.py before it gets used.

The cgi module was removed from Python 3.13+ (PEP 594), but Cython 0.29.x
still does 'import cgi' in _tempita.py. This hook patches it to handle
the missing cgi module by using html.escape as a fallback.

P4A calls these functions at specific points:
- prebuild_hook() - before any compilation starts
- before_build() / prebuild_arch() - per-architecture
"""

import os
import sys


def _patch_cython_tempita():
    """Find and patch _tempita.py to handle missing cgi module."""
    try:
        import Cython
        cython_dir = os.path.dirname(Cython.__file__)
        tempita_path = os.path.join(cython_dir, 'Tempita', '_tempita.py')
    except ImportError:
        tempita_path = None
    
    if not tempita_path or not os.path.exists(tempita_path):
        # Search common locations
        candidates = []
        for path in sys.path:
            if path:
                candidates.append(os.path.join(path, 'Cython', 'Tempita', '_tempita.py'))
        
        for c in candidates:
            if os.path.exists(c):
                tempita_path = c
                break
    
    if not tempita_path or not os.path.exists(tempita_path):
        print("[p4a_hook] _tempita.py not found in:", sys.path)
        return False
    
    print(f"[p4a_hook] Patching {tempita_path}")
    
    with open(tempita_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if '# cgi_patched_by_p4a_hook' in content:
        print("[p4a_hook] Already patched")
        return True
    
    # Replace the cgi import with a shim
    # The original is at line ~36: 'import cgi'
    new_content = content.replace(
        'import cgi\n',
        '''# cgi_patched_by_p4a_hook
try:
    import cgi
    import html as _cgi_html
except ImportError:
    # Python 3.13+ removed cgi (PEP 594), provide a shim
    import sys
    import types
    import html as _cgi_html
    cgi = types.ModuleType('cgi')
    cgi.escape = _cgi_html.escape
    cgi.parse_qs = None  # not used by Tempita
    sys.modules['cgi'] = cgi

'''
    )
    
    with open(tempita_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("[p4a_hook] Patched successfully")
    return True


def prebuild_hook(recipe, arch, dist_dir, **kwargs):
    """Called by p4a before any recipe is built."""
    print(f"[p4a_hook] prebuild_hook called for {recipe.name if hasattr(recipe, 'name') else recipe}")
    _patch_cython_tempita()


def before_build(self):
    """Called before build starts."""
    print("[p4a_hook] before_build called")
    _patch_cython_tempita()


# p4a looks for these functions:
# - prebuild_hook(recipe, arch, dist_dir, ...)
# - before_distribute(distribution)

print("[p4a_hook] p4a_hook.py loaded")