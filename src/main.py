"""
This module is the main entry point for the testing framework.
"""

import argparse
import json
import logging
import os
import subprocess
import sys

from app_config import AppConfig
from build_setup import BuildSetup
from run_setup import RunSetup
from system_config import SystemConfig
from target_setup import TargetSetup
from test_runner import TestRunner
from tester_config import TesterConfig
from utils.cleanup import cleanup_folder
from utils.create_runtime_kernel import create_examples_runtime
from utils.file_utils import copy_common
from utils.logger import setup_logger
from utils.setup_session import SessionSetup
from constants import set_tests_folder, get_tests_folder, set_app_folder, get_app_folder


def generate_target_configs(tester_config, app_config, system_config, session):
    """Generate all possible target configurations for given application on given system.

    A target configuration will generate the corresponding build configuration and
    run configurations.

    Return list of all target configurations in `targets` variable.
    """

    for plat, arch in app_config.config["targets"]:
        vmms = system_config.get_vmms(plat, arch)
        compilers = system_config.get_compilers(plat, arch)
        build_tools = BuildSetup.get_build_tools(plat, arch)
        run_tools = RunSetup.get_run_tools(plat, arch)
        tester_config.generate_target_configs(
            plat, arch, system_config.get_arch(), vmms, compilers, build_tools, run_tools
        )

    targets = []
    for config in tester_config.get_target_configs():
        t = TargetSetup(config, app_config, system_config, session=session)
        targets.append(t)

    return targets


def initialize_environment(app_dir: str, tests_dir: str = "", app_folder: str = "") -> bool:
    """
    Perform initial cleanup and setup configs needed before running tests.

    Args:
        app_dir: Path to the application directory to be tested
        tests_dir: Custom tests directory name (optional)
        app_folder: Custom app folder name (optional)

    Returns:
        bool: True if initialization succeeded, False otherwise
    """
    logger = logging.getLogger("test_framework")

    try:
        cwd = os.getcwd()

        # Call the cleanup script with custom directories
        logger.info("Running cleanup script")
        cleanup_script = os.path.join(cwd, "scripts", "utils", "cleanup.sh")
        if os.path.exists(cleanup_script):
            cleanup_args = [cleanup_script]
            if tests_dir != "" and tests_dir is not None:
                cleanup_args.append(tests_dir)
            if app_folder != "" and app_folder is not None:
                cleanup_args.append(app_folder)
            result = subprocess.run(cleanup_args, check=True, text=True, capture_output=True)
            logger.debug(f"Cleanup output: {result.stdout}")
        else:
            logger.warning(f"Cleanup script not found: {cleanup_script}")

        # Call the setup script with app_dir and custom app_folder as arguments
        logger.info(f"Running setup script for {app_dir}")
        setup_script = os.path.join(cwd, "scripts", "utils", "setup.sh")
        if os.path.exists(setup_script):
            setup_args = [setup_script, app_dir]
            print(setup_args)
            if app_folder != "" and app_folder is not None:
                setup_args.append(app_folder)
            result = subprocess.run(
                setup_args, check=True, text=True, capture_output=True
            )
            logger.debug(f"Setup output: {result.stdout}")
        else:
            logger.warning(f"Setup script not found: {setup_script}")

        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Script execution failed: {e}")
        logger.error(f"Error output: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Environment initialization failed: {str(e)}")
        return False


