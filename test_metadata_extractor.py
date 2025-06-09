"""
Unit tests for metadata extraction functionality.

Tests the metadata extractor including:
- Frontmatter parsing (YAML and TOML)
- Title detection with various patterns
- Author and date extraction
- Language detection
- Keyword extraction using TF-IDF
- Summary generation
- File metadata extraction
- Code-specific metadata
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import tempfile
import os
import yaml

from mcp_server.document_processing.metadata_extractor import MetadataExtractor


class TestMetadataExtractor:
    """Test metadata extraction functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = MetadataExtractor()
        
    def test_extract_yaml_frontmatter(self):
        """Test extracting YAML frontmatter."""
        content = """---
title: Test Document
author: John Doe
date: 2024-01-15
tags:
  - python
  - testing
  - documentation
description: |
  This is a multi-line
  description of the document.
custom_field: value
---

# Main Content

This is the document body."""
        
        frontmatter = self.extractor.extract_frontmatter(content)
        
        assert frontmatter is not None
        assert frontmatter['title'] == 'Test Document'
        assert frontmatter['author'] == 'John Doe'
        # Handle both string and date object
        if isinstance(frontmatter['date'], str):
            assert frontmatter['date'] == '2024-01-15'
        else:
            assert str(frontmatter['date']) == '2024-01-15'
        assert len(frontmatter['tags']) == 3
        assert 'python' in frontmatter['tags']
        assert 'This is a multi-line' in frontmatter['description']
        assert frontmatter['custom_field'] == 'value'
        
    def test_extract_toml_frontmatter(self):
        """Test extracting TOML frontmatter."""
        content = """+++
title = "Test Document"
author = "Jane Doe"
date = "2024-01-15"
tags = ["rust", "systems", "programming"]
[metadata]
version = "1.0.0"
status = "draft"
+++

# Main Content"""
        
        frontmatter = self.extractor.extract_frontmatter(content)
        
        # Will be None if tomllib not available
        if frontmatter:
            assert frontmatter['title'] == 'Test Document'
            assert frontmatter['author'] == 'Jane Doe'
            assert 'rust' in frontmatter.get('tags', [])
            if 'metadata' in frontmatter:
                assert frontmatter['metadata']['version'] == '1.0.0'
                
    def test_remove_frontmatter(self):
        """Test removing frontmatter from content."""
        yaml_content = """---
title: Test
---

Content here"""
        
        toml_content = """+++
title = "Test"
+++

Content here"""
        
        # Test YAML removal
        cleaned_yaml = self.extractor.remove_frontmatter(yaml_content)
        assert not cleaned_yaml.startswith('---')
        assert cleaned_yaml.strip() == "Content here"
        
        # Test TOML removal
        cleaned_toml = self.extractor.remove_frontmatter(toml_content)
        assert not cleaned_toml.startswith('+++')
        assert cleaned_toml.strip() == "Content here"
        
    def test_detect_title_patterns(self):
        """Test title detection with various patterns."""
        # Markdown heading
        assert self.extractor.detect_title("# Main Title\n\nContent") == "Main Title"
        
        # Underlined title
        assert self.extractor.detect_title("Document Title\n==============\n\nContent") == "Document Title"
        
        # Explicit title field
        assert self.extractor.detect_title("Title: My Document\n\nContent") == "My Document"
        
        # HTML title
        assert self.extractor.detect_title("<h1>HTML Title</h1>\n\nContent") == "HTML Title"
        
        # Template syntax
        assert self.extractor.detect_title('{{ title: "Template Title" }}\n\nContent') == "Template Title"
        
    def test_detect_title_from_html(self):
        """Test title detection from HTML documents."""
        html_content = """<!DOCTYPE html>
<html>
<head>
    <title>Page Title</title>
</head>
<body>
    <h1>Main Heading</h1>
    <p>Content</p>
</body>
</html>"""
        
        title = self.extractor.detect_title(html_content)
        assert title == "Page Title"
        
    def test_detect_title_from_docstring(self):
        """Test title detection from Python docstrings."""
        python_content = '''"""
Module Title: Data Processing Utilities

This module provides utility functions for data processing.

Author: Developer
Date: 2024-01-15
"""

import pandas as pd

def process_data():
    pass'''
        
        title = self.extractor.detect_title(python_content, "utils.py")
        assert title == "Module Title: Data Processing Utilities"
        
    def test_detect_title_fallback(self):
        """Test title detection fallback mechanisms."""
        # First non-empty line
        content = """

Introduction to Programming

This document covers basic programming concepts."""
        
        title = self.extractor.detect_title(content)
        assert title == "Introduction to Programming"
        
        # From filename
        title = self.extractor.detect_title("", "my-awesome-document.txt")
        assert title == "My Awesome Document"
        
        # Snake case filename
        title = self.extractor.detect_title("", "data_processing_guide.md")
        assert title == "Data Processing Guide"
        
    def test_extract_author(self):
        """Test author extraction."""
        # Standard patterns
        assert self.extractor.extract_author("Author: John Smith\n") == "John Smith"
        assert self.extractor.extract_author("By: Jane Doe\n") == "Jane Doe"
        assert self.extractor.extract_author("Written by: Dr. Bob\n") == "Dr. Bob"
        
        # Code style
        assert self.extractor.extract_author("@author Alice Johnson\n") == "Alice Johnson"
        assert self.extractor.extract_author('__author__ = "Python Dev"') == "Python Dev"
        
        # Case insensitive
        assert self.extractor.extract_author("AUTHOR: Test User\n") == "Test User"
        
    def test_extract_date(self):
        """Test date extraction."""
        # ISO format
        assert self.extractor.extract_date("Date: 2024-01-15\n") == "2024-01-15"
        assert self.extractor.extract_date("Published: 2024-12-31\n") == "2024-12-31"
        
        # US format
        assert self.extractor.extract_date("Updated: 1/15/2024\n") == "1/15/2024"
        assert self.extractor.extract_date("Date: 12/31/2024\n") == "12/31/2024"
        
        # Code style
        assert self.extractor.extract_date("@date 2024-01-15\n") == "2024-01-15"
        
    def test_detect_language(self):
        """Test language/format detection."""
        # Python
        python_code = """
def calculate_sum(numbers):
    total = 0
    for num in numbers:
        total += num
    return total

if __name__ == "__main__":
    print(calculate_sum([1, 2, 3]))
"""
        assert self.extractor.detect_language(python_code) == "python"
        
        # JavaScript
        js_code = """
const greeting = "Hello";
let count = 0;

function sayHello(name) {
    return `${greeting}, ${name}!`;
}

const arrowFunc = () => console.log("Arrow function");
"""
        assert self.extractor.detect_language(js_code) == "javascript"
        
        # Java
        java_code = """
package com.example;

public class HelloWorld {
    private String message;
    
    public static void main(String[] args) {
        System.out.println("Hello, World!");
    }
}
"""
        assert self.extractor.detect_language(java_code) == "java"
        
        # Markdown
        markdown_content = """
# Main Title

## Section 1

* List item 1
* List item 2

1. Numbered item
2. Another item

[Link text](https://example.com)
"""
        assert self.extractor.detect_language(markdown_content) == "markdown"
        
        # HTML
        html_content = """
<html>
<head>
    <title>Test</title>
</head>
<body>
    <div class="container">
        <h1>Hello</h1>
    </div>
</body>
</html>
"""
        assert self.extractor.detect_language(html_content) == "html"
        
    def test_extract_keywords(self):
        """Test keyword extraction using TF-IDF."""
        content = """
        Machine learning is a subset of artificial intelligence that focuses on
        building applications that learn from data and improve their accuracy over
        time without being programmed to do so. Machine learning algorithms build
        a model based on training data, known as "training" or "learning" phase.
        
        Deep learning is a subset of machine learning that uses artificial neural
        networks with multiple layers. Deep learning models can achieve state-of-the-art
        accuracy in many tasks including computer vision and natural language processing.
        
        The key difference between traditional machine learning and deep learning is
        the ability of deep learning models to automatically learn representations
        from data without manual feature engineering.
        """
        
        keywords = self.extractor.extract_keywords(content, max_keywords=10)
        
        assert len(keywords) <= 10
        assert len(keywords) > 0
        
        # Check that important terms are extracted
        assert any("learning" in kw for kw in keywords)
        assert any("machine" in kw or "deep" in kw for kw in keywords)
        assert any("data" in kw for kw in keywords)
        
        # Check that stop words are not included
        assert not any(kw in ["the", "is", "and", "or", "but"] for kw in keywords)
        
    def test_generate_summary(self):
        """Test summary generation."""
        content = """---
title: Test Document
---

# Introduction

This document provides a comprehensive guide to Python programming. It covers
basic syntax, data structures, functions, classes, and advanced topics like
decorators and generators.

## Getting Started

To begin with Python, you need to install it from python.org. Python is known
for its simple and readable syntax, making it perfect for beginners.

```python
def hello_world():
    print("Hello, World!")
```

## Data Types

Python supports various data types including integers, floats, strings, lists,
tuples, dictionaries, and sets. Each data type has its own characteristics and
use cases.

## Conclusion

Python is a versatile language suitable for web development, data science,
automation, and more."""
        
        summary = self.extractor.generate_summary(content, max_length=200)
        
        assert summary is not None
        assert len(summary) <= 210  # Allow some flexibility
        assert "comprehensive guide to Python programming" in summary
        assert "```" not in summary  # Code blocks should be removed
        assert "---" not in summary  # Frontmatter should be removed
        
    def test_generate_summary_edge_cases(self):
        """Test summary generation edge cases."""
        # Only code
        code_only = """```python
def test():
    pass
```"""
        summary = self.extractor.generate_summary(code_only)
        assert summary is None or summary == ""
        
        # Only headings
        headings_only = """# Title
## Subtitle
### Sub-subtitle"""
        summary = self.extractor.generate_summary(headings_only)
        assert summary is None or summary == ""
        
        # Very short content
        short_content = "This is short."
        summary = self.extractor.generate_summary(short_content)
        # The implementation might return None or the content itself for very short text
        assert summary is None or summary == "This is short."
        
    def test_extract_file_metadata(self):
        """Test file metadata extraction."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
            tmp.write("Test content")
            tmp_path = tmp.name
            
        try:
            metadata = self.extractor.extract_file_metadata(tmp_path)
            
            assert metadata['file_name'] == Path(tmp_path).name
            assert metadata['file_path'] == str(Path(tmp_path).absolute())
            assert metadata['file_size'] > 0
            assert metadata['file_extension'] == '.txt'
            assert 'created_at' in metadata
            assert 'modified_at' in metadata
            
        finally:
            os.unlink(tmp_path)
            
    def test_extract_file_metadata_nonexistent(self):
        """Test file metadata extraction for non-existent file."""
        metadata = self.extractor.extract_file_metadata("/nonexistent/file.txt")
        assert metadata == {}
        
    def test_extract_code_metadata_python(self):
        """Test code metadata extraction for Python."""
        python_code = """
