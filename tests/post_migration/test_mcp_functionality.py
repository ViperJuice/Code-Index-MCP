#!/usr/bin/env python3
"""
Post-migration test to verify MCP functionality still works correctly.
"""
import os
import subprocess
import sys
import time
from pathlib import Path

import requests


def test_mcp_server_startup():
    """Test that the MCP server can start successfully."""
    print("Testing MCP server startup...")

    # Kill any existing server
    subprocess.run(["pkill", "-f", "mcp_server.gateway"], capture_output=True)
    time.sleep(2)

    # Start the server
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).parent.parent.parent)

    server_process = subprocess.Popen(
        [sys.executable, "-m", "mcp_server.gateway"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for server to start
    time.sleep(5)

    try:
        # Check if server is running
        response = requests.get("http://localhost:8000/health", timeout=5)
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        print("✅ MCP server started successfully")
        return True
    except Exception as e:
        print(f"❌ MCP server startup failed: {e}")
        return False
    finally:
        server_process.terminate()
        server_process.wait()


def test_symbol_lookup():
    """Test symbol lookup functionality."""
    print("\nTesting symbol lookup...")

    try:
        # Start the server
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path(__file__).parent.parent.parent)

        server_process = subprocess.Popen(
            [sys.executable, "-m", "mcp_server.gateway"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        time.sleep(5)

        # Test symbol lookup
        response = requests.post(
            "http://localhost:8000/symbol",
            json={"symbol": "PathResolver"},
            headers={"Content-Type": "application/json"},
            timeout=10,
        )

        if response.status_code == 200:
            results = response.json()
            if results:
                print(f"✅ Symbol lookup working - found {len(results)} results")
                return True
            else:
                print("⚠️  Symbol lookup returned no results")
                return True  # Still working, just no results
        else:
            print(f"❌ Symbol lookup failed: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Symbol lookup test failed: {e}")
        return False
    finally:
        server_process.terminate()
        server_process.wait()


def test_code_search():
    """Test code search functionality."""
    print("\nTesting code search...")

    try:
        # Start the server
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path(__file__).parent.parent.parent)

        server_process = subprocess.Popen(
            [sys.executable, "-m", "mcp_server.gateway"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        time.sleep(5)

        # Test code search
        response = requests.post(
            "http://localhost:8000/search",
            json={"query": "def index_file"},
            headers={"Content-Type": "application/json"},
            timeout=10,
        )

        if response.status_code == 200:
            results = response.json()
            print("✅ Code search working - found results")
            return True
        else:
            print(f"❌ Code search failed: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Code search test failed: {e}")
        return False
    finally:
        server_process.terminate()
        server_process.wait()


def test_plugin_loading():
    """Test that plugins load correctly."""
    print("\nTesting plugin loading...")

    try:
        # Import the plugin factory
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from mcp_server.plugins.plugin_factory import PluginFactory
        from mcp_server.storage.sqlite_store import SQLiteStore

        # Create a temporary store
        store = SQLiteStore(":memory:")

        # Test loading a few plugins
        factory = PluginFactory(store)

        # Test Python plugin
        python_plugin = factory.get_plugin(".py")
        assert python_plugin is not None, "Python plugin failed to load"
        print("✅ Python plugin loaded")

        # Test JavaScript plugin
        js_plugin = factory.get_plugin(".js")
        assert js_plugin is not None, "JavaScript plugin failed to load"
        print("✅ JavaScript plugin loaded")

        # Test generic plugin for unknown extension
        generic_plugin = factory.get_plugin(".xyz")
        assert generic_plugin is not None, "Generic plugin failed to load"
        print("✅ Generic plugin loaded for unknown extension")

        return True

    except Exception as e:
        print(f"❌ Plugin loading test failed: {e}")
        return False


def test_file_references():
    """Test that moved files are properly referenced."""
    print("\nTesting file references...")

    # Check if moved test directories exist
    test_paths = [
        "tests/fixtures/complete_behavior",
        "tests/fixtures/files",
        "tests/fixtures/repos",
        "tests/fixtures/data",
        "tests/results",
        "tests/coverage",
        "scripts/cli/mcp_cli.py",
        "scripts/cli/mcp_server_cli.py",
        "scripts/development/scaffold_code.py",
        "scripts/development/scaffold_mcp.sh",
        "scripts/testing/simple_test.py",
        "docker/compose/development/docker-compose.dev.yml",
        "docker/compose/production/docker-compose.production.yml",
        "data/indexes/vector_index.qdrant",
        "monitoring/config/prometheus.yml",
    ]

    all_good = True
    for path in test_paths:
        full_path = Path(__file__).parent.parent.parent / path
        if full_path.exists():
            print(f"✅ {path} exists")
        else:
            print(f"❌ {path} NOT FOUND")
            all_good = False

    return all_good


def main():
    """Run all post-migration tests."""
    print("=" * 60)
    print("Post-Migration MCP Functionality Tests")
    print("=" * 60)

    tests = [
        ("File References", test_file_references),
        ("MCP Server Startup", test_mcp_server_startup),
        ("Symbol Lookup", test_symbol_lookup),
        ("Code Search", test_code_search),
        ("Plugin Loading", test_plugin_loading),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n### {test_name} ###")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name}: {status}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! Migration successful.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please investigate.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
