#!/usr/bin/env python3
"""Setup script for miniblockchain package."""

from setuptools import setup, find_packages

setup(
    name="miniblockchain",
    version="0.1.0",
    description="A minimal blockchain implementation with UTXO, Merkle trees, and smart contracts",
    author="Your Name",
    packages=find_packages(),
    install_requires=[
        "flask",
        "ecdsa",
    ],
    python_requires=">=3.7",
    entry_points={
        "console_scripts": [
            "miniblockchain=run:main",
        ],
    },
)
