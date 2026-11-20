import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from tester_config import TesterConfig as ConfigUnderTest


def test_multiple_vmms_have_independent_configs():
    tester = ConfigUnderTest.__new__(ConfigUnderTest)

    tester.config = {
        "source": {"base": "/tmp"},
        "tools": {
            "vmm": ["system"],
            "compiler": ["system"],
        },
    }

    tester.variants = [
        {
            "build": {
                "platform": "qemu",
                "arch": "x86_64",
                "build_tool": "make",
            },
            "runs": [
                {
                    "run_tool": "vmm",
                    "hypervisor": "none",
                }
            ],
        }
    ]

    tester.target_configs = []

    vmms = [
    {"platform": "qemu", "path": "/usr/bin/qemu-system-x86_64"},
    {"platform": "qemu", "path": "/usr/bin/qemu-system-x86_64-microvm"},
    ]

    compilers = [
        {"type": "gcc", "path": "/usr/bin/gcc"}
    ]

    tester.generate_target_configs(
        plat="qemu",
        arch="x86_64",
        sys_arch="x86_64",
        sys_vmms=vmms,
        sys_compilers=compilers,
        build_tools=["make"],
        run_tools=["vmm"],
    )

    configs = tester.get_target_configs()

    assert len(configs) == 2

    assert configs[0]["run"]["vmm"]["path"] == "/usr/bin/qemu-system-x86_64"
    assert configs[1]["run"]["vmm"]["path"] == "/usr/bin/qemu-system-x86_64-microvm"

    assert configs[0] is not configs[1]


def test_single_vmm():
    tester = ConfigUnderTest.__new__(ConfigUnderTest)

    tester.config = {
        "source": {"base": "/tmp"},
        "tools": {
            "vmm": ["system"],
            "compiler": ["system"],
        },
    }

    tester.variants = [
        {
            "build": {
                "platform": "qemu",
                "arch": "x86_64",
                "build_tool": "make",
            },
            "runs": [
                {
                    "run_tool": "vmm",
                    "hypervisor": "none",
                }
            ],
        }
    ]

    tester.target_configs = []

    tester.generate_target_configs(
        plat="qemu",
        arch="x86_64",
        sys_arch="x86_64",
        sys_vmms=[
            {"platform": "qemu", "path": "/usr/bin/qemu-system-x86_64"}
        ],
        sys_compilers=[
            {"type": "gcc", "path": "/usr/bin/gcc"}
        ],
        build_tools=["make"],
        run_tools=["vmm"],
    )

    configs = tester.get_target_configs()

    assert len(configs) == 1
    assert configs[0]["run"]["vmm"]["path"] == "/usr/bin/qemu-system-x86_64"


def test_no_vmm():
    tester = ConfigUnderTest.__new__(ConfigUnderTest)

    tester.config = {
        "source": {"base": "/tmp"},
        "tools": {
            "vmm": ["system"],
            "compiler": ["system"],
        },
    }

    tester.variants = [
        {
            "build": {
                "platform": "qemu",
                "arch": "x86_64",
                "build_tool": "make",
            },
            "runs": [
                {
                    "run_tool": "vmm",
                    "hypervisor": "none",
                }
            ],
        }
    ]

    tester.target_configs = []

    tester.generate_target_configs(
        plat="qemu",
        arch="x86_64",
        sys_arch="x86_64",
        sys_vmms=[],
        sys_compilers=[
            {"type": "gcc", "path": "/usr/bin/gcc"}
        ],
        build_tools=["make"],
        run_tools=["vmm"],
    )

    configs = tester.get_target_configs()

    
    assert len(configs) == 1
    assert configs[0]["run"]["vmm"] is None
    assert configs[0]["run"]["runs"] == []
