import pytest
import asyncio
import time
import json
import logging
from fastapi import status
from concurrent.futures import ThreadPoolExecutor
from typing import List

@pytest.mark.performance
class TestApiPerformance:
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, client, test_user):
        """Test API performance under concurrent load"""
        async def make_request():
            return client.get("/api/v1/users/1")
            
        # Create test user first
        client.post("/api/v1/users/", json=test_user)
        
        # Simulate 50 concurrent requests
        tasks = [make_request() for _ in range(50)]
        start_time = time.time()
        responses = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Assert performance metrics
        total_time = end_time - start_time
        assert total_time < 5.0  # Should handle 50 requests within 5 seconds
        
        # Check response status codes
        success_responses = [r for r in responses if r.status_code == 200]
        rate_limited_responses = [r for r in responses if r.status_code == 429]
        
        # Some requests should succeed, some should be rate limited
        assert len(success_responses) > 0
        assert len(rate_limited_responses) > 0

    def test_database_performance(self, client, test_user, test_penalty):
        """Test database operation performance"""
        # Create a batch of users and penalties
        users = []
        start_time = time.time()
        
        for i in range(100):
            user_data = {
                "username": f"testuser{i}",
                "email": f"test{i}@example.com"
            }
            response = client.post("/api/v1/users/", json=user_data)
            assert response.status_code == 201
            users.append(response.json())
        
        end_time = time.time()
        batch_insert_time = end_time - start_time
        
        # Batch insert should be reasonably fast
        assert batch_insert_time < 2.0  # 100 inserts should take less than 2 seconds
        
        # Test batch read performance
        start_time = time.time()
        for user in users:
            response = client.get(f"/api/v1/users/{user['id']}")
            assert response.status_code == 200
        end_time = time.time()
        
        batch_read_time = end_time - start_time
        assert batch_read_time < 1.0  # Reading should be faster than writing

@pytest.mark.security
class TestApiSecurity:
    def test_error_message_security(self, client):
        """Test that error responses don't leak sensitive information"""
        response = client.get("/api/v1/users/999")
        assert response.status_code == 404
        error_data = response.json()
        
        # Error should not contain stack traces or system paths
        assert "Traceback" not in json.dumps(error_data)
        assert "/Users/" not in json.dumps(error_data)
        assert "sqlite" not in json.dumps(error_data)

    def test_log_security(self, client, caplog):
        """Test that logs don't contain sensitive information"""
        with caplog.at_level(logging.ERROR):
            response = client.post(
                "/api/v1/users/",
                json={"username": "test", "password": "secret123", "email": "test@example.com"}
            )
            
            # Check logs don't contain sensitive data
            log_text = json.dumps([(r.message, r.levelname) for r in caplog.records])
            assert "secret123" not in log_text
            
            # But should still contain necessary error information
            if response.status_code >= 400:
                assert "error" in log_text.lower()

    def test_rate_limit_bypass_prevention(self, client, settings):
        """Test that rate limiting can't be bypassed with different headers"""
        # Try common headers used to spoof IP addresses
        headers = [
            {"X-Forwarded-For": "1.2.3.4"},
            {"X-Real-IP": "1.2.3.4"},
            {"CF-Connecting-IP": "1.2.3.4"},
            {"True-Client-IP": "1.2.3.4"}
        ]
        
        # Exhaust rate limit
        for _ in range(settings.RATE_LIMIT_MAX_REQUESTS + 1):
            response = client.get("/api/v1/users/1")
        assert response.status_code == 429
        
        # Try each header, should still be rate limited
        for header in headers:
            response = client.get("/api/v1/users/1", headers=header)
            assert response.status_code == 429

    def test_structured_error_responses(self, client):
        """Test that error responses follow a consistent structure"""
        # Test various error scenarios
        error_cases = [
            # 404 Not Found
            ("/api/v1/users/999", "GET", None),
            # 422 Validation Error
            ("/api/v1/users/", "POST", {"invalid": "data"}),
            # 429 Rate Limit
            ("/api/v1/users/1", "GET", None, settings.RATE_LIMIT_MAX_REQUESTS + 1)
        ]
        
        for path, method, data, repeat_count in error_cases:
            if repeat_count:
                for _ in range(repeat_count):
                    if method == "GET":
                        response = client.get(path)
                    else:
                        response = client.post(path, json=data)
            else:
                if method == "GET":
                    response = client.get(path)
                else:
                    response = client.post(path, json=data)
            
            error_data = response.json()
            # All errors should have a consistent structure
            assert "detail" in error_data
            assert isinstance(error_data["detail"], (str, list))
            if response.status_code == 429:
                assert "Retry-After" in response.headers