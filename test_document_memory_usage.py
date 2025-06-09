#!/usr/bin/env python3
"""Redirect to tests/performance/test_document_memory_usage.py"""

import sys
from pathlib import Path

# Add tests directory to path
tests_dir = Path(__file__).parent / "tests"
sys.path.insert(0, str(tests_dir))

# Import and run the actual test
from performance.test_document_memory_usage import *

if __name__ == "__main__":
    import pytest
    pytest.main([str(tests_dir / "performance" / "test_document_memory_usage.py"), "-v", "-m", "performance"])