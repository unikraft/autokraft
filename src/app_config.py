import os
import subprocess
import sys

import yaml

from constants import SCRIPT_DIR
from tester_config import TesterConfig


class AppConfig:
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

        return self.config["template"] != None

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

        return self.config["unikraft"] != None

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

    def _parse_user_config(self, user_config_file):
        """Parse config.yaml file.

        Populate corresponding entries in self.config.
        """

        with open(user_config_file, "r", encoding="utf-8") as stream:
            data = yaml.safe_load(stream)

        self.config["networking"] = False

        if not "networking" in data.keys():
            self.config["networking"] = False
        else:
            self.config["networking"] = data["networking"]

        if not "test_dir" in data.keys():
            self.config["test_dir"] = None
        else:
            self.config["test_dir"] = data["test_dir"]

        if not "memory" in data.keys():
            print(
                f"Error: 'memory' attribute is not defined in {user_config_file}'", file=sys.stderr
            )
            sys.exit(1)
        else:
            self.config["memory"] = data["memory"]

        if not "exposed_port" in data.keys():
            self.config["exposed_port"] = None
            self.config["public_port"] = None
        else:
            self.config["exposed_port"] = data["exposed_port"]
            self.config["public_port"] = data["public_port"]

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
            test_dir = os.path.abspath(self.user_config["test_dir"])
        else:
            test_dir = os.path.abspath(".tests")
        if self.config["rootfs"]:
            rootfs = os.path.join(os.getcwd(), self.config["rootfs"])
        else:
            rootfs = ""
        init_dir = os.getcwd()

        # shank: I need to fix this path to my local directory(tester_config.yaml)
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

    def __init__(self, app_config="Kraftfile", user_config="config.yaml"):
        """Initialize application configuration.

        Parse application config (`Kraftfile`) and user config (`config.yaml`)
        and populate all entries in the self.config dictionary.
        """

        self.config = {}
        self._parse_user_config(user_config)
        self._parse_app_config(app_config)

    def __str__(self):
        return str(self.config)
