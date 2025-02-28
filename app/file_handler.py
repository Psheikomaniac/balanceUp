import os
import logging
from datetime import datetime

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)


def rename_file(old_filepath, new_filename):
    new_filepath = os.path.join(os.path.dirname(old_filepath), new_filename)
    os.rename(old_filepath, new_filepath)
    logger.info(f"Renamed {old_filepath} to {new_filepath}")


def rename_files_in_folder(folder_path, db_path):
    if os.path.exists(folder_path):
        for filename in os.listdir(folder_path):
            if filename == 'latest.csv':
                old_filepath = os.path.join(folder_path, filename)
                current_date = datetime.now().strftime('%Y%m%d')
                new_filename = f"{current_date}.csv"
                rename_file(old_filepath, new_filename)
    else:
        logger.error(f"The directory {folder_path} does not exist.")
