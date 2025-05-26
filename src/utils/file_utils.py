import os
import shutil
from constants import TESTS_FOLDER, SCRIPT_DIR

def copy_common():
    """Copy all common scripts to the test directory.

    These scripts are to be used in the build, run and test phases.
    """
    
    base = os.path.abspath(TESTS_FOLDER)
    dest = os.path.join(base, "common")
    src = os.path.join(os.getcwd(), SCRIPT_DIR, "common")
    os.makedirs(dest, exist_ok=True)

    for item in os.listdir(src):
        src_path = os.path.join(src, item)
        dest_path = os.path.join(dest, item)

        if os.path.isdir(src_path):
            shutil.copytree(src_path, dest_path, dirs_exist_ok=True)
        else:
            if not os.path.exists(dest_path) or os.stat(src_path).st_mtime > os.stat(dest_path).st_mtime:
                shutil.copy2(src_path, dest_path)
