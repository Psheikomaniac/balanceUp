import os
import shutil
import csv
from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path

from app.utils.logging_config import get_logger
from app.config.settings import get_settings
from app.errors.exceptions import FileProcessingException

settings = get_settings()
logger = get_logger(__name__)

class FileHandler:
    """Centralized class for handling file operations"""
    
    def __init__(self, base_dir: str = None):
        self.base_dir = base_dir or settings.IMPORT_DIRECTORY
        self.archive_dir = settings.ARCHIVE_DIRECTORY
        
        # Ensure directories exist
        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(self.archive_dir, exist_ok=True)
    
    def list_files(self, directory: str = None, pattern: str = None) -> List[str]:
        """
        List files in a directory, optionally filtering by pattern
        
        Args:
            directory: Directory to list files from (defaults to base_dir)
            pattern: Optional filename pattern to filter by
            
        Returns:
            List of file paths
        """
        target_dir = directory or self.base_dir
        
        try:
            if not os.path.exists(target_dir):
                logger.warning(f"Directory does not exist: {target_dir}")
                return []
                
            files = [f for f in os.listdir(target_dir) if os.path.isfile(os.path.join(target_dir, f))]
            
            if pattern:
                import fnmatch
                files = [f for f in files if fnmatch.fnmatch(f, pattern)]
                
            return [os.path.join(target_dir, f) for f in files]
        except Exception as e:
            logger.error(f"Error listing files in {target_dir}: {str(e)}")
            raise FileProcessingException(f"Failed to list files: {str(e)}", target_dir)
    
    def standardize_filename(self, filepath: str) -> str:
        """
        Standardize filename to format: YYYYMMDD_HHMMSS_type.csv
        
        Args:
            filepath: Path to the file to standardize
            
        Returns:
            New standardized filepath
        """
        try:
            file_dir = os.path.dirname(filepath)
            filename = os.path.basename(filepath)
            
            # Extract date from filename if it exists in various formats
            date_formats = [
                # DD-MM-YYYY
                (r'(\d{2})-(\d{2})-(\d{4})', lambda m: f"{m.group(3)}{m.group(2)}{m.group(1)}"),
                # DD.MM.YYYY
                (r'(\d{2})\.(\d{2})\.(\d{4})', lambda m: f"{m.group(3)}{m.group(2)}{m.group(1)}"),
                # YYYY-MM-DD
                (r'(\d{4})-(\d{2})-(\d{2})', lambda m: f"{m.group(1)}{m.group(2)}{m.group(3)}"),
            ]
            
            import re
            date_str = None
            for pattern, formatter in date_formats:
                match = re.search(pattern, filename)
                if match:
                    date_str = formatter(match)
                    break
            
            # If no date found, use current date
            if not date_str:
                date_str = datetime.now().strftime("%Y%m%d")
            
            # Determine file type from name
            file_type = "unknown"
            if "punishment" in filename.lower() or "penalties" in filename.lower():
                file_type = "punishments"
            elif "transaction" in filename.lower():
                file_type = "transactions"
            elif "due" in filename.lower() or "dues" in filename.lower():
                file_type = "dues"
            
            # Generate timestamp
            timestamp = datetime.now().strftime("%H%M%S")
            
            # Create new filename
            new_filename = f"{date_str}_{timestamp}_{file_type}.csv"
            new_filepath = os.path.join(file_dir, new_filename)
            
            # Rename file
            os.rename(filepath, new_filepath)
            logger.info(f"Renamed file: {filename} -> {new_filename}")
            
            return new_filepath
        except Exception as e:
            logger.error(f"Error standardizing filename {filepath}: {str(e)}")
            raise FileProcessingException(f"Failed to standardize filename: {str(e)}", filepath)
    
    def read_csv(self, filepath: str, delimiter: str = ',', has_header: bool = True) -> List[Dict[str, str]]:
        """
        Read CSV file and return a list of dictionaries
        
        Args:
            filepath: Path to the CSV file
            delimiter: CSV delimiter character
            has_header: Whether the CSV has a header row
            
        Returns:
            List of dictionaries where keys are column names (or indices if no header)
        """
        try:
            result = []
            
            with open(filepath, 'r', encoding='utf-8') as file:
                if has_header:
                    reader = csv.DictReader(file, delimiter=delimiter)
                    result = list(reader)
                else:
                    reader = csv.reader(file, delimiter=delimiter)
                    rows = list(reader)
                    # Use column indices as keys
                    for row in rows:
                        result.append({str(i): val for i, val in enumerate(row)})
            
            logger.info(f"Read {len(result)} rows from {filepath}")
            return result
        except Exception as e:
            logger.error(f"Error reading CSV file {filepath}: {str(e)}")
            raise FileProcessingException(f"Failed to read CSV file: {str(e)}", filepath)
    
    def write_csv(self, filepath: str, data: List[Dict[str, Any]], fieldnames: List[str] = None, 
                 delimiter: str = ',') -> str:
        """
        Write list of dictionaries to CSV file
        
        Args:
            filepath: Path to write the CSV file
            data: List of dictionaries to write
            fieldnames: List of field names (columns) to include
            delimiter: CSV delimiter character
            
        Returns:
            Path to the written file
        """
        try:
            if not data:
                logger.warning(f"No data to write to {filepath}")
                return filepath
                
            if not fieldnames:
                fieldnames = list(data[0].keys())
                
            with open(filepath, 'w', encoding='utf-8', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter=delimiter)
                writer.writeheader()
                writer.writerows(data)
                
            logger.info(f"Wrote {len(data)} rows to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Error writing CSV file {filepath}: {str(e)}")
            raise FileProcessingException(f"Failed to write CSV file: {str(e)}", filepath)
    
    def archive_file(self, filepath: str) -> str:
        """
        Move a file to the archive directory
        
        Args:
            filepath: Path to the file to archive
            
        Returns:
            Path to the archived file
        """
        try:
            filename = os.path.basename(filepath)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_filename = f"{timestamp}_{filename}"
            archive_path = os.path.join(self.archive_dir, archive_filename)
            
            shutil.move(filepath, archive_path)
            logger.info(f"Archived file: {filepath} -> {archive_path}")
            
            return archive_path
        except Exception as e:
            logger.error(f"Error archiving file {filepath}: {str(e)}")
            raise FileProcessingException(f"Failed to archive file: {str(e)}", filepath)
    
    def detect_file_type(self, filepath: str) -> Optional[str]:
        """
        Detect file type from content or name
        
        Args:
            filepath: Path to the file
            
        Returns:
            Detected file type or None if unknown
        """
        filename = os.path.basename(filepath).lower()
        
        if "punishment" in filename or "penalties" in filename:
            return "punishments"
        elif "transaction" in filename:
            return "transactions"
        elif "due" in filename or "dues" in filename:
            return "dues"
            
        # If can't determine from name, try to inspect the file
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                header = file.readline().lower()
                
                if any(x in header for x in ["punishment", "penalty", "fine", "violation"]):
                    return "punishments"
                elif any(x in header for x in ["transaction", "payment"]):
                    return "transactions"
                elif any(x in header for x in ["due", "dues", "membership"]):
                    return "dues"
                    
            return None
        except Exception as e:
            logger.warning(f"Error detecting file type for {filepath}: {str(e)}")
            return None