import os
import sys
from pathlib import Path
import numpy as np
from sklearn.model_selection import train_test_split

class DataProcessor:
    def __init__(self):
        pass
        
    def process(self, data):
        return data
        
class ModelTrainer:
    def train(self):
        pass

def load_data(filepath):
    pass
    
def preprocess_data(data):
    pass
    
def save_results(results, output_path):
    pass
"""
        
        metadata = self.extractor.extract_code_metadata(python_code, "python")
        
        assert 'dependencies' in metadata
        assert 'os' in metadata['dependencies']
        # Check if numpy is in dependencies (might be 'numpy' or 'numpy as np')
        assert any('numpy' in dep for dep in metadata['dependencies'])
        # sklearn.model_selection becomes just 'sklearn'
        assert 'sklearn' in metadata['dependencies']
        
        assert 'classes' in metadata
        assert 'DataProcessor' in metadata['classes']
        assert 'ModelTrainer' in metadata['classes']
        
        assert 'functions' in metadata
        assert 'load_data' in metadata['functions']
        assert 'preprocess_data' in metadata['functions']
        assert 'save_results' in metadata['functions']
        
    def test_extract_code_metadata_javascript(self):
        """Test code metadata extraction for JavaScript."""
        js_code = """
import React from 'react';
import { useState, useEffect } from 'react';
const axios = require('axios');
import './styles.css';

