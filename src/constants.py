"""
Constants for the project.
"""

# Global variable for tests directory - can be modified at runtime
TESTS_FOLDER = ".tests"
# Global variable for app directory - can be modified at runtime
APP_FOLDER = ".app"
SCRIPT_DIR = "scripts"

def set_tests_folder(tests_dir: str):
    """Set the global tests folder directory."""
    global TESTS_FOLDER
    TESTS_FOLDER = tests_dir

def get_tests_folder() -> str:
    """Get the current tests folder directory."""
    return TESTS_FOLDER

def set_app_folder(app_dir: str):
    """Set the global app folder directory."""
    global APP_FOLDER
    APP_FOLDER = app_dir

def get_app_folder() -> str:
    """Get the current app folder directory."""
    return APP_FOLDER
