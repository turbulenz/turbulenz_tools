# Copyright (c) 2010-2011,2013 Turbulenz Limited
"""
Utilities.
"""

from glob import glob as standard_glob

def glob(pattern):
    """Slash consistent globbing."""
    return [ f.replace('\\', '/') for f in standard_glob(pattern) ]
