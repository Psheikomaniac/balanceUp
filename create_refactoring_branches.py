#!/usr/bin/env python3
"""
Branch Creation Automation Script for Balance Up API Refactoring

This script creates a hierarchical branching structure for the Balance Up API 
refactoring project, with main improvement area branches and feature branches.
"""

import subprocess
import sys
import os

# Main improvement areas with their corresponding feature branches
BRANCH_STRUCTURE = {
    "security": [
        "parameterize-sql-queries",
        "env-config-management",
        "input-validation",
        "add-auth-middleware",
        "restrict-cors",
    ],
    "docs": [
        "create-readme",
        "add-module-docstrings",
        "add-function-docstrings",
        "add-api-documentation",
        "create-architecture-diagram",
    ],
    "naming": [
        "standardize-terminology",
        "fix-file-naming",
        "rename-punishment-to-penalty",
        "normalize-database-fields",
        "align-variable-naming",
    ],
    "errors": [
        "add-custom-exceptions",
        "implement-logging",
        "add-transaction-rollbacks",
        "standardize-error-handling",
        "error-boundary-middleware",
    ],
    "modular": [
        "extract-db-connection",
        "refactor-large-functions",
        "create-utils-module",
        "implement-base-classes",
        "refactor-repetitive-code",
    ],
}

def run_git_command(command):
    """Run a git command and handle errors."""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            check=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {command}")
        print(f"Error message: {e.stderr}")
        return None

def verify_git_repo():
    """Verify we're in a git repository."""
    if not os.path.exists(".git"):
        git_root = run_git_command("git rev-parse --show-toplevel")
        if not git_root:
            print("Error: This does not appear to be a git repository.")
            print("Please run this script from the root of your git repository.")
            sys.exit(1)

def get_current_branch():
    """Get the current git branch."""
    return run_git_command("git branch --show-current")

def create_branches():
    """Create all branches for the refactoring project."""
    verify_git_repo()
    starting_branch = get_current_branch()
    
    print(f"Starting from branch: {starting_branch}")
    print("Creating branch structure for Balance Up API refactoring...")
    
    # First, make sure starting branch is up to date
    run_git_command(f"git checkout {starting_branch}")
    
    # Create and track branches for each improvement area
    for area, features in BRANCH_STRUCTURE.items():
        main_branch = f"main-{area}"
        
        # Create main branch for this area
        print(f"\nCreating main branch: {main_branch}")
        run_git_command(f"git checkout -b {main_branch} {starting_branch}")
        
        # Create feature branches for this area
        for feature in features:
            feature_branch = f"feat/{area}/{feature}"
            print(f"  Creating feature branch: {feature_branch}")
            run_git_command(f"git checkout -b {feature_branch} {main_branch}")
            
            # Add a README file with branch purpose to make the branch trackable
            with open("BRANCH_README.md", "w") as f:
                f.write(f"# Feature Branch: {feature_branch}\n\n")
                f.write(f"This branch is for implementing: {feature.replace('-', ' ').title()}\n")
                f.write(f"Parent branch: {main_branch}\n")
                f.write(f"Created by automation script on: {run_git_command('date')}\n")
            
            # Commit the README
            run_git_command('git add BRANCH_README.md')
            run_git_command(f'git commit -m "[{area}] chore: initialize {feature} branch"')
            
            # Return to the main branch for this area
            run_git_command(f"git checkout {main_branch}")
        
        # Return to the starting branch
        run_git_command(f"git checkout {starting_branch}")
    
    print("\nBranch creation complete!")
    print(f"Returned to starting branch: {get_current_branch()}")
    print("\nTo start working on a specific improvement area:")
    print("  git checkout main-<area>")
    print("\nTo work on a specific feature:")
    print("  git checkout feat/<area>/<feature>")

if __name__ == "__main__":
    create_branches()