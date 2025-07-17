# src/utils/logger.py
import logging
import os


def setup_logger(name, log_file="logs/run.log", level=logging.INFO):
    """Set up the logger with the specified log level.

    Args:
        name: The name of the logger.
        log_file: The file to which logs should be written.
        level: The logging level to use. Default is INFO.
    """
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(level)
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger
