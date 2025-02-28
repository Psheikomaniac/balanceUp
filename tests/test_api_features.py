import pytest
from fastapi.testclient import TestClient
from main import app
import logging
from app.config.settings import get_settings
from app.errors.exceptions import ValidationError

client = TestClient(app)
settings = get_settings()

def test_rate_limiting():
    """Test that rate limiting is working"""
    # Make requests up to the limit
    for _ in range(settings.RATE_LIMIT_MAX_REQUESTS):
        response = client.get("/api/v1/users")
        assert response.status_code != 429
    
    # Next request should be rate limited
    response = client.get("/api/v1/users")
    assert response.status_code == 429
    assert "Rate limit exceeded" in response.text

def test_error_handling():
    """Test custom error handling"""
    # Test 404 error
    response = client.get("/api/v1/nonexistent")
    assert response.status_code == 404
    assert response.json().get("error") is not None

    # Test validation error
    response = client.post("/api/v1/users", json={})
    assert response.status_code == 422
    assert "Validation error" in response.text

def test_structured_logging(caplog):
    """Test that logging is properly structured"""
    with caplog.at_level(logging.INFO):
        client.get("/api/v1/users")
        
    # Verify log structure
    assert len(caplog.records) > 0
    log_record = caplog.records[0]
    assert hasattr(log_record, "level")
    assert hasattr(log_record, "timestamp")
    assert hasattr(log_record, "logger")