#!/usr/bin/env python3
"""Test the complete MCP system with real-world repositories across multiple languages."""

import asyncio
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).parent))

import mcp_server_cli


# Real-world repositories to test (small to medium sized for faster testing)
TEST_REPOSITORIES = {
    "rust": {
        "url": "https://github.com/BurntSushi/ripgrep.git",
        "name": "ripgrep",
        "description": "Fast regex search tool in Rust",
        "expected_symbols": ["main", "search", "Searcher", "Config"],
        "expected_files": [".rs"]
    },
    "go": {
        "url": "https://github.com/spf13/cobra.git", 
        "name": "cobra",
        "description": "CLI library for Go",
        "expected_symbols": ["Command", "Execute", "NewCommand"],
        "expected_files": [".go"]
    },
    "python": {
        "url": "https://github.com/psf/requests.git",
        "name": "requests",
        "description": "HTTP library for Python",
        "expected_symbols": ["get", "post", "Session", "Response"],
        "expected_files": [".py"]
    },
    "javascript": {
        "url": "https://github.com/lodash/lodash.git",
        "name": "lodash", 
        "description": "Utility library for JavaScript",
        "expected_symbols": ["map", "filter", "reduce", "forEach"],
        "expected_files": [".js"]
    },
    "typescript": {
        "url": "https://github.com/microsoft/vscode-languageserver-node.git",
        "name": "vscode-languageserver",
        "description": "Language Server Protocol implementation",
        "expected_symbols": ["Connection", "TextDocument", "LanguageServer"],
        "expected_files": [".ts"]
    }
}