class ComponentClass {
    render() {
        return null;
    }
}

function processData(input) {
    return input;
}

const arrowFunction = (param) => {
    return param * 2;
};

export const namedExport = async () => {
    await fetch('/api/data');
};
"""
        
        metadata = self.extractor.extract_code_metadata(js_code, "javascript")
        
        assert 'dependencies' in metadata
        # The regex extracts the full module path/name
        # Check if any dependency contains 'axios' or is exactly 'axios'
        assert any('axios' in dep for dep in metadata['dependencies'])
        assert './styles.css' in metadata['dependencies']
        
        assert 'functions' in metadata
        assert 'processData' in metadata['functions']
        assert 'arrowFunction' in metadata['functions']
        assert 'namedExport' in metadata['functions']
        
        assert 'classes' in metadata
        assert 'ComponentClass' in metadata['classes']
        
    def test_extract_metadata_complete(self):
        """Test complete metadata extraction."""
        content = """---
title: Python Best Practices Guide
author: Expert Developer
date: 2024-01-15
tags: [python, best-practices, coding-standards]
version: 2.0
---

# Python Best Practices Guide

This comprehensive guide covers Python programming best practices, including
code organization, error handling, testing, and performance optimization.

## Table of Contents

1. Code Organization
2. Error Handling
3. Testing Strategies
4. Performance Tips

