from pathlib import Path
from typing import Iterable
import logging
import hashlib
from datetime import datetime
from .plugin_base import IPlugin, SymbolDef, SearchResult

logger = logging.getLogger(__name__)

class Dispatcher:
    def __init__(self, plugins: list[IPlugin]):
        self._plugins = plugins
        self._by_lang = {p.lang: p for p in plugins}
        # Cache for file hashes to avoid re-indexing unchanged files
        self._file_cache = {}  # path -> (mtime, size, content_hash)
    
    @property
    def plugins(self):
        """Get the dictionary of plugins by language."""
        return self._by_lang

    def _match_plugin(self, path: Path) -> IPlugin:
        for p in self._plugins:
            if p.supports(path):
                return p
        raise RuntimeError(f"No plugin for {path}")

    def lookup(self, symbol: str) -> SymbolDef | None:
        for p in self._plugins:
            res = p.getDefinition(symbol)
            if res:
                return res
        return None

    def search(self, query: str, semantic=False, limit=20) -> Iterable[SearchResult]:
        opts = {"semantic": semantic, "limit": limit}
        for p in self._plugins:
            yield from p.search(query, opts)
    
    def _get_file_hash(self, content: str) -> str:
        """Calculate SHA256 hash of file content."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _should_reindex(self, path: Path, content: str) -> bool:
        """Check if file needs re-indexing based on cache."""
        path_str = str(path)
        
        # Get current file stats
        try:
            stat = path.stat()
            mtime = stat.st_mtime
            size = stat.st_size
        except (OSError, IOError):
            # If we can't stat the file, assume we need to index it
            return True
        
        # Check cache
        if path_str not in self._file_cache:
            return True
        
        cached_mtime, cached_size, cached_hash = self._file_cache[path_str]
        
        # Quick check: if mtime and size are the same, assume content is unchanged
        if mtime == cached_mtime and size == cached_size:
            logger.debug(f"Skipping {path}: mtime and size unchanged")
            return False
        
        # If mtime or size changed, check content hash
        content_hash = self._get_file_hash(content)
        if content_hash == cached_hash:
            # Update cache with new mtime/size but same hash
            self._file_cache[path_str] = (mtime, size, content_hash)
            logger.debug(f"Skipping {path}: content unchanged despite mtime/size change")
            return False
        
        return True
    
    def index_file(self, path: Path) -> None:
        """Index a single file if it has changed."""
        try:
            # Find the appropriate plugin
            plugin = self._match_plugin(path)
            
            # Read file content
            try:
                content = path.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                # Try with different encodings
                try:
                    content = path.read_text(encoding='latin-1')
                except Exception as e:
                    logger.error(f"Failed to read {path}: {e}")
                    return
            
            # Check if we need to re-index
            if not self._should_reindex(path, content):
                return
            
            # Index the file
            logger.info(f"Indexing {path} with {plugin.lang} plugin")
            shard = plugin.indexFile(path, content)
            
            # Update cache
            stat = path.stat()
            content_hash = self._get_file_hash(content)
            self._file_cache[str(path)] = (stat.st_mtime, stat.st_size, content_hash)
            
            logger.info(f"Successfully indexed {path}: {len(shard.get('symbols', []))} symbols found")
            
        except RuntimeError as e:
            # No plugin found for this file type
            logger.debug(f"No plugin for {path}: {e}")
        except Exception as e:
            logger.error(f"Error indexing {path}: {e}", exc_info=True)
    
    def get_statistics(self) -> dict:
        """Get indexing statistics across all plugins."""
        stats = {"total": 0, "by_language": {}}
        
        for plugin in self._plugins:
            lang = plugin.lang
            # Count files in cache for this plugin
            count = 0
            for file_path in self._file_cache:
                try:
                    if plugin.supports(Path(file_path)):
                        count += 1
                except:
                    pass
            
            if count > 0:
                stats["total"] += count
                stats["by_language"][lang] = count
        
        return stats
