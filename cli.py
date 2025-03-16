#!/usr/bin/env python3
"""
Command-line interface for Balance Up application.
Provides commands for various operations including:
- Importing penalties from CSV files
- Managing users and penalties
- Database operations
"""

import argparse
import sys
import os
import logging
from datetime import datetime

# Set up paths for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from app.utils.logging_config import setup_logging, get_logger
from app.config.settings import get_settings
from app.database import get_db
from app.services.csv_importer import CSVImporter
from app.services.user_utils import UserUtils
from app.database.models import User, Penalty

# Initialize logging
setup_logging()
logger = get_logger(__name__)
settings = get_settings()

def import_files(args):
    """Import files from the cashbox directory"""
    directory = args.directory or settings.IMPORT_DIRECTORY
    
    logger.info(f"Starting import from directory: {directory}")
    importer = CSVImporter()
    
    try:
        results = importer.process_import_directory(directory)
        print(f"Import completed successfully:")
        print(f"  - Punishments: {results['punishments']}")
        print(f"  - Transactions: {results['transactions']}")
        print(f"  - Dues: {results['dues']}")
        if results['unknown'] > 0:
            print(f"  - Unknown file types: {results['unknown']}")
    except Exception as e:
        logger.error(f"Error during import: {str(e)}")
        print(f"Import failed: {str(e)}")
        return 1
    
    return 0

def list_users(args):
    """List all users in the database"""
    try:
        with next(get_db()) as db:
            query = db.query(User)
            
            if args.search:
                search_term = f"%{args.search}%"
                query = query.filter(
                    (User.name.ilike(search_term)) | 
                    (User.email.ilike(search_term))
                )
                
            # Apply pagination if specified
            if args.limit:
                query = query.limit(args.limit)
            if args.skip:
                query = query.offset(args.skip)
                
            users = query.all()
            
            # Print results
            if not users:
                print("No users found")
                return 0
                
            print(f"Found {len(users)} users:")
            for user in users:
                print(f"ID: {user.id}")
                print(f"  Name: {user.name}")
                if user.email:
                    print(f"  Email: {user.email}")
                if user.phone:
                    print(f"  Phone: {user.phone}")
                    
                # Get balance
                balance = UserUtils.get_user_balance(db, user.id)
                print(f"  Balance: {balance}")
                print()
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        print(f"Failed to list users: {str(e)}")
        return 1
        
    return 0

def show_user(args):
    """Show details for a specific user"""
    try:
        with next(get_db()) as db:
            # Get user by ID or name
            user = None
            if args.id:
                user = UserUtils.get_user_by_id(db, args.id)
            elif args.name:
                user = UserUtils.get_user_by_name(db, args.name)
                
            if not user:
                print(f"User not found")
                return 1
                
            # Display user details
            print(f"User Details:")
            print(f"ID: {user.id}")
            print(f"Name: {user.name}")
            if user.email:
                print(f"Email: {user.email}")
            if user.phone:
                print(f"Phone: {user.phone}")
            print(f"Created: {user.created_at}")
            print(f"Updated: {user.updated_at}")
            print()
            
            # Get penalties
            penalties = db.query(Penalty).filter(Penalty.user_id == user.id).all()
            
            # Calculate balance
            unpaid_penalties = [p for p in penalties if not p.paid]
            paid_penalties = [p for p in penalties if p.paid]
            
            total_unpaid = sum(p.amount for p in unpaid_penalties)
            total_paid = sum(p.amount for p in paid_penalties)
            
            print(f"Penalties:")
            print(f"  Total unpaid: {len(unpaid_penalties)} (€{total_unpaid:.2f})")
            print(f"  Total paid: {len(paid_penalties)} (€{total_paid:.2f})")
            print()
            
            # Show penalties if requested
            if args.show_penalties:
                if not penalties:
                    print("No penalties found")
                else:
                    print("Penalty List:")
                    for penalty in penalties:
                        status = "PAID" if penalty.paid else "UNPAID"
                        print(f"  - ID: {penalty.penalty_id}")
                        print(f"    Amount: €{penalty.amount:.2f}")
                        print(f"    Status: {status}")
                        if penalty.reason:
                            print(f"    Reason: {penalty.reason}")
                        print(f"    Date: {penalty.date}")
                        if penalty.paid and penalty.paid_at:
                            print(f"    Paid at: {penalty.paid_at}")
                        print()
    except Exception as e:
        logger.error(f"Error showing user: {str(e)}")
        print(f"Failed to show user: {str(e)}")
        return 1
        
    return 0

