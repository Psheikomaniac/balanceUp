from fastapi import HTTPException

class BaseAPIException(HTTPException):
    """Base exception for all API errors"""
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)

class ValidationError(BaseAPIException):
    """Raised when request validation fails"""
    def __init__(self, detail: str):
        super().__init__(status_code=422, detail=detail)

class AuthenticationError(BaseAPIException):
    """Raised when authentication fails"""
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(status_code=401, detail=detail)

class NotFoundError(BaseAPIException):
    """Raised when a requested resource is not found"""
    def __init__(self, detail: str):
        super().__init__(status_code=404, detail=detail)

class RateLimitError(BaseAPIException):
    """Raised when rate limit is exceeded"""
    def __init__(self, detail: str = "Rate limit exceeded"):
        super().__init__(status_code=429, detail=detail)