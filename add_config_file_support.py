#!/usr/bin/env python3
"""Add support for configuration and secret files to be indexed as plaintext."""

def get_config_file_extensions():
    """Extensions for configuration and secret files that should be indexed."""
    return {
        # Environment and configuration files
        ".env": "plaintext",
        ".env.local": "plaintext", 
        ".env.production": "plaintext",
        ".env.development": "plaintext",
        ".env.test": "plaintext",
        
        # Key and certificate files
        ".key": "plaintext",
        ".pem": "plaintext",
        ".crt": "plaintext",
        ".cer": "plaintext",
        ".pfx": "plaintext",
        ".p12": "plaintext",
        
        # Configuration files without extensions
        "": "plaintext",  # For files like "Dockerfile", "Makefile", etc.
        
        # Other config formats already supported:
        # .json, .yaml, .yml, .toml, .ini, .cfg, .conf
    }


def update_language_registry():
    """Update language registry to include plaintext as a supported language."""
    
    plaintext_config = {
        "code": "plaintext",
        "name": "PlainText",
        "extensions": [".txt", ".text", ".log", ".env", ".key", ".pem", ".crt", ".cer"],
        "symbols": [],  # No symbols for plaintext
        "query": ""  # No tree-sitter query needed
    }
    
    print("Add this to LANGUAGE_CONFIGS in language_registry.py:")
    print(f'    "plaintext": {plaintext_config},')
    

def create_plaintext_indexer():
    """Create a simple plaintext indexer that indexes all content."""
    
    code = '''
class PlainTextIndexer:
    """Simple indexer for plaintext files including configs and secrets."""
    
    def __init__(self, sqlite_store):
        self.store = sqlite_store
        self.lang = "plaintext"
        
    def supports(self, path: Path) -> bool:
        """Support common config and secret file patterns."""
        # Check extensions
        plaintext_exts = {'.txt', '.text', '.log', '.env', '.key', '.pem', '.crt', '.cer'}
        if path.suffix.lower() in plaintext_exts:
            return True
            
        # Check filenames without extensions
        no_ext_files = {'Dockerfile', 'Makefile', 'Procfile', 'Gemfile', 'Rakefile'}
        if path.name in no_ext_files:
            return True
            
        # Check patterns
        name_lower = path.name.lower()
        patterns = ['.env', 'dockerfile', 'makefile', '.gitignore', '.dockerignore']
        if any(pattern in name_lower for pattern in patterns):
            return True
            
        return False
        
    def indexFile(self, path: Path, content: str) -> dict:
        """Index plaintext file - just store the content for search."""
        # For plaintext, we can't extract symbols, but we can:
        # 1. Store the full content for search
        # 2. Extract key-value pairs from .env files
        # 3. Store line numbers for search results
        
        shard = {
            "path": str(path),
            "content": content,
            "language": "plaintext",
            "symbols": [],
            "lines": content.splitlines()
        }
        
        # For .env files, extract variables
        if '.env' in path.name:
            for i, line in enumerate(shard["lines"]):
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key = line.split('=')[0].strip()
                    shard["symbols"].append({
                        "name": key,
                        "kind": "variable",
                        "line": i + 1,
                        "signature": line
                    })
        
        # Store in database
        self.store.store_file(shard)
        return shard
'''
    
    print("\nPlainTextIndexer implementation:")
    print(code)


def update_dispatcher_to_support_all_files():
    """Update dispatcher to attempt indexing even without recognized extensions."""
    
    suggestion = '''
    # In dispatcher_enhanced.py, modify the index_directory method:
    
    # Instead of:
    if path.suffix not in supported_extensions:
        continue
        
    # Use:
    # Try to find a plugin that supports this file
    # This allows plugins to use custom logic beyond just extensions
    plugin = None
    for p in self._plugins:
        if p.supports(path):
            plugin = p
            break
            
    if not plugin and self._use_factory:
        # Try plaintext as fallback for unrecognized files
        plugin = self._ensure_plugin_loaded("plaintext")
        
    if plugin:
        try:
            self.index_file(path)
            stats["indexed_files"] += 1
        except Exception as e:
            logger.error(f"Failed to index {path}: {e}")
            stats["failed_files"] += 1
    '''
    
    print("\nDispatcher modification needed:")
    print(suggestion)


def main():
    print("CONFIGURATION FILE SUPPORT PLAN")
    print("=" * 60)
    
    print("\nProblem: .env and .key files are not indexed because they don't have")
    print("recognized programming language extensions.")
    
    print("\nSolution: Add plaintext support for configuration files")
    
    print("\n1. Configuration file extensions to support:")
    for ext, lang in get_config_file_extensions().items():
        if ext:
            print(f"   {ext} -> {lang}")
    
    print("\n2. Language registry update needed:")
    update_language_registry()
    
    print("\n3. PlainText indexer implementation:")
    create_plaintext_indexer()
    
    print("\n4. Dispatcher update:")
    update_dispatcher_to_support_all_files()
    
    print("\n" + "=" * 60)
    print("Benefits:")
    print("✓ .env files will be indexed and searchable")
    print("✓ API keys and secrets searchable locally") 
    print("✓ Configuration files included in index")
    print("✓ Still filtered during export for security")


if __name__ == "__main__":
    main()