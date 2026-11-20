"""
Unit tests for src/utils/runtime_manager.py.

Run from the repository root with:
    python -m unittest discover -s tests -v

The tests only use the standard library (plus PyYAML, already required by the framework).
Nothing is built: generation, kernel creation and cleanup are mocked.
"""

import os
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

# Test method names describe the scenario, so they do not need docstrings.
# pylint: disable=wrong-import-position,missing-function-docstring
from utils import runtime_manager as rm  # noqa: E402


def make_target(target_id, kernel_path):
    """Build a minimal object with the attributes runtime_manager uses from TargetSetup."""
    return SimpleNamespace(id=target_id, build_config=SimpleNamespace(kernel_path=kernel_path))


class TestGetRuntimeName(unittest.TestCase):
    """get_runtime_name() drops the ':local' tag added by AppConfig._rename_runtime()."""

    def test_versioned_runtime(self):
        self.assertEqual(rm.get_runtime_name("node/18:local"), "node/18")

    def test_latest_runtime(self):
        self.assertEqual(rm.get_runtime_name("base:local"), "base")

    def test_missing_runtime(self):
        for value in (None, ""):
            with self.assertRaises(ValueError):
                rm.get_runtime_name(value)


class TestGetCatalogRuntimePath(unittest.TestCase):
    """get_catalog_runtime_path() maps an example path to catalog/library/<runtime>."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self.catalog = os.path.join(self.tmp.name, "catalog")
        self.app_dir = os.path.join(self.catalog, "examples", "httpserver-nodejs18")
        os.makedirs(self.app_dir)
        os.makedirs(os.path.join(self.catalog, "library", "node", "18"))
        os.makedirs(os.path.join(self.catalog, "library", "base"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_versioned_runtime(self):
        self.assertEqual(
            rm.get_catalog_runtime_path(self.app_dir, "node/18"),
            os.path.join(self.catalog, "library", "node", "18"),
        )

    def test_base_runtime(self):
        self.assertEqual(
            rm.get_catalog_runtime_path(self.app_dir, "base"),
            os.path.join(self.catalog, "library", "base"),
        )

    def test_app_outside_catalog(self):
        with self.assertRaises(ValueError):
            rm.get_catalog_runtime_path(os.path.join(self.tmp.name, "elsewhere", "app"), "base")

    def test_catalog_prefix_is_not_enough(self):
        # The old code split on the substring 'catalog', which also matched e.g. 'mycatalog'.
        with self.assertRaises(ValueError):
            rm.get_catalog_runtime_path(os.path.join(self.tmp.name, "mycatalog", "app"), "base")

    def test_missing_runtime_directory(self):
        with self.assertRaises(FileNotFoundError):
            rm.get_catalog_runtime_path(self.app_dir, "doesnotexist/1.0")


class KernelDirTestCase(unittest.TestCase):
    """Base class: three targets with kernels in a temporary runtime_kernels/ directory."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self.kernels = [os.path.join(self.tmp.name, f"kernel{i}") for i in range(3)]
        # TargetSetup ids are 1-based, selected_targets are 0-based.
        self.targets = [make_target(i + 1, path) for i, path in enumerate(self.kernels)]

    def tearDown(self):
        self.tmp.cleanup()

    def create_kernels(self, *indexes):
        """Create the kernel files of the given (0-based) targets."""
        for i in indexes:
            with open(self.kernels[i], "w", encoding="utf-8") as stream:
                stream.write("kernel")


class TestGetMissingRuntimeKernels(KernelDirTestCase):
    """get_missing_runtime_kernels() only looks at the selected targets."""

    def test_all_missing(self):
        self.assertEqual(rm.get_missing_runtime_kernels(self.targets, [0, 1, 2]), self.targets)

    def test_none_missing(self):
        self.create_kernels(0, 1, 2)
        self.assertEqual(rm.get_missing_runtime_kernels(self.targets, [0, 1, 2]), [])

    def test_only_selected_targets(self):
        self.create_kernels(0)
        # Target 3 (index 2) is missing but not selected, so it must not be reported.
        self.assertEqual(rm.get_missing_runtime_kernels(self.targets, {0, 1}), [self.targets[1]])


