"""
Utility functions for process management.
"""
import subprocess
import shlex
import logging

def terminate_buildkitd() -> None:
    """
    Terminate the buildkitd process if it is running.
    """
    logger = logging.getLogger(__name__)
    try:
        logger.info("Attempting to terminate buildkitd process...")
        result = subprocess.run(
            shlex.split("sudo pkill buildkitd"),
            capture_output=True,
            text=True,
            check=False  # Do not raise an exception on non-zero exit codes
        )
        if result.returncode == 0:
            logger.info("[✓] buildkitd process terminated successfully.")
        else:
            logger.warning("[!] No buildkitd process found to terminate.")
    except Exception as e:
        logger.error(f"[✗] Error while terminating buildkitd process: {e}")
