#!/usr/bin/env python3
"""
Script to fix linting issues by running black and isort on all Python files.
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and print the result."""
    print(f"\n{description}...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(f"Warnings/Errors: {result.stderr}")
        return result.returncode == 0
    except Exception as e:
        print(f"Error running command: {e}")
        return False


def main():
    """Main function to fix linting issues."""
    # Get all Python files
    root_files = list(Path(".").glob("*.py"))
    test_files = list(Path("tests").glob("*.py"))
    all_files = root_files + test_files
    
    print(f"Found {len(all_files)} Python files to process")
    
    # Run isort
    isort_cmd = ["isort", "--profile", "black", "--line-length", "100"] + [str(f) for f in all_files]
    if not run_command(isort_cmd, "Running isort to fix import sorting"):
        print("isort failed!")
        return 1
    
    # Run black
    black_cmd = ["black", "--line-length", "100"] + [str(f) for f in all_files]
    if not run_command(black_cmd, "Running black to fix code formatting"):
        print("black failed!")
        return 1
    
    # Run flake8 to check for remaining issues
    flake8_cmd = [
        "flake8", ".", "--count", "--select=E9,F63,F7,F82",
        "--show-source", "--statistics"
    ]
    if not run_command(flake8_cmd, "Running flake8 to check for syntax errors"):
        print("flake8 found syntax errors!")
        return 1
    
    print("\n✅ All linting issues fixed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
