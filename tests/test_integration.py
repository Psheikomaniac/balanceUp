import pytest
import time
from fastapi import status
from app.database import crud

@pytest.mark.integration
class TestUserEndpoints:
    def test_create_user(self, client, test_user):
        """Test user creation endpoint"""
        response = client.post(
            "/api/v1/users/",
            json=test_user
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == test_user["username"]
        assert "id" in data

    def test_get_user(self, client, test_user):
        """Test user retrieval endpoint"""
        # First create a user
        create_response = client.post("/api/v1/users/", json=test_user)
        user_id = create_response.json()["id"]
        
        # Then retrieve it
        response = client.get(f"/api/v1/users/{user_id}")
        assert response.status_code == 200
        assert response.json()["username"] == test_user["username"]

@pytest.mark.integration
class TestPenaltyEndpoints:
    def test_create_penalty(self, client, test_penalty, test_user):
        """Test penalty creation endpoint"""
        # First ensure user exists
        client.post("/api/v1/users/", json=test_user)
        
        response = client.post(
            "/api/v1/penalties/",
            json=test_penalty
        )
        assert response.status_code == 201
        data = response.json()
        assert data["amount"] == test_penalty["amount"]
        assert data["user_id"] == test_penalty["user_id"]

    def test_get_user_penalties(self, client, test_penalty, test_user):
        """Test retrieving penalties for a user"""
        # Create user and penalty
        client.post("/api/v1/users/", json=test_user)
        client.post("/api/v1/penalties/", json=test_penalty)
        
        response = client.get(f"/api/v1/penalties/user/{test_user['id']}")
        assert response.status_code == 200
        penalties = response.json()
        assert len(penalties) > 0
        assert penalties[0]["user_id"] == test_user["id"]

@pytest.mark.integration
class TestRateLimiting:
    def test_rate_limit_exceeded(self, client, test_settings):
        """Test rate limiting middleware"""
        # Make requests up to the limit
        for _ in range(test_settings.RATE_LIMIT_MAX_REQUESTS):
            response = client.get("/api/v1/users/1")
            assert response.status_code != 429
        
        # Next request should be rate limited
        response = client.get("/api/v1/users/1")
        assert response.status_code == 429
        assert "Rate limit exceeded" in response.json()["error"]
        
        # Wait for rate limit window to reset
        time.sleep(test_settings.RATE_LIMIT_WINDOW + 1)
        response = client.get("/api/v1/users/1")
        assert response.status_code != 429

@pytest.mark.integration
class TestErrorHandling:
    def test_not_found_handling(self, client):
        """Test 404 error handling"""
        response = client.get("/api/v1/users/999")
        assert response.status_code == 404
        error_response = response.json()
        assert "error" in error_response
        assert error_response["error"] == "Resource not found"

    def test_validation_error_handling(self, client):
        """Test validation error handling"""
        response = client.post(
            "/api/v1/users/",
            json={"invalid_field": "value"}
        )
        assert response.status_code == 422
        error_response = response.json()
        assert "error" in error_response
        assert "Validation error" in error_response["error"]