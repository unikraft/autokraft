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
from utils.file_utils import copy_common
from utils.logger import setup_logger
from utils.setup_session import SessionSetup


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


def initialize_environment(app_dir: str) -> bool:
    """
    Perform initial cleanup and setup configs needed before running tests.

    Args:
        app_dir: Path to the application directory to be tested

    Returns:
        bool: True if initialization succeeded, False otherwise
    """
    logger = logging.getLogger("test_framework")

    try:
        cwd = os.getcwd()

        # Call the cleanup script
        logger.info("Running cleanup script")
        cleanup_script = os.path.join(cwd, "scripts", "utils", "cleanup.sh")
        if os.path.exists(cleanup_script):
            result = subprocess.run([cleanup_script], check=True, text=True, capture_output=True)
            logger.debug(f"Cleanup output: {result.stdout}")
        else:
            logger.warning(f"Cleanup script not found: {cleanup_script}")

        # Call the setup script with app_dir as argument
        logger.info(f"Running setup script for {app_dir}")
        setup_script = os.path.join(cwd, "scripts", "utils", "setup.sh")
        if os.path.exists(setup_script):
            result = subprocess.run(
                [setup_script, app_dir], check=True, text=True, capture_output=True
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
        "--verbose", "-v", action="store_true", help="Enable verbose output (debug level logs)"
    )

    return parser.parse_args()


def main():
    """Main entry point for the testing framework."""

    args = parse_arguments()

    # Set up logger with appropriate verbosity
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logger("test_framework", level=log_level)

    logger = logging.getLogger("test_framework")
    logger.info("Main Started")

    app_dir = os.path.abspath(args.app_dir)
    if not os.path.exists(app_dir):
        logger.error(f"Not a file: {app_dir}")
        sys.exit(1)

    if not initialize_environment(app_dir):
        logger.error("Environment initialization failed. Exiting.")
        sys.exit(1)

    try:
        session = SessionSetup(app_dir, custom_session_name=args.test_session_name)
        logger.info(f"Session initialized: {session.session_name}")
        t = TesterConfig()
        a = AppConfig(app_dir)
        a.generate_init(t)
        s = SystemConfig()

        copy_common()

        targets = generate_target_configs(t, a, s, session=session)

        for t in targets:
            t.generate()

        for target_config in targets:
            runner = TestRunner(target_config, app_dir, session)
            runner.run_test()
        logger.info("All tests completed successfully.")

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    sys.exit(main())