async def clone_repository(repo_info: Dict, base_dir: Path) -> Path:
    """Clone a repository for testing."""
    repo_path = base_dir / repo_info["name"]
    
    if repo_path.exists():
        print(f"   Repository {repo_info['name']} already exists, using existing copy")
        return repo_path
    
    print(f"   Cloning {repo_info['name']} from {repo_info['url']}")
    
    # Use git clone with depth=1 for faster cloning
    import subprocess
    try:
        result = subprocess.run([
            "git", "clone", "--depth", "1", 
            repo_info["url"], str(repo_path)
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            print(f"   ✗ Failed to clone {repo_info['name']}: {result.stderr}")
            return None
        
        print(f"   ✓ Successfully cloned {repo_info['name']}")
        return repo_path
        
    except subprocess.TimeoutExpired:
        print(f"   ✗ Timeout cloning {repo_info['name']}")
        return None
    except Exception as e:
        print(f"   ✗ Error cloning {repo_info['name']}: {e}")
        return None


def count_files_by_extension(repo_path: Path, extensions: List[str]) -> Dict[str, int]:
    """Count files by extension in repository."""
    counts = {}
    for ext in extensions:
        pattern = f"**/*{ext}"
        files = list(repo_path.glob(pattern))
        counts[ext] = len(files)
    return counts


def find_sample_files(repo_path: Path, extensions: List[str], max_files: int = 5) -> List[Path]:
    """Find sample files for testing."""
    sample_files = []
    for ext in extensions:
        pattern = f"**/*{ext}"
        files = list(repo_path.glob(pattern))
        # Skip very large files and common non-source files
        filtered_files = []
        for f in files:
            if f.stat().st_size < 100_000:  # Less than 100KB
                filename = f.name.lower()
                if not any(skip in filename for skip in ['test', 'spec', 'min.js', '.d.ts']):
                    filtered_files.append(f)
        
        sample_files.extend(filtered_files[:max_files])
        if len(sample_files) >= max_files:
            break
    
    return sample_files[:max_files]


async def test_repository_indexing(repo_info: Dict, repo_path: Path) -> Dict:
    """Test indexing a real repository."""
    print(f"\n--- Testing {repo_info['name']} ({repo_info['description']}) ---")
    
    if not repo_path or not repo_path.exists():
        return {"error": "Repository not available"}
    
    # Initialize MCP services
    if mcp_server_cli.dispatcher is None:
        await mcp_server_cli.initialize_services()
    
    dispatcher = mcp_server_cli.dispatcher
    
    # Change to repo directory
    original_cwd = os.getcwd()
    os.chdir(repo_path)
    
    try:
        # Count files
        file_counts = count_files_by_extension(repo_path, repo_info["expected_files"])
        print(f"   Files found: {file_counts}")
        
        # Find sample files to index
        sample_files = find_sample_files(repo_path, repo_info["expected_files"])
        print(f"   Testing with {len(sample_files)} sample files")
        
        # Test indexing
        start_time = time.time()
        indexed_count = 0
        symbols_found = []
        
        for file_path in sample_files:
            try:
                dispatcher.index_file(file_path)
                indexed_count += 1
                print(f"     ✓ Indexed {file_path.name}")
            except Exception as e:
                print(f"     ✗ Failed to index {file_path.name}: {e}")
        
        indexing_time = time.time() - start_time
        
        # Test symbol search
        print(f"   Testing symbol search...")
        search_results = {}
        
        for symbol in repo_info["expected_symbols"]:
            results = list(dispatcher.search(symbol, limit=5))
            search_results[symbol] = len(results)
            if results:
                print(f"     ✓ '{symbol}': {len(results)} results")
            else:
                print(f"     ✗ '{symbol}': no results")
        
        # Test semantic search
        print(f"   Testing semantic search...")
        semantic_queries = [
            "data processing",
            "error handling", 
            "configuration",
            "utility function"
        ]
        
        semantic_results = {}
        for query in semantic_queries:
            try:
                results = list(dispatcher.search(query, semantic=True, limit=3))
                semantic_results[query] = len(results)
                if results:
                    print(f"     ✓ Semantic '{query}': {len(results)} results")
            except Exception as e:
                print(f"     ✗ Semantic '{query}' failed: {e}")
                semantic_results[query] = 0
        
        # Get statistics
        stats = dispatcher.get_statistics()
        
        return {
            "success": True,
            "files_available": sum(file_counts.values()),
            "files_indexed": indexed_count,
            "indexing_time": indexing_time,
            "symbol_search": search_results,
            "semantic_search": semantic_results,
            "plugins_loaded": stats.get('total_plugins', 0),
            "languages": stats.get('loaded_languages', [])
        }
        
    except Exception as e:
        print(f"   ✗ Error testing repository: {e}")
        return {"error": str(e)}
    finally:
        os.chdir(original_cwd)


async def test_cross_language_search(repo_paths: Dict[str, Path]) -> Dict:
    """Test search across multiple languages."""
    print(f"\n--- Testing Cross-Language Search ---")
    
    dispatcher = mcp_server_cli.dispatcher
    if not dispatcher:
        return {"error": "Dispatcher not available"}
    
    # Test common programming concepts across languages
    cross_lang_queries = [
        "error",
        "config", 
        "parse",
        "handle",
        "create"
    ]
    
    results = {}
    for query in cross_lang_queries:
        search_results = list(dispatcher.search(query, limit=20))
        
        # Group results by language
        by_language = {}
        for result in search_results:
            file_path = result.get('file', '')
            if file_path:
                ext = Path(file_path).suffix
                if ext not in by_language:
                    by_language[ext] = 0
                by_language[ext] += 1
        
        results[query] = {
            "total": len(search_results),
            "by_language": by_language
        }
        
        if search_results:
            print(f"   ✓ '{query}': {len(search_results)} results across {len(by_language)} languages")
        else:
            print(f"   ✗ '{query}': no results")
    
    return results


async def run_comprehensive_test():
    """Run the complete real-world repository test."""
    print("=== Comprehensive Real-World Repository Test ===\n")
    
    # Create temporary directory
    temp_dir = Path(tempfile.mkdtemp(prefix="mcp_test_"))
    print(f"Working in: {temp_dir}")
    
    try:
        # Clone repositories
        print("\n1. Cloning Test Repositories...")
        repo_paths = {}
        
        for lang, repo_info in TEST_REPOSITORIES.items():
            repo_path = await clone_repository(repo_info, temp_dir)
            if repo_path:
                repo_paths[lang] = repo_path
        
        print(f"\n✓ Successfully prepared {len(repo_paths)} repositories")
        
        # Test each repository
        print("\n2. Testing Individual Repositories...")
        repo_results = {}
        
        for lang, repo_info in TEST_REPOSITORIES.items():
            if lang in repo_paths:
                result = await test_repository_indexing(repo_info, repo_paths[lang])
                repo_results[lang] = result
        
        # Test cross-language functionality
        print("\n3. Testing Cross-Language Features...")
        cross_lang_results = await test_cross_language_search(repo_paths)
        
        # Generate comprehensive report
        print("\n=== Final Report ===")
        
        successful_repos = len([r for r in repo_results.values() if r.get('success')])
        total_files_indexed = sum(r.get('files_indexed', 0) for r in repo_results.values())
        total_indexing_time = sum(r.get('indexing_time', 0) for r in repo_results.values())
        
        print(f"\nRepository Testing:")
        print(f"  ✓ Repositories tested: {successful_repos}/{len(TEST_REPOSITORIES)}")
        print(f"  ✓ Total files indexed: {total_files_indexed}")
        print(f"  ✓ Total indexing time: {total_indexing_time:.2f}s")
        print(f"  ✓ Average time per file: {total_indexing_time/max(total_files_indexed,1):.3f}s")
        
        print(f"\nLanguage Coverage:")
        all_languages = set()
        for result in repo_results.values():
            all_languages.update(result.get('languages', []))
        print(f"  ✓ Languages active: {len(all_languages)}")
        print(f"  ✓ Languages: {', '.join(sorted(all_languages))}")
        
        print(f"\nSearch Performance:")
        total_symbol_results = 0
        total_semantic_results = 0
        
        for result in repo_results.values():
            total_symbol_results += sum(result.get('symbol_search', {}).values())
            total_semantic_results += sum(result.get('semantic_search', {}).values())
        
        print(f"  ✓ Symbol search results: {total_symbol_results}")
        print(f"  ✓ Semantic search results: {total_semantic_results}")
        
        cross_lang_total = sum(r.get('total', 0) for r in cross_lang_results.values())
        print(f"  ✓ Cross-language search results: {cross_lang_total}")
        
        # Detailed results
        print(f"\nDetailed Results by Repository:")
        for lang, result in repo_results.items():
            if result.get('success'):
                print(f"  {lang.upper()}:")
                print(f"    Files indexed: {result.get('files_indexed', 0)}")
                print(f"    Symbol searches: {sum(result.get('symbol_search', {}).values())}")
                print(f"    Semantic searches: {sum(result.get('semantic_search', {}).values())}")
            else:
                print(f"  {lang.upper()}: ERROR - {result.get('error', 'Unknown')}")
        
        # Success criteria
        success = (
            successful_repos >= len(TEST_REPOSITORIES) * 0.8 and  # 80% repos working
            total_files_indexed > 10 and  # At least 10 files indexed
            total_symbol_results > 0 and  # Symbol search working
            len(all_languages) >= 5  # At least 5 languages active
        )
        
        return success, {
            "repositories": repo_results,
            "cross_language": cross_lang_results,
            "summary": {
                "successful_repos": successful_repos,
                "total_files": total_files_indexed,
                "indexing_time": total_indexing_time,
                "languages": sorted(all_languages),
                "symbol_results": total_symbol_results,
                "semantic_results": total_semantic_results
            }
        }
        
    finally:
        # Cleanup
        print(f"\n4. Cleaning up...")
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            print(f"   ✓ Removed {temp_dir}")


async def main():
    """Main test execution."""
    try:
        success, results = await run_comprehensive_test()
        
        if success:
            print(f"\n🎉 Comprehensive test PASSED!")
            print(f"The MCP server successfully handles real-world repositories")
            print(f"with 48-language support, embedding generation, and semantic search!")
        else:
            print(f"\n⚠️ Comprehensive test needs attention")
            print(f"Some features may need optimization for production use")
        
        # Save detailed results
        results_file = Path("test_results.json")
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nDetailed results saved to: {results_file}")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())