def pay_penalty(args):
    """Mark a penalty as paid"""
    try:
        with next(get_db()) as db:
            # Find the penalty
            penalty = db.query(Penalty).filter(Penalty.penalty_id == args.id).first()
            
            if not penalty:
                print(f"Penalty not found with ID: {args.id}")
                return 1
                
            if penalty.paid:
                print(f"Penalty is already marked as paid (paid on {penalty.paid_at})")
                return 0
                
            # Mark as paid
            penalty.mark_as_paid()
            db.commit()
            
            # Get user
            user = db.query(User).filter(User.id == penalty.user_id).first()
            username = user.name if user else "Unknown User"
            
            print(f"Marked penalty {penalty.penalty_id} as paid")
            print(f"Amount: €{penalty.amount:.2f}")
            print(f"User: {username}")
            print(f"Paid at: {penalty.paid_at}")
            
    except Exception as e:
        logger.error(f"Error marking penalty as paid: {str(e)}")
        print(f"Failed to mark penalty as paid: {str(e)}")
        return 1
        
    return 0

def list_unpaid(args):
    """List all unpaid penalties"""
    try:
        with next(get_db()) as db:
            query = db.query(Penalty).filter(Penalty.paid == False)
            
            # Filter by user if specified
            if args.user:
                user = UserUtils.get_user_by_name(db, args.user)
                if not user:
                    print(f"User not found: {args.user}")
                    return 1
                    
                query = query.filter(Penalty.user_id == user.id)
                
            penalties = query.all()
            
            if not penalties:
                print("No unpaid penalties found")
                return 0
                
            # Group by user
            user_penalties = {}
            for penalty in penalties:
                if penalty.user_id not in user_penalties:
                    user_penalties[penalty.user_id] = []
                user_penalties[penalty.user_id].append(penalty)
                
            # Print results
            total_amount = sum(p.amount for p in penalties)
            print(f"Found {len(penalties)} unpaid penalties (Total: €{total_amount:.2f}):")
            print()
            
            for user_id, penalties in user_penalties.items():
                user = db.query(User).filter(User.id == user_id).first()
                username = user.name if user else "Unknown User"
                
                user_total = sum(p.amount for p in penalties)
                print(f"{username} - {len(penalties)} penalties (€{user_total:.2f}):")
                
                for penalty in penalties:
                    print(f"  - ID: {penalty.penalty_id}")
                    print(f"    Amount: €{penalty.amount:.2f}")
                    if penalty.reason:
                        print(f"    Reason: {penalty.reason}")
                    print(f"    Date: {penalty.date}")
                    print()
    except Exception as e:
        logger.error(f"Error listing unpaid penalties: {str(e)}")
        print(f"Failed to list unpaid penalties: {str(e)}")
        return 1
        
    return 0

def main():
    """Main entry point for CLI"""
    parser = argparse.ArgumentParser(
        description="Balance Up - Command-line interface for managing penalties",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Import command
    import_parser = subparsers.add_parser("import", help="Import files from cashbox directory")
    import_parser.add_argument("--directory", "-d", help="Directory to import from")
    
    # List users command
    list_users_parser = subparsers.add_parser("list-users", help="List all users")
    list_users_parser.add_argument("--search", "-s", help="Search term for filtering users")
    list_users_parser.add_argument("--limit", "-l", type=int, help="Limit number of results")
    list_users_parser.add_argument("--skip", type=int, help="Number of results to skip")
    
    # Show user command
    show_user_parser = subparsers.add_parser("show-user", help="Show details for a specific user")
    show_user_group = show_user_parser.add_mutually_exclusive_group(required=True)
    show_user_group.add_argument("--id", help="User ID")
    show_user_group.add_argument("--name", "-n", help="User name")
    show_user_parser.add_argument("--show-penalties", "-p", action="store_true", help="Show user penalties")
    
    # Pay penalty command
    pay_parser = subparsers.add_parser("pay", help="Mark a penalty as paid")
    pay_parser.add_argument("id", help="Penalty ID")
    
    # List unpaid penalties command
    unpaid_parser = subparsers.add_parser("unpaid", help="List all unpaid penalties")
    unpaid_parser.add_argument("--user", "-u", help="Filter by user name")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
        
    # Run appropriate command
    if args.command == "import":
        return import_files(args)
    elif args.command == "list-users":
        return list_users(args)
    elif args.command == "show-user":
        return show_user(args)
    elif args.command == "pay":
        return pay_penalty(args)
    elif args.command == "unpaid":
        return list_unpaid(args)
    else:
        parser.print_help()
        return 1

if __name__ == "__main__":
    sys.exit(main())