import platform
import re
import shutil
import subprocess


class SystemConfig:
    """Extract system configuration information.
    Store in appropriate class members.

    self.os: operating system / platform info
    self.arch: CPU architecture
    self.hypervisor: hypervisor / acceleration
    self.vmms: virtual machine monitor paths (split by architecture and type)
    self.compilers: compiler paths (split by architecture and type)
    """

    def _get_os(self):
        """Get operating system information.

        Store in the self.of dictionary.
        """

        info = platform.uname()
        self.os = {"type": info.system, "kernel_version": info.release, "distro": None}
        if self.os["type"] == "Linux":
            self.os["distro"] = platform.freedesktop_os_release()["ID"]

    def _get_arch(self):
        """Get machine architecture information.

        Store in the self.arch string.
        """

        self.arch = platform.machine()
        if self.arch == "aarch64":
            self.arch = "arm64"

    def get_arch(self):
        """Return machine architecture information."""

        return self.arch

    def _get_hypervisor(self):
        """Get hypervisor information.

        Store in the self.hypervisor string.
        """

        self.hypervisor = ""
        if self.os["type"] == "Linux":
            with subprocess.Popen("lsmod", stdout=subprocess.PIPE) as proc:
                content = proc.stdout.read()
                if re.search(b"\\nkvm", content):
                    self.hypervisor = "kvm"

    def _get_paths(self, string, pattern):
        """Get full paths for string (part of a command).

        Use Bash completion to expand string to a full command. Match result
        against pattern. Only select results that match.
        Use `which` to get the absolute path for the full command.

        Return list of full paths.

        TODO: This has only been tested on Bash.
        Test on other shells.
        """

        cmds = []
        with subprocess.Popen(
            ["bash", "-c", f"compgen -A command {string}"], stdout=subprocess.PIPE
        ) as proc:
            for l in proc.stdout.readlines():
                l = l.decode("utf-8").strip()
                if re.match(pattern, l):
                    cmds.append(l)

        cmds = set(cmds)
        paths = []
        for c in cmds:
            if shutil.which(c):
                paths.append(shutil.which(c))

        return paths

    def _get_vmms(self):
        """Get VMMs information.

        Store in the self.vmms dictionary.
        """

        qemu_x86_64_paths = self._get_paths("qemu-system-", "^qemu-system-x86_64$")
        qemu_arm64_paths = self._get_paths("qemu-system-", "^qemu-system-aarch64")
        fc_x86_64_paths = self._get_paths("firecracker-", "^firecracker-x86_64")
        fc_arm64_paths = self._get_paths("firecracker-", "^firecracker-aarch64")
        self.vmms = {
            "arm64": {"qemu": qemu_arm64_paths, "fc": fc_arm64_paths},
            "x86_64": {"qemu": qemu_x86_64_paths, "fc": fc_x86_64_paths},
        }

    def _get_compilers(self):
        """Get compilers information.

        Store in the self.compilers dictionary.
        """

        gcc_x86_64_paths = self._get_paths("gcc-", "^gcc-[0-9]+$")
        gcc_arm64_paths = self._get_paths("aarch64-linux-gnu-gcc-", "aarch64-linux-gnu-gcc-[0-9]+$")
        clang_paths = self._get_paths("clang-", "^clang-[0-9]+$")
        self.compilers = {
            "arm64": {"gcc": gcc_arm64_paths, "clang": clang_paths},
            "x86_64": {"gcc": gcc_x86_64_paths, "clang": clang_paths},
        }

    def get_vmms(self, plat, arch):
        """Get available VMMs for platform and architecture.

        Return list of dictionaries of available VMMs.
        """

        ret_list = []
        if not arch in self.vmms.keys():
            return []
        if not plat in self.vmms[arch].keys():
            return []
        for v in self.vmms[arch][plat]:
            ret_list.append({"type": plat, "path": v})
        return ret_list

    def get_compilers(self, plat, arch):
        """Get available compilers for platform and architecture.

        The platform is not used; it is passed as a parameter for future use.

        Return list of dictionaries of available compilers.
        """

        ret_list = []
        for k, v in self.compilers[arch].items():
            for l in v:
                ret_list.append({"type": k, "path": l})
        return ret_list

    def __init__(self):
        """Initialize object.

        Extract all system information: operating system, architecture,
        hypervisor, VMMs, compilers.
        """

        self._get_os()
        self._get_arch()
        self._get_hypervisor()
        self._get_vmms()
        self._get_compilers()

    def __str__(self):
        vmm_list = self.vmms["arm64"]["qemu"]
        vmm_list.extend(self.vmms["arm64"]["fc"])
        vmm_list.extend(self.vmms["x86_64"]["qemu"])
        vmm_list.extend(self.vmms["x86_64"]["fc"])
        vmm_str = ", ".join(vmm for vmm in vmm_list)

        comp_list = self.compilers["arm64"]["gcc"]
        comp_list.extend(self.compilers["arm64"]["clang"])
        comp_list.extend(self.compilers["x86_64"]["gcc"])
        comp_list.extend(self.compilers["x86_64"]["clang"])
        comp_str = ", ".join(comp for comp in comp_list)

        return (
            f'os: {self.os["type"]}, kernel: {self.os["kernel_version"]}, '
            f'distro: {self.os["distro"]}, arch: {self.arch}, '
            f"hypervisor: {self.hypervisor}, vmms: {vmm_str}, "
            f"compilers: {comp_str}"
        )
