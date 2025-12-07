#!/usr/bin/env python3
"""Test MCP server integration with enhanced dispatcher."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

import mcp_server_cli


async def test_mcp_integration():
    """Test the MCP server with enhanced dispatcher."""
    print("=== Testing MCP Server Integration ===\n")

    # Initialize services
    print("Initializing MCP services...")
    await mcp_server_cli.initialize_services()

    if mcp_server_cli.dispatcher is None:
        print("❌ Dispatcher failed to initialize")
        return False

    dispatcher = mcp_server_cli.dispatcher
    print(f"✓ Dispatcher initialized: {dispatcher.__class__.__name__}")

    # Get status
    print("\n--- Testing Status ---")
    stats = dispatcher.get_statistics()
    health = dispatcher.health_check()

    print(f"Dispatcher type: {dispatcher.__class__.__name__}")
    print(f"Supported languages: {stats.get('supported_languages', 0)}")
    print(f"Initially loaded plugins: {stats.get('total_plugins', 0)}")
    print(f"Health status: {health.get('status', 'unknown')}")

    # List supported languages
    languages = dispatcher.supported_languages
    print(f"\nSupported languages ({len(languages)}):")
    for i in range(0, len(languages), 10):
        batch = languages[i : i + 10]
        print(f"  {', '.join(batch)}")

    # Test indexing a Go file
    print("\n--- Testing File Indexing ---")

    # Create a test Go file
    test_file = Path("test_sample.go")
    test_file.write_text(
        """package main

import "fmt"

func fibonacci(n int) int {
    if n <= 1 {
        return n
    }
    return fibonacci(n-1) + fibonacci(n-2)
}

func main() {
    for i := 0; i < 10; i++ {
        fmt.Printf("F(%d) = %d\\n", i, fibonacci(i))
    }
}
"""
    )

    try:
        # Index the file
        print(f"Indexing {test_file}...")
        dispatcher.index_file(test_file)
        print("✓ File indexed successfully")

        # Check if Go plugin was loaded
        loaded_langs = (
            dispatcher._loaded_languages if hasattr(dispatcher, "_loaded_languages") else set()
        )
        if "go" in loaded_langs:
            print("✓ Go plugin was dynamically loaded")

        # Search for the function
        print("\nSearching for 'fibonacci'...")
        results = list(dispatcher.search("fibonacci", limit=5))
        print(f"Found {len(results)} results:")
        for result in results[:3]:
            print(
                f"  - {result.get('file', 'N/A')}:{result.get('line', 'N/A')} - {result.get('snippet', 'N/A').strip()}"
            )

        # Look up symbol
        print("\nLooking up symbol 'fibonacci'...")
        definition = dispatcher.lookup("fibonacci")
        if definition:
            print("✓ Found definition:")
            print(f"  - Kind: {definition.get('kind', 'N/A')}")
            print(f"  - File: {definition.get('defined_in', 'N/A')}")
            print(f"  - Line: {definition.get('line', 'N/A')}")
        else:
            print("✗ Symbol not found")

        # Final statistics
        print("\n--- Final Statistics ---")
        final_stats = dispatcher.get_statistics()
        print(f"Total plugins loaded: {final_stats.get('total_plugins', 0)}")
        print(f"Languages loaded: {', '.join(sorted(final_stats.get('loaded_languages', [])))}")
        print("Operations performed:")
        for op, count in final_stats.get("operations", {}).items():
            if count > 0:
                print(f"  - {op}: {count}")

        return True

    finally:
        # Cleanup
        test_file.unlink(missing_ok=True)


async def main():
    """Run the test."""
    success = await test_mcp_integration()
    if success:
        print("\n✅ MCP integration test passed!")
    else:
        print("\n❌ MCP integration test failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
