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
    print(f"Usage: {argv0} <path/to/tester.yaml>", file=sys.stderr)


def main():
    if len(sys.argv) != 2:
        usage(sys.argv[0])
        sys.exit(1)

    if not os.path.exists(sys.argv[1]):
        print(f"Not a file: {sys.argv[1]}")
        sys.exit(1)

    try:
        t = TesterConfig(sys.argv[1])
        a = AppConfig()
        a.generate_init(t)
        s = SystemConfig()

        copy_common()

        targets = generate_target_configs(t, a, s)
        for t in targets:
            t.generate()

    finally:
        # cleanup_folder()
        pass


if __name__ == "__main__":
    sys.exit(main())
