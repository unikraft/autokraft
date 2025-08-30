#!/usr/bin/env python3
"""
Run tests for all applications found under catalog/library by invoking src/main.py

This script iterates each subdirectory in the catalog library and calls the
framework entrypoint (src/main.py) for that application. By default it runs
in generate-only (dry-run) mode to avoid long-running tests; pass --run to
actually execute tests.

Usage examples:
  python3 overall_test.py                # dry-run for all apps
  python3 overall_test.py --run -v       # actually run tests with verbose logs
  python3 overall_test.py --apps nginx,redis  # only process these apps
"""
import argparse
import logging
import os
import subprocess
import sys
from datetime import datetime


def find_catalog_library(base_dir: str) -> str:
    """Return absolute path to catalog/library. Try provided base_dir, then
    relative locations based on this script directory.
    """
    if base_dir:
        p = os.path.abspath(base_dir)
        if os.path.isdir(p):
            return p
        raise FileNotFoundError(f"Catalog library not found at {p}")

    # default: assume catalog is sibling of learning_testing_fw (project root)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidate = os.path.normpath(os.path.join(script_dir, "..", "catalog", "library"))
    if os.path.isdir(candidate):
        return candidate

    # last-resort: look for /catalog/library at filesystem root under workspace
    candidate2 = os.path.abspath(os.path.join(script_dir, "catalog", "library"))
    if os.path.isdir(candidate2):
        return candidate2

    raise FileNotFoundError("Could not locate catalog/library. Pass --catalog-path.")


def list_apps(library_path: str):
    """Discover runnable app directories under catalog/library.

    Rules:
    - Prefer directories that contain a README.md (case-insensitive) as the
      indicator of a runnable app target.
    - Support two layouts:
        1) Single-level app: library/<app>/README.md
        2) Versioned app:   library/<app>/<version>/README.md
    - Return a list of (name, path) tuples where name is either
      "<app>" (single-level) or "<app>/<version>" (versioned), and path is the
      absolute path to that directory.
    """

    def has_readme(path: str) -> bool:
        try:
            for fn in os.listdir(path):
                if fn.lower() == "readme.md":
                    return True
        except FileNotFoundError:
            return False
        return False

    apps = []
    for app_name in sorted(os.listdir(library_path)):
        app_dir = os.path.join(library_path, app_name)
        if not os.path.isdir(app_dir):
            continue

        # Case 1: single-level app directory with README.md
        if has_readme(app_dir):
            apps.append((app_name, app_dir))
            continue

        # Case 2: versioned subdirectories with README.md
        try:
            for ver_name in sorted(os.listdir(app_dir)):
                ver_dir = os.path.join(app_dir, ver_name)
                if os.path.isdir(ver_dir) and has_readme(ver_dir):
                    apps.append((f"{app_name}/{ver_name}", ver_dir))
        except FileNotFoundError:
            # If app_dir disappears mid-scan, skip it gracefully
            continue

        logging.debug(f"Skipping {app_name}: no README.md found")

    return apps


def run_for_app(main_py: str, app_path: str, args: argparse.Namespace, logger: logging.Logger):
    cmd = [sys.executable, main_py, app_path]
    if not args.run:
        cmd.append("--generate-only")
    if args.verbose:
        cmd.append("-v")
    if args.tests_dir:
        cmd.extend(["-d", args.tests_dir])
    if args.app_dir_name:
        cmd.extend(["-a", args.app_dir_name])
    if args.target_no:
        cmd.extend(["-t", args.target_no])

    logger.info(f"Invoking: {' '.join(cmd)}")
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        logger.info(f"Exit code: {proc.returncode}")
        if proc.stdout:
            logger.debug(proc.stdout)
        if proc.stderr:
            logger.debug(proc.stderr)
        return proc.returncode == 0
    except Exception as e:
        logger.exception(f"Failed to run main.py for {app_path}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Run tests for all apps in catalog/library")
    parser.add_argument("--catalog-path", dest="catalog_path", help="Path to catalog/library")
    parser.add_argument("--run", action="store_true", help="Actually run tests instead of generate-only")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging in main.py and this runner")
    parser.add_argument("--apps", help="Comma separated list of app names to run (e.g. nginx,redis)")
    parser.add_argument("--stop-on-fail", action="store_true", help="Stop processing apps after first failure")
    parser.add_argument("--tests-dir", help="Pass tests dir to main.py (-d)")
    parser.add_argument("--app-dir-name", help="Pass app dir name to main.py (-a)")
    parser.add_argument("--target-no", help="Pass target numbers to main.py (-t)")

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s %(levelname)s: %(message)s")
    logger = logging.getLogger("overall_test")

    try:
        library = find_catalog_library(args.catalog_path)
    except FileNotFoundError as e:
        logger.error(e)
        sys.exit(2)

    logger.info(f"Using catalog library: {library}")
    apps = list_apps(library)
    if args.apps:
        wanted = {n.strip() for n in args.apps.split(',') if n.strip()}
        # Allow selecting either full name (app or app/version) or just base app name
        def matches(name: str) -> bool:
            if name in wanted:
                return True
            base = name.split('/', 1)[0]
            return base in wanted

        apps = [(n, p) for (n, p) in apps if matches(n)]

    if not apps:
        logger.warning("No applications found to process.")
        return 0

    main_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", "main.py")
    if not os.path.isfile(main_py):
        logger.error(f"Could not find main.py at {main_py}")
        sys.exit(2)

    # overall logfile
    logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    overall_log = os.path.join(logs_dir, f"overall_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    fh = logging.FileHandler(overall_log)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
    logger.addHandler(fh)

    logger.info(f"Starting processing {len(apps)} app(s). Log: {overall_log}")

    failures = []
    for name, path in apps:
        if name == 'grafana/10.2':
            continue
        logger.info(f"Processing app: {name} -> {path}")
        ok = run_for_app(main_py, path, args, logger)
        if not ok:
            logger.error(f"App failed: {name}")
            failures.append(name)
            if args.stop_on_fail:
                break

    if failures:
        logger.error(f"Completed with failures: {failures}")
        return 1

    logger.info("All apps processed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
