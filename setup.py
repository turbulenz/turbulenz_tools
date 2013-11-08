#!/usr/bin/env python
# Copyright (c) 2013 Turbulenz Limited

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

from turbulenz_tools import __version__

import platform
import sys
from glob import iglob

if 'sdist' in sys.argv:
    SCRIPTS = list(iglob('scripts/*'))
elif platform.system() == 'Windows':
    SCRIPTS = list(iglob('scripts/*.bat'))
else:
    SCRIPTS = [ s for s in iglob('scripts/*') if not s.endswith('.bat') ]

setup(name='turbulenz_tools',
    version=__version__,
    description='Tools for the creation of games with the Turbulenz Engine',
    author='Turbulenz Limited',
    author_email='support@turbulenz.com',
    url='https://turbulenz.com/',
    install_requires=[
        'simplejson>=2.1.5',
        'jinja2>=2.4',
        'PyYAML>=3.09',
        'jsmin>=2.0.2',
        'urllib3>=1.7.1'
        ],
    scripts=SCRIPTS,
    packages=[ 'turbulenz_tools', 'turbulenz_tools.tools', 'turbulenz_tools.utils' ],
    include_package_data=True,
    package_data={},
    zip_safe=False,
    license = 'MIT',
    platforms = 'Posix; MacOS X; Windows',
    classifiers = ['Development Status :: 5 - Production/Stable',
                   'Intended Audience :: Developers',
                   'License :: OSI Approved :: MIT License',
                   'Operating System :: OS Independent',
                   'Topic :: Software Development',
                   'Programming Language :: Python :: 2.7'],
    )
