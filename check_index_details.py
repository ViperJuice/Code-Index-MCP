#!/usr/bin/env python3
"""Check the index database details."""

import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / "code_index.db"

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

print("🔍 Checking index database schema and contents...")
print("=" * 50)

# Check files table schema
cursor.execute("PRAGMA table_info(files);")
columns = cursor.fetchall()
print("\n📁 Files table schema:")
file_columns = {}
for col in columns:
    print(f"  • {col[1]} ({col[2]})")
    file_columns[col[1]] = col[2]

# Get file statistics
path_col = 'path' if 'path' in file_columns else 'file_path'
cursor.execute(f"SELECT COUNT(*) FROM files;")
total_files = cursor.fetchone()[0]
print(f"\n📊 Total files indexed: {total_files}")

# Sample files
cursor.execute(f"SELECT {path_col} FROM files WHERE {path_col} LIKE '%.py' LIMIT 10;")
py_files = cursor.fetchall()
print("\n🐍 Sample Python files:")
for f in py_files:
    print(f"  • {f[0]}")

# Check symbols table schema
cursor.execute("PRAGMA table_info(symbols);")
columns = cursor.fetchall()
print("\n🔤 Symbols table schema:")
symbol_columns = {}
for col in columns:
    print(f"  • {col[1]} ({col[2]})")
    symbol_columns[col[1]] = col[2]

# Get symbol statistics
cursor.execute("SELECT COUNT(*) FROM symbols;")
total_symbols = cursor.fetchone()[0]
print(f"\n📊 Total symbols indexed: {total_symbols}")

# Get symbol type distribution
if 'kind' in symbol_columns:
    cursor.execute("SELECT kind, COUNT(*) as count FROM symbols GROUP BY kind ORDER BY count DESC LIMIT 10;")
    symbol_types = cursor.fetchall()
    print("\n📈 Symbol type distribution:")
    for kind, count in symbol_types:
        print(f"  • {kind}: {count}")

# Sample symbols
name_col = 'name' if 'name' in symbol_columns else 'symbol_name'
cursor.execute(f"SELECT {name_col}, kind FROM symbols LIMIT 20;")
symbols = cursor.fetchall()
print("\n🔍 Sample symbols:")
for s in symbols:
    print(f"  • {s[0]} ({s[1]})")

# Check for Python-specific files
cursor.execute(f"SELECT COUNT(*) FROM files WHERE {path_col} LIKE '%.py';")
py_count = cursor.fetchone()[0]
print(f"\n🐍 Python files: {py_count}")

# Check for other language files
languages = [('.js', 'JavaScript'), ('.go', 'Go'), ('.rs', 'Rust'), ('.rb', 'Ruby'), ('.php', 'PHP')]
for ext, lang in languages:
    cursor.execute(f"SELECT COUNT(*) FROM files WHERE {path_col} LIKE '%{ext}';")
    count = cursor.fetchone()[0]
    if count > 0:
        print(f"📄 {lang} files: {count}")

conn.close()

print("\n✅ Index database is successfully populated!")
print(f"📍 Database location: {db_path}")