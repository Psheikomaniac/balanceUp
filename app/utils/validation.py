"""
Validation utilities for the BalanceUp API

This module provides centralized validation functions and security measures
to ensure input data is properly validated across the application.
"""

import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Union
from pydantic import ValidationError
from enum import Enum

# Constants for validation
UUID_PATTERN = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
PHONE_PATTERN = r'^\+?1?\d{9,15}$'
EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
DATE_FORMAT = '%Y-%m-%d'

# Sanitization characters to remove from inputs
SANITIZE_CHARS = {
    '<', '>', '"', "'", ';', '(', ')', '{', '}', '&', '|', '`', '$', '\\'
}

class ValidationErrorType(Enum):
    """Types of validation errors for better error classification"""
    INVALID_FORMAT = "invalid_format"
    MISSING_FIELD = "missing_field"
    INVALID_TYPE = "invalid_type"
    INVALID_VALUE = "invalid_value"
    INVALID_UUID = "invalid_uuid"
    INVALID_DATE = "invalid_date"
    INVALID_PHONE = "invalid_phone"
    INVALID_EMAIL = "invalid_email"
    INVALID_AMOUNT = "invalid_amount"
    SECURITY_RISK = "security_risk"


class ValidationResult:
    """
    Object representing the result of a validation operation
    with structured information about validation errors.
    """
    def __init__(self, is_valid: bool = True, errors: Optional[Dict[str, Any]] = None):
        self.is_valid = is_valid
        self.errors = errors or {}
    
    def add_error(self, field: str, error_type: ValidationErrorType, message: str):
        """Add a validation error for a specific field"""
        if field not in self.errors:
            self.errors[field] = []
        
        self.errors[field].append({
            "type": error_type.value,
            "message": message
        })
        self.is_valid = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the validation result to a dictionary representation"""
        return {
            "is_valid": self.is_valid,
            "errors": self.errors
        }


def is_valid_uuid(value: str) -> bool:
    """
    Validate that a string is a valid UUID
    
    Args:
        value: The string to validate
        
    Returns:
        bool: True if the value is a valid UUID, False otherwise
    """
    if not value:
        return False
    
    # Try UUID parsing
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError):
        # Fall back to regex in case parsing fails
        return bool(re.match(UUID_PATTERN, value))


def is_valid_phone(value: str) -> bool:
    """
    Validate that a string is a valid phone number
    
    Args:
        value: The string to validate
        
    Returns:
        bool: True if the value is a valid phone number, False otherwise
    """
    if not value:
        return True  # Phone is optional
    
    return bool(re.match(PHONE_PATTERN, value))


def is_valid_email(value: str) -> bool:
    """
    Validate that a string is a valid email address
    
    Args:
        value: The string to validate
        
    Returns:
        bool: True if the value is a valid email address, False otherwise
    """
    if not value:
        return True  # Email is optional
    
    return bool(re.match(EMAIL_PATTERN, value))


def sanitize_input(value: str) -> str:
    """
    Sanitize input by removing potentially dangerous characters
    
    Args:
        value: The string to sanitize
        
    Returns:
        str: The sanitized string
    """
    if not value or not isinstance(value, str):
        return value
    
    # Remove dangerous characters
    for char in SANITIZE_CHARS:
        value = value.replace(char, '')
    
    return value


def validate_request_params(params: Dict[str, Any]) -> ValidationResult:
    """
    Validate request parameters against common security threats
    
    Args:
        params: Dictionary of request parameters to validate
        
    Returns:
        ValidationResult: Result of the validation
    """
    result = ValidationResult()
    
    for key, value in params.items():
        # Skip None values
        if value is None:
            continue
        
        # Validate strings
        if isinstance(value, str):
            # Check for potential SQL injection patterns
            sql_patterns = ["--", ";", "/*", "*/", "UNION", "SELECT", "INSERT", "UPDATE", 
                           "DELETE", "DROP", "EXEC", "EXECUTE", "TRUNCATE"]
            
            for pattern in sql_patterns:
                if pattern.upper() in value.upper():
                    result.add_error(
                        field=key,
                        error_type=ValidationErrorType.SECURITY_RISK,
                        message=f"Potential security risk detected in field '{key}'"
                    )
                    break
        
        # Validate numeric values
        if key.endswith('_id') and isinstance(value, str):
            if not is_valid_uuid(value):
                result.add_error(
                    field=key,
                    error_type=ValidationErrorType.INVALID_UUID,
                    message=f"Field '{key}' must be a valid UUID"
                )
    
    return result


def validate_date_format(date_string: str) -> bool:
    """
    Validate that a string is a valid date in the format YYYY-MM-DD
    
    Args:
        date_string: The string to validate
        
    Returns:
        bool: True if the value is a valid date, False otherwise
    """
    if not date_string:
        return True
    
    try:
        datetime.strptime(date_string, DATE_FORMAT)
        return True
    except ValueError:
        return False


def safe_convert_to_int(value: Any, default: int = 0) -> int:
    """
    Safely convert a value to an integer with a default value if conversion fails
    
    Args:
        value: The value to convert
        default: Default value to return if conversion fails
        
    Returns:
        int: The converted integer or the default value
    """
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default