#!/usr/bin/env python3
"""
Simple runner to execute the reranking metadata preservation tests
"""

import subprocess
import sys


def run_tests():
    """Run the reranking metadata preservation tests"""
    print("Running reranking metadata preservation tests...")
    print("-" * 60)

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/test_reranking_metadata_preservation.py",
        "-v",  # Verbose output
        "-s",  # Show print statements
        "--tb=short",  # Short traceback format
    ]

    result = subprocess.run(cmd, capture_output=False)

    print("-" * 60)
    if result.returncode == 0:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed.")

    return result.returncode


if __name__ == "__main__":
    sys.exit(run_tests())
