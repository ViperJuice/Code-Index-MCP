#!/usr/bin/env python3
"""Test language detection from index database"""
import sqlite3
from pathlib import Path

def get_indexed_languages(db_path: str) -> dict:
    """Get languages and their file counts from the index"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    languages = {}
    for row in cursor.execute("""
        SELECT language, COUNT(*) as count 
        FROM files 
        WHERE language IS NOT NULL 
        GROUP BY language 
        ORDER BY count DESC
    """).fetchall():
        languages[row[0]] = row[1]
    
    conn.close()
    return languages

# Test with current index
db_path = "/workspaces/Code-Index-MCP/.indexes/f7b49f5d0ae0/current.db"
languages = get_indexed_languages(db_path)

print("=== Languages in current repository ===")
for lang, count in languages.items():
    print(f"{lang}: {count} files")

print(f"\nTotal languages: {len(languages)}")
print(f"Top 3 languages: {list(languages.keys())[:3]}")

# Map file extensions to plugin languages
language_map = {
    'python': 'python',
    'js': 'javascript', 
    'javascript': 'javascript',
    'ts': 'typescript',
    'typescript': 'typescript',
    'java': 'java',
    'go': 'go',
    'rust': 'rust',
    'c': 'c',
    'cpp': 'cpp',
    'c++': 'cpp',
    'cs': 'csharp',
    'csharp': 'csharp',
    'rb': 'ruby',
    'ruby': 'ruby',
    'swift': 'swift',
    'kotlin': 'kotlin',
    'kt': 'kotlin',
    'html': 'html',
    'css': 'css',
    'md': 'markdown',
    'markdown': 'markdown',
    'txt': 'plaintext',
    'text': 'plaintext'
}

# Get plugin languages needed
plugin_languages = set()
for lang in languages:
    if lang in language_map:
        plugin_languages.add(language_map[lang])

print(f"\nPlugin languages needed: {sorted(plugin_languages)}")
print(f"Number of plugins to load: {len(plugin_languages)} (vs 47 total)")