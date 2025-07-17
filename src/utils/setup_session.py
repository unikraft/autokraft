import logging
import os
from datetime import datetime


class SessionSetup:
    """
    Class to handle session setup including session name generation and directory creation.
    """

    def __init__(self, app_dir, custom_session_name=None):
        """
        Initialize SessionSetup with application directory path.

        Args:
            app_dir (str): Path to the application directory being tested
        """
        self.app_dir = app_dir
        self.logger = logging.getLogger("test_framework")
        self._generate_session_name(custom_session_name)
        self.session_dir = self._setup_directory()

    def _generate_session_name(self, custom_session_name=None):
        """
        Generate a session name with timestamp.

        Args:
            custom_session_name (str, optional): Custom session name provided by user.
                                                If None, 'session' will be used as default.

        Returns:
            str: Generated session name with timestamp in format: name_dd_mm_yyyy_hh_mm
        """
        # Use custom name or default to 'session'
        base_name = custom_session_name if custom_session_name else "session"

        # Get current date and time
        now = datetime.now()
        timestamp = now.strftime("%d_%m_%Y_%H_%M")

        # Combine base name with timestamp
        self.session_name = f"{base_name}_{timestamp}"
        self.logger.info(f"Generated session name: {self.session_name}")

    def _setup_directory(self):
        """
        Create session directory using the generated session name and app_dir.

        Returns:
            str: Path to the created session directory

        Raises:
            ValueError: If session name hasn't been generated yet
            OSError: If directory creation fails
        """
        if not self.session_name:
            raise ValueError("Session name must be generated before setting up directory")

        # Remove path before /catalog from app_directory
        catalog_index = self.app_dir.find("/catalog")
        if catalog_index != -1:
            tmp_app_directory_structure = self.app_dir[catalog_index + 1 :]  # Remove leading '/'
        else:
            # If /catalog not found, use the entire app_dir structure
            tmp_app_directory_structure = os.path.basename(self.app_dir)

        # Get current working directory
        cwd = os.getcwd()

        # Create session directory path: cwd/sessions/{tmp_app_directory_structure}/{session_name}
        self.session_dir = os.path.join(
            cwd, ".sessions", tmp_app_directory_structure, self.session_name
        )
        self.session_reports_dir = os.path.join(self.session_dir, "reports")

        try:
            # Create the directory with parents=True to create all intermediate directories
            os.makedirs(self.session_reports_dir , exist_ok=True)
            self.logger.info(f"Session directory created: {self.session_dir}")

            return self.session_dir

        except OSError as e:
            self.logger.error(f"Failed to create session directory {self.session_dir}: {e}")
            raise
