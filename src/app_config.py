"""
This module defines the AppConfig class, which is used to extract and store application
configuration.
"""

import os
import subprocess
import sys

import yaml

from constants import SCRIPT_DIR, get_tests_folder
from tester_config import TesterConfig
from utils.base import Loggable


class AppConfig(Loggable):
    """Store application configuration.

    Configuration is read from the application configuration file (typically
    `Kraftfile`) and the user configuration file (typically `config.yaml`).
    """

    def has_template(self):
        """Check if application config is a template.

        A template generally means that the application is running in
        binary-compatibility mode and using the ELF Loader.

        Return true or false.
        """

        return self.config["template"] is not None

    def has_einitrd(self):
        """Check if application is conifgured to use an embedded initial
        ramdisk.

        This is generally configured in the `Kraftfile` by an option such as
        `CONFIG_LIBVFSCORE_AUTOMOUNT_CI_EINITRD`.

        Return true or false.
        """

        return self.einitrd

    def is_runtime(self):
        """Check if application is a binary-compatibility runtime.

        This means that the application builds a kernel image. And the kernel
        image can then be used to run applications using binary-compatibility
        mode.

        Return true or false.
        """

        return self.is_kernel()

    def is_kernel(self):
        """Check if application builds into a kernel image.

        The alternative is the application uses a pre-existing runtime, and
        doesn't require the building of a kernel.

        Return true or false.
        """

        return self.config["unikraft"] is not None

    def is_example(self):
        """Check if application is an example.

        An example application uses a pre-existing runtime / kernel. There is
        no kernel build phase.

        Return true or false.
        """

        return not self.is_runtime()

    def is_bincompat(self):
        """Check if application is a binary-compatible runtime.

        If the application uses a template, that template is ELF Loader, so
        the application is building into a binary-compatible runtime.

        Return true or false.
        """

        return self.has_template()

    def has_networking(self):
        """Check if application has networking.

        The networking option is part of the `config.yaml` file.

        Return true or false.
        """

        return self.config["networking"]

    def has_rootfs(self):
        """Check if application has a root filesystem.

        The root filesystem is part of the `Kraftfile`.

        Return true or false.
        """

        return self.config["rootfs"]

    def _get_targets_from_runtime(self):
        """Get targets (as pair of plat and arch) from runtime package.

        Parse the `kraft pkg` output and extract runtime targets. This is
        useful for examples, that don't specify targets in the `Kraftfile`.
        But they specify a runtime that specifies targets.

        Populate the self.config['targets'] array as array of (plat, arch)
        pairs.
        """

        kraft_proc = subprocess.Popen(
            ["kraft", "pkg", "info", "--log-level", "panic", self.config["runtime"], "-o", "json"],
            stdout=subprocess.PIPE,
        )
        jq_proc = subprocess.Popen(
            ["jq", "-r", ".[] | .plat"], stdin=subprocess.PIPE, stdout=subprocess.PIPE
        )
        kraft_output, _ = kraft_proc.communicate()
        jq_out, _ = jq_proc.communicate(kraft_output)

        targets = []
        for full_plat in jq_out.decode().split("\n"):
            if full_plat:
                plat = full_plat.split("/")[0]
                arch = full_plat.split("/")[1]
                targets.append((plat, arch))
            self.config["targets"] = targets

    def _parse_user_config(self, run_config_file):
        """Parse config.yaml file.

        Populate corresponding entries in self.config.
        """
        relative_path = self.app_dir.split("/catalog")[-1]
        run_config_path = os.path.join("test-app-config/catalog" + relative_path, run_config_file)
        
        with open(run_config_path, "r", encoding="utf-8") as stream:
            data = yaml.safe_load(stream)

        self.config["networking"] = False

        if not "Networking" in data["RunMetadata"].keys():
            self.config["networking"] = False
        else:
            self.config["networking"] = data["RunMetadata"]["Networking"]

        if not "test_dir" in data.keys():
            self.config["test_dir"] = None
        else:
            self.config["test_dir"] = data["test_dir"]

        if not "Memory" in data["RunMetadata"].keys():
            self.logger.warning(f"Error: 'memory' attribute is not defined in {run_config_path}.")
            sys.exit(1)
        else:
            self.config["memory"] = data["RunMetadata"]["Memory"]

        if not "ExposedPort" in data["RunMetadata"].keys():
            self.config["exposed_port"] = None
            self.config["public_port"] = None
        else:
            self.config["exposed_port"] = data["RunMetadata"]["ExposedPort"]
            self.config["public_port"] = data["RunMetadata"]["PublicPort"]

    def _parse_app_config(self, app_config_file):
        """Parse Kraftfile.

        Populate corresponding entries in self.config.
        """

        with open(app_config_file, "r", encoding="utf-8") as stream:
            data = yaml.safe_load(stream)

        self.einitrd = False
        self.config["unikraft"] = None
        if "unikraft" in data.keys():
            self.config["unikraft"] = {}
            if isinstance(data["unikraft"], dict):
                if "kconfig" in data["unikraft"].keys():
                    self.config["unikraft"]["kconfig"] = data["unikraft"]["kconfig"]
                    if (
                        "CONFIG_LIBVFSCORE_AUTOMOUNT_CI_EINITRD"
                        in self.config["unikraft"]["kconfig"].keys()
                        and self.config["unikraft"]["kconfig"][
                            "CONFIG_LIBVFSCORE_AUTOMOUNT_CI_EINITRD"
                        ]
                        == "y"
                    ):
                        self.einitrd = True
                        self.config["unikraft"]["kconfig"].pop(
                            "CONFIG_LIBVFSCORE_AUTOMOUNT_CI_EINITRD"
                        )
                        self.config["unikraft"]["kconfig"].pop("CONFIG_LIBVFSCORE_AUTOMOUNT_CI")

        if not "template" in data.keys():
            self.config["template"] = None
        else:
            if isinstance(data["template"], dict):
                if "source" in data["template"].keys():
                    self.config["template"] = data["template"]["source"].split("/")[-1]
                    if self.config["template"].endswith(".git"):
                        self.config["template"] = self.config["template"][:-4]
                else:
                    self.config["template"] = None
            else:
                self.config["template"] = data["template"].split("/")[-1]
                if self.config["template"].endswith(".git"):
                    self.config["template"] = self.config["template"][:-4]

        if not "name" in data.keys():
            self.config["name"] = os.path.basename(os.getcwd())
        else:
            self.config["name"] = data["name"]

        if not "runtime" in data.keys():
            self.config["runtime"] = None
        else:
            self.config["runtime"] = data["runtime"]
            if self.is_example():
                self.config["runtime"] = self.config["runtime"].split(":")[0] + ":local"

        if not "targets" in data.keys():
            self.config["targets"] = None
            if self.is_example():
                self._get_targets_from_runtime()
        else:
            targets = []
            for t in data["targets"]:
                plat = t.split("/")[0]
                arch = t.split("/")[1]
                targets.append((plat, arch))
            self.config["targets"] = targets

        if not "cmd" in data.keys():
            self.config["cmd"] = None
        else:
            self.config["cmd"] = " ".join(c for c in data["cmd"])

        if not "rootfs" in data.keys():
            self.config["rootfs"] = None
        else:
            self.config["rootfs"] = data["rootfs"]

        self.config["libraries"] = {}
        if "libraries" in data.keys():
            for l in data["libraries"].keys():
                self.config["libraries"][l] = {}
                self.config["libraries"][l]["kconfig"] = {}
                if isinstance(data["libraries"][l], dict):
                    if "kconfig" in data["libraries"][l].keys():
                        self.config["libraries"][l]["kconfig"] = data["libraries"][l]["kconfig"]

    def generate_init(self, tester_config: TesterConfig):
        """Generate filesystem initialization script.

        The script (`app_fs_init.sh`) is generated in the top-level test
        directory. It is used to initialize the filesystem before other build
        or run steps.
        """

        if self.config["test_dir"]:
            # shank: Instance of 'AppConfig' has no 'user_config' member
            test_dir = os.path.abspath(self.config["test_dir"])
        else:
            test_dir = os.path.abspath(get_tests_folder())
        if self.config["rootfs"]:
            rootfs = os.path.join(os.getcwd(), ".app", self.config["rootfs"])
        else:
            rootfs = ""
        init_dir = os.getcwd()
        test_app_dir = os.path.join(init_dir, ".app")
        base = tester_config.config["source"]["base"]

        name = self.config["name"]

        if self.has_template():
            app_dir = os.path.join(os.path.join(base, "apps"), self.config["template"])
        else:
            app_dir = os.getcwd()

        with open(os.path.join(SCRIPT_DIR, "tpl_app_fs_init.sh"), "r", encoding="utf-8") as stream:
            raw_content = stream.read()

        content = raw_content.format(**locals())

        os.makedirs(test_dir, exist_ok=True)

        with open(os.path.join(test_dir, "app_fs_init.sh"), "w", encoding="utf-8") as stream:
            stream.write(content)
        os.chmod(os.path.join(test_dir, "app_fs_init.sh"), 0o755)

        self.logger.info("Running app_fs_init.sh")
        log_file_path = os.path.join(test_dir, "app_fs_init.log")
        try:
            with open(log_file_path, "w", encoding="utf-8") as log_file:
                result = subprocess.run(
                    ["bash", os.path.join(test_dir, "app_fs_init.sh")],
                    stdout=log_file,
                    stderr=log_file,
                    text=True,
                )
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error running app_fs_init.sh: {e}")
        self.logger.info(
            f"Initialized application filesystem initrd.cpio is stored in {app_dir}/initrd.cpio"
        )
        self.initrd_cpio_path = os.path.join(app_dir, "initrd.cpio")
        return 0 if self.initrd_cpio_path is None else 1, self.initrd_cpio_path

    def __init__(self, app_dir: str, app_config=".app/Kraftfile", run_config="RunConfig.yaml"):
        """Initialize application configuration.

        Parse application config (`Kraftfile`) and user run_config (`RunConfig.yaml`)
        and populate all entries in the self.config dictionary.
        """
        super().__init__()
        self.app_dir = app_dir
        self.config = {}
        self._parse_user_config(run_config)
        self._parse_app_config(app_config)
        self.initrd_cpio_path = None

    def __str__(self):
        return str(self.config)
