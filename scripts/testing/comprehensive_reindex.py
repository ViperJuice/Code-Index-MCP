#!/usr/bin/env python3
"""
Comprehensive re-indexing script for Code-Index-MCP repository.
Properly indexes all files with full symbol extraction and BM25 content.
"""

import sys
import os
from pathlib import Path
import json
import time
from datetime import datetime
import hashlib
from typing import Dict, List, Any, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set environment variables
os.environ["MCP_ENABLE_MULTI_REPO"] = "true"
os.environ["MCP_INDEX_STORAGE_PATH"] = "/workspaces/Code-Index-MCP/.indexes"
os.environ["PYTHONPATH"] = "/workspaces/Code-Index-MCP"

from mcp_server.indexer.bm25_indexer import BM25Indexer
from mcp_server.indexer.index_engine import IndexEngine
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.core.path_utils import PathUtils
from mcp_server.plugins.plugin_factory import PluginFactory
from mcp_server.plugins.language_registry import get_language_by_extension, get_all_extensions


class ComprehensiveIndexer:
    """Comprehensive indexer with full symbol extraction."""
    
    def __init__(self, workspace_root: Path, repo_hash: str):
        self.workspace_root = workspace_root
        self.repo_hash = repo_hash
        self.index_dir = PathUtils.get_index_storage_path() / repo_hash
        self.index_path = self.index_dir / "code_index.db"
        
        # Statistics
        self.stats = {
            "total_files": 0,
            "indexed_files": 0,
            "failed_files": 0,
            "skipped_files": 0,
            "total_symbols": 0,
            "by_language": {},
            "errors": []
        }
        
        # Exclusion patterns
        self.exclude_dirs = {
            '.git', '__pycache__', 'node_modules', 'venv', 'env', 
            '.pytest_cache', '.mypy_cache', '.coverage', 'dist', 
            'build', '.eggs', 'test_repos', '.tox', 'htmlcov',
            'site-packages', '.ipynb_checkpoints', '.venv'
        }
        
        self.exclude_extensions = {
            '.pyc', '.pyo', '.so', '.dll', '.dylib', '.egg', 
            '.whl', '.tar', '.gz', '.zip', '.jpg', '.png', 
            '.gif', '.ico', '.svg', '.pdf', '.doc', '.docx'
        }
    
    def should_index_file(self, file_path: Path) -> bool:
        """Check if file should be indexed."""
        # Check directory exclusions
        for part in file_path.parts:
            if part in self.exclude_dirs:
                return False
        
        # Check extension exclusions
        if file_path.suffix.lower() in self.exclude_extensions:
            return False
        
        # Check file size (skip very large files)
        try:
            if file_path.stat().st_size > 10 * 1024 * 1024:  # 10MB
                return False
        except:
            return False
        
        return True
    
    def create_index(self):
        """Create a fresh index with proper schema."""
        print(f"\nCreating fresh index at: {self.index_path}")
        
        # Ensure directory exists
        self.index_dir.mkdir(parents=True, exist_ok=True)
        
        # Create SQLite store
        self.store = SQLiteStore(str(self.index_path))
        
        # Create index engine
        self.engine = IndexEngine(
            storage=self.store,
            enable_bm25=True,
            enable_semantic=False  # Disable for now
        )
        
        # Create BM25 indexer
        self.bm25_indexer = BM25Indexer(self.store)
        
        # Initialize plugin factory
        self.plugin_factory = PluginFactory()
        
        print("✓ Index infrastructure created")
    
    def discover_files(self) -> List[Path]:
        """Discover all files to index."""
        print("\nDiscovering files...")
        files_to_index = []
        
        for file_path in self.workspace_root.rglob('*'):
            if file_path.is_file():
                self.stats["total_files"] += 1
                
                if self.should_index_file(file_path):
                    files_to_index.append(file_path)
                else:
                    self.stats["skipped_files"] += 1
        
        print(f"✓ Found {len(files_to_index)} files to index (skipped {self.stats['skipped_files']})")
        return files_to_index
    
    def index_file(self, file_path: Path) -> bool:
        """Index a single file with symbol extraction."""
        try:
            # Read file content
            try:
                content = file_path.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                # Try latin-1 as fallback
                try:
                    content = file_path.read_text(encoding='latin-1')
                except:
                    return False
            
            # Get file metadata
            stat = file_path.stat()
            file_hash = hashlib.md5(content.encode()).hexdigest()
            relative_path = file_path.relative_to(self.workspace_root)
            
            # Detect language
            language = get_language_by_extension(file_path.suffix)
            if not language:
                language = 'text'
            
            # Update language stats
            self.stats["by_language"][language] = self.stats["by_language"].get(language, 0) + 1
            
            # Get appropriate plugin for symbol extraction
            plugin = None
            try:
                plugin = self.plugin_factory.create_plugin(language, enable_semantic=False)
            except:
                # Fallback to generic plugin
                pass
            
            # Extract symbols if plugin available
            symbols = []
            if plugin and hasattr(plugin, 'extract_symbols'):
                try:
                    symbol_results = plugin.extract_symbols(content, str(file_path))
                    if symbol_results:
                        symbols = symbol_results
                        self.stats["total_symbols"] += len(symbols)
                except:
                    pass
            
            # Index the file
            file_data = {
                'path': str(file_path),
                'relative_path': str(relative_path),
                'content': content,
                'language': language,
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'hash': file_hash
            }
            
            # Add to engine (handles both files table and BM25)
            self.engine.add_document(file_data, symbols=symbols)
            
            # Also ensure BM25 indexing
            self.bm25_indexer.index_content(
                file_id=self.stats["indexed_files"] + 1,
                filepath=str(file_path),
                content=content,
                language=language,
                symbols=[s.get('name', '') for s in symbols] if symbols else []
            )
            
            self.stats["indexed_files"] += 1
            return True
            
        except Exception as e:
            self.stats["failed_files"] += 1
            self.stats["errors"].append({
                "file": str(file_path),
                "error": str(e)
            })
            return False
    
    def run_indexing(self):
        """Run the complete indexing process."""
        start_time = time.time()
        
        print("\n" + "=" * 60)
        print("COMPREHENSIVE RE-INDEXING")
        print("=" * 60)
        print(f"Repository: {self.workspace_root}")
        print(f"Index location: {self.index_path}")
        
        # Create index
        self.create_index()
        
        # Discover files
        files_to_index = self.discover_files()
        
        # Index files
        print(f"\nIndexing {len(files_to_index)} files...")
        for i, file_path in enumerate(files_to_index):
            if self.index_file(file_path):
                if (i + 1) % 100 == 0:
                    print(f"  Progress: {i + 1}/{len(files_to_index)} files indexed...")
            
            # Commit periodically
            if (i + 1) % 500 == 0:
                self.store.commit()
        
        # Final commit
        self.store.commit()
        
        # Optimize indexes
        print("\nOptimizing indexes...")
        self.bm25_indexer.optimize()
        
        # Create metadata
        elapsed_time = time.time() - start_time
        self.create_metadata(elapsed_time)
        
        # Update registry
        self.update_registry()
        
        # Print summary
        print("\n" + "=" * 60)
        print("INDEXING COMPLETE")
        print("=" * 60)
        print(f"Total files found: {self.stats['total_files']}")
        print(f"Files indexed: {self.stats['indexed_files']}")
        print(f"Files skipped: {self.stats['skipped_files']}")
        print(f"Files failed: {self.stats['failed_files']}")
        print(f"Total symbols: {self.stats['total_symbols']}")
        print(f"Time taken: {elapsed_time:.2f} seconds")
        print("\nLanguage breakdown:")
        for lang, count in sorted(self.stats["by_language"].items(), key=lambda x: x[1], reverse=True):
            print(f"  {lang}: {count} files")
        
        if self.stats["errors"]:
            print(f"\nErrors encountered: {len(self.stats['errors'])}")
            for error in self.stats["errors"][:5]:
                print(f"  - {error['file']}: {error['error']}")
        
        print(f"\n✅ Index ready at: {self.index_path}")
    
    def create_metadata(self, elapsed_time: float):
        """Create index metadata file."""
        metadata = {
            "repository": str(self.workspace_root),
            "repository_hash": self.repo_hash,
            "indexed_at": datetime.now().isoformat(),
            "indexing_time_seconds": elapsed_time,
            "statistics": self.stats,
            "schema_version": "2.0",
            "features": {
                "bm25_search": True,
                "symbol_extraction": True,
                "semantic_search": False,
                "multi_repo": True
            }
        }
        
        metadata_path = self.index_dir / ".index_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"\n✓ Metadata saved to: {metadata_path}")
    
    def update_registry(self):
        """Update repository registry."""
        registry_path = PathUtils.get_index_storage_path() / "repository_registry.json"
        
        # Load existing registry
        if registry_path.exists():
            with open(registry_path, 'r') as f:
                registry = json.load(f)
        else:
            registry = {}
        
        # Update entry
        registry[self.repo_hash] = {
            "repository_id": self.repo_hash,
            "name": self.workspace_root.name,
            "path": str(self.workspace_root),
            "index_path": str(self.index_path),
            "language_stats": self.stats["by_language"],
            "total_files": self.stats["indexed_files"],
            "total_symbols": self.stats["total_symbols"],
            "indexed_at": datetime.now().isoformat(),
            "active": True,
            "priority": 10
        }
        
        # Save registry
        with open(registry_path, 'w') as f:
            json.dump(registry, f, indent=2)
        
        print(f"✓ Registry updated")


def main():
    """Main entry point."""
    workspace_root = PathUtils.get_workspace_root()
    repo_hash = "844145265d7a"  # Current repository hash
    
    indexer = ComprehensiveIndexer(workspace_root, repo_hash)
    indexer.run_indexing()


if __name__ == "__main__":
    main()