def parse_target_numbers(target_arg):
    """Parse target numbers from various input formats.
    
    Supports:
    - Comma separated: "1,3,5"
    - Space separated: "1 3 5" 
    - Ranges: "1:5" or "1-5"
    - Mixed: "1,3:5,7"
    
    Args:
        target_arg: String containing target numbers in supported formats
        
    Returns:
        set: Set of target numbers (0-based indexing)
    """
    if not target_arg:
        return set()
    
    target_numbers = set()
    
    # Split by comma first to handle mixed formats
    parts = target_arg.replace(' ', ',').split(',')
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
            
        # Handle range notation (: or -)
        if ':' in part or '-' in part:
            separator = ':' if ':' in part else '-'
            try:
                start, end = part.split(separator, 1)
                start_num = int(start.strip()) - 1  # Convert to 0-based
                end_num = int(end.strip()) - 1      # Convert to 0-based
                if start_num <= end_num:
                    target_numbers.update(range(start_num, end_num + 1))
            except ValueError:
                raise ValueError(f"Invalid range format: {part}")
        else:
            # Handle single number
            try:
                target_numbers.add(int(part.strip()) - 1)  # Convert to 0-based
            except ValueError:
                raise ValueError(f"Invalid target number: {part}")
    
    return target_numbers


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Testing Framework")
    parser.add_argument(
        "app_dir", help="Path to the application directory which needs to be tested"
    )
    parser.add_argument(
        "--test-session-name",
        "-n",
        dest="test_session_name",
        help="Custom test session name (random will be selected if not provided)",
    )
    parser.add_argument(
        "--tests-dir",
        "-d",
        dest="tests_dir",
        help="Custom tests directory name (default: .tests). Will be created if it doesn't exist.",
    )
    parser.add_argument(
        "--app-dir-name",
        "-a",
        dest="app_dir_name",
        help="Custom app directory name (default: .app). Will be created if it doesn't exist.",
    )
    parser.add_argument(
        "--target-no",
        "-t",
        dest="target_numbers",
        help="Target numbers to test. Supports: comma-separated (1,3,5), space-separated (1 3 5), ranges (1:5 or 1-5), or mixed (1,3:5,7). Uses 1-based indexing.",
    )
    parser.add_argument(
        "--generate-only",
        "-g",
        action="store_true",
        help="Only generate target configurations and exit without running tests",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output (debug level logs)"
    )

    return parser.parse_args()


def touch_makefile_uk():
    """Touch Makefile.uk in the current working directory."""
    makefile_path = os.path.join(os.getcwd(), "Makefile.uk")
    with open(makefile_path, "a"):
        os.utime(makefile_path, None)


