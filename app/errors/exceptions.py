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

class ResourceNotFoundException(Exception):
    """Exception raised when a requested resource is not found"""
    def __init__(self, resource_type: str, resource_id: str = None):
        message = f"{resource_type} not found"
        if resource_id:
            message += f" with ID: {resource_id}"
        super().__init__(message)


class DuplicateResourceException(Exception):
    """Exception raised when attempting to create a resource that already exists"""
    def __init__(self, resource_type: str, identifier: str = None):
        message = f"{resource_type} already exists"
        if identifier:
            message += f" with identifier: {identifier}"
        super().__init__(message)


class UnauthorizedException(Exception):
    """Exception raised when a user is not authorized to perform an action"""
    def __init__(self, message: str = "Unauthorized access"):
        super().__init__(message)


class ValidationException(Exception):
    """Exception raised when data validation fails"""
    def __init__(self, message: str, details: dict = None):
        self.details = details
        super().__init__(message)


class DatabaseException(Exception):
    """Exception raised when a database operation fails"""
    def __init__(self, message: str, original_exception: Exception = None):
        self.original_exception = original_exception
        super().__init__(message)


class FileProcessingException(Exception):
    """Exception raised when file processing operations fail"""
    def __init__(self, message: str, file_path: str = None):
        message_with_path = message
        if file_path:
            message_with_path += f" (file: {file_path})"
        super().__init__(message_with_path)