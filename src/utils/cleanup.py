"""
This module provides the method to clean up the test folder.
"""

import os
import shutil

from constants import TESTS_FOLDER


def cleanup_folder():
    """Clean up the .tests folder by removing it if it exists."""
    if os.path.exists(TESTS_FOLDER):
        print(f"Cleaning up: {TESTS_FOLDER}")
        shutil.rmtree(TESTS_FOLDER)
        print("Cleanup complete.")
