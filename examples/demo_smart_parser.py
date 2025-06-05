#!/usr/bin/env python3
"""Demonstration of the SmartParser system with the Python plugin."""

import sys
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.plugins.python_plugin.plugin import Plugin
from mcp_server.core.logging import setup_logging

# Sample Python code to parse
SAMPLE_CODE = '''
"""A sample Python module for testing SmartParser."""

class Calculator:
    """A simple calculator class."""
    
    def __init__(self):
        self.result = 0
    
    def add(self, a: float, b: float) -> float:
        """Add two numbers."""
        return a + b
    
    def subtract(self, a: float, b: float) -> float:
        """Subtract b from a."""
        return a - b

async def fetch_data(url: str) -> dict:
    """Fetch data from a URL asynchronously."""
    # Placeholder implementation
    return {"url": url, "status": "ok"}

def main():
    """Main entry point."""
    calc = Calculator()
    print(f"2 + 3 = {calc.add(2, 3)}")
    print(f"5 - 2 = {calc.subtract(5, 2)}")

if __name__ == "__main__":
    main()
'''

def main():
    """Demonstrate SmartParser functionality."""
    # Set up logging
    setup_logging(log_level="DEBUG")
    logger = logging.getLogger(__name__)
    
    print("=== SmartParser Demonstration ===\n")
    
    # Initialize the Python plugin
    plugin = Plugin()
    
    # Get parser information
    parser_info = plugin.get_parser_info()
    print(f"Current parser backend: {parser_info['current_backend']}")
    print(f"Available backends: {parser_info['available_backends']}")
    print()
    
    # Parse with the default backend
    print(f"Parsing sample code with {parser_info['current_backend']} backend...")
    result = plugin.indexFile("sample.py", SAMPLE_CODE)
    
    print(f"\nFound {len(result['symbols'])} symbols:")
    for symbol in result['symbols']:
        print(f"  - {symbol['kind']}: {symbol['symbol']} at line {symbol['line']}")
        print(f"    Signature: {symbol['signature']}")
        print(f"    Span: lines {symbol['span'][0]}-{symbol['span'][1]}")
    
    # Try switching backends if available
    if len(parser_info['available_backends']) > 1:
        other_backend = [b for b in parser_info['available_backends'] 
                        if b != parser_info['current_backend']][0]
        
        print(f"\n\nSwitching to {other_backend} backend...")
        if plugin.switch_parser_backend(other_backend):
            print(f"Successfully switched to {other_backend}")
            
            # Parse again with the new backend
            print(f"\nParsing with {other_backend} backend...")
            result2 = plugin.indexFile("sample.py", SAMPLE_CODE)
            
            print(f"\nFound {len(result2['symbols'])} symbols:")
            for symbol in result2['symbols']:
                print(f"  - {symbol['kind']}: {symbol['symbol']} at line {symbol['line']}")
                print(f"    Signature: {symbol['signature']}")
                print(f"    Span: lines {symbol['span'][0]}-{symbol['span'][1]}")
            
            # Compare results
            if len(result['symbols']) == len(result2['symbols']):
                print(f"\n✓ Both backends found the same number of symbols!")
            else:
                print(f"\n⚠ Different symbol counts: {len(result['symbols'])} vs {len(result2['symbols'])}")
    
    print("\n=== Demonstration Complete ===")

if __name__ == "__main__":
    main()