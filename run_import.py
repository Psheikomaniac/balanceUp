import os
import sys
from datetime import datetime

# Add the project root directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.data_importer import import_data

# Check if a specific file is provided as command line argument
if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
    csv_file_path = sys.argv[1]
    print(f"Importing from specified file: {csv_file_path}")
    import_data(csv_file_path)
    sys.exit(0)

# Path to cashbox directory
cashbox_dir = os.path.join('app', 'cashbox')

# Look for cashbox files in specified format
csv_files = [f for f in os.listdir(cashbox_dir) if f.endswith('.csv')]
if not csv_files:
    print("No CSV files found in the cashbox directory")
    sys.exit(1)

# Filter for files matching the cashbox format
cashbox_files = [f for f in csv_files if f.startswith('cashbox-')]
if cashbox_files:
    # Sort cashbox files by modification time to get the most recent one
    latest_file = sorted(cashbox_files, key=lambda f: os.path.getmtime(os.path.join(cashbox_dir, f)))[-1]
    print(f"Importing from most recent cashbox file: {os.path.join(cashbox_dir, latest_file)}")
    import_data(os.path.join(cashbox_dir, latest_file))
else:
    print("No cashbox files found in the format cashbox-{dues|punishments|transaction}-YYYYMMDD-HHMMSS.csv")
    sys.exit(1)