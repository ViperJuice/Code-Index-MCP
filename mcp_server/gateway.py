from fastapi import FastAPI, HTTPException
from typing import Optional, Dict, Any, List
from pathlib import Path
from .dispatcher import Dispatcher
from .plugin_base import SymbolDef, SearchResult
from .plugins.python_plugin.plugin import Plugin as PythonPlugin

app = FastAPI(title="MCP Server")
dispatcher: Dispatcher | None = None

@app.on_event("startup")
async def startup_event():
    """Initialize the dispatcher and register plugins on startup."""
    global dispatcher
    
    # Create the PythonPlugin
    python_plugin = PythonPlugin()
    
    # Create a new Dispatcher instance with the plugin
    dispatcher = Dispatcher([python_plugin])
    
    # Store dispatcher in app.state for potential future use
    app.state.dispatcher = dispatcher
    
    print("MCP Server initialized with Python plugin")

@app.get("/symbol", response_model=SymbolDef | None)
def symbol(symbol: str):
    if dispatcher is None:
        raise HTTPException(503, "Dispatcher not ready")
    return dispatcher.lookup(symbol)

@app.get("/search", response_model=list[SearchResult])
def search(q: str, semantic: bool = False, limit: int = 20):
    if dispatcher is None:
        raise HTTPException(503, "Dispatcher not ready")
    return list(dispatcher.search(q, semantic=semantic, limit=limit))

@app.get("/status")
def status() -> Dict[str, Any]:
    """Returns server status including plugin information and statistics."""
    if dispatcher is None:
        return {
            "status": "error",
            "plugins": 0,
            "indexed_files": {"total": 0, "by_language": {}},
            "version": "0.1.0",
            "message": "Dispatcher not initialized"
        }
    
    try:
        # Get plugin count
        plugin_count = len(dispatcher._plugins) if hasattr(dispatcher, '_plugins') else 0
        
        # Get indexed files statistics
        indexed_stats = {"total": 0, "by_language": {}}
        if hasattr(dispatcher, 'get_statistics'):
            indexed_stats = dispatcher.get_statistics()
        elif hasattr(dispatcher, '_plugins'):
            # Calculate basic statistics from plugins
            for plugin in dispatcher._plugins:
                if hasattr(plugin, 'get_indexed_count'):
                    count = plugin.get_indexed_count()
                    indexed_stats["total"] += count
                    lang = getattr(plugin, 'language', getattr(plugin, 'lang', 'unknown'))
                    indexed_stats["by_language"][lang] = count
        
        return {
            "status": "operational",
            "plugins": plugin_count,
            "indexed_files": indexed_stats,
            "version": "0.1.0"
        }
    except Exception as e:
        return {
            "status": "error",
            "plugins": 0,
            "indexed_files": {"total": 0, "by_language": {}},
            "version": "0.1.0",
            "message": str(e)
        }

@app.get("/plugins")
def plugins() -> List[Dict[str, str]]:
    """Returns list of loaded plugins with their information."""
    if dispatcher is None:
        raise HTTPException(503, "Dispatcher not ready")
    
    plugin_list = []
    if hasattr(dispatcher, '_plugins'):
        for plugin in dispatcher._plugins:
            # Get plugin name from class name or other attribute
            name = plugin.__class__.__name__
            # Get language from 'language' or 'lang' attribute
            language = getattr(plugin, 'language', getattr(plugin, 'lang', 'unknown'))
            plugin_info = {
                "name": name,
                "language": language
            }
            plugin_list.append(plugin_info)
    
    return plugin_list

@app.post("/reindex")
async def reindex(path: Optional[str] = None) -> Dict[str, str]:
    """Triggers manual reindexing of files.
    
    Args:
        path: Optional specific directory path to reindex. If not provided,
              reindexes all configured paths.
    
    Returns:
        Task status information.
    """
    if dispatcher is None:
        raise HTTPException(503, "Dispatcher not ready")
    
    try:
        # Since dispatcher has index_file method, we can use it for reindexing
        if path:
            # Reindex specific path
            target_path = Path(path)
            if not target_path.exists():
                raise HTTPException(404, f"Path not found: {path}")
            
            indexed_count = 0
            if target_path.is_file():
                # Single file
                dispatcher.index_file(target_path)
                indexed_count = 1
            else:
                # Directory - find all supported files
                for file_path in target_path.rglob("*"):
                    if file_path.is_file():
                        try:
                            # Check if any plugin supports this file
                            for plugin in dispatcher._plugins:
                                if plugin.supports(file_path):
                                    dispatcher.index_file(file_path)
                                    indexed_count += 1
                                    break
                        except Exception as e:
                            # Log but continue with other files
                            print(f"Failed to index {file_path}: {e}")
            
            return {
                "status": "completed",
                "message": f"Reindexed {indexed_count} files in {path}"
            }
        else:
            # Reindex all Python files (current implementation)
            indexed_count = 0
            for py_file in Path(".").rglob("*.py"):
                try:
                    dispatcher.index_file(py_file)
                    indexed_count += 1
                except Exception as e:
                    # Log but continue
                    print(f"Failed to index {py_file}: {e}")
            
            return {
                "status": "completed",
                "message": f"Reindexed {indexed_count} Python files"
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Reindexing failed: {str(e)}")
