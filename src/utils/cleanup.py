"""
This module provides the method to clean up the test folder.
"""

import os
import shutil

from constants import get_tests_folder


def cleanup_folder():
    """Clean up the tests folder by removing it if it exists."""
    tests_folder = get_tests_folder()
    if os.path.exists(tests_folder):
        print(f"Cleaning up: {tests_folder}")
        shutil.rmtree(tests_folder)
        print("Cleanup complete.")
