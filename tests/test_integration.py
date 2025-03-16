import pytest
import time
from fastapi import status
from fastapi.testclient import TestClient
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
        assert data["email"] == test_user["email"]
        assert data["username"] == test_user["username"]

    def test_get_user(self, client, test_user):
        """Test user retrieval endpoint"""
        # First create a user
        create_response = client.post("/api/v1/users/", json=test_user)
        assert create_response.status_code == 201
        user_id = create_response.json()["id"]

        # Then retrieve it
        response = client.get(f"/api/v1/users/{user_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user["email"]

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
        assert data["reason"] == test_penalty["reason"]

    def test_get_user_penalties(self, client, test_penalty, test_user):
        """Test retrieving penalties for a user"""
        # Create user and penalty
        client.post("/api/v1/users/", json=test_user)
        client.post("/api/v1/penalties/", json=test_penalty)

        response = client.get(f"/api/v1/users/{test_user['id']}/penalties")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert data[0]["amount"] == test_penalty["amount"]

@pytest.mark.integration
class TestRateLimiting:
    def test_basic_rate_limiting(self, client, settings):
        """Test that rate limiting blocks excessive requests"""
        # Make requests up to the limit
        for _ in range(settings.RATE_LIMIT_MAX_REQUESTS):
            response = client.get("/api/v1/users/1")
            assert response.status_code in [200, 404]  # Either found or not found is fine
            
        # Next request should be rate limited
        response = client.get("/api/v1/users/1")
        assert response.status_code == 429
        assert "Retry-After" in response.headers
        
    def test_rate_limit_reset(self, client, settings):
        """Test that rate limits reset after the window"""
        # Make requests up to the limit
        for _ in range(settings.RATE_LIMIT_MAX_REQUESTS):
            client.get("/api/v1/users/1")
            
        # Wait for the rate limit window to expire
        time.sleep(settings.RATE_LIMIT_WINDOW)
        
        # Should be able to make requests again
        response = client.get("/api/v1/users/1")
        assert response.status_code in [200, 404]
        
    def test_rate_limit_by_ip(self, client, settings):
        """Test that rate limits are applied per IP"""
        # Make requests with different IP headers
        headers1 = {"X-Forwarded-For": "1.2.3.4"}
        headers2 = {"X-Forwarded-For": "5.6.7.8"}
        
        # Exhaust rate limit for first IP
        for _ in range(settings.RATE_LIMIT_MAX_REQUESTS + 1):
            response = client.get("/api/v1/users/1", headers=headers1)
        assert response.status_code == 429
        
        # Second IP should still work
        response = client.get("/api/v1/users/1", headers=headers2)
        assert response.status_code in [200, 404]

@pytest.mark.integration
class TestErrorHandling:
    def test_not_found_handling(self, client):
        """Test 404 error handling"""
        response = client.get("/api/v1/users/999")
        assert response.status_code == 404
        error_data = response.json()
        assert "detail" in error_data
        assert error_data["detail"] == "Not Found"

    def test_validation_error_handling(self, client):
        """Test validation error handling"""
        response = client.post(
            "/api/v1/users/",
            json={"invalid_field": "value"}
        )
        assert response.status_code == 422
        error_data = response.json()
        assert "detail" in error_data  # FastAPI's default validation error format
        assert isinstance(error_data["detail"], list)
        assert len(error_data["detail"]) > 0