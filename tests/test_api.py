"""
Integration tests for FastAPI endpoints.
Uses TestClient — no real Azure credentials required for structure tests.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app

client = TestClient(app)


def test_health_endpoint():
    """Health check should always respond."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "services" in data
    assert "version" in data
    # All 7 services should be listed
    assert len(data["services"]) == 7


def test_api_info_endpoint():
    """API info should return AI-102 coverage."""
    response = client.get("/api/v1/info")
    assert response.status_code == 200
    data = response.json()
    assert "ai102_coverage" in data
    coverage = data["ai102_coverage"]
    # All 7 AI services should be documented
    assert "document_intelligence" in coverage
    assert "ai_language" in coverage
    assert "azure_openai" in coverage
    assert "computer_vision" in coverage
    assert "translator" in coverage
    assert "content_safety" in coverage
    assert "ai_search" in coverage


def test_docs_available():
    """Swagger UI should be accessible."""
    response = client.get("/docs")
    assert response.status_code == 200


def test_redoc_available():
    """ReDoc should be accessible."""
    response = client.get("/redoc")
    assert response.status_code == 200


def test_list_document_models():
    """Document models list should return all prebuilt models."""
    with patch("app.routers.documents.DocumentIntelligenceService") as MockService:
        mock_instance = MagicMock()
        mock_instance.list_models.return_value = [
            {"model_id": "prebuilt-read", "description": "Extract text"},
            {"model_id": "prebuilt-invoice", "description": "Extract invoice fields"},
        ]
        MockService.return_value = mock_instance

        response = client.get("/api/v1/documents/models")
        assert response.status_code == 200
