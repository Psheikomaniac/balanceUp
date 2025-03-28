"""
Secure file handling service.

This module provides a secure file handling service for safely interacting with
files in the system. It implements security best practices for file operations
including:
- Path traversal prevention
- File access control based on allowed directories
- File extension validation
- Content validation
- File size limits
- Hash verification

All file operations should use this service rather than direct file system access
to ensure consistent security controls are applied.
"""
import os
import shutil
import hashlib
from typing import List, Tuple, Optional
import logging

from app.utils.file_validation import (
    validate_filename,
    validate_file_path,
    validate_file_content,
    is_file_size_valid
)
from app.errors.exceptions import FileValidationError, SecurityError

logger = logging.getLogger(__name__)

def compute_file_hash(file_path: str, algorithm: str = 'sha256') -> str:
    """
    Compute the hash of a file using the specified algorithm.
    
    Args:
        file_path: Path to the file
        algorithm: Hash algorithm to use (default: sha256)
        
    Returns:
        str: Hexadecimal digest of the file hash
    """
    hash_obj = hashlib.new(algorithm)
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()

class SecureFileHandler:
    """
    Secure file handler for safely performing file operations.
    
    This class provides methods for securely reading, writing, and manipulating
    files with proper validation and security controls.
    """
    
    def __init__(
        self,
        allowed_dirs: List[str],
        allowed_extensions: List[str],
        max_file_size: int = 10 * 1024 * 1024,  # 10MB default
    ):
        """
        Initialize the secure file handler.
        
        Args:
            allowed_dirs: List of directories that can be accessed
            allowed_extensions: List of allowed file extensions (including dot)
            max_file_size: Maximum allowed file size in bytes
        """
        self.allowed_dirs = [os.path.abspath(d) for d in allowed_dirs]
        self.allowed_extensions = [ext.lower() for ext in allowed_extensions]
        self.max_file_size = max_file_size
        logger.info(f"Initialized SecureFileHandler with {len(allowed_dirs)} allowed directories")
        
    def validate_file(self, file_path: str) -> Tuple[bool, str]:
        """
        Validate if a file meets all security requirements.
        
        Args:
            file_path: Path to the file to validate
            
        Returns:
            Tuple[bool, str]: (is_valid, validation_message)
            
        Raises:
            FileValidationError: If file validation fails
            SecurityError: If a security violation is detected
        """
        file_path = os.path.abspath(file_path)
        
        # Check if file exists
        if not os.path.isfile(file_path):
            raise FileValidationError(f"File does not exist: {file_path}")
        
        # Check if file is in allowed directory
        parent_dir = os.path.dirname(file_path)
        if not any(os.path.commonpath([parent_dir, allowed_dir]) == allowed_dir 
                  for allowed_dir in self.allowed_dirs):
            logger.warning(f"File access denied for path: {file_path}")
            raise SecurityError(f"File access denied: {file_path}")
        
        # Validate filename
        filename = os.path.basename(file_path)
        if not validate_filename(filename):
            raise FileValidationError(f"Invalid filename: {filename}")
        
        # Validate file extension
        _, ext = os.path.splitext(file_path)
        if ext.lower() not in self.allowed_extensions:
            raise FileValidationError(f"Unsupported file extension: {ext}")
        
        # Validate file path
        if not validate_file_path(file_path):
            raise SecurityError(f"Invalid file path: {file_path}")
        
        # Validate file size
        if not is_file_size_valid(file_path, self.max_file_size):
            raise FileValidationError(
                f"File size exceeds maximum allowed size ({self.max_file_size} bytes)"
            )
        
        # Validate file content
        content_valid, message = validate_file_content(file_path, ext.lower())
        if not content_valid:
            raise FileValidationError(f"File content validation failed: {message}")
        
        return True, "File validation successful"
    
    def read_file(self, file_path: str) -> str:
        """
        Securely read the contents of a file.
        
        Args:
            file_path: Path to the file to read
            
        Returns:
            str: Contents of the file
            
        Raises:
            FileValidationError: If file validation fails
            SecurityError: If a security violation is detected
        """
        self.validate_file(file_path)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            logger.debug(f"Successfully read file: {file_path}")
            return content
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {str(e)}")
            raise FileValidationError(f"Error reading file: {str(e)}")
    
    def save_file(self, file_path: str, destination_dir: str, new_filename: Optional[str] = None) -> str:
        """
        Securely save a file to a new location.
        
        Args:
            file_path: Path to the source file
            destination_dir: Directory to save the file to
            new_filename: New filename (if None, original filename is used)
            
        Returns:
            str: Path to the saved file
            
        Raises:
            FileValidationError: If file validation fails
            SecurityError: If a security violation is detected
        """
        self.validate_file(file_path)
        
        # Validate destination directory
        destination_dir = os.path.abspath(destination_dir)
        if not any(os.path.commonpath([destination_dir, allowed_dir]) == allowed_dir 
                  for allowed_dir in self.allowed_dirs):
            logger.warning(f"Destination directory access denied: {destination_dir}")
            raise SecurityError(f"Destination directory access denied: {destination_dir}")
        
        # Ensure destination directory exists
        if not os.path.exists(destination_dir):
            os.makedirs(destination_dir, exist_ok=True)
        
        # Determine target filename
        if new_filename is None:
            new_filename = os.path.basename(file_path)
        
        # Validate new filename
        if not validate_filename(new_filename):
            raise FileValidationError(f"Invalid new filename: {new_filename}")
        
        # Construct destination path
        destination_path = os.path.join(destination_dir, new_filename)
        
        # Copy the file
        try:
            shutil.copy2(file_path, destination_path)
            logger.info(f"Successfully saved file to: {destination_path}")
            return destination_path
        except Exception as e:
            logger.error(f"Error saving file to {destination_path}: {str(e)}")
            raise FileValidationError(f"Error saving file: {str(e)}")
    
    def move_file(self, file_path: str, destination_dir: str, new_filename: Optional[str] = None) -> str:
        """
        Securely move a file to a new location.
        
        Args:
            file_path: Path to the source file
            destination_dir: Directory to move the file to
            new_filename: New filename (if None, original filename is used)
            
        Returns:
            str: Path to the moved file
            
        Raises:
            FileValidationError: If file validation fails
            SecurityError: If a security violation is detected
        """
        # Save the file first
        destination_path = self.save_file(file_path, destination_dir, new_filename)
        
        # Remove the original file
        try:
            os.remove(file_path)
            logger.info(f"Successfully moved file from {file_path} to {destination_path}")
            return destination_path
        except Exception as e:
            logger.error(f"Error removing original file {file_path}: {str(e)}")
            raise FileValidationError(f"Error moving file: {str(e)}")
    
    def delete_file(self, file_path: str) -> bool:
        """
        Securely delete a file.
        
        Args:
            file_path: Path to the file to delete
            
        Returns:
            bool: True if the file was successfully deleted
            
        Raises:
            FileValidationError: If file validation fails
            SecurityError: If a security violation is detected
        """
        self.validate_file(file_path)
        
        try:
            os.remove(file_path)
            logger.info(f"Successfully deleted file: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error deleting file {file_path}: {str(e)}")
            raise FileValidationError(f"Error deleting file: {str(e)}")
            
    def get_file_hash(self, file_path: str, algorithm: str = 'sha256') -> str:
        """
        Get the hash of a file.
        
        Args:
            file_path: Path to the file
            algorithm: Hash algorithm to use (default: sha256)
            
        Returns:
            str: Hexadecimal digest of the file hash
            
        Raises:
            FileValidationError: If file validation fails
            SecurityError: If a security violation is detected
        """
        self.validate_file(file_path)
        
        try:
            return compute_file_hash(file_path, algorithm)
        except Exception as e:
            logger.error(f"Error computing hash for file {file_path}: {str(e)}")
            raise FileValidationError(f"Error computing file hash: {str(e)}")