# utils/base.py
import logging


class Loggable:
    def __init__(self):
        self.logger = logging.getLogger("test_framework")
