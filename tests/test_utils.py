"""Test utilities for document processing tests."""

import json
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List

import psutil


def load_test_data(filename: str) -> Any:
    """Load test data from JSON file."""
    test_data_dir = Path(__file__).parent / "test_data"
    file_path = test_data_dir / filename

    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def create_test_markdown(complexity: str = "simple") -> str:
    """Create test markdown content of varying complexity."""
    if complexity == "simple":
        return """# Title

This is a paragraph.

## Section

Another paragraph."""

    elif complexity == "medium":
        return """---
title: Test Document
author: Test Author
date: 2024-01-01
---

# Main Title

## Introduction

This is the introduction with **bold** and *italic* text.

### Subsection

- List item 1
- List item 2

## Code Section

```python
def test():
    return "Hello"
```

## Conclusion

Final thoughts."""

    elif complexity == "complex":
        return """---
title: Complex Document
author: Multiple Authors
tags: [test, complex, documentation]
version: 1.0.0
---

# Complex Document Structure

## Table of Contents

1. [Introduction](#introduction)
2. [Main Content](#main-content)
3. [Code Examples](#code-examples)
4. [Tables](#tables)
5. [Conclusion](#conclusion)

## Introduction

This document demonstrates complex markdown features.

## Main Content

### Nested Lists

1. First level
   1. Second level
      - Third level with bullet
      - Another bullet
   2. Back to numbered
2. Continue first level

### Blockquotes

> This is a blockquote
>> Nested blockquote
>>> Triple nested

### Links and Images

[External Link](https://example.com)
[Internal Link](#introduction)
![Alt Text](image.png)

## Code Examples

### Python

```python
class DocumentProcessor:
    def __init__(self, config):
        self.config = config
    
    def process(self, document):
        # Process the document
        return self.transform(document)
```

### JavaScript

```javascript
const processDocument = async (doc) => {
    const result = await transform(doc);
    return result;
};
```

## Tables

| Feature | Support | Notes |
|---------|---------|-------|
| Headings | ✅ | All levels |
| Lists | ✅ | Nested |
| Code | ✅ | Syntax highlighting |
| Tables | ✅ | GFM style |

## Conclusion

This demonstrates various markdown features."""

    return ""


def create_test_plaintext(topic: str = "general") -> str:
    """Create test plaintext content for different topics."""
    if topic == "general":
        return """This is a general document about various topics.

The first topic discusses the importance of testing. Testing helps ensure 
software quality and prevents bugs from reaching production.

The second topic covers documentation. Good documentation is essential for 
maintainability and knowledge sharing among team members.

Finally, we conclude that both testing and documentation are critical 
components of professional software development."""

    elif topic == "technical":
        return """Technical Specification Document

1. System Architecture

The system follows a microservices architecture pattern. Each service is 
independently deployable and communicates via REST APIs. The main services 
include authentication, data processing, and reporting.

2. Database Design

We use PostgreSQL for structured data and Redis for caching. The database 
schema is normalized to third normal form. Indexes are created on frequently 
queried columns to optimize performance.

3. API Design

All APIs follow RESTful principles. Endpoints use proper HTTP verbs and 
return appropriate status codes. Authentication is handled via JWT tokens 
with refresh token rotation.

4. Performance Requirements

The system must handle 1000 concurrent users with response times under 
200ms for read operations and under 500ms for write operations."""

    elif topic == "narrative":
        return """The Journey of Software Development

Once upon a time, in a world of ever-evolving technology, developers 
embarked on a quest to create perfect software. They faced many challenges 
along the way.

The first challenge was understanding user requirements. Users spoke in 
their own language, while developers thought in terms of code and logic. 
Bridging this gap required patience and clear communication.

Next came the design phase. Architects drew blueprints, designers crafted 
interfaces, and developers planned the implementation. Each decision had 
far-reaching consequences.

Finally, the coding began. Lines of code transformed ideas into reality. 
Bugs were discovered and fixed. Features were tested and refined. The 
software slowly took shape.

In the end, the developers learned that perfection was not a destination 
but a journey of continuous improvement."""

    return ""


@contextmanager
def timer(name: str = "Operation"):
    """Context manager for timing operations."""
    start_time = time.time()
    yield
    end_time = time.time()
    duration = end_time - start_time
    print(f"{name} took {duration:.3f} seconds")


@contextmanager
def memory_monitor():
    """Context manager for monitoring memory usage."""
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB

    yield

    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_used = final_memory - initial_memory
    print(f"Memory used: {memory_used:.2f} MB")


def generate_large_content(size_mb: int) -> str:
    """Generate large content for performance testing."""
    # Approximate 1MB of text
    base_text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 1000
    base_size = len(base_text.encode("utf-8")) / 1024 / 1024

    repetitions = int(size_mb / base_size)
    return (base_text + "\n\n") * repetitions


def assert_performance(duration: float, max_duration: float, operation: str):
    """Assert that an operation completed within time limit."""
    assert (
        duration <= max_duration
    ), f"{operation} took {duration:.3f}s, exceeding limit of {max_duration}s"


def assert_memory_usage(memory_mb: float, max_memory_mb: float, operation: str):
    """Assert that an operation used acceptable memory."""
    assert (
        memory_mb <= max_memory_mb
    ), f"{operation} used {memory_mb:.2f}MB, exceeding limit of {max_memory_mb}MB"


def create_mock_search_results(query: str, count: int = 5) -> List[Dict[str, Any]]:
    """Create mock search results for testing."""
    results = []
    for i in range(count):
        results.append(
            {
                "id": f"result-{i}",
                "score": 0.9 - (i * 0.1),
                "content": f"Result {i} for query: {query}",
                "metadata": {
                    "source": f"document-{i}.md",
                    "section": f"Section {i}",
                    "line": i * 10,
                },
            }
        )
    return results


def create_malformed_content(error_type: str) -> str:
    """Create malformed content for error testing."""
    if error_type == "invalid_yaml":
        return """---
title: Invalid YAML
invalid_key this has no colon
nested:
  - missing: value
  bad indentation
---

# Content"""

    elif error_type == "incomplete_code":
        return """# Document

```python
def incomplete():
    # This code block is never closed
    return None"""

    elif error_type == "binary_content":
        return "# Document\n\n" + "\x00\x01\x02\x03\x04" + "\n\nBinary content"

    elif error_type == "circular_reference":
        return """# Document

See [Section A](#section-a)

## Section A

See [Section B](#section-b)

## Section B  

See [Section A](#section-a)"""

    return ""
