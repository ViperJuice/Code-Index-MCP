"""Setup script for mcp-index-kit Python package."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="mcp-index-kit",
    version="1.0.0",
    author="MCP Team",
    description="Portable index management for repositories using MCP Code Indexer",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/mcp-index-kit",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "click>=8.0",
        "requests>=2.28.0",
    ],
    entry_points={
        "console_scripts": [
            "mcp-index=scripts.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["templates/*", ".github/workflows/*"],
    },
)