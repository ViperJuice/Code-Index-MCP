#!/usr/bin/env python3
"""
Patch MCP server to use BM25 direct dispatcher.
This creates a patched version of mcp_server_cli.py that uses BM25 search directly.
"""

import shutil
from pathlib import Path
from mcp_server.core.path_utils import PathUtils


def create_patched_server():
    """Create a patched version of the MCP server that uses BM25 direct search."""
    
    # Read the original server file
    original_file = Path("PathUtils.get_workspace_root()/scripts/cli/mcp_server_cli.py")
    patched_file = Path("PathUtils.get_workspace_root()/scripts/cli/mcp_server_cli_patched.py")
    
    content = original_file.read_text()
    
    # Add BM25DirectDispatcher import
    import_section = """from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.plugin_system import PluginManager
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.utils.index_discovery import IndexDiscovery"""
    
    patched_import = """from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.plugin_system import PluginManager
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.utils.index_discovery import IndexDiscovery

# Import BM25 direct dispatcher
sys.path.insert(0, "PathUtils.get_workspace_root()/scripts")
from fix_mcp_bm25_integration import BM25DirectDispatcher"""
    
    content = content.replace(import_section, patched_import)
    
    # Replace dispatcher initialization
    dispatcher_init = """        # Create enhanced dispatcher with dynamic plugin loading
        logger.info("Creating enhanced dispatcher with dynamic plugin loading...")
        dispatcher = EnhancedDispatcher(
            plugins=plugin_instances,  # Use existing plugins as base
            sqlite_store=sqlite_store,
            enable_advanced_features=True,
            use_plugin_factory=True,  # Enable dynamic loading
            lazy_load=True,  # Load plugins on demand
            semantic_search_enabled=True
        )
        
        supported_languages = dispatcher.supported_languages
        logger.info(f"Enhanced dispatcher created - supports {len(supported_languages)} languages")
        logger.info(f"Languages: {', '.join(supported_languages[:10])}{'...' if len(supported_languages) > 10 else ''}")"""
    
    patched_dispatcher = """        # Use BM25 direct dispatcher instead
        logger.info("Creating BM25 direct dispatcher...")
        dispatcher = BM25DirectDispatcher()
        
        # Check if index exists
        health = dispatcher.health_check()
        if health['status'] != 'operational':
            logger.error(f"BM25 dispatcher not operational: {health}")
            raise RuntimeError("No valid BM25 index found")
        
        logger.info(f"BM25 dispatcher initialized with index: {health['index']}")
        logger.info(f"Supports all languages via BM25 full-text search")"""
    
    content = content.replace(dispatcher_init, patched_dispatcher)
    
    # Write patched file
    patched_file.write_text(content)
    print(f"Created patched server at: {patched_file}")
    
    # Also create a simpler standalone version
    create_standalone_server()


