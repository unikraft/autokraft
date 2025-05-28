import os

import yaml

from build_setup import BuildSetup
from run_setup import RunSetup


class TargetSetup:
    """Create setup for target.

    A target is defined by a build setup that generates a unikernel
    image and filesystem, and run setups that run the image and filesystem.
    """

    class_id = 1

    def __init__(self, config, app_config, system_config):
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
            base = os.path.abspath(".tests")
        self.dir = os.path.join(base, "{:05d}".format(self.id))
        self.build_config = BuildSetup(self.dir, self.config["build"], self.config, app_config)
        self.run_configs = []
        idx = 1
        for r in self.config["run"]["runs"]:
            if r["networking"] == "none" and app_config.config["networking"] == True:
                continue
            if r["networking"] != "none" and app_config.config["networking"] == False:
                continue
            if r["rootfs"] != "none" and (app_config.has_einitrd() or not app_config.has_rootfs()):
                continue
            if r["rootfs"] == "none" and not app_config.has_einitrd() and app_config.has_rootfs():
                continue
            run_dir = os.path.join(self.dir, "run-{:02d}".format(idx))
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
        # Generate config.yaml.
        with open(os.path.join(self.dir, "config.yaml"), "w") as outfile:
            outfile.write(f"base: {self.config['base']}\n")
            yaml.dump(self.config["build"], outfile, default_flow_style=False)
            if self.config["run"]["vmm"]:
                outfile.write(f"vmm: {self.config['run']['vmm']['path']}\n")
        self.build_config.generate()
        for r in self.run_configs:
            os.mkdir(r.dir, mode=0o755)
            with open(os.path.join(r.dir, "config.yaml"), "w") as outfile:
                yaml.dump(r.config, outfile, default_flow_style=False)
            r.generate()
