"""Caching and data manifest utilities."""

import hashlib
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class DataManifest:
    """Manages data provenance manifest (data_manifest.yml).

    Tracks:
    - Source URLs
    - Download timestamps
    - File hashes
    - Notes/metadata
    """

    def __init__(self, manifest_path: Path):
        """Initialize manifest manager.

        Args:
            manifest_path: Path to data_manifest.yml file
        """
        self.manifest_path = manifest_path
        self._data: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        """Load manifest from disk or create empty."""
        if self.manifest_path.exists():
            with open(self.manifest_path) as f:
                return yaml.safe_load(f) or {"files": {}}
        return {"files": {}}

    def _save(self) -> None:
        """Save manifest to disk."""
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.manifest_path, "w") as f:
            yaml.dump(self._data, f, default_flow_style=False, sort_keys=False)

    def record(
        self,
        file_key: str,
        source_url: str,
        file_path: Path,
        notes: str = "",
    ) -> None:
        """Record a downloaded file in the manifest.

        Args:
            file_key: Unique identifier for this file entry
            source_url: URL the file was downloaded from
            file_path: Local path to the downloaded file
            notes: Optional notes about the file
        """
        file_hash = self._compute_hash(file_path) if file_path.exists() else "N/A"

        self._data["files"][file_key] = {
            "source_url": source_url,
            "download_timestamp": datetime.now(UTC).isoformat(),
            "file_hash": file_hash,
            "local_path": str(file_path),
            "notes": notes,
        }
        self._save()
        logger.info(f"Manifest: recorded {file_key}")

    def get_entry(self, file_key: str) -> dict[str, Any] | None:
        """Get manifest entry for a file key."""
        return self._data.get("files", {}).get(file_key)

    def has_entry(self, file_key: str) -> bool:
        """Check if file key exists in manifest."""
        return file_key in self._data.get("files", {})

    @staticmethod
    def _compute_hash(file_path: Path, algorithm: str = "sha256") -> str:
        """Compute hash of a file.

        Args:
            file_path: Path to file
            algorithm: Hash algorithm (default: sha256)

        Returns:
            Hex digest of file hash
        """
        hasher = hashlib.new(algorithm)
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()


class CacheManager:
    """Manages file caching with manifest integration.

    Provides:
    - Check if cached file exists and is fresh
    - Store downloaded content with manifest logging
    - Retrieve cached content
    """

    def __init__(self, cache_dir: Path, manifest: DataManifest):
        """Initialize cache manager.

        Args:
            cache_dir: Directory for cached files
            manifest: DataManifest instance for provenance tracking
        """
        self.cache_dir = cache_dir
        self.manifest = manifest
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_cache_path(self, key: str) -> Path:
        """Get local cache file path for a key.

        Args:
            key: Unique cache key (used as filename)

        Returns:
            Path to cached file
        """
        # Sanitize key for filesystem
        safe_key = key.replace("/", "_").replace(":", "_").replace("?", "_")
        return self.cache_dir / safe_key

    def has_cached(self, key: str) -> bool:
        """Check if a fresh cached file exists.

        Args:
            key: Cache key

        Returns:
            True if cached file exists
        """
        return self.get_cache_path(key).exists()

    def store(
        self,
        key: str,
        content: bytes | str,
        source_url: str,
        notes: str = "",
    ) -> Path:
        """Store content in cache and record in manifest.

        Args:
            key: Cache key
            content: Content to cache (bytes or string)
            source_url: URL content was downloaded from
            notes: Optional notes for manifest

        Returns:
            Path to cached file
        """
        cache_path = self.get_cache_path(key)

        # Write content
        if isinstance(content, str):
            cache_path.write_text(content)
        else:
            cache_path.write_bytes(content)

        # Record in manifest
        self.manifest.record(key, source_url, cache_path, notes)
        logger.info(f"Cached: {key} -> {cache_path}")

        return cache_path

    def load_text(self, key: str) -> str | None:
        """Load cached text content.

        Args:
            key: Cache key

        Returns:
            Cached text content or None if not cached
        """
        cache_path = self.get_cache_path(key)
        if cache_path.exists():
            return cache_path.read_text()
        return None

    def load_bytes(self, key: str) -> bytes | None:
        """Load cached binary content.

        Args:
            key: Cache key

        Returns:
            Cached bytes or None if not cached
        """
        cache_path = self.get_cache_path(key)
        if cache_path.exists():
            return cache_path.read_bytes()
        return None
