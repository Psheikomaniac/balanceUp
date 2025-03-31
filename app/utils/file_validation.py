"""
File validation utilities for secure file handling.
"""
import os
import magic
import hashlib
import re
from typing import Tuple, List
from pathlib import Path

# Allowed file types and their magic numbers
ALLOWED_MIME_TYPES = {
    'text/csv',
    'text/plain',
    'application/vnd.ms-excel',  # For legacy Excel CSV
}

# Maximum file size (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

# Allowed characters in filenames
FILENAME_PATTERN = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_.-]*$')

def is_safe_filename(filename: str) -> bool:
    """Validate that a filename is safe."""
    if not filename or '..' in filename:
        return False
        
    if len(filename) > 255:
        return False
        
    if not FILENAME_PATTERN.match(filename):
        return False
        
    ext = Path(filename).suffix.lower()
    if ext not in ['.csv', '.txt']:
        return False
        
    return True

def validate_filename(filename: str) -> bool:
    """Validate that a filename is safe and complies with security standards."""
    return is_safe_filename(filename)

def is_safe_file_path(file_path: str, allowed_dirs: List[str]) -> bool:
    """Validate that a file path is safe and within allowed directories."""
    try:
        abs_path = os.path.abspath(os.path.realpath(file_path))
        return any(
            os.path.commonpath([abs_path, allowed_dir]) == allowed_dir
            for allowed_dir in allowed_dirs
        )
    except (ValueError, OSError):
        return False

def validate_file_path(file_path: str) -> bool:
    """Validate a file path for security considerations."""
    # Normalize the path
    file_path = os.path.normpath(file_path)
    
    # Check for path traversal attempts
    if '..' in file_path:
        return False
        
    # Check path length
    if len(file_path) > 255:
        return False
        
    # Check if path is absolute (depending on security requirements)
    if not os.path.isabs(file_path):
        return False
        
    return True

def is_file_size_valid(file_path: str, max_size: int = MAX_FILE_SIZE) -> bool:
    """Check if file size is within the allowed limit."""
    try:
        file_size = os.path.getsize(file_path)
        return file_size <= max_size
    except (OSError, IOError):
        return False

def validate_file_content(file_path: str, ext: str = None) -> Tuple[bool, str]:
    """Validate file content for security and format compliance."""
    try:
        if os.path.getsize(file_path) > MAX_FILE_SIZE:
            return False, "File exceeds maximum allowed size"
            
        mime_type = magic.from_file(file_path, mime=True)
        if mime_type not in ALLOWED_MIME_TYPES:
            return False, f"Invalid file type: {mime_type}"
        
        # Additional validation based on file extension
        if ext and ext.lower() == '.csv':
            # CSV-specific validation
            with open(file_path, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f):
                    if i >= 5:  # Check first 5 lines
                        break
                        
                    if line.startswith('=') or line.startswith('+') or line.startswith('-') or line.startswith('@'):
                        return False, "Potential formula injection detected"
                        
                    if any(char in line for char in ['<', '>', '{', '}', '(', ')', ';']):
                        return False, "Invalid characters detected"
        
        return True, ""
        
    except Exception as e:
        return False, f"Error validating file: {str(e)}"

def sanitize_filename(filename: str) -> str:
    """Sanitize a filename to make it safe."""
    filename = os.path.basename(filename)
    filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
    filename = re.sub(r'^[._-]+', '', filename)
    
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255-len(ext)] + ext
    
    return filename

def compute_file_hash(file_path: str) -> str:
    """Compute SHA-256 hash of a file."""
    sha256_hash = hashlib.sha256()
    
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    
    return sha256_hash.hexdigest()