#!/usr/bin/env python3
"""Find populated indexes."""

import sqlite3
from pathlib import Path

indexes_path = Path(".indexes")
populated = []

for repo_dir in indexes_path.iterdir():
    if repo_dir.is_dir():
        db_path = repo_dir / "current.db"
        if db_path.exists():
            try:
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()
                
                # Check file count
                cursor.execute("SELECT COUNT(*) FROM files WHERE language IS NOT NULL")
                count = cursor.fetchone()[0]
                
                if count > 0:
                    # Get language stats
                    cursor.execute("""
                        SELECT language, COUNT(*) as cnt 
                        FROM files 
                        WHERE language IS NOT NULL 
                        GROUP BY language 
                        ORDER BY cnt DESC 
                        LIMIT 5
                    """)
                    languages = cursor.fetchall()
                    
                    populated.append({
                        "repo_id": repo_dir.name,
                        "file_count": count,
                        "top_languages": languages
                    })
                    
                conn.close()
            except Exception as e:
                pass

# Sort by file count
populated.sort(key=lambda x: x["file_count"], reverse=True)

print("\nPopulated indexes found:")
print("="*80)

for idx in populated[:10]:  # Show top 10
    print(f"\nRepo ID: {idx['repo_id']}")
    print(f"Files: {idx['file_count']}")
    print("Top languages:")
    for lang, count in idx['top_languages']:
        print(f"  - {lang}: {count} files")

print(f"\nTotal populated indexes: {len(populated)}")