def create_standalone_server():
    """Create a standalone MCP server with BM25 search."""
    
    standalone_content = '''#!/usr/bin/env python3
"""
Standalone MCP server with BM25 search support.
This server provides direct BM25 search without requiring plugins.
"""

import os
import sys
import json
import logging
import sqlite3
import hashlib
import subprocess
from pathlib import Path
from typing import Any, Sequence, Optional, Dict, List, Iterable

# MCP imports
import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

# Set up logging - send all logs to stderr
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)


class BM25Dispatcher:
    """Simple BM25 dispatcher for MCP."""
    
    def __init__(self):
        self.index_root = Path.home() / ".mcp" / "indexes"
        self._current_index = None
        self._detect_current_index()
        self._stats = {"searches": 0, "lookups": 0}
    
    def _detect_current_index(self):
        """Detect the current repository's index."""
        try:
            # Get git remote URL
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                remote_url = result.stdout.strip()
                repo_hash = hashlib.sha256(remote_url.encode()).hexdigest()[:12]
                
                # Look for current.db in centralized location
                current_db = self.index_root / repo_hash / "current.db"
                if current_db.exists():
                    self._current_index = current_db.resolve()
                    logger.info(f"Using index: {self._current_index}")
                    return
        except Exception as e:
            logger.warning(f"Could not detect git repository: {e}")
        
        # Fallback to symlink in .mcp-index
        current_link = Path.cwd() / ".mcp-index" / "current"
        if current_link.exists() and current_link.is_symlink():
            self._current_index = current_link.resolve()
            logger.info(f"Using index from symlink: {self._current_index}")
    
    def search(self, query: str, semantic: bool = False, limit: int = 20) -> List[Dict[str, Any]]:
        """Search BM25 index."""
        if not self._current_index or not self._current_index.exists():
            return []
        
        self._stats["searches"] += 1
        conn = sqlite3.connect(str(self._current_index))
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT filepath, filename, 
                       snippet(bm25_content, -1, '<<', '>>', '...', 20) as snippet,
                       rank
                FROM bm25_content
                WHERE bm25_content MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (query, limit))
            
            results = []
            for filepath, filename, snippet, rank in cursor.fetchall():
                results.append({
                    'file': filepath,
                    'filename': filename,
                    'line': 1,  # Default, would need content analysis for exact line
                    'snippet': snippet,
                    'score': abs(rank)
                })
            return results
        finally:
            conn.close()
    
    def lookup(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Look up symbol definition."""
        self._stats["lookups"] += 1
        
        # Try different patterns
        patterns = [
            f'class {symbol}', f'def {symbol}', f'function {symbol}',
            f'const {symbol}', f'var {symbol}', f'let {symbol}',
            f'type {symbol}', f'interface {symbol}'
        ]
        
        for pattern in patterns:
            results = self.search(pattern, limit=5)
            if results:
                best = results[0]
                
                # Detect kind from snippet
                snippet_lower = best['snippet'].lower()
                kind = 'symbol'
                if 'class' in snippet_lower:
                    kind = 'class'
                elif 'def' in snippet_lower or 'function' in snippet_lower:
                    kind = 'function'
                elif any(kw in snippet_lower for kw in ['const', 'var', 'let']):
                    kind = 'variable'
                
                # Detect language from extension
                ext = Path(best['file']).suffix.lower()
                lang_map = {
                    '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
                    '.java': 'java', '.go': 'go', '.rs': 'rust',
                    '.cpp': 'cpp', '.c': 'c', '.cs': 'csharp'
                }
                
                return {
                    'symbol': symbol,
                    'kind': kind,
                    'language': lang_map.get(ext, 'unknown'),
                    'defined_in': best['file'],
                    'line': best['line'],
                    'signature': best['snippet'],
                    'doc': ''
                }
        
        return None
    
    def get_statistics(self):
        """Get statistics."""
        return {
            'operations': self._stats,
            'total_operations': sum(self._stats.values()),
            'backend': 'bm25_direct',
            'index_path': str(self._current_index) if self._current_index else None
        }
    
    def health_check(self):
        """Check health."""
        return {
            'status': 'operational' if self._current_index and self._current_index.exists() else 'degraded',
            'backend': 'bm25_direct',
            'index': str(self._current_index) if self._current_index else None
        }
    
    @property
    def supported_languages(self):
        """All languages supported via BM25."""
        return ['python', 'javascript', 'typescript', 'java', 'go', 'rust', 
                'cpp', 'c', 'csharp', 'ruby', 'php', 'swift', 'kotlin']


# Initialize server
server = Server("code-index-mcp-bm25-direct")
dispatcher = None


async def initialize_services():
    """Initialize the BM25 dispatcher."""
    global dispatcher
    
    dispatcher = BM25Dispatcher()
    health = dispatcher.health_check()
    
    if health['status'] != 'operational':
        logger.error(f"No valid BM25 index found: {health}")
        raise RuntimeError("No BM25 index available. Run 'mcp-index index' to create one.")
    
    logger.info(f"BM25 dispatcher ready with index: {health['index']}")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """List available tools."""
    return [
        types.Tool(
            name="symbol_lookup",
            description="[MCP-FIRST] Look up symbol definitions. ALWAYS use this before grep/find for symbol searches.",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "The symbol name to look up"}
                },
                "required": ["symbol"]
            }
        ),
        types.Tool(
            name="search_code",
            description="[MCP-FIRST] Search code patterns. ALWAYS use this before grep/find for content searches.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"},
                    "semantic": {"type": "boolean", "description": "Whether to use semantic search", "default": False},
                    "limit": {"type": "integer", "description": "Maximum number of results", "default": 20}
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="get_status",
            description="Get the status of the code index server.",
            inputSchema={"type": "object", "properties": {}}
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict | None) -> Sequence[types.TextContent]:
    """Handle tool calls."""
    if dispatcher is None:
        await initialize_services()
    
    try:
        if name == "symbol_lookup":
            symbol = arguments.get("symbol") if arguments else None
            if not symbol:
                return [types.TextContent(type="text", text="Error: 'symbol' parameter is required")]
            
            result = dispatcher.lookup(symbol)
            if result:
                response = {
                    "symbol": result["symbol"],
                    "kind": result["kind"],
                    "language": result["language"],
                    "defined_in": result["defined_in"],
                    "line": result["line"],
                    "signature": result["signature"]
                }
                
                if result.get("line") and result.get("defined_in"):
                    offset = result["line"] - 1
                    response["_usage_hint"] = f"To view: Read(file_path='{result['defined_in']}', offset={offset})"
                
                return [types.TextContent(type="text", text=json.dumps(response, indent=2))]
            else:
                return [types.TextContent(type="text", text=f"Symbol '{symbol}' not found")]
        
        elif name == "search_code":
            query = arguments.get("query") if arguments else None
            if not query:
                return [types.TextContent(type="text", text="Error: 'query' parameter is required")]
            
            limit = arguments.get("limit", 20) if arguments else 20
            results = dispatcher.search(query, limit=limit)
            
            if results:
                results_data = []
                for r in results:
                    item = {
                        "file": r["file"],
                        "line": r["line"],
                        "snippet": r["snippet"]
                    }
                    if r.get("line") and r.get("file"):
                        offset = r["line"] - 1
                        item["_usage_hint"] = f"To view: Read(file_path='{r['file']}', offset={offset})"
                    results_data.append(item)
                
                return [types.TextContent(type="text", text=json.dumps(results_data, indent=2))]
            else:
                return [types.TextContent(type="text", text="No results found")]
        
        elif name == "get_status":
            stats = dispatcher.get_statistics()
            health = dispatcher.health_check()
            
            status = {
                "status": health["status"],
                "version": "0.2.0-bm25",
                "backend": "bm25_direct",
                "index": health.get("index"),
                "statistics": stats
            }
            
            return [types.TextContent(type="text", text=json.dumps(status, indent=2))]
        
        else:
            return [types.TextContent(type="text", text=f"Unknown tool: {name}")]
    
    except Exception as e:
        logger.error(f"Error calling tool {name}: {e}", exc_info=True)
        return [types.TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, initialize_services, {})


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
'''
    
    standalone_file = Path("PathUtils.get_workspace_root()/scripts/cli/mcp_server_bm25.py")
    standalone_file.write_text(standalone_content)
    standalone_file.chmod(0o755)
    
    print(f"Created standalone BM25 server at: {standalone_file}")


if __name__ == "__main__":
    create_patched_server()