"""
Setup configuration for GrepNet.

Modern Python projects use pyproject.toml instead.
This file is provided for compatibility with older build tools.
"""

from setuptools import setup, find_packages

setup(
    name='grepnet',
    version='5.0.0',
    description='Network-aware grep for CIDR blocks and IP ranges',
    long_description=open('README.md').read() if open('README.md', 'r').read() else '',
    long_description_content_type='text/markdown',
    author='GrepNet Contributors',
    license='GPL-3.0-or-later',
    python_requires='>=3.9',
    package_dir={'': 'src'},
    packages=find_packages('src'),
    entry_points={
        'console_scripts': [
            'grepnet=grepnet.cli:run',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: System Administrators',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Natural Language :: English',
        'Operating System :: POSIX',
        'Operating System :: MacOS',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Topic :: System :: Networking',
        'Topic :: System :: Systems Administration',
        'Topic :: Utilities',
    ],
    keywords='cidr grep ip network ipv6 ipv4',
)