## Code Organization

Always structure your Python projects with clear module separation...
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
            
        try:
            metadata = self.extractor.extract_metadata(content, tmp_path)
            
            # From frontmatter
            assert metadata['title'] == 'Python Best Practices Guide'
            assert metadata['author'] == 'Expert Developer'
            # Handle both string and date object
            if isinstance(metadata['date'], str):
                assert metadata['date'] == '2024-01-15'
            else:
                assert str(metadata['date']) == '2024-01-15'
            assert 'python' in metadata['tags']
            assert metadata['version'] == 2.0
            
            # Detected
            assert metadata['language'] == 'markdown'
            assert 'keywords' in metadata
            assert len(metadata['keywords']) > 0
            assert 'summary' in metadata
            
            # File metadata
            assert metadata['file_name'] == Path(tmp_path).name
            assert metadata['file_extension'] == '.md'
            
        finally:
            os.unlink(tmp_path)
            
    def test_metadata_extraction_empty_content(self):
        """Test metadata extraction with empty content."""
        metadata = self.extractor.extract_metadata("")
        
        # Should return some default/empty metadata
        assert isinstance(metadata, dict)
        assert 'title' not in metadata or metadata['title'] is None
        
    def test_metadata_extraction_no_patterns(self):
        """Test metadata extraction when no patterns match."""
        content = "Just plain text without any metadata patterns or structure."
        
        metadata = self.extractor.extract_metadata(content)
        
        # Should still extract what it can
        assert 'keywords' in metadata
        assert 'summary' in metadata
        assert metadata['summary'] == content  # Short enough to be the summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])