@mock.patch.object(rm, "cleanup_runtime_session")
@mock.patch.object(rm, "create_examples_runtime")
@mock.patch.object(rm, "generate_runtime_configs")
@mock.patch.object(rm, "get_catalog_runtime_path", return_value="/catalog/library/node/18")
class TestEnsureRuntimeKernels(KernelDirTestCase):
    """ensure_runtime_kernels() generates only when needed and always cleans up."""

    def test_skips_when_all_kernels_exist(self, catalog, generate, create, cleanup):
        self.create_kernels(0, 1, 2)
        result = rm.ensure_runtime_kernels("/app", "node/18:local", self.targets, [0, 1, 2])
        self.assertFalse(result)
        catalog.assert_not_called()
        generate.assert_not_called()
        create.assert_not_called()
        cleanup.assert_not_called()

    def test_generates_when_a_kernel_is_missing(self, catalog, generate, create, cleanup):
        self.create_kernels(0, 2)
        result = rm.ensure_runtime_kernels("/app", "node/18:local", self.targets, [0, 1, 2])
        self.assertTrue(result)
        catalog.assert_called_once_with("/app", "node/18")
        generate.assert_called_once_with("/catalog/library/node/18")
        create.assert_called_once_with([0, 1, 2], self.targets, "node/18")
        cleanup.assert_called_once_with()

    def test_cleans_up_when_generation_fails(self, _catalog, generate, create, cleanup):
        generate.side_effect = subprocess.CalledProcessError(1, "main.py")
        with self.assertRaises(subprocess.CalledProcessError):
            rm.ensure_runtime_kernels("/app", "node/18:local", self.targets, [0])
        create.assert_not_called()
        cleanup.assert_called_once_with()

    def test_cleans_up_on_ctrl_c(self, _catalog, _generate, create, cleanup):
        create.side_effect = KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            rm.ensure_runtime_kernels("/app", "node/18:local", self.targets, [0])
        cleanup.assert_called_once_with()

    def test_no_cleanup_when_runtime_path_is_invalid(self, catalog, generate, _create, cleanup):
        # Nothing was created yet, so there is nothing to clean up.
        catalog.side_effect = FileNotFoundError("missing")
        with self.assertRaises(FileNotFoundError):
            rm.ensure_runtime_kernels("/app", "doesnotexist/1.0:local", self.targets, [0])
        generate.assert_not_called()
        cleanup.assert_not_called()

    def test_force_rebuilds_only_selected_kernels(self, _catalog, generate, create, cleanup):
        self.create_kernels(0, 1, 2)
        result = rm.ensure_runtime_kernels("/app", "node/18:local", self.targets, [1], force=True)
        self.assertTrue(result)
        self.assertTrue(os.path.exists(self.kernels[0]))
        self.assertFalse(os.path.exists(self.kernels[1]))
        self.assertTrue(os.path.exists(self.kernels[2]))
        generate.assert_called_once()
        create.assert_called_once_with([1], self.targets, "node/18")
        cleanup.assert_called_once_with()


class TestGenerateRuntimeConfigs(unittest.TestCase):
    """generate_runtime_configs() runs main.py with the current interpreter."""

    @mock.patch.object(rm.subprocess, "run")
    def test_command(self, run):
        run.return_value = SimpleNamespace(stdout="")
        rm.generate_runtime_configs("/catalog/library/base")
        cmd = run.call_args.args[0]
        self.assertEqual(cmd[0], sys.executable)
        self.assertTrue(cmd[1].endswith(os.path.join("src", "main.py")))
        self.assertEqual(
            cmd[2:],
            [
                "/catalog/library/base",
                "--tests-dir",
                ".runtime_tests",
                "--app-dir-name",
                ".runtime_app",
                "--generate-only",
            ],
        )
        self.assertTrue(run.call_args.kwargs["check"])


class TestCleanupRuntimeSession(unittest.TestCase):
    """cleanup_runtime_session() never raises."""

    @mock.patch.object(rm.subprocess, "run")
    def test_calls_cleanup_script(self, run):
        rm.cleanup_runtime_session()
        cmd = run.call_args.args[0]
        self.assertTrue(cmd[0].endswith(os.path.join("scripts", "utils", "cleanup.sh")))
        self.assertEqual(cmd[1:], [".runtime_tests", ".runtime_app"])

    @mock.patch.object(rm.subprocess, "run", side_effect=OSError("no such file"))
    def test_errors_are_only_logged(self, _run):
        with self.assertLogs("test_framework", level="WARNING"):
            rm.cleanup_runtime_session()


if __name__ == "__main__":
    unittest.main()
