import os
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import re
import uuid

from app.services.file_handler import FileHandler
from app.utils.logging_config import get_logger
from app.config.settings import get_settings
from app.errors.exceptions import FileProcessingException
from app.database import get_db
from sqlalchemy.orm import Session

logger = get_logger(__name__)
settings = get_settings()

class CSVImporter:
    """Service for importing CSV data into the database"""
    
    def __init__(self):
        self.file_handler = FileHandler()
    
    def process_import_directory(self, directory: str = None) -> Dict[str, int]:
        """
        Process all CSV files in the import directory
        
        Args:
            directory: Optional directory path (defaults to settings.IMPORT_DIRECTORY)
            
        Returns:
            Dictionary with counts of imported records by file type
        """
        import_stats = {"punishments": 0, "transactions": 0, "dues": 0, "unknown": 0}
        target_dir = directory or settings.IMPORT_DIRECTORY
        
        # Get all CSV files
        csv_files = self.file_handler.list_files(target_dir, "*.csv")
        if not csv_files:
            logger.info(f"No CSV files found in {target_dir}")
            return import_stats
            
        logger.info(f"Found {len(csv_files)} CSV files to process")
        
        # Process each file
        for file_path in csv_files:
            try:
                # Standardize filename
                standardized_path = self.file_handler.standardize_filename(file_path)
                
                # Detect file type
                file_type = self.file_handler.detect_file_type(standardized_path)
                if not file_type:
                    logger.warning(f"Unknown file type: {standardized_path}")
                    file_type = "unknown"
                
                # Import data based on file type
                imported_count = self._import_file_by_type(standardized_path, file_type)
                import_stats[file_type] += imported_count
                
                # Archive file after successful import
                self.file_handler.archive_file(standardized_path)
                
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {str(e)}")
                # Continue processing other files
        
        return import_stats
    
    def _import_file_by_type(self, file_path: str, file_type: str) -> int:
        """
        Import a file based on its detected type
        
        Args:
            file_path: Path to the CSV file
            file_type: Type of data in the file (punishments, transactions, dues)
            
        Returns:
            Number of records imported
        """
        if file_type == "punishments":
            return self._import_punishments(file_path)
        elif file_type == "transactions":
            return self._import_transactions(file_path)
        elif file_type == "dues":
            return self._import_dues(file_path)
        else:
            logger.warning(f"No import handler for file type: {file_type}")
            return 0
    
    def _import_punishments(self, file_path: str) -> int:
        """
        Import punishment data from CSV
        
        Args:
            file_path: Path to the CSV file
            
        Returns:
            Number of records imported
        """
        try:
            # Read CSV data
            data = self.file_handler.read_csv(file_path)
            if not data:
                return 0
                
            # Map CSV columns to database columns
            mapped_data = []
            for row in data:
                mapped_row = self._map_punishment_columns(row)
                if mapped_row:
                    mapped_data.append(mapped_row)
            
            # Import data to database
            with next(get_db()) as db:
                return self._save_punishments_to_db(db, mapped_data)
                
        except Exception as e:
            logger.error(f"Error importing punishments from {file_path}: {str(e)}")
            raise FileProcessingException(f"Failed to import punishments: {str(e)}", file_path)
    
    def _map_punishment_columns(self, row: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        Map CSV columns to database columns for punishments
        
        Args:
            row: Dictionary representing a CSV row
            
        Returns:
            Mapped dictionary or None if required fields are missing
        """
        # Normalized column names (lowercase)
        norm_row = {k.lower().strip(): v for k, v in row.items()}
        
        # Map fields - handle different possible column names
        mapped = {}
        
        # Map user information
        for field in ['user_id', 'userid', 'id', 'player_id', 'playerid']:
            if field in norm_row and norm_row[field]:
                mapped['user_id'] = norm_row[field]
                break
                
        for field in ['user_name', 'username', 'name', 'player_name', 'playername']:
            if field in norm_row and norm_row[field]:
                mapped['user_name'] = norm_row[field]
                break
        
        # Map penalty information
        for field in ['amount', 'penalty_amount', 'fine', 'penalty', 'payment_amount']:
            if field in norm_row and norm_row[field]:
                try:
                    mapped['amount'] = float(norm_row[field].replace(',', '.'))
                except ValueError:
                    logger.warning(f"Invalid amount value: {norm_row[field]}")
                break
                
        for field in ['reason', 'description', 'penalty_reason', 'violation']:
            if field in norm_row and norm_row[field]:
                mapped['reason'] = norm_row[field]
                break
                
        for field in ['date', 'penalty_date', 'issued_date', 'punishment_date']:
            if field in norm_row and norm_row[field]:
                mapped['date'] = self._parse_date(norm_row[field])
                break
        
        # Check if we have the minimum required fields
        required_fields = ['user_name', 'amount']
        if not all(field in mapped for field in required_fields):
            logger.warning(f"Missing required fields in row: {row}")
            return None
            
        return mapped
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """
        Parse a date string in various formats
        
        Args:
            date_str: Date string in various possible formats
            
        Returns:
            ISO format date string (YYYY-MM-DD) or None if parsing fails
        """
        date_formats = [
            # DD.MM.YYYY or DD-MM-YYYY
            (r'(\d{1,2})[.-](\d{1,2})[.-](\d{4})', '%d.%m.%Y'),
            # YYYY-MM-DD
            (r'(\d{4})-(\d{1,2})-(\d{1,2})', '%Y-%m-%d'),
            # MM/DD/YYYY
            (r'(\d{1,2})/(\d{1,2})/(\d{4})', '%m/%d/%Y'),
        ]
        
        # Try parsing with patterns
        for pattern, fmt in date_formats:
            if re.match(pattern, date_str):
                try:
                    return datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
                except ValueError:
                    continue
        
        # If all fail, try a flexible approach
        try:
            from dateutil import parser
            return parser.parse(date_str).strftime('%Y-%m-%d')
        except:
            logger.warning(f"Failed to parse date: {date_str}")
            return None
    
    def _save_punishments_to_db(self, db: Session, punishments: List[Dict[str, Any]]) -> int:
        """
        Save punishment data to the database
        
        Args:
            db: Database session
            punishments: List of punishment dictionaries
            
        Returns:
            Number of records saved
        """
        from app.database.models import Penalty, User
        
        saved_count = 0
        
        for p in punishments:
            try:
                # Find or create user
                user = db.query(User).filter(User.name == p['user_name']).first()
                if not user:
                    user = User(
                        name=p['user_name'],
                        id=p.get('user_id') or str(uuid.uuid4())
                    )
                    db.add(user)
                    db.flush()
                
                # Create penalty
                penalty = Penalty(
                    penalty_id=str(uuid.uuid4()),
                    user_id=user.id,
                    amount=p['amount'],
                    reason=p.get('reason', ''),
                    date=p.get('date'),
                    paid=False
                )
                
                db.add(penalty)
                saved_count += 1
                
            except Exception as e:
                logger.error(f"Error saving punishment: {str(e)}")
                # Continue processing other records
        
        db.commit()
        logger.info(f"Saved {saved_count} punishments to database")
        return saved_count
    
    def _import_transactions(self, file_path: str) -> int:
        """
        Import transaction data from CSV
        
        Args:
            file_path: Path to the CSV file
            
        Returns:
            Number of records imported
        """
        # TODO: Implement transaction import logic
        logger.info(f"Transaction import not yet implemented for {file_path}")
        return 0
    
    def _import_dues(self, file_path: str) -> int:
        """
        Import dues data from CSV
        
        Args:
            file_path: Path to the CSV file
            
        Returns:
            Number of records imported
        """
        # TODO: Implement dues import logic
        logger.info(f"Dues import not yet implemented for {file_path}")
        return 0
