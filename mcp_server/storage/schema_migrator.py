"""Schema migration support for artifact extracted directories."""

from pathlib import Path
from typing import TYPE_CHECKING

from mcp_server.core.errors import ArtifactError

if TYPE_CHECKING:
    from mcp_server.storage.sqlite_store import SQLiteStore


class UnknownSchemaVersionError(ArtifactError):
    """Raised when an artifact carries a schema version this tool doesn't recognize."""


class SchemaMigrationError(ArtifactError):
    """Raised when a known migration step fails during execution."""


class SchemaMigrator:
    SUPPORTED_VERSIONS: tuple = ("1", "2")
    CURRENT_VERSION: str = "2"

    def __init__(self, store: "SQLiteStore") -> None:
        self._store = store

    def is_known(self, version: str) -> bool:
        return version in self.SUPPORTED_VERSIONS

    def migrate_artifact(
        self,
        extracted_dir: Path,
        from_version: str,
        to_version: str,
    ) -> Path:
        """Migrate extracted_dir from from_version to to_version in place.

        Equal versions → no-op. Older known → run ordered migrations.
        Unknown version (either end) → raise UnknownSchemaVersionError.
        """
        if not self.is_known(from_version):
            raise UnknownSchemaVersionError(
                f"Artifact schema version {from_version!r} is not supported by this tool"
            )
        if not self.is_known(to_version):
            raise UnknownSchemaVersionError(
                f"Target schema version {to_version!r} is not supported by this tool"
            )
        if from_version == to_version:
            return extracted_dir

        # Walk the ordered chain from from_version up to to_version
        chain = list(self.SUPPORTED_VERSIONS)
        try:
            start = chain.index(from_version)
            end = chain.index(to_version)
        except ValueError as exc:
            raise UnknownSchemaVersionError(str(exc)) from exc

        if start >= end:
            # Downgrade not supported; treat as unknown path
            raise UnknownSchemaVersionError(
                f"Cannot downgrade schema from {from_version!r} to {to_version!r}"
            )

        current_dir = extracted_dir
        for i in range(start, end):
            step_from = chain[i]
            step_to = chain[i + 1]
            method_name = f"_migrate_{step_from}_to_{step_to}"
            method = getattr(self, method_name, None)
            if method is None:
                raise SchemaMigrationError(
                    f"No migration handler for {step_from!r} → {step_to!r}"
                )
            try:
                current_dir = method(current_dir)
            except SchemaMigrationError:
                raise
            except Exception as exc:
                raise SchemaMigrationError(
                    f"Migration {step_from!r} → {step_to!r} failed: {exc}"
                ) from exc

        return current_dir

    def _migrate_1_to_2(self, extracted_dir: Path) -> Path:
        """Apply schema 1→2 migration to the extracted artifact directory.

        Schema v2 added the schema_version table; for artifact dirs, this is
        a metadata-only bump — no file content changes are required.
        """
        return extracted_dir
