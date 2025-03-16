from typing import Optional, Dict, Any

class BaseError(Exception):
    """Base exception class for application errors"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

class DatabaseError(BaseError):
    """Raised when a database operation fails"""
    pass

class ResourceNotFoundException(BaseError):
    """Raised when a requested resource is not found"""
    pass

class ValidationError(BaseError):
    """Raised when data validation fails"""
    pass

class AuthenticationError(BaseError):
    """Raised when authentication fails"""
    pass

class AuthorizationError(BaseError):
    """Raised when user lacks permission for an operation"""
    pass

class RateLimitExceededError(BaseError):
    """Raised when rate limit is exceeded"""
    pass

class BusinessLogicError(BaseError):
    """Raised when a business rule is violated"""
    def __init__(self, message: str, rule: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.rule = rule

class PaymentError(BusinessLogicError):
    """Raised when a payment operation fails"""
    pass

class InsufficientFundsError(PaymentError):
    """Raised when user has insufficient funds"""
    pass

class DuplicateResourceError(DatabaseError):
    """Raised when attempting to create a duplicate resource"""
    pass

class DataIntegrityError(DatabaseError):
    """Raised when data integrity is violated"""
    pass

class ConfigurationError(BaseError):
    """Raised when there's a configuration issue"""
    pass