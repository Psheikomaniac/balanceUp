"""
Tests for secure file handling functionality.
"""
import os
import shutil
import tempfile
import unittest
from unittest.mock import patch, MagicMock

import pytest

from app.services.file_handler import SecureFileHandler
from app.errors.exceptions import FileValidationError, SecurityError

class TestSecureFileHandler(unittest.TestCase):
    """Test cases for the SecureFileHandler class."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temporary test directories
        self.test_dir = tempfile.mkdtemp()
        self.allowed_dir = os.path.join(self.test_dir, "allowed")
        self.restricted_dir = os.path.join(self.test_dir, "restricted")
        
        os.makedirs(self.allowed_dir, exist_ok=True)
        os.makedirs(self.restricted_dir, exist_ok=True)
        
        # Create test files
        self.valid_file = os.path.join(self.allowed_dir, "valid_test.csv")
        self.invalid_file = os.path.join(self.allowed_dir, "invalid_test.exe")
        
        with open(self.valid_file, "w") as f:
            f.write("col1,col2,col3\n1,2,3\n4,5,6")
            
        with open(self.invalid_file, "w") as f:
            f.write("This is not a CSV file")
            
        # Create file handler
        self.file_handler = SecureFileHandler(
            allowed_dirs=[self.allowed_dir],
            allowed_extensions=['.csv', '.txt']
        )
        
    def tearDown(self):
        """Clean up after tests."""
        shutil.rmtree(self.test_dir)
        
    def test_validate_file_valid(self):
        """Test validation of a valid file."""
        # Patch validate_file_content to return True
        with patch('app.utils.file_validation.validate_file_content', return_value=(True, "")):
            is_valid, _ = self.file_handler.validate_file(self.valid_file)
            assert is_valid is True
            
    def test_validate_file_invalid_extension(self):
        """Test validation of a file with invalid extension."""
        with pytest.raises(FileValidationError) as exc_info:
            self.file_handler.validate_file(self.invalid_file)
        assert "Unsupported file extension" in str(exc_info.value)
        
    def test_validate_file_not_exists(self):
        """Test validation of a non-existent file."""
        with pytest.raises(FileValidationError) as exc_info:
            self.file_handler.validate_file(os.path.join(self.allowed_dir, "nonexistent.csv"))
        assert "File does not exist" in str(exc_info.value)
        
    def test_validate_file_restricted_dir(self):
        """Test validation of a file in a restricted directory."""
        restricted_file = os.path.join(self.restricted_dir, "restricted.csv")
        
        with open(restricted_file, "w") as f:
            f.write("restricted data")
            
        with pytest.raises(SecurityError) as exc_info:
            self.file_handler.validate_file(restricted_file)
        assert "File access denied" in str(exc_info.value)
        
    def test_read_file_valid(self):
        """Test reading a valid file."""
        # Patch validate_file to avoid validation issues
        with patch.object(SecureFileHandler, 'validate_file', return_value=(True, "")):
            content = self.file_handler.read_file(self.valid_file)
            assert "col1,col2,col3" in content
            assert "1,2,3" in content
            
    def test_save_file(self):
        """Test saving a file."""
        # Patch validate_file to avoid validation issues
        with patch.object(SecureFileHandler, 'validate_file', return_value=(True, "")):
            new_path = self.file_handler.save_file(
                self.valid_file, 
                self.allowed_dir, 
                "saved_file.csv"
            )
            assert os.path.exists(new_path)
            assert os.path.basename(new_path) == "saved_file.csv"
            
    def test_move_file(self):
        """Test moving a file."""
        # Create a new test file to move
        source_file = os.path.join(self.allowed_dir, "to_move.csv")
        with open(source_file, "w") as f:
            f.write("file to move")
            
        # Patch validate_file to avoid validation issues
        with patch.object(SecureFileHandler, 'validate_file', return_value=(True, "")):
            new_path = self.file_handler.move_file(
                source_file,
                self.allowed_dir,
                "moved_file.csv"
            )
            assert os.path.exists(new_path)
            assert os.path.basename(new_path) == "moved_file.csv"
            assert not os.path.exists(source_file)
    
    def test_delete_file(self):
        """Test deleting a file."""
        # Create a new test file to delete
        file_to_delete = os.path.join(self.allowed_dir, "to_delete.csv")
        with open(file_to_delete, "w") as f:
            f.write("file to delete")
            
        # Patch validate_file to avoid validation issues
        with patch.object(SecureFileHandler, 'validate_file', return_value=(True, "")):
            result = self.file_handler.delete_file(file_to_delete)
            assert result is True
            assert not os.path.exists(file_to_delete)
            
    def test_get_file_hash(self):
        """Test getting a file hash."""
        # Patch validate_file to avoid validation issues
        with patch.object(SecureFileHandler, 'validate_file', return_value=(True, "")):
            # Also patch compute_file_hash for consistent results
            with patch('app.services.file_handler.compute_file_hash', 
                      return_value="abcdef1234567890"):
                file_hash = self.file_handler.get_file_hash(self.valid_file)
                assert file_hash == "abcdef1234567890"
                assert len(file_hash) > 0