import os
import logging
import shutil
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def rename_file(old_filepath: str, new_filename: str):
    new_filepath = os.path.join(os.path.dirname(old_filepath), new_filename)
    os.rename(old_filepath, new_filepath)
    logger.info(f"Renamed {old_filepath} to {new_filepath}")

def rename_files_in_folder(folder_path: str):
    if os.path.exists(folder_path):
        for filename in os.listdir(folder_path):
            if filename.startswith('cashbox-punishments-') and filename.endswith('.csv'):
                old_filepath = os.path.join(folder_path, filename)
                formatted_date = extract_and_format_date(filename)
                new_filename = f"{formatted_date}.csv"
                rename_file(old_filepath, new_filename)
    else:
        logger.error(f"The directory {folder_path} does not exist.")

def extract_and_format_date(old_filename: str) -> str:
    parts = old_filename.split('-')
    date_time_str = f'{parts[2]}-{parts[3]}-{parts[4]}-{parts[5].split(".")[0]}'
    date_time_obj = datetime.strptime(date_time_str, '%d-%m-%Y-%H%M%S')
    formatted_date = date_time_obj.strftime('%Y%m%d')
    return formatted_date

def rename_latest_csv(cashbox_dir: str):
    """
    Rename latest.csv to YYYYMMDD.csv format in the cashbox directory
    """
    latest_file = os.path.join(cashbox_dir, 'latest.csv')
    if os.path.exists(latest_file):
        new_filename = datetime.now().strftime('%Y%m%d.csv')
        new_filepath = os.path.join(cashbox_dir, new_filename)
        
        # If target file already exists, create a backup
        if os.path.exists(new_filepath):
            backup_path = os.path.join(cashbox_dir, f"{new_filename}.bak")
            shutil.move(new_filepath, backup_path)
            
        # Rename latest.csv to new date-based filename
        os.rename(latest_file, new_filepath)
        return new_filepath
    return None