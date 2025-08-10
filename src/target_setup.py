"""
This module provides the TargetSetup class to create setups for targets.
"""

import os

import yaml

from build_setup import BuildSetup
from run_setup import RunSetup
from constants import get_tests_folder


class TargetSetup:
    """Create setup for target.

    A target is defined by a build setup that generates a unikernel
    image and filesystem, and run setups that run the image and filesystem.
    """

    class_id = 1

    def __init__(self, config, app_config, system_config, session):
        """Initialize target setup.

        Use the config argument to initialize. Instantiate a BuildSetup class and
        multiple RunSetup classes.

        Consider the application configuration and the system configuration.
        """

        self.config = config
        self.id = TargetSetup.class_id
        TargetSetup.class_id += 1
        if app_config.config["test_dir"]:
            base = os.path.abspath(app_config.user_config["test_dir"])
        else:
            base = os.path.abspath(get_tests_folder())
        self.dir = os.path.join(base, f"{self.id:05d}")
        self.session_dir = session.session_dir
        self.build_config = BuildSetup(self.dir, self.config["build"], self.config, app_config)
        self.run_configs = []
        idx = 1
        for r in self.config["run"]["runs"]:
            if r["networking"] == "none" and app_config.config["networking"] is True:
                continue
            if r["networking"] != "none" and app_config.config["networking"] is False:
                continue
            if r["rootfs"] != "none" and (app_config.has_einitrd() or not app_config.has_rootfs()):
                continue
            if r["rootfs"] == "none" and not app_config.has_einitrd() and app_config.has_rootfs():
                continue
            run_dir = os.path.join(self.dir, f"run-{idx:02d}")
            idx += 1
            self.run_configs.append(
                RunSetup(
                    run_dir, r, self.config, self.build_config, app_config, system_config.get_arch()
                )
            )

    def generate(self):
        """Generate target directory.

        The target directory name is an index. Its contents are:

        - config.yaml: target / build configuration
        - build configuration files (Kraftfile, Dockerfile, root filesystem, defconfig)
        - run directories, also as indexes
        """

        # Create directory.
        os.mkdir(self.dir, mode=0o755)

        tests_index = self.dir.find(get_tests_folder())
        if tests_index == -1:
            raise ValueError(f"Target directory must be inside {get_tests_folder()} directory")
        
        tests_dir_structure = self.dir[tests_index + 1 :]

        # Creating a new path for the sessions
        # cwd + catalog_structure + session_name + test_dir_structure
        self.session_build_dir = os.path.join(self.session_dir, tests_dir_structure)

        # Generate config.yaml.
        with open(os.path.join(self.dir, "config.yaml"), "w", encoding="utf-8") as outfile:
            outfile.write(f"base: {self.config['base']}\n")
            yaml.dump(self.config["build"], outfile, default_flow_style=False)
            if self.config["run"]["vmm"]:
                outfile.write(f"vmm: {self.config['run']['vmm']['path']}\n")
        # Creating duplicate config.yaml in session directory
        os.makedirs(self.session_build_dir, exist_ok=True)
        with open(os.path.join(self.session_build_dir, "config.yaml"), "w", encoding="utf-8") as outfile:
            outfile.write(f"base: {self.config['base']}\n")
            yaml.dump(self.config["build"], outfile, default_flow_style=False)
            if self.config["run"]["vmm"]:
                outfile.write(f"vmm: {self.config['run']['vmm']['path']}\n")
        
        self.build_config.generate()
        for r in self.run_configs:
            os.mkdir(r.dir, mode=0o755)
            with open(os.path.join(r.dir, "config.yaml"), "w", encoding="utf-8") as outfile:
                yaml.dump(r.config, outfile, default_flow_style=False)

            # Creating duplicate runs/config.yaml in session directory
            tests_index = r.dir.find(get_tests_folder())
            if tests_index == -1:
                print(f"[ERROR]Target run directory must be inside {get_tests_folder()} directory")
                raise ValueError(f"Target run directory must be inside {get_tests_folder()} directory")

            tests_dir_structure = r.dir[tests_index + 1 :]
            session_run_dir = os.path.join(self.session_dir, tests_dir_structure)
            os.makedirs(session_run_dir, exist_ok=True)

            with open(os.path.join(session_run_dir, "config.yaml"), "w", encoding="utf-8") as outfile:
                yaml.dump(r.config, outfile, default_flow_style=False)
            
            r.generate()
