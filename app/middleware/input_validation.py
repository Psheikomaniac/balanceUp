from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import re
import uuid
from decimal import Decimal, InvalidOperation
from typing import Dict, Any

class InputValidationMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.patterns = {
            'uuid': re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
            'email': re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
            'phone': re.compile(r'^\+?[1-9]\d{1,14}$'),
            'amount': re.compile(r'^-?\d+\.?\d*$')
        }

    async def dispatch(self, request: Request, call_next):
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                body = await request.json()
                self._validate_request_data(body)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        response = await call_next(request)
        return response

    def _validate_request_data(self, data: Dict[str, Any]):
        for key, value in data.items():
            if key == 'user_id':
                self._validate_uuid(value)
            elif key == 'email':
                self._validate_email(value)
            elif key == 'phone':
                self._validate_phone(value)
            elif key in ['amount', 'balance']:
                self._validate_amount(value)
            elif key in ['name', 'reason', 'description']:
                self._validate_text(value)

    def _validate_uuid(self, value: str):
        if not isinstance(value, str) or not self.patterns['uuid'].match(value):
            try:
                uuid.UUID(value)
            except ValueError:
                raise ValueError("Invalid UUID format")

    def _validate_email(self, value: str):
        if not isinstance(value, str) or not self.patterns['email'].match(value):
            raise ValueError("Invalid email format")

    def _validate_phone(self, value: str):
        if not isinstance(value, str) or not self.patterns['phone'].match(value):
            raise ValueError("Invalid phone number format")

    def _validate_amount(self, value: Any):
        try:
            amount = Decimal(str(value))
            if amount <= 0:
                raise ValueError("Amount must be greater than zero")
        except (TypeError, ValueError, InvalidOperation):
            raise ValueError("Invalid amount format")

    def _validate_text(self, value: str):
        if not isinstance(value, str):
            raise ValueError("Invalid text format")
        
        dangerous_patterns = [
            '<script', 'javascript:', 'eval(', 
            'onload=', 'onerror=', 'onclick=',
            'data:text/html', 'alert(', '--',
            ';', '`', '$(',
        ]
        
        value_lower = value.lower()
        for pattern in dangerous_patterns:
            if pattern in value_lower:
                raise ValueError("Invalid characters in text input")