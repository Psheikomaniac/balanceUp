"""
Tests for security features and input validation.
"""

import os
import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import tempfile
import uuid
from decimal import Decimal

from app.main import app
from app.utils.file_validation import (
    is_safe_filename,
    is_safe_file_path,
    validate_file_content,
    sanitize_filename,
    compute_file_hash
)
from app.services.file_handler import SecureFileHandler
from app.database.schemas import PenaltyBase, UserBase

client = TestClient(app)

def test_input_validation_middleware():
    """Test that the input validation middleware catches invalid input"""
    # Test invalid UUID format
    response = client.post(
        "/api/v1/penalties",
        json={
            "user_id": "invalid-uuid",
            "amount": 100,
            "reason": "Test penalty"
        }
    )
    assert response.status_code == 400
    assert "Invalid UUID format" in response.json()["error"]

    # Test amount validation
    response = client.post(
        "/api/v1/penalties",
        json={
            "user_id": str(uuid.uuid4()),
            "amount": -100,
            "reason": "Test penalty"
        }
    )
    assert response.status_code == 400
    assert "Amount must be" in response.json()["error"]

def test_filename_validation():
    """Test filename validation functions"""
    # Test safe filenames
    assert is_safe_filename("valid_file.csv")
    assert is_safe_filename("test-123.csv")
    
    # Test unsafe filenames
    assert not is_safe_filename("../unsafe.csv")
    assert not is_safe_filename("unsafe/file.csv")
    assert not is_safe_filename("unsafe*file.csv")
    assert not is_safe_filename(";unsafe.csv")

def test_file_path_validation():
    """Test file path validation"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a test file
        test_file = Path(temp_dir) / "test.csv"
        test_file.touch()
        
        # Test with allowed directory
        assert is_safe_file_path(str(test_file), [temp_dir])
        
        # Test with file outside allowed directory
        outside_file = Path(temp_dir).parent / "outside.csv"
        outside_file.touch()
        assert not is_safe_file_path(str(outside_file), [temp_dir])

def test_file_content_validation():
    """Test file content validation"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Test valid CSV
        valid_csv = Path(temp_dir) / "valid.csv"
        with open(valid_csv, "w") as f:
            f.write("header1,header2\nvalue1,value2\n")
        
        is_valid, error = validate_file_content(str(valid_csv))
        assert is_valid
        assert error is None
        
        # Test invalid file type
        invalid_file = Path(temp_dir) / "invalid.exe"
        with open(invalid_file, "w") as f:
            f.write("not a csv file")
        
        is_valid, error = validate_file_content(str(invalid_file))
        assert not is_valid
        assert "Invalid file type" in error

def test_secure_file_handler():
    """Test SecureFileHandler functionality"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set up test directories
        import_dir = Path(temp_dir) / "import"
        archive_dir = Path(temp_dir) / "archive"
        os.makedirs(import_dir)
        os.makedirs(archive_dir)
        
        handler = SecureFileHandler()
        handler.import_dir = str(import_dir)
        handler.archive_dir = str(archive_dir)
        
        # Test file listing with unsafe names
        unsafe_file = import_dir / "../unsafe.csv"
        try:
            unsafe_file.touch()
        except OSError:
            pass  # Expected for some unsafe paths
            
        safe_file = import_dir / "safe.csv"
        safe_file.touch()
        
        files = handler.list_import_files()
        assert len(files) == 1
        assert "safe.csv" in files[0]

def test_penalty_schema_validation():
    """Test PenaltyBase schema validation"""
    # Test valid penalty
    valid_penalty = {
        "user_id": str(uuid.uuid4()),
        "amount": Decimal("100.00"),
        "reason": "Valid penalty",
        "currency": "EUR"
    }
    penalty = PenaltyBase(**valid_penalty)
    assert penalty.amount == Decimal("100.00")
    
    # Test invalid amount
    with pytest.raises(ValueError):
        PenaltyBase(
            user_id=str(uuid.uuid4()),
            amount=Decimal("0.00"),
            reason="Invalid amount"
        )
    
    # Test invalid currency
    with pytest.raises(ValueError):
        PenaltyBase(
            user_id=str(uuid.uuid4()),
            amount=Decimal("100.00"),
            reason="Invalid currency",
            currency="INVALID"
        )

def test_user_schema_validation():
    """Test UserBase schema validation"""
    # Test valid user
    valid_user = {
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "+1234567890"
    }
    user = UserBase(**valid_user)
    assert user.name == "John Doe"
    
    # Test invalid email
    with pytest.raises(ValueError):
        UserBase(
            name="John Doe",
            email="invalid-email"
        )
    
    # Test invalid phone
    with pytest.raises(ValueError):
        UserBase(
            name="John Doe",
            phone="invalid-phone"
        )
    
    # Test invalid name
    with pytest.raises(ValueError):
        UserBase(
            name="John<script>alert('xss')</script>",
            email="john@example.com"
        )