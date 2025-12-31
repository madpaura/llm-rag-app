"""
Pytest configuration and fixtures for PDF extraction tests.
"""
import pytest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="session")
def test_data_dir(tmp_path_factory):
    """Create a temporary directory for test data."""
    return tmp_path_factory.mktemp("test_data")


@pytest.fixture
def mock_settings(monkeypatch, tmp_path):
    """Mock settings for testing."""
    monkeypatch.setattr("services.ingestion_service.settings.UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setattr("services.ingestion_service.settings.CHUNK_SIZE", 1000)
    monkeypatch.setattr("services.ingestion_service.settings.CHUNK_OVERLAP", 200)
    return tmp_path
