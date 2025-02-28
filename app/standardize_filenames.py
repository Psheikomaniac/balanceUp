#!/usr/bin/env python3
import os
import re
import sys
import csv
from datetime import datetime

def detect_file_type(file_path):
    """Try to detect file type by reading headers"""
    try:
        with open(file_path, mode='r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file, delimiter=';')
            headers = reader.fieldnames
            if headers:
                if any(h.startswith('penalty_') or h.startswith('penatly_') for h in headers):
                    return 'punishments'
                elif any(h.startswith('due_') for h in headers):
                    return 'dues'
                elif any(h.startswith('transaction_') for h in headers):
                    return 'transactions'
    except Exception:
        pass
    return None

def standardize_filenames(directory):
    """
    Standardize filenames in the cashbox directory to follow the format:
    YYYYMMDD_{type}.csv
    """
    print(f"Scanning directory: {directory}")
    standard_pattern = re.compile(r'^\d{8}_(dues|punishments|transactions)\.csv$')
    
    for filename in os.listdir(directory):
        if not filename.endswith('.csv'):
            continue
            
        if standard_pattern.match(filename):
            print(f"File already has standard name: {filename}")
            continue
            
        # Check for cashbox pattern
        cashbox_pattern = re.compile(r'^cashbox-(dues|punishments|transactions)-(\d{2})-(\d{2})-(\d{4})-\d{6}\.csv$')
        match = cashbox_pattern.match(filename)
        
        if match:
            file_type, day, month, year = match.groups()
            new_filename = f"{year}{month}{day}_{file_type}.csv"
            old_path = os.path.join(directory, filename)
            new_path = os.path.join(directory, new_filename)
            
            print(f"Renaming {filename} -> {new_filename}")
            try:
                if os.path.exists(new_path):
                    print(f"Error: Target file {new_filename} already exists. Skipping.")
                    continue
                os.rename(old_path, new_path)
            except Exception as e:
                print(f"Error renaming file: {e}")
        else:
            # Try to find date pattern in the filename - interpret as YYYYMMDD
            date_pattern = re.compile(r'^(\d{4})(\d{2})(\d{2})\.csv$')
            match = date_pattern.match(filename)
            
            if match:
                year, month, day = match.groups()
                
                # Detect file type
                file_path = os.path.join(directory, filename)
                file_type = detect_file_type(file_path)
                
                if not file_type:
                    file_type = "transactions"  # Default if detection fails
                
                new_filename = f"{year}{month}{day}_{file_type}.csv"
                old_path = os.path.join(directory, filename)
                new_path = os.path.join(directory, new_filename)
                
                print(f"Renaming {filename} -> {new_filename} (detected type: {file_type})")
                try:
                    if os.path.exists(new_path):
                        print(f"Error: Target file {new_filename} already exists. Skipping.")
                        continue
                    os.rename(old_path, new_path)
                except Exception as e:
                    print(f"Error renaming file: {e}")
            else:
                print(f"Could not determine date format for: {filename}")

if __name__ == "__main__":
    cashbox_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cashbox')
    standardize_filenames(cashbox_dir)