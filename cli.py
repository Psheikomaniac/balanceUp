#!/usr/bin/env python3
import click
import os
import sys
from pathlib import Path

# Add the project root directory to Python path
root_dir = Path(__file__).parent.absolute()
sys.path.append(str(root_dir))

from app.utils.logging_config import setup_logging, get_logger
from app.database.migrate_db import migrate_db
from app.database.test_migration import test_migration

# Set up logging
setup_logging()
logger = get_logger(__name__)

@click.group()
def cli():
    """Command line interface for the Balance Up application."""
    pass

@cli.group()
def db():
    """Database management commands."""
    pass

@db.command("migrate")
@click.option("--test", is_flag=True, help="Run in test mode without modifying the actual database")
def run_migration(test):
    """Migrate the database to the latest schema."""
    if test:
        logger.info("Running migration in test mode...")
        success = test_migration()
        if success:
            click.echo("Migration test completed successfully!")
        else:
            click.echo("Migration test failed!")
            sys.exit(1)
    else:
        logger.info("Running database migration...")
        try:
            migrate_db()
            click.echo("Database migration completed successfully!")
        except Exception as e:
            click.echo(f"Error during migration: {str(e)}")
            sys.exit(1)

@cli.group()
def import_data():
    """Data import commands."""
    pass

@import_data.command("csv")
@click.option("--directory", "-d", help="Directory containing CSV files to import")
def import_csv(directory):
    """Import data from CSV files."""
    from app.services.csv_importer import CSVImporter
    
    logger.info(f"Importing CSV data from directory: {directory}")
    importer = CSVImporter()
    try:
        stats = importer.process_import_directory(directory)
        click.echo("Import completed successfully!")
        click.echo(f"Imported:")
        click.echo(f"  - {stats['punishments']} punishments")
        click.echo(f"  - {stats['transactions']} transactions")
        click.echo(f"  - {stats['dues']} dues")
    except Exception as e:
        click.echo(f"Error during import: {str(e)}")
        sys.exit(1)

@cli.group()
def users():
    """User management commands."""
    pass

@users.command("list")
@click.option("--with-penalties", is_flag=True, help="Include penalties in output")
def list_users(with_penalties):
    """List all users."""
    from app.database import get_db
    from app.database import crud
    
    logger.info("Listing users...")
    try:
        with next(get_db()) as db:
            users_data = crud.get_users(db)
            click.echo(f"Found {len(users_data)} users:")
            
            for user in users_data:
                click.echo(f"User: {user.name} (ID: {user.id})")
                if with_penalties:
                    penalties = crud.get_user_penalties(db, user.id)
                    if penalties:
                        click.echo(f"  Penalties: {len(penalties)}")
                        for p in penalties:
                            status = "PAID" if p.paid else "UNPAID"
                            click.echo(f"  - {p.amount:.2f}: {p.reason} [{status}]")
                    else:
                        click.echo("  No penalties")
                    click.echo(f"  Balance: {user.total_unpaid_penalties:.2f}")
    except Exception as e:
        click.echo(f"Error: {str(e)}")
        sys.exit(1)

@users.command("add")
@click.option("--name", required=True, help="User name")
@click.option("--email", help="User email")
@click.option("--phone", help="User phone number")
def add_user(name, email, phone):
    """Add a new user."""
    from app.database import get_db
    from app.database import crud
    from app.database import schemas
    
    logger.info(f"Adding user: {name}")
    try:
        with next(get_db()) as db:
            user_data = schemas.UserCreate(
                name=name,
                email=email,
                phone=phone
            )
            user = crud.create_user(db, user_data)
            click.echo(f"User added successfully: {user.name} (ID: {user.id})")
    except Exception as e:
        click.echo(f"Error: {str(e)}")
        sys.exit(1)

@cli.group()
def penalties():
    """Penalty management commands."""
    pass

@penalties.command("list")
@click.option("--paid", is_flag=True, help="Show only paid penalties")
@click.option("--unpaid", is_flag=True, help="Show only unpaid penalties")
def list_penalties(paid, unpaid):
    """List penalties."""
    from app.database import get_db
    from app.database import crud
    
    logger.info("Listing penalties...")
    try:
        with next(get_db()) as db:
            # Determine paid filter
            paid_filter = None
            if paid and not unpaid:
                paid_filter = True
            elif unpaid and not paid:
                paid_filter = False
                
            penalties_data = crud.get_penalties(db, paid=paid_filter)
            click.echo(f"Found {len(penalties_data)} penalties:")
            
            for p in penalties_data:
                status = "PAID" if p.paid else "UNPAID"
                user = crud.get_user(db, p.user_id)
                username = user.name if user else "Unknown User"
                click.echo(f"{username}: {p.amount:.2f} - {p.reason} [{status}]")
    except Exception as e:
        click.echo(f"Error: {str(e)}")
        sys.exit(1)

@penalties.command("add")
@click.option("--user-id", required=True, help="User ID")
@click.option("--amount", required=True, type=float, help="Penalty amount")
@click.option("--reason", help="Penalty reason")
def add_penalty(user_id, amount, reason):
    """Add a new penalty."""
    from app.database import get_db
    from app.database import crud
    from app.database import schemas
    
    logger.info(f"Adding penalty for user {user_id}: {amount}")
    try:
        with next(get_db()) as db:
            # Check if user exists
            user = crud.get_user(db, user_id)
            if not user:
                click.echo(f"Error: User with ID {user_id} not found")
                sys.exit(1)
                
            penalty_data = schemas.PenaltyCreate(
                user_id=user_id,
                amount=amount,
                reason=reason
            )
            penalty = crud.create_penalty(db, penalty_data)
            click.echo(f"Penalty added successfully: {penalty.amount} for {user.name}")
    except Exception as e:
        click.echo(f"Error: {str(e)}")
        sys.exit(1)

@penalties.command("mark-paid")
@click.option("--penalty-id", required=True, help="Penalty ID")
def mark_penalty_paid(penalty_id):
    """Mark a penalty as paid."""
    from app.database import get_db
    from app.database import crud
    
    logger.info(f"Marking penalty {penalty_id} as paid")
    try:
        with next(get_db()) as db:
            penalty = crud.mark_penalty_paid(db, penalty_id)
            if penalty:
                user = crud.get_user(db, penalty.user_id)
                username = user.name if user else "Unknown User"
                click.echo(f"Marked penalty as paid: {penalty.amount} for {username}")
            else:
                click.echo(f"Error: Penalty with ID {penalty_id} not found")
                sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    cli()