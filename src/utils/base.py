# utils/base.py
import logging
import os

class Loggable:
    def __init__(self):
        """Initialize the Loggable class with a logger."""
        self.logger = logging.getLogger("test_framework")
