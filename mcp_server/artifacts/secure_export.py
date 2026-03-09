"""Secure index export with gitignore filtering."""

from __future__ import annotations

import fnmatch
import json
import shutil
import sqlite3
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple


class SecureIndexExporter:
    """Export index artifacts with gitignore filtering."""

    def __init__(self) -> None:
        self.gitignore_patterns = self._load_gitignore_patterns()
        self.mcp_ignore_patterns = self._load_mcp_ignore_patterns()
        self.all_patterns = self.gitignore_patterns + self.mcp_ignore_patterns

    def _load_gitignore_patterns(self) -> List[str]:
        patterns = []
        gitignore_path = Path(".gitignore")

        if gitignore_path.exists():
            for line in gitignore_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and not line.startswith("!"):
                    patterns.append(line)

        return patterns

    def _load_mcp_ignore_patterns(self) -> List[str]:
        ignore_path = Path(".mcp-index-ignore")
        default_patterns = [
            "*.env",
            ".env*",
            "*.key",
            "*.pem",
            "*secret*",
            "*password*",
            ".aws/*",
            ".ssh/*",
            "node_modules/*",
            "__pycache__/*",
            "*.pyc",
        ]

        if ignore_path.exists():
            patterns = []
            for line in ignore_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.append(line)
            return patterns

        return default_patterns

    def _should_exclude(self, file_path: str) -> bool:
        path = Path(file_path)

        for pattern in self.all_patterns:
            if pattern.endswith("/"):
                if any(part == pattern[:-1] for part in path.parts):
                    return True
            elif fnmatch.fnmatch(str(path), pattern) or fnmatch.fnmatch(
                path.name, pattern
            ):
                return True

        return False

    def create_filtered_database(
        self, source_db: str, target_db: str
    ) -> Tuple[int, int]:
        shutil.copy2(source_db, target_db)

        conn = sqlite3.connect(target_db)
        cursor = conn.cursor()
        excluded_count = 0
        total_count = 0

        try:
            try:
                cursor.execute(
                    "SELECT id, relative_path FROM files WHERE relative_path IS NOT NULL"
                )
                files = cursor.fetchall()
            except sqlite3.OperationalError:
                cursor.execute("SELECT id, path FROM files")
                files = cursor.fetchall()

            total_count = len(files)
            ids_to_delete = []
            excluded_files = []

            for file_id, file_path in files:
                if self._should_exclude(file_path):
                    ids_to_delete.append(file_id)
                    excluded_files.append(file_path)
                    excluded_count += 1

            if ids_to_delete:
                placeholders = ",".join("?" * len(ids_to_delete))
                cursor.execute(
                    f"DELETE FROM files WHERE id IN ({placeholders})", ids_to_delete
                )
                cursor.execute(
                    f"DELETE FROM symbols WHERE file_id IN ({placeholders})",
                    ids_to_delete,
                )
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='imports'"
                )
                if cursor.fetchone():
                    cursor.execute(
                        f"DELETE FROM imports WHERE file_id IN ({placeholders})",
                        ids_to_delete,
                    )

            cursor.execute("VACUUM")
            conn.commit()

            if excluded_files:
                log_path = Path("excluded_files.log")
                with log_path.open("w", encoding="utf-8") as handle:
                    handle.write(
                        f"Excluded {len(excluded_files)} files from index export:\n\n"
                    )
                    for file_path in sorted(excluded_files):
                        handle.write(f"{file_path}\n")
        finally:
            conn.close()

        return total_count - excluded_count, excluded_count

    def create_secure_archive(
        self, output_path: str = "secure_index_archive.tar.gz"
    ) -> Dict[str, Any]:
        stats: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "files_included": 0,
            "files_excluded": 0,
            "archive_size": 0,
            "components": [],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            source_db = Path("code_index.db")
            if source_db.exists():
                target_db = temp_path / "code_index.db"
                included, excluded = self.create_filtered_database(
                    str(source_db), str(target_db)
                )
                stats["files_included"] = included
                stats["files_excluded"] = excluded
                stats["components"].append("code_index.db")

            vector_dir = Path("vector_index.qdrant")
            if vector_dir.exists():
                shutil.copytree(vector_dir, temp_path / "vector_index.qdrant")
                stats["components"].append("vector_index.qdrant")

            metadata_path = Path(".index_metadata.json")
            if metadata_path.exists():
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                metadata["security"] = {
                    "filtered": True,
                    "excluded_patterns": len(self.all_patterns),
                    "export_timestamp": stats["timestamp"],
                    "files_excluded": stats["files_excluded"],
                }
                (temp_path / ".index_metadata.json").write_text(
                    json.dumps(metadata, indent=2), encoding="utf-8"
                )
                stats["components"].append(".index_metadata.json")

            with tarfile.open(output_path, "w:gz") as tar:
                for item in temp_path.iterdir():
                    tar.add(item, arcname=item.name)

            archive_path = Path(output_path)
            stats["archive_size"] = archive_path.stat().st_size

        return stats
