"""
THis module provides the BuildSetup class, which manages the build setup.
"""

import logging
import os
import subprocess

from constants import SCRIPT_DIR

logging.basicConfig(
    level=logging.INFO,  # Set the logging level
    format="%(asctime)s - %(levelname)s - %(message)s",  # Log format
)


class BuildSetup:
    """Manage build setup.

    A build setup consists of configuration files and build scripts, that specify
    the build configuration, build tools.
    """

    def __init__(self, base_dir, config, target_config, app_config):
        """Initialize build setup.

        Use the config argument to populate the configuration.
        Make use of the target configuration and the application configuration.
        """

        # logging.info(f"Initializing BuildSetup {base_dir}...")
        self.dir = base_dir
        self.config = config
        self.target_config = target_config
        self.app_config = app_config
        self.kernel_name = (
            f"{self.app_config.config['name']}_{self.config['platform']}-{self.config['arch']}"
        )
        self.kernel_path = os.path.join(
            os.path.join(os.path.join(self.dir, ".unikraft"), "build"), self.kernel_name
        )
        if app_config.is_example():
            self.kernel_path = os.path.join(
                os.path.join(os.path.join(self.dir, ".unikraft"), "bin"), "kernel"
            )

    @staticmethod
    def get_build_tools(plat, arch):
        """Get the list the potential build tools."""

        return ["make", "kraft"]

    def _generate_defconfig(self):
        """Generate default configuration file for Make-based build."""

        with open(os.path.join(self.dir, "defconfig"), "w", encoding="utf-8") as stream:
            stream.write(f"CONFIG_UK_NAME=\"{self.app_config.config['name']}\"\n")
            stream.write(f"CONFIG_UK_DEFNAME=\"{self.app_config.config['name']}\"\n")
            if self.app_config.has_einitrd():
                stream.write("CONFIG_LIBVFSCORE_AUTOMOUNT_CI_EINITRD=y\n")
                stream.write("CONFIG_LIBVFSCORE_AUTOMOUNT_CI=y\n")
                einitrd_cpio_path = os.path.join(self.dir, "initrd.cpio")
                stream.write(f'CONFIG_LIBVFSCORE_AUTOMOUNT_EINITRD_PATH="{einitrd_cpio_path}"\n')
            else:
                stream.write("CONFIG_LIBVFSCORE_AUTOMOUNT_CI_EINITRD=n\n")
                stream.write("CONFIG_LIBVFSCORE_AUTOMOUNT_CI=n\n")
            if self.config["platform"] == "qemu":
                stream.write("CONFIG_PLAT_KVM=y\n")
                stream.write("CONFIG_KVM_VMM_QEMU=y\n")
            if self.config["platform"] == "fc":
                stream.write("CONFIG_PLAT_KVM=y\n")
                stream.write("CONFIG_KVM_VMM_FIRECRACKER=y\n")
            if self.config["platform"] == "xen":
                stream.write("CONFIG_PLAT_XEN=y\n")
            if self.config["arch"] == "arm64":
                stream.write("CONFIG_ARCH_ARM_64=y\n")
                if self.config["compiler"]["type"] == "clang":
                    stream.write("CONFIG_ARM64_ERRATUM_858921=n\n")
                    stream.write("CONFIG_ARM64_ERRATUM_835769=n\n")
                    stream.write("CONFIG_ARM64_ERRATUM_843419=n\n")
            if self.config["arch"] == "x86_64":
                stream.write("CONFIG_ARCH_X86_64=y\n")
            if self.app_config.config["unikraft"]:
                for k, v in self.app_config.config["unikraft"]["kconfig"].items():
                    stream.write(f"{k}={v}\n")
            if "libraries" in self.app_config.config.keys():
                for l in self.app_config.config["libraries"].keys():
                    if l.startswith("lib"):
                        stream.write(f"CONFIG_{l.replace('-', '_').upper()}=y\n")
                    else:
                        stream.write(f"CONFIG_LIB{l.replace('-', '_').upper()}=y\n")
                    for k, v in self.app_config.config["libraries"][l]["kconfig"].items():
                        stream.write(f"{k}={v}\n")

    def _generate_makefile(self):
        """Generate Makefile for Make-based build."""

        with open(os.path.join(SCRIPT_DIR, "tpl_Makefile"), "r", encoding="utf-8") as stream:
            raw_content = stream.read()

        libs = ""
        if "libraries" in self.app_config.config.keys():
            for l in self.app_config.config["libraries"].keys():
                libs += f"$(LIBS_BASE)/{l}:"
            libs = libs[:-1]
        base = self.target_config["base"]
        target_dir = self.dir

        if self.app_config.has_template():
            app_dir = os.path.join(
                os.path.join(self.target_config["base"], "apps"), self.app_config.config["template"]
            )
        else:
            app_dir = os.getcwd()

        content = raw_content.format(**locals())

        with open(os.path.join(self.dir, "Makefile"), "w", encoding="utf-8") as stream:
            stream.write(content)

    def _generate_kraftfile(self):
        """Generate Kraftfile for Kraft-based build.

        The generated Kraftfile is more-ore-less a copy of the initial Kraftfile.
        Custom einitrd configuration, debug levels configuration is added.
        """

        with open(os.path.join(self.dir, "Kraftfile"), "w", encoding="utf-8") as stream:
            stream.write("spec: v0.6\n\n")

            stream.write(f"name: {self.app_config.config['name']}\n\n")

            if self.app_config.config["runtime"]:
                stream.write(f"runtime: {self.app_config.config['runtime']}\n\n")

            if self.app_config.config["rootfs"]:
                if os.path.basename(self.app_config.config["rootfs"]) == "Dockerfile":
                    rootfs = os.path.join(os.getcwd(), ".app", self.app_config.config["rootfs"])
                else:
                    rootfs = os.path.join(os.getcwd(), ".app", "rootfs")
                stream.write(f"rootfs: {rootfs}\n\n")

            if self.app_config.config["cmd"]:
                stream.write(f"cmd: \"{self.app_config.config['cmd']}\"\n\n")

            if self.app_config.config["template"]:
                template_path = os.path.join(
                    os.path.join(self.target_config["base"], "apps"),
                    self.app_config.config["template"],
                )
                stream.write("template:\n")
                stream.write(f"  source: {template_path}\n\n")

            stream.write("targets:\n")
            stream.write(f"- {self.config['platform']}/{self.config['arch']}\n\n")

            if self.app_config.config["unikraft"]:
                unikraft_path = os.path.join(self.target_config["base"], "unikraft")
                stream.write("unikraft:\n")
                stream.write(f"  source: {unikraft_path}\n")
                if self.app_config.config["unikraft"]["kconfig"]:
                    stream.write("  kconfig:\n")
                    for k, v in self.app_config.config["unikraft"]["kconfig"].items():
                        if isinstance(v, str):
                            v = f'"{v}"'
                        stream.write(f"    {k}: {v}\n")
                    if self.app_config.has_einitrd():
                        stream.write("    CONFIG_LIBVFSCORE_AUTOMOUNT_CI_EINITRD: 'y'\n")
                        stream.write("    CONFIG_LIBVFSCORE_AUTOMOUNT_CI: 'y'\n")
                        # einitrd_cpio_path = os.path.join(self.dir, "initrd.cpio")
                        # stream.write(f"    CONFIG_LIBVFSCORE_AUTOMOUNT_EINITRD_PATH: \
                        #  '{einitrd_cpio_path}'\n")
                    else:
                        stream.write("    CONFIG_LIBVFSCORE_AUTOMOUNT_CI_EINITRD: 'n'\n")
                        stream.write("    CONFIG_LIBVFSCORE_AUTOMOUNT_CI: 'n'\n")
                    if self.config["arch"] == "arm64":
                        if self.config["compiler"]["type"] == "clang":
                            stream.write("    CONFIG_ARM64_ERRATUM_858921: 'n'\n")
                            stream.write("    CONFIG_ARM64_ERRATUM_835769: 'n'\n")
                            stream.write("    CONFIG_ARM64_ERRATUM_843419: 'n'\n")
                    stream.write("\n")
                stream.write("\n")

            if "libraries" in self.app_config.config.keys() and not self.app_config.is_example():
                stream.write("libraries:\n")
                for l in self.app_config.config["libraries"].keys():
                    lib_path = os.path.join(os.path.join(self.target_config["base"], "libs"), l)
                    stream.write(f"  {l}:\n")
                    stream.write(f"    source: {lib_path}\n")
                    if self.app_config.config["libraries"][l]["kconfig"]:
                        stream.write("    kconfig:\n")
                        for k, v in self.app_config.config["libraries"][l]["kconfig"].items():
                            if isinstance(v, str):
                                v = f'"{v}"'
                            stream.write(f"      {k}: {v}\n")

    def _generate_run_kraftfile(self):
        """Generate minimal Kraftfile for run Kraft-based runs in case of
        Make-based builds.

        The generated Kraftfile contains only minimal information:
          - spec
          - name
          - rootfs
          - targets
          - cmd
          - runtime or kernel
        Custom einitrd configuration, debug levels configuration is added.
        """

        with open(os.path.join(self.dir, "Kraftfile"), "w", encoding="utf-8") as stream:
            stream.write("spec: v0.6\n\n")

            stream.write(f"name: {self.app_config.config['name']}\n\n")

            if self.app_config.config["runtime"]:
                stream.write(f"runtime: {self.app_config.config['runtime']}\n\n")

            if self.app_config.config["rootfs"]:
                if os.path.basename(self.app_config.config["rootfs"]) == "Dockerfile":
                    rootfs = os.path.join(os.getcwd(), ".app", self.app_config.config["rootfs"])
                else:
                    rootfs = os.path.join(os.getcwd(), ".app", "rootfs")
                stream.write(f"rootfs: {rootfs}\n\n")

            if self.app_config.config["cmd"]:
                stream.write(f"cmd: \"{self.app_config.config['cmd']}\"\n\n")

            stream.write("targets:\n")
            stream.write(f"- {self.config['platform']}/{self.config['arch']}\n\n")

            if self.app_config.config["unikraft"]:
                unikraft_path = os.path.join(self.target_config["base"], "unikraft")
                stream.write("unikraft:\n")
                stream.write(f"  source: {unikraft_path}\n")

    def _get_compiler_vars(self):
        """Generate compiler variables, typically CROSS_COMPILE and COMPILER."""

        cross_compile, compiler = "", ""
        if self.config["arch"] == "x86_64":
            compiler = self.config["compiler"]["path"]
        if self.config["arch"] == "arm64":
            idx = self.config["compiler"]["path"].find(self.config["compiler"]["type"])
            cross_compile = f"export CROSS_COMPILE={self.config['compiler']['path'][0:idx]}"
            compiler = self.config["compiler"]["path"][idx:]

        return (cross_compile, compiler)

    def _generate_build_make(self):
        """Generate build script for Make-based build."""

        with open(os.path.join(SCRIPT_DIR, "tpl_build_make.sh"), "r", encoding="utf-8") as stream:
            raw_content = stream.read()

        target_dir = self.dir
        # (cross_compile, compiler) = self._get_compiler_vars()
        compiler = self.config["compiler"]["path"]
        init_dir = os.getcwd()

        content = raw_content.format(**locals())

        with open(os.path.join(self.dir, "build"), "w", encoding="utf-8") as stream:
            stream.write(content)
        os.chmod(os.path.join(self.dir, "build"), 0o755)

    def _generate_build_make_einitrd(self):
        """Generate build einitird script for Make-based build."""

        with open(
            os.path.join(SCRIPT_DIR, "tpl_build_make_einitrd.sh"), "r", encoding="utf-8"
        ) as stream:
            raw_content = stream.read()

        base = self.target_config["base"]
        target_dir = self.dir
        rootfs = os.path.join(os.getcwd(), ".app", self.app_config.config["rootfs"])
        name = self.app_config.config["name"]
        # (cross_compile, compiler) = self._get_compiler_vars()
        compiler = self.config["compiler"]["path"]
        init_dir = os.getcwd()

        content = raw_content.format(**locals())

        with open(os.path.join(self.dir, "build"), "w", encoding="utf-8") as stream:
            stream.write(content)
        os.chmod(os.path.join(self.dir, "build"), 0o755)

        if self.app_config.initrd_cpio_path is not None and os.path.exists(
            self.app_config.initrd_cpio_path
        ):
            result = subprocess.run(["cp", self.app_config.initrd_cpio_path, target_dir])
            if result.returncode != 0:
                logging.error(
                    f"Failed to copy initrd cpio file from {self.app_config.initrd_cpio_path} to {target_dir}"
                )
        else:
            raise FileNotFoundError(
                f"Initrd cpio file {self.app_config.initrd_cpio_path} does not exist."
            )

    def _generate_build_kraft(self):
        """Generate build script for Kraft-based build."""

        with open(os.path.join(SCRIPT_DIR, "tpl_build_kraft.sh"), "r", encoding="utf-8") as stream:
            raw_content = stream.read()

        if self.app_config.config["rootfs"]:
            rootfs = os.path.join(os.getcwd(), ".app", self.app_config.config["rootfs"])
        else:
            rootfs = ""
        target_dir = self.dir
        plat = self.config["platform"]
        arch = self.config["arch"]
        # (cross_compile, compiler) = self._get_compiler_vars()

        content = raw_content.format(**locals())

        with open(os.path.join(self.dir, "build"), "w", encoding="utf-8") as stream:
            stream.write(content)
        os.chmod(os.path.join(self.dir, "build"), 0o755)

    def generate(self):
        """Generate all required build files.

        Consider:

        - the build tool
        - the application type (kernel or example)
        - the use of embedded initrd
        """

        if self.config["build_tool"] == "make":
            if self.app_config.is_kernel():
                self._generate_defconfig()
                self._generate_makefile()
                if self.app_config.has_einitrd():
                    self._generate_build_make_einitrd()
                else:
                    self._generate_build_make()
                self._generate_run_kraftfile()
        elif self.config["build_tool"] == "kraft":
            self._generate_kraftfile()
            self._generate_build_kraft()