def main():
    """Main entry point for the testing framework."""

    args = parse_arguments()

    # Set custom directories if provided
    if args.tests_dir:
        set_tests_folder(args.tests_dir)

    if args.app_dir_name:
        set_app_folder(args.app_dir_name)

    # Set up logger with appropriate verbosity
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logger("test_framework", level=log_level)

    logger = logging.getLogger("test_framework")
    logger.info("Main Started")

    app_dir = os.path.abspath(args.app_dir)
    if not os.path.exists(app_dir):
        logger.error(f"Not a file: {app_dir}")
        sys.exit(1)

    if not initialize_environment(app_dir, args.tests_dir, args.app_dir_name):
        logger.error("Environment initialization failed. Exiting.")
        sys.exit(1)

    # Touch Makefile.uk before starting testing
    touch_makefile_uk()

    try:
        session = SessionSetup(app_dir, custom_session_name=args.test_session_name)
        logger.info(f"Session initialized: {session.session_name}")
        logger.info(f"Using tests directory: {get_tests_folder()}")
        logger.info(f"Using app directory: {get_app_folder()}")
        t = TesterConfig()
        a = AppConfig(app_dir)
        s = SystemConfig()

        # here we can generate the runtimes if not created yet
        if a.config["runtime"] is not None:
            # TODO: Check if runtimes already exist l: 
            # check if the runtime_kernel/a.config['runtime'].split(":")[0] directory is present or not

            logger.info(f"Generating runtimes...{a.config['runtime']}")

            # Call the new_session.sh script
            cwd = os.getcwd()
            # TODO: Later need to pass the specific runtime
            # Currently its only creating base runtime.
            runtime_name = a.config['runtime'].split(":")[0]
            
            # Extract catalog base path from app_dir
            app_dir_parts = app_dir.split('catalog')
            if len(app_dir_parts) > 1:
                catalog_base_path = app_dir_parts[0] + 'catalog/library'
                catalog_runtime_path = os.path.join(catalog_base_path, runtime_name)
            else:
                logger.error(f"Could not extract catalog path from app_dir: {app_dir}")
                sys.exit(1)
            logger.info(f"Catalog runtime path: {catalog_runtime_path}")
            new_session_script = os.path.join(cwd, "scripts", "utils", "new_session.sh")
            if os.path.exists(new_session_script):
                try:
                    result = subprocess.run(
                        [new_session_script, catalog_runtime_path], check=True, text=True, capture_output=True
                    )
                    logger.debug(f"New session script output: {result.stdout}")
                except subprocess.CalledProcessError as e:
                    logger.error(f"New session script execution failed: {e}")
                    logger.error(f"Error output: {e.stderr}")
                    sys.exit(1)
            else:
                logger.warning(f"New session script not found: {new_session_script}")
            # TODO: Also remove this non persistent session before exiting (from the logs?)
        else:
            logger.info("Runtimes already exist, skipping generation.")
        copy_common()

        if not a.is_example():
            # Generating the initrd.cpio
            a.generate_init(t)

        targets = generate_target_configs(t, a, s, session=session)

        for t in targets:
            logger.info(f"Generating target configuration: {t.id} at {t.dir}")
            t.generate()

        # Parse target numbers if provided
        selected_targets = None
        if args.target_numbers:
            try:
                selected_targets = parse_target_numbers(args.target_numbers)
                logger.info(f"Selected target numbers: {sorted([n+1 for n in selected_targets])}")
                
                # Validate target numbers are within range
                if selected_targets and max(selected_targets) >= len(targets):
                    logger.error(f"Target number out of range. Available targets: 1-{len(targets)}")
                    sys.exit(1)
            except ValueError as e:
                logger.error(f"Invalid target number format: {e}")
                sys.exit(1)
        else:
            selected_targets = list(range(len(targets)))

        logger.info(f"Generated {len(targets)} target configuration(s) successfully.")

        # If example, then create the key target runtimes.
        if a.is_example():
            logger.info("Generating key target runtimes for example application.")
            runtime_name = a.config['runtime'].split(":")[0]
            create_examples_runtime(selected_targets, targets, runtime_name)


        # Exit early if generate-only flag is set
        if args.generate_only:
            logger.info("Generate-only mode enabled. Exiting without running tests.")
            return 0

        # call app_init_fs.sh file for examples
        if a.is_example():
            logger.info("Running app_init_fs.sh for example application.")
            a.generate_init(t)

        # Copy log files from .tests directory to session_dir
        tests_dir = get_tests_folder()
        if os.path.exists(tests_dir):
            for file_name in os.listdir(tests_dir):
                if file_name.endswith(".log"):
                    source_path = os.path.join(tests_dir, file_name)
                    destination_path = os.path.join(session.session_dir, file_name)
                    try:
                        logger.info(f"Copying log file {file_name} to session directory.")
                        os.makedirs(session.session_dir, exist_ok=True)
                        with open(source_path, "rb") as src, open(destination_path, "wb") as dst:
                            dst.write(src.read())
                    except Exception as e:
                        logger.error(f"Failed to copy log file {file_name}: {e}")
        else:
            logger.warning(f"Tests directory not found: {tests_dir}")
        

        # Run tests for selected or all targets
        tests_run = 0
        for test_no, target_config in enumerate(targets):
            # Skip if specific targets selected and this isn't one of them
            if selected_targets is not None and test_no not in selected_targets:
                logger.debug(f"Skipping target {test_no + 1}")
                continue
                
            logger.info(f"Running target {test_no + 1} of {len(targets)}")
            runner = TestRunner(target_config, app_dir, session)
            runner.run_test()
            tests_run += 1
            
        logger.info(f"Completed {tests_run} test(s) successfully.")

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    sys.exit(main())
