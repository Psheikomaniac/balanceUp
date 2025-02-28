import os
import re
from datetime import datetime

def rename_file(old_path):
    """Rename a file from cashbox-{type}-DD-MM-YYYY-HHMMSS.csv to YYYYMMDD_{type}.csv"""
    basename = os.path.basename(old_path)
    pattern = re.compile(r'^cashbox-(dues|punishments|transactions)-(\d{2})-(\d{2})-(\d{4})-\d{6}\.csv$')
    
    match = pattern.match(basename)
    if match:
        file_type, day, month, year = match.groups()
        new_name = f"{year}{month}{day}_{file_type}.csv"
        new_path = os.path.join(os.path.dirname(old_path), new_name)
        os.rename(old_path, new_path)
        print(f'File successfully renamed to {new_name}')
        return new_path
    return old_path

def rename_files_in_folder(folder_path):
    """Process all matching files in the given folder"""
    for filename in os.listdir(folder_path):
        if filename.startswith('cashbox-') and filename.endswith('.csv'):
            old_filepath = os.path.join(folder_path, filename)
            rename_file(old_filepath)

if __name__ == "__main__":
    folder_path = os.path.join(os.path.dirname(__file__), 'cashbox')
    rename_files_in_folder(folder_path)
