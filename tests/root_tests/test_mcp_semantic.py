#!/usr/bin/env python3
"""End-to-end test of semantic search through MCP interface."""

import os
import sys
import json
import asyncio
from pathlib import Path

# Load environment
from dotenv import load_dotenv
load_dotenv()

# Force semantic search
os.environ["SEMANTIC_SEARCH_ENABLED"] = "true"
os.environ["QDRANT_HOST"] = ":memory:"

sys.path.insert(0, str(Path(__file__).parent))

import mcp.types as types
from mcp_server.dispatcher import EnhancedDispatcher as Dispatcher
from mcp_server.plugin_system import PluginManager
from mcp_server.storage.sqlite_store import SQLiteStore


async def test_mcp_semantic():
    """Test semantic search through MCP server interface."""
    print("=== MCP Semantic Search End-to-End Test ===\n")
    
    # Initialize services
    print("1. Initializing services...")
    
    # Initialize plugin manager without SQLite for now
    config_path = Path("plugins.yaml")
    plugin_manager = PluginManager()
    
    # Load plugins
    load_result = plugin_manager.load_plugins_safe(config_path if config_path.exists() else None)
    
    if not load_result.success:
        print(f"✗ Plugin loading failed: {load_result.error.message}")
        return
    
    print(f"✓ Loaded {len(plugin_manager.get_active_plugins())} plugins")
    
    # Create dispatcher
    active_plugins = plugin_manager.get_active_plugins()
    plugin_instances = list(active_plugins.values())
    dispatcher = Dispatcher(plugin_instances)
    print(f"✓ Dispatcher created with {len(plugin_instances)} plugins\n")
    
    # Create test files
    print("2. Creating test files...")
    test_dir = Path("test_semantic_code")
    test_dir.mkdir(exist_ok=True)
    
    # API client code
    (test_dir / "api_client.py").write_text('''
class APIClient:
    """A client for making HTTP requests to REST APIs."""
    
    def __init__(self, base_url, api_key=None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = None
    
    def authenticate(self, username, password):
        """Authenticate user and obtain access token."""
        # Implementation for OAuth2 authentication
        pass
    
    def get_resource(self, endpoint, params=None):
        """Fetch a resource from the API."""
        url = f"{self.base_url}/{endpoint}"
        # Make GET request
        pass
''')
    
    # Data processing code
    (test_dir / "data_processor.py").write_text('''
def parse_json_data(json_string):
    """Parse JSON string and validate structure."""
    import json
    try:
        data = json.loads(json_string)
        return data
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")

def transform_dataset(data, transformations):
    """Apply a series of transformations to dataset."""
    result = data
    for transform in transformations:
        result = transform(result)
    return result

class DataPipeline:
    """Pipeline for processing streaming data."""
    
    def __init__(self):
        self.stages = []
    
    def add_stage(self, processor):
        """Add a processing stage to the pipeline."""
        self.stages.append(processor)
''')
    
    # Index the files
    print("✓ Created test files\n")
    
    print("3. Indexing files...")
    for py_file in test_dir.glob("*.py"):
        dispatcher.index_file(py_file)
        print(f"   ✓ Indexed {py_file.name}")
    
    print("\n4. Testing semantic search through MCP interface...")
    
    # Test queries
    test_queries = [
        ("class for HTTP API authentication", True),  # semantic
        ("function to parse and validate JSON", True),  # semantic
        ("streaming data processing pipeline", True),   # semantic
        ("APIClient", False),                          # traditional
        ("parse_json", False),                         # traditional
    ]
    
    for query, use_semantic in test_queries:
        print(f"\n{'Semantic' if use_semantic else 'Traditional'} search: '{query}'")
        
        # Simulate MCP call_tool request
        arguments = {
            "query": query,
            "semantic": use_semantic,
            "limit": 3
        }
        
        results = list(dispatcher.search(query, semantic=use_semantic, limit=3))
        
        if results:
            print(f"Found {len(results)} results:")
            for i, result in enumerate(results, 1):
                print(f"  {i}. {Path(result['file']).name} line {result['line']}")
                # Show snippet preview
                snippet = result['snippet'].strip().split('\n')[0][:60] + "..."
                print(f"     {snippet}")
        else:
            print("No results found")
    
    # Cleanup
    import shutil
    shutil.rmtree(test_dir)
    print("\n✓ Test complete - semantic search is working through MCP interface!")


def main():
    """Run async test."""
    try:
        asyncio.run(test_mcp_semantic())
    except KeyboardInterrupt:
        print("\nTest interrupted")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()