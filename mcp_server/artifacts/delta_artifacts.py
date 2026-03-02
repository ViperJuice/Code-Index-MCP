"""Delta artifact generation and apply helpers."""

from __future__ import annotations

import hashlib
import io
import json
import tarfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


@dataclass
class DeltaOperation:
    """A single delta operation for file synchronization."""

    op: str
    path: str
    source: str = ""


@dataclass
class DeltaManifest:
    """Delta metadata connecting base and target commits."""

    base_commit: str
    target_commit: str
    operations: List[DeltaOperation]
    checksums: Dict[str, str]

    def to_dict(self) -> Dict[str, object]:
        return {
            "base_commit": self.base_commit,
            "target_commit": self.target_commit,
            "operations": [op.__dict__ for op in self.operations],
            "checksums": self.checksums,
        }


def _sha256(file_path: Path) -> str:
    digest = hashlib.sha256()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_delta_manifest(
    base_dir: Path, target_dir: Path, base_commit: str, target_commit: str
) -> DeltaManifest:
    """Create manifest of file changes between base and target directories."""
    base_files = {p.relative_to(base_dir).as_posix(): p for p in base_dir.rglob("*") if p.is_file()}
    target_files = {
        p.relative_to(target_dir).as_posix(): p for p in target_dir.rglob("*") if p.is_file()
    }

    operations: List[DeltaOperation] = []
    checksums: Dict[str, str] = {}

    for rel_path in sorted(target_files):
        if rel_path not in base_files:
            operations.append(DeltaOperation(op="add", path=rel_path))
            checksums[rel_path] = _sha256(target_files[rel_path])
        else:
            old_hash = _sha256(base_files[rel_path])
            new_hash = _sha256(target_files[rel_path])
            if old_hash != new_hash:
                operations.append(DeltaOperation(op="modify", path=rel_path))
                checksums[rel_path] = new_hash

    for rel_path in sorted(base_files):
        if rel_path not in target_files:
            operations.append(DeltaOperation(op="delete", path=rel_path))

    return DeltaManifest(
        base_commit=base_commit,
        target_commit=target_commit,
        operations=operations,
        checksums=checksums,
    )


def build_delta_archive(manifest: DeltaManifest, target_dir: Path, archive_path: Path) -> Path:
    """Build tar.gz delta archive containing manifest and changed files."""
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path, "w:gz") as tar:
        payload = json.dumps(manifest.to_dict(), indent=2).encode("utf-8")
        info = tarfile.TarInfo("delta-manifest.json")
        info.size = len(payload)
        tar.addfile(info, fileobj=io.BytesIO(payload))

        for operation in manifest.operations:
            if operation.op in {"add", "modify"}:
                source = target_dir / operation.path
                if source.exists():
                    tar.add(source, arcname=f"files/{operation.path}")

    return archive_path


def apply_delta_archive(base_dir: Path, archive_path: Path) -> None:
    """Apply delta archive to base directory in place."""
    with tarfile.open(archive_path, "r:gz") as tar:
        manifest_member = tar.getmember("delta-manifest.json")
        manifest_data = json.load(tar.extractfile(manifest_member))

        operations = [DeltaOperation(**item) for item in manifest_data.get("operations", [])]
        checksums = manifest_data.get("checksums", {})

        for operation in operations:
            target = base_dir / operation.path
            if operation.op == "delete":
                if target.exists():
                    target.unlink()
                continue

            file_member = tar.getmember(f"files/{operation.path}")
            target.parent.mkdir(parents=True, exist_ok=True)
            extracted = tar.extractfile(file_member)
            if extracted is None:
                raise ValueError(f"Missing file payload for {operation.path}")
            target.write_bytes(extracted.read())

            expected = checksums.get(operation.path)
            if expected and _sha256(target) != expected:
                raise ValueError(f"Checksum mismatch applying delta for {operation.path}")
