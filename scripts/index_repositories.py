#!/usr/bin/env python3
"""
Unified repository indexing script.
This is the main entry point for indexing repositories with both SQL and semantic support.
"""

import os
import sys
import argparse
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.index_all_repos_with_mcp import main as index_with_mcp
from scripts.index_all_repos_semantic_simple import main as index_semantic_only
from scripts.create_mcp_indexes_direct import main as create_sql_only


def main():
    parser = argparse.ArgumentParser(description="Index repositories for MCP Server")
    parser.add_argument(
        "--mode",
        choices=["full", "semantic", "sql"],
        default="full",
        help="Indexing mode: full (SQL+semantic), semantic (only embeddings), sql (only BM25)"
    )
    parser.add_argument(
        "--repos",
        choices=["test", "all"],
        default="test",
        help="Which repositories to index"
    )
    parser.add_argument(
        "--no-limit",
        action="store_true",
        help="Don't limit the number of files per repository"
    )
    
    args = parser.parse_args()
    
    # Ensure environment is set up
    if os.path.exists(".env"):
        from dotenv import load_dotenv
        load_dotenv()
    
    if args.mode == "full":
        print("Running full indexing (SQL + Semantic)...")
        index_with_mcp()
    elif args.mode == "semantic":
        print("Running semantic-only indexing...")
        index_semantic_only()
    elif args.mode == "sql":
        print("Running SQL-only indexing...")
        create_sql_only()
    
    print("\nIndexing complete!")
    print("\nNote: Restart the MCP server to use the updated indexes.")


if __name__ == "__main__":
    main()