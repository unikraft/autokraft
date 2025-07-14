"""
This module provide the TesterConfig class to retrive and store tester configurations.
"""

import itertools
import sys

import yaml
from utils.base import Loggable

class TesterConfig(Loggable):
    """Interact with tester configuration.

    Configuration is read from the global tester configuration file.
    Extract valid configurations from tester configuration file.

    Provide configurations for target definition: get_target_configs()
    """

    def __init__(self, config_file="src/tester_config.yaml"):
        super().__init__()
        try:
            with open(config_file, "r", encoding="utf8") as stream:
                self.config = yaml.safe_load(stream)
                self.variants = self._generate_variants()
                self.target_configs = []
        except IOError:
            self.logger.error(f"Error: Unable to open configuration file '{config_file}'", file=sys.stderr)

    def _generate_full_variants(self):
        """Generate all possible configuration variants.

        Create all combinations of values from the 'variants' dictionary in
        the tester configuration file.

        Each variant is a dictionary, e.g.
        {'arch': 'x86_64', 'hypervisor': 'kvm', 'platform': 'qemu', ...}

        Return a list of all variants.
        """

        build_variants = self.config["variants"]["build"]
        run_variants = self.config["variants"]["run"]
        build_configs = list(
            dict(zip(build_variants.keys(), values))
            for values in itertools.product(*build_variants.values())
        )
        run_configs = list(
            dict(zip(run_variants.keys(), values))
            for values in itertools.product(*run_variants.values())
        )

        full_variants = []
        for b in build_configs:
            new_variant = {}
            new_variant["build"] = b
            new_variant["runs"] = []
            for r in run_configs:
                new_variant["runs"].append(r)
            full_variants.append(new_variant)

        return full_variants

    def _get_exclude_variants(self):
        """Get variants to be excluded from all possible variants.

        Parse values in the 'exclude_variants' list in the tester
        configuration file.

        Each exclude variant is a dictionary with various keys, e.g:
        {'networking': 'brigde', 'platform': 'fc'}
        """

        variants = {**self.config["variants"]["build"], **self.config["variants"]["run"]}
        exclude_variants = self.config["exclude_variants"]
        ret = []

        for e in exclude_variants:
            tmp_dict = {}
            for k1, v1 in e.items():
                if isinstance(v1, list):
                    l = []
                    for v2 in v1:
                        if v2.startswith("not"):
                            tmp_l = list(set(variants[k1]) - set([v2.split(" ")[1]]))
                        else:
                            tmp_l = [v2]
                        l = set.union(set(l), set(tmp_l))
                    tmp_dict[k1] = l
                elif isinstance(v1, str):
                    if v1.startswith("not"):
                        l = list(set(variants[k1]) - set([v1.split(" ")[1]]))
                    else:
                        l = [v1]
                    tmp_dict[k1] = l
                else:
                    l = [v1]
                    tmp_dict[k1] = l
            ret.extend(list(dict(zip(tmp_dict, x)) for x in itertools.product(*tmp_dict.values())))

        return ret

    def _generate_variants(self):
        """Generate valid variants.

        Valid variants are those that are not excluded. In short, do a diff
        between all variants (with _generate_full_variants()) and the excluded
        variants (with _get_exlude_variants()).

        An exclude variant is a dictionary. A variant is a dictionary with a
        build configuration and an array of run configurations.

        Return list of variants, i.e. a subset of full_variants.
        """

        exclude_variants = self._get_exclude_variants()
        full_variants = self._generate_full_variants()
        ret_variants = []

        for f in full_variants:
            # First check if entire build variant is to be excluded
            # (together # with all its run variants).
            b = f["build"]
            for e in exclude_variants:
                excluded = True
                for k, v in e.items():
                    if k in b.keys():
                        if b[k] != v:
                            excluded = False
                            break
                    else:
                        excluded = False
                        break
                if excluded:
                    break
            if excluded:
                continue

            # Check for run variants to be excluded.
            run_variants = []
            for r in f["runs"]:
                linear_variant = {**b, **r}
                excluded = True
                for e in exclude_variants:
                    excluded = True
                    for k, v in e.items():
                        if linear_variant[k] != v:
                            excluded = False
                            break
                    if excluded:
                        break
                if excluded:
                    continue
                run_variants.append(r)
            ret_variants.append({"build": b, "runs": run_variants})

        return ret_variants

    def _generate_compilers(self, plat, arch, sys_compilers):
        """Generate compiler configurations.

        Generate compiler configurations using system compiler configuration
        and tester configuration for the specific architecture. The platform
        is also passed as argument for potential future use.

        Return list of compiler configurations. Each item in the list is
        a dictionary, e.g.:
        {'type': 'gcc', 'path': '/usr/bin/gcc'}
        """

        compilers = []

        for c in self.config["tools"]["compiler"]:
            if isinstance(c, dict):
                if c["arch"] == arch:
                    compilers.append({"type": c["type"], "path": c["path"]})
                continue
            if c == "system":
                compilers += sys_compilers

        return compilers

    def _generate_vmms(self, plat, arch, sys_vmms):
        """Generate VMM configurations.

        Generate VMM configurations using system VMM configuration and tester
        configuration for the specific platform and architecture.

        Return list of compiler configurations. Each item in the list is
        a dictionary, e.g.:
        {'platform': 'qemu', 'path': '/usr/bin/qemu-system-x86_64'}
        """

        vmms = []

        for v in self.config["tools"]["vmm"]:
            if isinstance(v, dict):
                if v["arch"] == arch and v["type"] == plat:
                    vmms.append({"platform": v["type"], "path": v["path"]})
                continue
            if v == "system":
                vmms += sys_vmms

        return vmms

    def generate_target_configs(
        self, plat, arch, sys_arch, sys_vmms, sys_compilers, build_tools, run_tools
    ):
        """Generate configurations for target.

        The target is defined by the platform, architecture, system VMMs,
        system compiler, build tools and run tools. Do an intersection between
        the valid variants list and the target specification.

        Return list of target configurations. Each item in the list is a
        dictionary, e.g.:
        {'arch': 'x86_64', ..., 'base': '...', 'compiler': '...' }'
        """

        for v in self.variants:
            for b in build_tools:
                if not (
                    plat == v["build"]["platform"]
                    and arch == v["build"]["arch"]
                    and b == v["build"]["build_tool"]
                ):
                    continue

                vmm_list = self._generate_vmms(plat, arch, sys_vmms)
                comp_list = self._generate_compilers(plat, arch, sys_compilers)
                if not comp_list:
                    continue
                # Currently, Kraft can only build using GCC.
                # So, irrespective of the available compilers, generate only
                # one Kraft build target.
                if b == "kraft":
                    comp_list = [{"type": "gcc", "path": "default"}]
                for comp in comp_list:
                    _config = {}
                    _config["build"] = v["build"].copy()
                    _config["base"] = self.config["source"]["base"]

                    _config["build"]["compiler"] = comp

                    if not vmm_list:
                        _config["run"] = {}
                        _config["run"]["vmm"] = None
                        _config["run"]["runs"] = []
                        self.target_configs.append(_config)
                        continue

                    for vmm in vmm_list:
                        _config["run"] = {}
                        _config["run"]["vmm"] = vmm
                        _config["run"]["runs"] = []
                        for r in v["runs"]:
                            for rt in run_tools:
                                if rt == r["run_tool"]:
                                    if r["hypervisor"] == "none" or (
                                        r["hypervisor"] != "none" and arch == sys_arch
                                    ):
                                        _config["run"]["runs"].append(r)
                        self.target_configs.append(_config)

    def get_target_configs(self):
        """Retrieve target configurations."""

        return self.target_configs

    def __str__(self):
        return str(self.config)
