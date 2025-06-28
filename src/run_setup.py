"""
This module provides the RunSetup class to manage the run setup for applications.
"""

import os

from constants import SCRIPT_DIR


class RunSetup:
    """Manage run setup.

    A run setup consists of configuration files and scripts that specify and depend on
    VMM, network configuration and filesystem configuration.
    """

    def __init__(self, base_dir, config, target_config, build_config, app_config, sys_arch):
        """Initialize run setup.

        Use the config argument to populate the configuration.
        Make use of the target configuration, build configuration, application
        configuration and system configuration.
        """

        self.dir = base_dir
        self.config = config
        self.target_config = target_config
        self.build_config = build_config
        self.app_config = app_config
        self.sys_arch = sys_arch

    @staticmethod
    def get_run_tools(plat, arch):
        """Get the list the potential run tool types."""

        return ["vmm", "kraft"]

    def _generate_from_template(self, template_name, output_name):
        """Generate output file from template.

        A template file stores variables that are to be replaced. Such variables
        define platform, architecture, used memory etc.
        """
        with open(os.path.join(SCRIPT_DIR, template_name), "r", encoding="utf-8") as stream:
            raw_content = stream.read()

        base = self.target_config["base"]
        name = self.app_config.config["name"]
        run_dir = self.dir
        target_dir = os.path.dirname(self.dir)
        plat = self.target_config["build"]["platform"]
        arch = self.target_config["build"]["arch"]
        memory = f"{self.app_config.config['memory']}"
        cmd = self.app_config.config["cmd"]
        kernel = self.build_config.kernel_path
        port_ext = self.app_config.config["public_port"]
        port_int = self.app_config.config["exposed_port"]
        if self.target_config["run"]["vmm"]:
            vmm = self.target_config["run"]["vmm"]["path"]
        hypervisor_option = ""
        if self.config["hypervisor"] != "none":
            if self.target_config["build"]["platform"] == "qemu":
                if self.config["run_tool"] == "vmm":
                    hypervisor_option = "-enable-kvm"
        if self.config["hypervisor"] == "none":
            if self.target_config["build"]["platform"] == "qemu":
                if self.config["run_tool"] == "kraft":
                    hypervisor_option = "-W"
        machine = ""
        if arch != self.sys_arch:
            machine = "-machine virt"
        if self.config["networking"] == "nat" and arch == "arm64":
            name = ""

        if self.app_config.has_template():
            app_dir = os.path.join(
                os.path.join(self.target_config["base"], "apps"), self.app_config.config["template"]
            )
        else:
            app_dir = os.getcwd()

        content = raw_content.format(**locals())

        with open(os.path.join(self.dir, output_name), "w", encoding="utf-8") as stream:
            stream.write(content)

    def _generate_fc_config_from_template(self, template_name):
        """Generate Firecracker configuration files (config.json) from template."""

        self._generate_from_template(template_name, "config.json")

    def _generate_run_script_from_template(self, template_name):
        """Generate run script from template."""

        self._generate_from_template(template_name, "run")
        os.chmod(os.path.join(self.dir, "run"), 0o755)

    def _generate_firecracker(self):
        """Generate Firecracker run configuration file (`config.json`) and run script (`run`)."""

        if self.app_config.has_einitrd() or not self.app_config.has_rootfs():
            if self.config["networking"] == "none":
                self._generate_fc_config_from_template("tpl_run_firecracker_nonet_noinitrd.json")
                self._generate_run_script_from_template("tpl_run_firecracker_nonet_noinitrd.sh")
            else:
                self._generate_fc_config_from_template(
                    f"tpl_run_firecracker_net_{self.config['networking']}_noinitrd.json"
                )
                self._generate_run_script_from_template(
                    f"tpl_run_firecracker_net_{self.config['networking']}_noinitrd.sh"
                )
        else:
            if self.config["networking"] == "none":
                self._generate_fc_config_from_template("tpl_run_firecracker_nonet_initrd.json")
                self._generate_run_script_from_template("tpl_run_firecracker_nonet_initrd.sh")
            else:
                self._generate_fc_config_from_template(
                    f"tpl_run_firecracker_net_{self.config['networking']}_initrd.json"
                )
                self._generate_run_script_from_template(
                    f"tpl_run_firecracker_net_{self.config['networking']}_initrd.sh"
                )

    def _generate_qemu(self):
        """Generate QEMU run script (`run`)."""

        if self.app_config.has_einitrd() or not self.app_config.has_rootfs():
            if self.config["networking"] == "none":
                self._generate_run_script_from_template("tpl_run_qemu_net_nat_noinitrd.sh")
            else:
                self._generate_run_script_from_template(
                    f"tpl_run_qemu_net_{self.config['networking']}_noinitrd.sh"
                )
        else:
            if self.config["networking"] == "none":
                self._generate_run_script_from_template("tpl_run_qemu_net_nat_initrd.sh")
            else:
                self._generate_run_script_from_template(
                    f"tpl_run_qemu_net_{self.config['networking']}_initrd.sh"
                )

    def _generate_xen(self):
        """Generate Xen configuration file (`xen.cfg`) and run script (`run`)."""

        pass

    def _generate_kraft(self):
        """Generate Kraft run script (`run`)."""

        if self.config["networking"] == "none":
            self._generate_run_script_from_template("tpl_run_kraft_nonet.sh")
        else:
            self._generate_run_script_from_template(
                f"tpl_run_kraft_net_{self.config['networking']}.sh"
            )

    def generate(self):
        """Generate run configuration file and scripts according to run tool (and VMM)."""

        if self.config["run_tool"] == "vmm":
            if self.target_config["build"]["platform"] == "fc":
                self._generate_firecracker()
            elif self.target_config["build"]["platform"] == "qemu":
                self._generate_qemu()
            elif self.target_config["build"]["platform"] == "xen":
                self._generate_xen()
        elif self.config["run_tool"] == "kraft":
            self._generate_kraft()
