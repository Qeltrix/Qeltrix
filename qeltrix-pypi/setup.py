#!/usr/bin/env python3
"""
Qeltrix (.qltx) - Content-derived, parallel, streaming obfuscation container (PoC)

Copyright (c) 2025 @hejhdiss(Muhammed Shafin P)
All rights reserved.
Licensed under GPLv3.
"""

import setuptools


setuptools.setup(
    name="qeltrix",
    version="0.0.0a0", 
    description="Content-derived, parallel, streaming obfuscation container",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    
    py_modules=[
        "qeltrix",
        "qeltrix_2",
        "qeltrix_3",
        "qeltrix_4",
        "qeltrix_5",
        "qltx"
    ],
    
    author="Muhammed Shafin P",
    author_email="hejhdiss@gmail.com",
    url="https://github.com/hejhdiss/Qeltrix",
    
    license="GPL-3.0-only", 
    
    install_requires=[
        "lz4>=4.0.0",
        "cryptography>=41.0.0",
        "zstandard"
    ],
    
 
    entry_points={
        'console_scripts': [
            'qltx = qltx:main',
            'qeltrix = qeltrix:main',
            'qeltrix-2 = qeltrix_2:main',
            'qeltrix-3 = qeltrix_3:main',
            'qeltrix-4 = qeltrix_4:main',
            'qeltrix-5 = qeltrix_5:main',
        ],
    },
    python_requires=">=3.8",
    
    include_package_data=True, 
)
