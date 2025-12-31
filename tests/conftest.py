"""Pytest configuration and fixtures."""

import os
import tempfile
from pathlib import Path

import pytest

from banklab.config import Config


@pytest.fixture
def temp_data_dir():
    """Create a temporary data directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_config(temp_data_dir):
    """Create a test configuration with temp directories."""
    config = Config()
    config.data_dir = temp_data_dir
    config.tickers = ["JPM", "MS"]
    config.ensure_dirs()
    return config


@pytest.fixture
def mock_fred_api_key(monkeypatch):
    """Set a mock FRED API key for testing."""
    monkeypatch.setenv("FRED_API_KEY", "test_api_key_12345")


# Skip network tests if running in CI without network
def pytest_configure(config):
    """Add custom markers."""
    config.addinivalue_line("markers", "network: marks tests as requiring network access")


def pytest_collection_modifyitems(config, items):
    """Skip network tests if SKIP_NETWORK_TESTS is set."""
    if os.getenv("SKIP_NETWORK_TESTS"):
        skip_network = pytest.mark.skip(reason="SKIP_NETWORK_TESTS is set")
        for item in items:
            if "network" in item.keywords:
                item.add_marker(skip_network)
