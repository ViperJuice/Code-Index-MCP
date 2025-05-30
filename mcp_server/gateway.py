from fastapi import FastAPI, HTTPException
from typing import Optional, Dict, Any, List
from pathlib import Path
import logging
from .dispatcher import Dispatcher
from .plugin_base import SymbolDef, SearchResult
from .plugins.python_plugin.plugin import Plugin as PythonPlugin
from .storage.sqlite_store import SQLiteStore
from .watcher import FileWatcher
from .core.logging import setup_logging

# Set up logging
setup_logging(log_level="INFO")
logger = logging.getLogger(__name__)

app = FastAPI(title="MCP Server")
dispatcher: Dispatcher | None = None
sqlite_store: SQLiteStore | None = None
file_watcher: FileWatcher | None = None

@app.on_event("startup")
async def startup_event():
    """Initialize the dispatcher and register plugins on startup."""
    global dispatcher, sqlite_store, file_watcher
    
    try:
        # Initialize SQLite store
        logger.info("Initializing SQLite store...")
        sqlite_store = SQLiteStore("code_index.db")
        logger.info("SQLite store initialized successfully")
        
        # Create the PythonPlugin with SQLite store
        logger.info("Creating Python plugin...")
        python_plugin = PythonPlugin(sqlite_store=sqlite_store)
        logger.info("Python plugin created successfully")
        
        # Create a new Dispatcher instance with the plugin
        logger.info("Creating dispatcher...")
        dispatcher = Dispatcher([python_plugin])
        logger.info("Dispatcher created with 1 plugin")
        
        # Initialize file watcher with dispatcher
        logger.info("Starting file watcher...")
        file_watcher = FileWatcher(Path("."), dispatcher)
        file_watcher.start()
        logger.info("File watcher started for current directory")
        
        # Store in app.state for potential future use
        app.state.dispatcher = dispatcher
        app.state.sqlite_store = sqlite_store
        app.state.file_watcher = file_watcher
        
        logger.info("MCP Server initialized successfully with Python plugin, SQLite persistence, and file watcher")
    except Exception as e:
        logger.error(f"Failed to initialize MCP Server: {e}", exc_info=True)
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    global file_watcher
    
    if file_watcher:
        try:
            file_watcher.stop()
            logger.info("File watcher stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping file watcher: {e}", exc_info=True)

@app.get("/symbol", response_model=SymbolDef | None)
def symbol(symbol: str):
    if dispatcher is None:
        logger.error("Symbol lookup attempted but dispatcher not ready")
        raise HTTPException(503, "Dispatcher not ready")
    
    try:
        logger.debug(f"Looking up symbol: {symbol}")
        result = dispatcher.lookup(symbol)
        if result:
            logger.debug(f"Found symbol: {symbol}")
        else:
            logger.debug(f"Symbol not found: {symbol}")
        return result
    except Exception as e:
        logger.error(f"Error looking up symbol '{symbol}': {e}", exc_info=True)
        raise HTTPException(500, f"Internal error during symbol lookup: {str(e)}")

@app.get("/search", response_model=list[SearchResult])
def search(q: str, semantic: bool = False, limit: int = 20):
    if dispatcher is None:
        logger.error("Search attempted but dispatcher not ready")
        raise HTTPException(503, "Dispatcher not ready")
    
    try:
        logger.debug(f"Searching for: '{q}' (semantic={semantic}, limit={limit})")
        results = list(dispatcher.search(q, semantic=semantic, limit=limit))
        logger.debug(f"Search returned {len(results)} results")
        return results
    except Exception as e:
        logger.error(f"Error during search for '{q}': {e}", exc_info=True)
        raise HTTPException(500, f"Internal error during search: {str(e)}")

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
        
        # Add database statistics if available
        db_stats = {}
        if sqlite_store:
            db_stats = sqlite_store.get_statistics()
        
        return {
            "status": "operational",
            "plugins": plugin_count,
            "indexed_files": indexed_stats,
            "database": db_stats,
            "version": "0.1.0"
        }
    except Exception as e:
        logger.error(f"Error getting server status: {e}", exc_info=True)
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
        logger.error("Plugin list requested but dispatcher not ready")
        raise HTTPException(503, "Dispatcher not ready")
    
    try:
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
        
        logger.debug(f"Returning {len(plugin_list)} plugins")
        return plugin_list
    except Exception as e:
        logger.error(f"Error getting plugin list: {e}", exc_info=True)
        raise HTTPException(500, f"Internal error getting plugins: {str(e)}")

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
        logger.error("Reindex requested but dispatcher not ready")
        raise HTTPException(503, "Dispatcher not ready")
    
    try:
        logger.info(f"Manual reindex requested for path: {path or 'all'}")
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
                            logger.warning(f"Failed to index {file_path}: {e}")
            
            logger.info(f"Successfully reindexed {indexed_count} files in {path}")
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
                    logger.warning(f"Failed to index {py_file}: {e}")
            
            logger.info(f"Successfully reindexed {indexed_count} Python files")
            return {
                "status": "completed",
                "message": f"Reindexed {indexed_count} Python files"
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reindexing failed: {e}", exc_info=True)
        raise HTTPException(500, f"Reindexing failed: {str(e)}")
