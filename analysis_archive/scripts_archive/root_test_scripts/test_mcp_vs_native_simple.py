#!/usr/bin/env python3
"""Simple test to compare MCP vs native retrieval performance."""

import os
import sys
import time
import json
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.utils.direct_searcher import DirectSearcher
from mcp_server.plugin_system.plugin_manager import PluginManager

def create_test_codebase(base_dir):
    """Create a simple test codebase."""
    repo_path = base_dir / "test_repo"
    repo_path.mkdir(parents=True)
    
    # Create Python files
    (repo_path / "main.py").write_text("""
# Main application entry point
import sys
from utils import Logger, ConfigManager
from api import APIServer

def main():
    '''Main function to start the application.'''
    logger = Logger(__name__)
    config = ConfigManager()
    
    logger.info("Starting application...")
    
    server = APIServer(config)
    server.start()
    
if __name__ == "__main__":
    main()
""")
    
    (repo_path / "utils.py").write_text("""
# Utility classes and functions
import logging
import json
from pathlib import Path

class Logger:
    '''Simple logging wrapper.'''
    def __init__(self, name):
        self.logger = logging.getLogger(name)
        
    def info(self, message):
        self.logger.info(message)
        
    def error(self, message):
        self.logger.error(message)

class ConfigManager:
    '''Manages application configuration.'''
    def __init__(self, config_file="config.json"):
        self.config_file = Path(config_file)
        self.config = self.load_config()
        
    def load_config(self):
        if self.config_file.exists():
            with open(self.config_file) as f:
                return json.load(f)
        return {}
        
    def get(self, key, default=None):
        return self.config.get(key, default)
""")
    
    (repo_path / "api.py").write_text("""
# API server implementation
from flask import Flask, jsonify

class APIServer:
    '''REST API server.'''
    def __init__(self, config):
        self.config = config
        self.app = Flask(__name__)
        self.setup_routes()
        
    def setup_routes(self):
        @self.app.route('/health')
        def health():
            return jsonify({"status": "healthy"})
            
        @self.app.route('/api/v1/data')
        def get_data():
            return jsonify({"data": []})
            
    def start(self):
        port = self.config.get('port', 8080)
        self.app.run(port=port)
""")
    
    # Create JavaScript files
    js_dir = repo_path / "frontend"
    js_dir.mkdir()
    
    (js_dir / "app.js").write_text("""
// Main frontend application
import { Logger } from './utils.js';
import { APIClient } from './api.js';

class Application {
    constructor() {
        this.logger = new Logger('Application');
        this.api = new APIClient();
    }
    
    async initialize() {
        this.logger.log('Initializing application...');
        await this.api.connect();
    }
    
    run() {
        this.initialize().then(() => {
            this.logger.log('Application started');
        });
    }
}

const app = new Application();
app.run();
""")
    
    (js_dir / "utils.js").write_text("""
// Frontend utilities
export class Logger {
    constructor(name) {
        this.name = name;
    }
    
    log(message) {
        console.log(`[${this.name}] ${message}`);
    }
    
    error(message) {
        console.error(`[${this.name}] ${message}`);
    }
}

export function formatDate(date) {
    return date.toISOString().split('T')[0];
}
""")
    
    return repo_path

def test_mcp_search(repo_path, queries):
    """Test searching with MCP dispatcher."""
    print("\n=== Testing MCP Search ===")
    
    # Create index
    index_path = repo_path.parent / "mcp_index.db"
    store = SQLiteStore(str(index_path))
    
    # Create dispatcher with store
    dispatcher = EnhancedDispatcher(sqlite_store=store)
    
    # Index the repository
    print("Indexing repository with MCP...")
    start_time = time.time()
    
    # Get plugin manager from dispatcher
    plugin_manager = dispatcher.plugin_manager
    
    # Index files
    file_count = 0
    for file_path in repo_path.rglob("*"):
        if file_path.is_file() and file_path.suffix in [".py", ".js"]:
            try:
                # Get plugin for file
                plugin = plugin_manager.get_plugin_for_file(str(file_path))
                if plugin:
                    # Parse file
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    result = plugin.parse_file(str(file_path), content)
                    
                    # Store in database
                    if result:
                        for symbol in result.symbols:
                            store.add_symbol(
                                repo_id="test_repo",
                                file_path=str(file_path.relative_to(repo_path)),
                                symbol_name=symbol.name,
                                symbol_type=symbol.type,
                                line_number=symbol.line,
                                column=0,
                                definition=symbol.definition
                            )
                        file_count += 1
            except Exception as e:
                print(f"  Error indexing {file_path}: {e}")
    
    index_time = time.time() - start_time
    print(f"  Indexed {file_count} files in {index_time:.3f}s")
    
    # Test searches
    results = {}
    print("\nPerforming MCP searches:")
    
    for query in queries:
        start = time.time()
        search_results = dispatcher.search_code(query, limit=10)
        search_time = time.time() - start
        
        results[query] = {
            "count": len(search_results),
            "time": search_time,
            "results": search_results[:3]  # Keep first 3 for analysis
        }
        
        print(f"  '{query}': {len(search_results)} results in {search_time:.3f}s")
    
    return results, index_time

