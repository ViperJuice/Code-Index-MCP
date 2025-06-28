#!/usr/bin/env python3
"""
Fetch diverse repositories across 20+ programming languages for comprehensive MCP testing.

This script clones a carefully selected set of repositories representing different:
- Programming paradigms (OOP, functional, systems)
- Language families (C-like, JVM, scripting)
- Project sizes (small libraries to large frameworks)
- Use cases (web, systems, tools, libraries)
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple
import time
from datetime import datetime

# Repository configuration with diversity in mind
REPOSITORIES = {
    # Systems Languages
    "systems": {
        "c": [
            ("redis/redis", "In-memory data structure store", "medium"),
            ("curl/curl", "Command line tool for transferring data", "medium"),
        ],
        "cpp": [
            ("nlohmann/json", "JSON for Modern C++", "small"),
            ("grpc/grpc", "High performance RPC framework", "large"),
        ],
        "rust": [
            ("rust-lang/rustlings", "Small exercises to learn Rust", "small"),
            ("tokio-rs/tokio", "Async runtime for Rust", "medium"),
        ],
        "zig": [
            ("ziglang/zig", "General-purpose programming language", "large"),
        ],
    },
    
    # Web/Scripting Languages
    "web": {
        "python": [
            ("django/django", "High-level Python web framework", "large"),
            ("psf/requests", "Simple HTTP library", "small"),
            ("pallets/flask", "Lightweight WSGI web framework", "medium"),
        ],
        "javascript": [
            ("facebook/react", "JavaScript library for building UIs", "large"),
            ("expressjs/express", "Fast, unopinionated web framework", "small"),
        ],
        "typescript": [
            ("microsoft/TypeScript", "TypeScript language", "large"),
        ],
        "ruby": [
            ("rails/rails", "Web application framework", "large"),
        ],
        "php": [
            ("laravel/framework", "Web application framework", "large"),
        ],
        "perl": [
            ("mojolicious/mojo", "Real-time web framework", "medium"),
        ],
    },
    
    # JVM Languages
    "jvm": {
        "java": [
            ("spring-projects/spring-boot", "Spring Boot framework", "large"),
            ("apache/kafka", "Distributed streaming platform", "large"),
        ],
        "kotlin": [
            ("ktorio/ktor", "Asynchronous framework for web apps", "medium"),
        ],
        "scala": [
            ("akka/akka", "Actor-based concurrent framework", "large"),
        ],
        "clojure": [
            ("ring-clojure/ring", "HTTP server abstraction", "small"),
        ],
    },
    
    # Modern Languages
    "modern": {
        "go": [
            ("gin-gonic/gin", "HTTP web framework", "medium"),
            ("hashicorp/terraform", "Infrastructure as Code", "large"),
        ],
        "swift": [
            ("Alamofire/Alamofire", "HTTP networking library", "medium"),
        ],
        "dart": [
            ("dart-lang/sdk", "Dart SDK core libraries", "large"),
        ],
    },
    
    # Functional Languages
    "functional": {
        "elixir": [
            ("phoenixframework/phoenix", "Productive web framework", "large"),
        ],
        "haskell": [
            ("yesodweb/yesod", "Web framework", "large"),
        ],
    },
    
    # Other Important Languages
    "other": {
        "csharp": [
            ("dotnet/aspnetcore", "Cross-platform .NET framework", "large"),
        ],
        "lua": [
            ("kong/kong", "Cloud-native API gateway", "large"),
        ],
    }
}

class RepositoryFetcher:
    """Fetches and manages diverse repositories for testing."""
    
    def __init__(self, base_dir: str = "test_repos"):
        self.base_dir = Path(base_dir)
        self.stats_file = Path("test_results/repository_stats.json")
        self.stats = {}
        
    def setup_directories(self):
        """Create directory structure for test repositories."""
        # Create base directories
        self.base_dir.mkdir(exist_ok=True)
        Path("test_results").mkdir(exist_ok=True)
        
        # Create category directories
        for category in REPOSITORIES.keys():
            (self.base_dir / category).mkdir(exist_ok=True)
            
        # Update .gitignore
        gitignore_path = Path(".gitignore")
        if gitignore_path.exists():
            content = gitignore_path.read_text()
            if "test_repos/" not in content:
                gitignore_path.write_text(content + "\ntest_repos/\n")
        else:
            gitignore_path.write_text("test_repos/\n")
            
        print(f"✓ Created directory structure under {self.base_dir}/")
        
    def clone_repository(self, owner_repo: str, category: str, language: str, 
                        description: str, size: str) -> Dict:
        """Clone a single repository and collect statistics."""
        repo_name = owner_repo.split("/")[1]
        repo_path = self.base_dir / category / language / repo_name
        
        print(f"\n{'='*60}")
        print(f"Cloning {owner_repo} ({language} - {size})")
        print(f"Description: {description}")
        print(f"{'='*60}")
        
        # Skip if already exists
        if repo_path.exists():
            print(f"✓ Repository already exists at {repo_path}")
            return self._analyze_repository(repo_path, owner_repo, language, description, size)
        
        # Create language directory
        repo_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Clone with appropriate depth based on size
        depth = 1 if size in ["large", "medium"] else None
        url = f"https://github.com/{owner_repo}.git"
        
        cmd = ["git", "clone"]
        if depth:
            cmd.extend(["--depth", str(depth)])
        cmd.extend([url, str(repo_path)])
        
        start_time = time.time()
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            clone_time = time.time() - start_time
            print(f"✓ Cloned in {clone_time:.1f}s")
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to clone: {e.stderr}")
            return None
            
        return self._analyze_repository(repo_path, owner_repo, language, description, size)
        
    def _analyze_repository(self, repo_path: Path, owner_repo: str, 
                          language: str, description: str, size: str) -> Dict:
        """Analyze repository to collect statistics."""
        stats = {
            "repository": owner_repo,
            "language": language,
            "description": description,
            "size_category": size,
            "path": str(repo_path),
            "fetched_at": datetime.now().isoformat(),
            "metrics": {}
        }
        
        # Count files by extension
        file_stats = self._count_files_by_extension(repo_path)
        
        # Calculate repository metrics
        total_files = sum(file_stats.values())
        total_size = self._get_directory_size(repo_path)
        
        # Get lines of code (approximate)
        loc = self._count_lines_of_code(repo_path, language)
        
        stats["metrics"] = {
            "total_files": total_files,
            "files_by_extension": file_stats,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "approximate_loc": loc,
            "primary_language_files": file_stats.get(self._get_file_extension(language), 0)
        }
        
        print(f"\nRepository Statistics:")
        print(f"  Total files: {total_files:,}")
        print(f"  Size: {stats['metrics']['total_size_mb']} MB")
        print(f"  Approximate LOC: {loc:,}")
        print(f"  {language} files: {stats['metrics']['primary_language_files']}")
        
        return stats
        
    def _count_files_by_extension(self, path: Path) -> Dict[str, int]:
        """Count files grouped by extension."""
        extensions = {}
        
        for file_path in path.rglob("*"):
            if file_path.is_file() and not self._should_ignore(file_path):
                ext = file_path.suffix.lower()
                if not ext:
                    ext = "no_extension"
                extensions[ext] = extensions.get(ext, 0) + 1
                
        return dict(sorted(extensions.items(), key=lambda x: x[1], reverse=True)[:10])
        
    def _should_ignore(self, path: Path) -> bool:
        """Check if path should be ignored."""
        ignore_patterns = [
            ".git", "__pycache__", "node_modules", ".pytest_cache",
            "target", "dist", "build", ".idea", ".vscode"
        ]
        
        path_str = str(path)
        return any(pattern in path_str for pattern in ignore_patterns)
        
    def _get_directory_size(self, path: Path) -> int:
        """Get total size of directory in bytes."""
        total = 0
        for file_path in path.rglob("*"):
            if file_path.is_file() and not self._should_ignore(file_path):
                try:
                    total += file_path.stat().st_size
                except:
                    pass
        return total
        
    def _count_lines_of_code(self, path: Path, language: str) -> int:
        """Approximate lines of code for the primary language."""
        ext = self._get_file_extension(language)
        total_lines = 0
        
        for file_path in path.rglob(f"*{ext}"):
            if file_path.is_file() and not self._should_ignore(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        total_lines += sum(1 for _ in f)
                except:
                    pass
                    
        return total_lines
        
    def _get_file_extension(self, language: str) -> str:
        """Get primary file extension for a language."""
        extensions = {
            "python": ".py",
            "javascript": ".js",
            "typescript": ".ts",
            "go": ".go",
            "rust": ".rs",
            "java": ".java",
            "c": ".c",
            "cpp": ".cpp",
            "csharp": ".cs",
            "ruby": ".rb",
            "php": ".php",
            "swift": ".swift",
            "kotlin": ".kt",
            "scala": ".scala",
            "clojure": ".clj",
            "elixir": ".ex",
            "haskell": ".hs",
            "dart": ".dart",
            "lua": ".lua",
            "perl": ".pl",
            "zig": ".zig"
        }
        return extensions.get(language, "")
        
    def fetch_all(self, resume=False):
        """Fetch all configured repositories."""
        self.setup_directories()
        
        # Load existing stats if resuming
        if resume and self.stats_file.exists():
            with open(self.stats_file) as f:
                existing_data = json.load(f)
            all_stats = existing_data.get("repositories", [])
            failed = existing_data.get("summary", {}).get("failed_repositories", [])
            fetched_repos = {s["repository"] for s in all_stats}
            print(f"\nResuming: {len(fetched_repos)} already fetched")
        else:
            all_stats = []
            failed = []
            fetched_repos = set()
        
        # Count total repos to fetch
        total_repos = sum(len(repos) for cat in REPOSITORIES.values() for repos in cat.values())
        remaining = total_repos - len(fetched_repos)
        print(f"\nFetching {remaining} remaining repositories (of {total_repos} total)...")
        
        batch_count = 0
        for category, languages in REPOSITORIES.items():
            for language, repos in languages.items():
                for owner_repo, description, size in repos:
                    # Skip if already fetched
                    if owner_repo in fetched_repos:
                        continue
                        
                    stats = self.clone_repository(owner_repo, category, language, description, size)
                    if stats:
                        all_stats.append(stats)
                        self.stats[owner_repo] = stats
                    else:
                        failed.append(owner_repo)
                    
                    batch_count += 1
                    
                    # Save progress every 5 repos
                    if batch_count % 5 == 0:
                        self._save_progress(all_stats, failed)
                        print(f"\n✓ Progress saved: {len(all_stats)}/{total_repos} repositories")
                        
        # Final save
        self._save_progress(all_stats, failed)
            
        print(f"\n{'='*60}")
        print(f"FETCH COMPLETE")
        print(f"{'='*60}")
        print(f"✓ Successfully fetched: {len(all_stats)} repositories")
        print(f"✓ Languages covered: {len(set(s['language'] for s in all_stats))}")
        if failed:
            print(f"✗ Failed: {len(failed)} - {failed}")
        print(f"✓ Statistics saved to: {self.stats_file}")
        
        # Print language distribution
        lang_counts = {}
        for stats in all_stats:
            lang = stats["language"]
            lang_counts[lang] = lang_counts.get(lang, 0) + 1
            
        print(f"\nLanguage Distribution:")
        for lang, count in sorted(lang_counts.items()):
            print(f"  {lang}: {count} repositories")
            
    def _save_progress(self, all_stats: List[Dict], failed: List[str]):
        """Save current progress to file."""
        self.stats_file.parent.mkdir(exist_ok=True)
        with open(self.stats_file, 'w') as f:
            json.dump({
                "summary": {
                    "total_repositories": len(all_stats),
                    "total_languages": len(set(s["language"] for s in all_stats)),
                    "fetch_date": datetime.now().isoformat(),
                    "failed_repositories": failed
                },
                "repositories": all_stats
            }, f, indent=2)


def main():
    """Main entry point."""
    fetcher = RepositoryFetcher()
    
    # Add option to fetch specific language/category
    if len(sys.argv) > 1:
        if sys.argv[1] == "--stats-only":
            # Just show current stats
            if fetcher.stats_file.exists():
                with open(fetcher.stats_file) as f:
                    data = json.load(f)
                print(json.dumps(data["summary"], indent=2))
            else:
                print("No statistics found. Run without --stats-only to fetch repositories.")
        elif sys.argv[1] == "--resume":
            # Resume from where we left off
            fetcher.fetch_all(resume=True)
        else:
            print(f"Usage: {sys.argv[0]} [--stats-only] [--resume]")
    else:
        fetcher.fetch_all()


if __name__ == "__main__":
    main()