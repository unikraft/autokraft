"""
This module is the main entry point for the testing framework.
"""

import json
import logging
import os
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


def generate_target_configs(tester_config, app_config, system_config):
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
        t = TargetSetup(config, app_config, system_config)
        targets.append(t)

    return targets


def usage(argv0):
    """Prints the usage instructions for the script."""
    print(f"Usage: {argv0} <path/to/origina/app/dir>", file=sys.stderr)


def main():
    """Main entry point for the testing framework."""

    if len(sys.argv) != 2:
        usage(sys.argv[0])
        sys.exit(1)

    logger = logging.getLogger("test_framework")

    app_dir = os.path.abspath(sys.argv[1])
    if not os.path.exists(app_dir):
        logger.error(f"Not a file: {app_dir}")
        sys.exit(1)

    try:
        t = TesterConfig()
        a = AppConfig()
        a.generate_init(t)
        s = SystemConfig()

        copy_common()

        targets = generate_target_configs(t, a, s)

        for t in targets:
            t.generate()

        for target_config in targets:
            runner = TestRunner(target_config, app_dir)
            runner.run_test()

    finally:
        # TODO: Copy the test logs to the test-app-config directory
        # Cleanup the folder after running tests.
        # cleanup_folder()
        pass


if __name__ == "__main__":
    sys.exit(main())
