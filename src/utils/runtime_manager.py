"""
Manage the runtime kernels used by example applications.

An example application (e.g. `examples/httpserver-nodejs18`) does not build its own
kernel. It runs on top of a runtime from `catalog/library` (e.g. `node/18`). Before the
example can be tested, the runtime kernels matching the selected targets have to exist in
`runtime_kernels/<runtime>/`.

Generating them is expensive: a second, generate-only instance of the framework is run on
the runtime application (in `.runtime_tests/` and `.runtime_app/`), and then the kernels
are built. This module makes sure that this only happens when a kernel is actually missing,
and that the temporary directories are always removed afterwards.
"""

import logging
import os
import subprocess
import sys

from utils.create_runtime_kernel import create_examples_runtime

RUNTIME_TESTS_DIR = ".runtime_tests"
RUNTIME_APP_DIR = ".runtime_app"

# src/main.py, resolved relative to this file so it does not depend on the current directory.
MAIN_SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "main.py")

logger = logging.getLogger("test_framework")


def get_runtime_name(runtime: str) -> str:
    """Return the runtime directory name from a renamed runtime.

    `AppConfig._rename_runtime()` already turns `node:18` into `node/18:local` and
    `base:latest` into `base:local`, so only the `:local` tag has to be dropped.

    Examples: 'node/18:local' -> 'node/18', 'base:local' -> 'base'.
    """
    if not runtime:
        raise ValueError("Application has no runtime configured")
    return runtime.split(":")[0]


def get_catalog_runtime_path(app_dir: str, runtime_name: str) -> str:
    """Return the path to the runtime application in `catalog/library`.

    The catalog root is found from the path of the application under test, e.g.
    `/x/catalog/examples/httpserver-nodejs18` + `node/18` -> `/x/catalog/library/node/18`.

    Raise ValueError if `app_dir` is not inside a `catalog` directory and FileNotFoundError
    if the runtime directory does not exist.
    """
    parts = os.path.abspath(app_dir).split(os.sep)
    if "catalog" not in parts:
        raise ValueError(f"Could not find a 'catalog' directory in app path: {app_dir}")
    # Use the last 'catalog' component, in case a parent directory is also named 'catalog'.
    catalog_index = len(parts) - 1 - parts[::-1].index("catalog")
    catalog_root = os.sep.join(parts[: catalog_index + 1]) or os.sep

    runtime_path = os.path.join(catalog_root, "library", runtime_name)
    if not os.path.isdir(runtime_path):
        raise FileNotFoundError(f"Runtime directory not found: {runtime_path}")
    return runtime_path


def validate_selected_targets(targets: list, selected_targets) -> None:
    """Raise ValueError if a selected target index is not a valid index into `targets`.

    `selected_targets` holds 0-based indexes, so `-t 0` on the command line becomes -1.
    Python would accept -1 as an index and silently pick the last target, which, with
    `--rebuild-runtime`, would delete a kernel that is then never rebuilt.
    """
    invalid = sorted(i for i in selected_targets if not 0 <= i < len(targets))
    if invalid:
        raise ValueError(
            f"Invalid target number(s): {', '.join(str(i + 1) for i in invalid)}. "
            f"Available targets: 1-{len(targets)}"
        )


def get_missing_runtime_kernels(targets: list, selected_targets) -> list:
    """Return the selected targets whose runtime kernel file does not exist yet.

    `selected_targets` holds 0-based target indexes, as produced by `parse_target_numbers()`.
    For example applications, `target.build_config.kernel_path` already points to
    `runtime_kernels/<runtime>/<kernel_name>`.
    """
    return [
        targets[i]
        for i in sorted(selected_targets)
        if not os.path.exists(targets[i].build_config.kernel_path)
    ]


def generate_runtime_configs(catalog_runtime_path: str) -> None:
    """Generate the build configurations of the runtime in `.runtime_tests/`.

    This runs the framework in generate-only mode on the runtime application, using the
    same Python interpreter as the current process (so it does not depend on the name of
    the virtual environment, unlike `scripts/utils/new_session.sh`).

    Raise subprocess.CalledProcessError if the generation fails.
    """
    cmd = [
        sys.executable,
        MAIN_SCRIPT,
        catalog_runtime_path,
        "--tests-dir",
        RUNTIME_TESTS_DIR,
        "--app-dir-name",
        RUNTIME_APP_DIR,
        "--generate-only",
    ]
    logger.info("Generating runtime configurations for %s", catalog_runtime_path)
    result = subprocess.run(cmd, check=True, text=True, capture_output=True)
    logger.debug("Runtime generation output: %s", result.stdout)


def cleanup_runtime_session() -> None:
    """Remove the temporary `.runtime_tests/` and `.runtime_app/` directories.

    `scripts/utils/cleanup.sh` is used because the build may leave files owned by root.
    Errors are only logged: cleanup must never hide the original result or exception.
    """
    cleanup_script = os.path.join(os.getcwd(), "scripts", "utils", "cleanup.sh")
    try:
        subprocess.run(
            [cleanup_script, RUNTIME_TESTS_DIR, RUNTIME_APP_DIR],
            check=True,
            text=True,
            capture_output=True,
        )
        logger.info("Removed temporary runtime session directories.")
    except (OSError, subprocess.CalledProcessError) as e:
        logger.warning("Could not remove temporary runtime session directories: %s", e)


def ensure_runtime_kernels(
    app_dir: str, runtime: str, targets: list, selected_targets, force: bool = False
) -> bool:
    """Make sure the runtime kernels of the selected targets exist.

    If every selected target already has its kernel in `runtime_kernels/` and `force` is
    False, nothing is generated. Otherwise the runtime configurations are generated, the
    missing kernels are built and the temporary session is removed, even on error or
    Ctrl+C.

    With `force=True` (`--rebuild-runtime`), the kernels of the selected targets are
    deleted first so they are rebuilt, e.g. after a change in Unikraft.

    Return True if kernels were (re)generated, False if generation was skipped.

    Raise ValueError if a selected target index is invalid (checked before any kernel is
    deleted) and RuntimeError if a selected kernel is still missing after generation.
    """
    validate_selected_targets(targets, selected_targets)
    runtime_name = get_runtime_name(runtime)

    if force:
        for target in (targets[i] for i in selected_targets):
            kernel_path = target.build_config.kernel_path
            if os.path.exists(kernel_path):
                logger.info("Removing runtime kernel to rebuild it: %s", kernel_path)
                os.remove(kernel_path)

    missing = get_missing_runtime_kernels(targets, selected_targets)
    if not missing:
        logger.info(
            "All runtime kernels for %s already exist in runtime_kernels/, skipping generation.",
            runtime_name,
        )
        return False

    logger.info(
        "Missing %d runtime kernel(s) for %s (targets: %s), generating them.",
        len(missing),
        runtime_name,
        ", ".join(str(t.id) for t in missing),
    )
    catalog_runtime_path = get_catalog_runtime_path(app_dir, runtime_name)
    try:
        generate_runtime_configs(catalog_runtime_path)
        create_examples_runtime(selected_targets, targets, runtime_name)
        # create_examples_runtime() only prints some failures (kraft pkg errors, no matching
        # configuration) and returns normally, so check that the kernels really exist.
        still_missing = get_missing_runtime_kernels(targets, selected_targets)
        if still_missing:
            raise RuntimeError(
                "Runtime kernel(s) still missing after generation: "
                + ", ".join(t.build_config.kernel_path for t in still_missing)
            )
    finally:
        cleanup_runtime_session()
    return True
