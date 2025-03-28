"""
Custom exceptions for the application's security and validation features.
"""
from typing import Optional, Any

class BaseAppException(Exception):
    """Base exception class for the application"""
    def __init__(self, message: str, status_code: int = 400, details: Optional[Any] = None):
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)

class FileValidationError(BaseAppException):
    """Raised when file validation fails"""
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message=message, status_code=400, details=details)

class InputValidationError(BaseAppException):
    """Raised when input validation fails"""
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message=message, status_code=400, details=details)

class SecurityError(BaseAppException):
    """Raised when a security check fails"""
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message=message, status_code=403, details=details)

class RateLimitExceededError(BaseAppException):
    """Raised when rate limit is exceeded"""
    def __init__(self, message: str = "Rate limit exceeded", details: Optional[Any] = None):
        super().__init__(message=message, status_code=429, details=details)

class AuthenticationError(BaseAppException):
    """Raised when authentication fails"""
    def __init__(self, message: str = "Authentication failed", details: Optional[Any] = None):
        super().__init__(message=message, status_code=401, details=details)

class AuthorizationError(BaseAppException):
    """Raised when authorization fails"""
    def __init__(self, message: str = "Not authorized", details: Optional[Any] = None):
        super().__init__(message=message, status_code=403, details=details)

class ResourceNotFoundError(BaseAppException):
    """Raised when a requested resource is not found"""
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message=message, status_code=404, details=details)

class DatabaseError(BaseAppException):
    """Raised when a database operation fails"""
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message=message, status_code=500, details=details)