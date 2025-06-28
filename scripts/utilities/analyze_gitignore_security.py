#!/usr/bin/env python3
"""Analyze gitignore patterns and check for security issues in index sharing."""

import sqlite3
from pathlib import Path
import fnmatch
import json
from typing import Set, List, Dict, Any

class GitignoreAnalyzer:
    """Analyze indexed files against gitignore patterns."""
    
    def __init__(self, db_path: str = "code_index.db"):
        self.db_path = db_path
        self.gitignore_patterns = self._load_gitignore_patterns()
        self.sensitive_patterns = [
            "*.env",
            ".env*",
            "*.key",
            "*.pem", 
            "*.p12",
            "*_secret*",
            "*password*",
            "*.credentials",
            "config/secrets/*",
            ".aws/*",
            ".ssh/*",
        ]
        
    def _load_gitignore_patterns(self) -> List[str]:
        """Load patterns from .gitignore file."""
        patterns = []
        gitignore_path = Path(".gitignore")
        
        if gitignore_path.exists():
            with open(gitignore_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if line and not line.startswith('#'):
                        # Handle negation patterns
                        if line.startswith('!'):
                            continue  # Skip for now
                        patterns.append(line)
                        
        return patterns
        
    def _should_be_ignored(self, file_path: str) -> bool:
        """Check if file should be ignored based on gitignore patterns."""
        path = Path(file_path)
        
        # Check each component of the path
        for pattern in self.gitignore_patterns:
            # Handle directory patterns
            if pattern.endswith('/'):
                if any(part == pattern[:-1] for part in path.parts):
                    return True
            # Handle file patterns
            elif fnmatch.fnmatch(str(path), pattern):
                return True
            elif fnmatch.fnmatch(path.name, pattern):
                return True
                
        return False
        
    def _is_sensitive(self, file_path: str) -> bool:
        """Check if file might contain sensitive information."""
        path = Path(file_path)
        
        for pattern in self.sensitive_patterns:
            if fnmatch.fnmatch(str(path), pattern):
                return True
            if fnmatch.fnmatch(path.name, pattern):
                return True
                
        return False
        
    def analyze_indexed_files(self) -> Dict[str, Any]:
        """Analyze all indexed files for security issues."""
        results = {
            "total_indexed": 0,
            "should_be_ignored": [],
            "sensitive_files": [],
            "safe_files": 0,
            "recommendations": []
        }
        
        # Connect to SQLite database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get all indexed files
            cursor.execute("SELECT path FROM files")
            files = cursor.fetchall()
            
            results["total_indexed"] = len(files)
            
            for (file_path,) in files:
                # Check if should be ignored
                if self._should_be_ignored(file_path):
                    results["should_be_ignored"].append(file_path)
                    
                # Check if sensitive
                if self._is_sensitive(file_path):
                    results["sensitive_files"].append(file_path)
                    
            results["safe_files"] = results["total_indexed"] - len(results["should_be_ignored"]) - len(results["sensitive_files"])
            
            # Generate recommendations
            if results["should_be_ignored"]:
                results["recommendations"].append(
                    f"⚠️  {len(results['should_be_ignored'])} files are indexed but should be ignored per .gitignore"
                )
                
            if results["sensitive_files"]:
                results["recommendations"].append(
                    f"🚨 {len(results['sensitive_files'])} potentially sensitive files are indexed!"
                )
                
            if not results["should_be_ignored"] and not results["sensitive_files"]:
                results["recommendations"].append(
                    "✅ No obvious security issues found in indexed files"
                )
                
        finally:
            conn.close()
            
        return results
        
    def check_index_artifact_contents(self) -> Dict[str, Any]:
        """Check what would be included in index artifacts."""
        results = self.analyze_indexed_files()
        
        # Additional checks for artifact safety
        artifact_issues = []
        
        # Check if .env files would be included
        env_files = [f for f in results["sensitive_files"] if '.env' in f]
        if env_files:
            artifact_issues.append(f"🚨 {len(env_files)} .env files would be shared!")
            
        # Check for other sensitive patterns
        key_files = [f for f in results["sensitive_files"] if any(p in f for p in ['.key', '.pem', 'secret'])]
        if key_files:
            artifact_issues.append(f"🔑 {len(key_files)} key/secret files would be shared!")
            
        results["artifact_safety"] = {
            "safe_to_share": len(artifact_issues) == 0,
            "issues": artifact_issues
        }
        
        return results


def main():
    """Main entry point."""
    print("GITIGNORE SECURITY ANALYZER")
    print("="*60)
    
    analyzer = GitignoreAnalyzer()
    
    # Analyze indexed files
    print("\n📊 Analyzing indexed files...")
    results = analyzer.analyze_indexed_files()
    
    print(f"\n📁 Total indexed files: {results['total_indexed']}")
    print(f"✅ Safe files: {results['safe_files']}")
    print(f"⚠️  Should be ignored: {len(results['should_be_ignored'])}")
    print(f"🚨 Sensitive files: {len(results['sensitive_files'])}")
    
    # Show examples
    if results["should_be_ignored"]:
        print("\n⚠️  Examples of files that should be ignored:")
        for f in results["should_be_ignored"][:5]:
            print(f"   - {f}")
            
    if results["sensitive_files"]:
        print("\n🚨 Examples of sensitive files:")
        for f in results["sensitive_files"][:5]:
            print(f"   - {f}")
            
    # Check artifact safety
    print("\n🔒 Checking index artifact safety...")
    artifact_results = analyzer.check_index_artifact_contents()
    
    if artifact_results["artifact_safety"]["safe_to_share"]:
        print("✅ Index artifacts appear safe to share")
    else:
        print("❌ Security issues found in index artifacts:")
        for issue in artifact_results["artifact_safety"]["issues"]:
            print(f"   {issue}")
            
    # Recommendations
    print("\n📋 Recommendations:")
    for rec in results["recommendations"]:
        print(f"   {rec}")
        
    # Save detailed report
    report_path = Path("gitignore_security_report.json")
    with open(report_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n📄 Detailed report saved to: {report_path}")


if __name__ == "__main__":
    main()