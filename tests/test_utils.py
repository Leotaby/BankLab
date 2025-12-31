"""Tests for utility modules."""

import pytest
import yaml

from banklab.utils.cache import CacheManager, DataManifest
from banklab.utils.http import PoliteRequester


class TestDataManifest:
    """Tests for DataManifest functionality."""

    def test_creates_new_manifest(self, temp_data_dir):
        """Test that new manifest is created if doesn't exist."""
        manifest_path = temp_data_dir / "manifest.yml"
        manifest = DataManifest(manifest_path)

        assert manifest._data == {"files": {}}

    def test_record_creates_entry(self, temp_data_dir):
        """Test that record creates proper manifest entry."""
        manifest_path = temp_data_dir / "manifest.yml"
        manifest = DataManifest(manifest_path)

        # Create a test file
        test_file = temp_data_dir / "test.txt"
        test_file.write_text("hello world")

        manifest.record(
            file_key="test_key",
            source_url="https://example.com/data.txt",
            file_path=test_file,
            notes="Test file",
        )

        # Check entry exists
        entry = manifest.get_entry("test_key")
        assert entry is not None
        assert entry["source_url"] == "https://example.com/data.txt"
        assert entry["notes"] == "Test file"
        assert "download_timestamp" in entry
        assert "file_hash" in entry

    def test_manifest_persists_to_disk(self, temp_data_dir):
        """Test that manifest is saved to disk."""
        manifest_path = temp_data_dir / "manifest.yml"
        manifest = DataManifest(manifest_path)

        test_file = temp_data_dir / "test.txt"
        test_file.write_text("hello")

        manifest.record("key1", "http://example.com", test_file)

        # Read back from disk
        with open(manifest_path) as f:
            data = yaml.safe_load(f)

        assert "key1" in data["files"]

    def test_has_entry(self, temp_data_dir):
        """Test has_entry method."""
        manifest_path = temp_data_dir / "manifest.yml"
        manifest = DataManifest(manifest_path)

        test_file = temp_data_dir / "test.txt"
        test_file.write_text("hello")

        manifest.record("exists", "http://example.com", test_file)

        assert manifest.has_entry("exists")
        assert not manifest.has_entry("does_not_exist")

    def test_compute_hash_deterministic(self, temp_data_dir):
        """Test that file hash is deterministic."""
        test_file = temp_data_dir / "test.txt"
        test_file.write_text("hello world")

        hash1 = DataManifest._compute_hash(test_file)
        hash2 = DataManifest._compute_hash(test_file)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex digest


class TestCacheManager:
    """Tests for CacheManager functionality."""

    def test_store_and_load_text(self, temp_data_dir):
        """Test storing and loading text content."""
        manifest = DataManifest(temp_data_dir / "manifest.yml")
        cache = CacheManager(temp_data_dir / "cache", manifest)

        cache.store("test.txt", "hello world", "http://example.com")

        loaded = cache.load_text("test.txt")
        assert loaded == "hello world"

    def test_store_and_load_bytes(self, temp_data_dir):
        """Test storing and loading binary content."""
        manifest = DataManifest(temp_data_dir / "manifest.yml")
        cache = CacheManager(temp_data_dir / "cache", manifest)

        binary_data = b"\x00\x01\x02\x03"
        cache.store("test.bin", binary_data, "http://example.com")

        loaded = cache.load_bytes("test.bin")
        assert loaded == binary_data

    def test_has_cached(self, temp_data_dir):
        """Test checking if file is cached."""
        manifest = DataManifest(temp_data_dir / "manifest.yml")
        cache = CacheManager(temp_data_dir / "cache", manifest)

        assert not cache.has_cached("test.txt")

        cache.store("test.txt", "hello", "http://example.com")

        assert cache.has_cached("test.txt")

    def test_cache_key_sanitization(self, temp_data_dir):
        """Test that cache keys with special chars are sanitized."""
        manifest = DataManifest(temp_data_dir / "manifest.yml")
        cache = CacheManager(temp_data_dir / "cache", manifest)

        # Key with special characters
        key = "http://example.com/path?param=value"
        cache.store(key, "data", "http://example.com")

        # Should be able to load it back
        assert cache.load_text(key) == "data"

        # Path should not contain special chars
        cache_path = cache.get_cache_path(key)
        assert "/" not in cache_path.name
        assert "?" not in cache_path.name

    def test_load_nonexistent_returns_none(self, temp_data_dir):
        """Test that loading nonexistent file returns None."""
        manifest = DataManifest(temp_data_dir / "manifest.yml")
        cache = CacheManager(temp_data_dir / "cache", manifest)

        assert cache.load_text("does_not_exist") is None
        assert cache.load_bytes("does_not_exist") is None


class TestPoliteRequester:
    """Tests for PoliteRequester functionality."""

    def test_user_agent_header_set(self):
        """Test that User-Agent header is set."""
        requester = PoliteRequester(user_agent="Test Agent")

        assert requester.session.headers["User-Agent"] == "Test Agent"

    def test_default_headers_set(self):
        """Test that default headers are properly configured."""
        requester = PoliteRequester(user_agent="Test Agent")

        headers = requester.session.headers
        assert "Accept" in headers
        assert "Accept-Encoding" in headers

    @pytest.mark.network
    def test_get_json_success(self):
        """Test successful JSON request."""
        requester = PoliteRequester(user_agent="BankLab Tests")

        # Use httpbin for testing
        data = requester.get_json("https://httpbin.org/json")

        assert isinstance(data, dict)

    @pytest.mark.network
    def test_get_text_success(self):
        """Test successful text request."""
        requester = PoliteRequester(user_agent="BankLab Tests")

        text = requester.get_text("https://httpbin.org/robots.txt")

        assert isinstance(text, str)
        assert len(text) > 0
