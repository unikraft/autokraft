import os
import shutil

from constants import TESTS_FOLDER


def cleanup_folder():
    if os.path.exists(TESTS_FOLDER):
        print(f"Cleaning up: {TESTS_FOLDER}")
        shutil.rmtree(TESTS_FOLDER)
        print("Cleanup complete.")
