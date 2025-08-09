"""
Constants for the project.
"""

# Global variable for tests directory - can be modified at runtime
TESTS_FOLDER = ".tests"
SCRIPT_DIR = "scripts"

def set_tests_folder(tests_dir: str):
    """Set the global tests folder directory."""
    global TESTS_FOLDER
    TESTS_FOLDER = tests_dir

def get_tests_folder() -> str:
    """Get the current tests folder directory."""
    return TESTS_FOLDER
