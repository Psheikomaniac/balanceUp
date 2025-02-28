import pytest
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List
import json
import logging
from fastapi import status

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
        # Create test user
        client.post("/api/v1/users/", json=test_user)
        
        # Measure bulk penalty creation performance
        penalties = [
            {**test_penalty, "reason": f"Test Penalty {i}"}
            for i in range(100)
        ]
        
        start_time = time.time()
        for penalty in penalties:
            response = client.post("/api/v1/penalties/", json=penalty)
            assert response.status_code in (201, 429)  # Account for rate limiting
        end_time = time.time()
        
        # Assert bulk operation performance
        total_time = end_time - start_time
        assert total_time < 10.0  # Should handle 100 creations within 10 seconds

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
                json={"password": "secret123", "email": "test@example.com"}
            )
            
            # Check logs don't contain sensitive data
            log_text = json.dumps([(r.message, r.levelname) for r in caplog.records])
            assert "secret123" not in log_text
            
            # But should still contain necessary error information
            if response.status_code >= 400:
                assert "error" in log_text

    def test_rate_limit_bypass_prevention(self, client, test_settings):
        """Test that rate limiting can't be bypassed with different headers"""
        headers_variations = [
            {},
            {"X-Forwarded-For": "1.2.3.4"},
            {"X-Real-IP": "1.2.3.4"},
            {"User-Agent": "Custom-Agent"}
        ]
        
        # Try to bypass rate limit with different headers
        for headers in headers_variations:
            # Make requests up to the limit
            for _ in range(test_settings.RATE_LIMIT_MAX_REQUESTS):
                client.get("/api/v1/users/1", headers=headers)
            
            # Next request should still be rate limited
            response = client.get("/api/v1/users/1", headers=headers)
            assert response.status_code == 429
            
            # Wait for rate limit to reset
            time.sleep(test_settings.RATE_LIMIT_WINDOW + 1)