def test_native_search(repo_path, queries):
    """Test searching with native grep/ripgrep."""
    print("\n=== Testing Native Search ===")
    
    results = {}
    
    # Test if ripgrep is available
    has_rg = subprocess.run(["which", "rg"], capture_output=True).returncode == 0
    
    print(f"Using: {'ripgrep' if has_rg else 'grep'}")
    
    for query in queries:
        start = time.time()
        
        if has_rg:
            # Use ripgrep
            cmd = ["rg", "-n", "--json", query, str(repo_path)]
        else:
            # Use grep
            cmd = ["grep", "-rn", query, str(repo_path)]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            search_time = time.time() - start
            
            # Count matches
            if has_rg:
                # Parse ripgrep JSON output
                lines = result.stdout.strip().split('\n')
                matches = [l for l in lines if l and json.loads(l).get('type') == 'match']
                count = len(matches)
            else:
                # Count grep lines
                count = len(result.stdout.strip().split('\n')) if result.stdout else 0
            
            results[query] = {
                "count": count,
                "time": search_time
            }
            
            print(f"  '{query}': {count} results in {search_time:.3f}s")
            
        except Exception as e:
            print(f"  '{query}': Error - {e}")
            results[query] = {"count": 0, "time": 0, "error": str(e)}
    
    return results

def main():
    """Run performance comparison."""
    print("MCP vs Native Search Performance Comparison")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        
        # Create test codebase
        print("Creating test codebase...")
        repo_path = create_test_codebase(base_dir)
        
        # Define test queries
        queries = [
            "Logger",           # Class name
            "load_config",      # Method name
            "APIServer",        # Another class
            "initialize",       # Common method name
            "error",           # Common term
            "config.get",      # Method call pattern
        ]
        
        # Test MCP
        mcp_results, index_time = test_mcp_search(repo_path, queries)
        
        # Test native
        native_results = test_native_search(repo_path, queries)
        
        # Compare results
        print("\n=== Performance Comparison ===")
        print(f"MCP Index Time: {index_time:.3f}s")
        print("\nQuery Performance:")
        print(f"{'Query':<20} {'MCP Time':<12} {'Native Time':<12} {'MCP Count':<10} {'Native Count':<10}")
        print("-" * 70)
        
        total_mcp_time = 0
        total_native_time = 0
        
        for query in queries:
            mcp = mcp_results.get(query, {})
            native = native_results.get(query, {})
            
            mcp_time = mcp.get('time', 0)
            native_time = native.get('time', 0)
            
            total_mcp_time += mcp_time
            total_native_time += native_time
            
            print(f"{query:<20} {mcp_time:<12.3f} {native_time:<12.3f} {mcp.get('count', 0):<10} {native.get('count', 0):<10}")
        
        print("-" * 70)
        print(f"{'Total':<20} {total_mcp_time:<12.3f} {total_native_time:<12.3f}")
        
        # Summary
        print(f"\n=== Summary ===")
        print(f"MCP indexing overhead: {index_time:.3f}s")
        print(f"Average MCP query time: {total_mcp_time/len(queries):.3f}s")
        print(f"Average native query time: {total_native_time/len(queries):.3f}s")
        
        speedup = total_native_time / total_mcp_time if total_mcp_time > 0 else 0
        print(f"Native is {speedup:.2f}x faster for queries")
        print(f"Break-even after {index_time / (total_native_time - total_mcp_time):.1f} queries" 
              if total_native_time > total_mcp_time else "MCP is faster!")

if __name__ == "__main__":
    main()