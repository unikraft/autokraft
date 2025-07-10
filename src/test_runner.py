"""
This module provides TestRunner class to manage the test execution.
"""

import csv
import os
import subprocess
import time
from subprocess import PIPE, Popen, run

import yaml

from target_setup import TargetSetup


class TestRunner:
    """
    This TestRunner class is designed to manage the test execution.
    """

    def __init__(self, target: TargetSetup, o_app_dir: str) -> None:
        """
        Initialize the TestRunner with a specific target configrations.

        :param targets: Specific TargetSetup object for TestRunner.
        """
        self.target = target
        self.test_app_dir = os.path.join(
            os.getcwd(),
            "test-app-config",
            "catalog" + o_app_dir.split("/catalog")[-1]
        )
        if not os.path.exists(self.test_app_dir):
            raise FileNotFoundError(f"Test app directory does not exist: {self.test_app_dir}")
        
        with open(os.path.join(self.test_app_dir, "BuildConfig.yaml"), "r") as f:
            self.test_build_config = yaml.safe_load(f)
        
        return None
        
    def _build_target(self) -> int:
        """
        Build the target setup.

        This method will execute the build configuration for the target.
        """

        build_script_path = os.path.join(self.target.build_config.dir, "build")

        if not os.path.exists(build_script_path):
            raise FileNotFoundError(f"Build script directory does not exist: {build_script_path}")

        print("Building target:", self.target.id)

        # Initialize log files with headers
        self._write_log_file(
            self.target.build_config.dir, "build_stdout.log", f"=== BUILD STARTED for {self.target.id} ===\n", mode="w"
        )
        self._write_log_file(
            self.target.build_config.dir, "build_stderr.log", f"=== BUILD STARTED for {self.target.id} ===\n", mode="w"
        )

        threshold_timeout = self.test_build_config.get("th_time", 180)  

        try:
            # Use subprocess.run with timeout for better control
            result = subprocess.run(
                ["bash", build_script_path],
                cwd=self.target.build_config.dir,
                capture_output=True,
                text=True,
                timeout=threshold_timeout,
                check=False   # Don't raise exception on non-zero exit codes
            )
            
            self._write_log_file(
                self.target.build_config.dir, "build_stdout.log", result.stdout, mode="a+"
            )
            self._write_log_file(
                self.target.build_config.dir, "build_stderr.log", result.stderr, mode="a+"
            )
            self._write_log_file(
                self.target.build_config.dir, "build_returncode.log", str(result.returncode), mode="w"
            )
            
            if result.returncode != 0:
                print(f"[!] Build completed with non-zero exit code: {result.returncode}")
                self._write_log_file(
                    self.target.build_config.dir, "build_stdout.log", f"\n=== BUILD FAILED with exit code {result.returncode} ===\n", mode="a+"
                )
            else:
                print(f"[✓] Build completed successfully")
                self._write_log_file(
                    self.target.build_config.dir, "build_stdout.log", f"\n=== BUILD COMPLETED SUCCESSFULLY ===\n", mode="a+"
                )
                
        except subprocess.TimeoutExpired:
            print(f"[✗] Build timed out after {threshold_timeout} seconds")
            # Append timeout information to existing logs
            timeout_msg = f"\n=== BUILD TIMEOUT - Process killed after {threshold_timeout} seconds ===\n"
            self._write_log_file(
                self.target.build_config.dir, "build_stderr.log", timeout_msg, mode="a+"
            )
            self._write_log_file(
                self.target.build_config.dir, "build_returncode.log", "-1", mode="w"
            )
        except Exception as e:
            print(f"[✗] Build failed with exception: {e}")
            # Append error information to existing logs
            error_msg = f"\n=== BUILD ERROR: {str(e)} ===\n"
            self._write_log_file(
                self.target.build_config.dir, "build_stderr.log", error_msg, mode="a+"
            )
            self._write_log_file(
                self.target.build_config.dir, "build_returncode.log", "-2", mode="w"
            )

        return result.returncode if 'result' in locals() else -1

    def _run_target(self, run_target_dir: str) -> bool:
        """
        Run the target setup.

        This method will execute the run configurations for the target.
        """
        run_script_path = os.path.join(run_target_dir, "run")
        run_log_path = os.path.join(run_target_dir, "run.log")

        # Start run script in background
        with open(run_log_path, "w") as run_log_file:
            process = subprocess.Popen(
                ["bash", run_script_path],
                cwd=run_target_dir,
                stdout=run_log_file,
                stderr=run_log_file,
            )

        print("Sleep started for 3 seconds to allow unikernel to start")
        time.sleep(3)

        is_run_success = self._test_target_run(
            self.target.build_config.dir
        )  # TODO: This is required to be done symultaniously.
        
        print(f"Run test result: {str(process.stdout) + str(process.stderr)}")
        print("/n/n")

        # Wait for the unikernel to finish or timeout
        try:
            process.wait(timeout=2)
        except Exception as e:
            process.terminate()

        return is_run_success

    def _test_target_build(self, kernel_path: str) -> bool:
        """
        Returns True is the kernel is built successfully. By checking the kernel path.
        
        Args:
            kernel_path (str): The path to the kernel file.
            
        Returns:
            bool: True if the kernel is built successfully, False otherwise.
        """

        return True if os.path.exists(kernel_path) else False

    def _test_target_run(self, run_target_dir: str) -> bool:
        """
        Test the target run.

        This method will execute the test configurations for the target.

        Args:
            run_target_dir (str): The directory where the target is running.
        Returns:
            bool: True if the test was successful, False otherwise.
        """
        print(f"Testing target run in directory: {run_target_dir}")

        with open("config.yaml", "r") as f:
            app_config = yaml.safe_load(f)

        curl_log_path = os.path.join(run_target_dir, "run_curl.log")
        networking_enabled = app_config.get("networking", False)
        curl_command = app_config.get("testing_command", "curl http://localhost:8080")

        # If networking is enabled, send a curl request
        if networking_enabled:
            try:
                print(f"Sending curl request: {curl_command} with timeout of 4 seconds")
                curl_result = run(
                    list(curl_command.split(" ")), capture_output=True, text=True, timeout=4
                )
                with open(curl_log_path, "a") as f:
                    f.write("STDOUT: \n" + curl_result.stdout)
                    f.write("STDERR: \n" + curl_result.stderr)
                print(f"Curl request completed with stdout: {curl_result.stdout + curl_result.stderr}")
            except Exception as e:
                with open(curl_log_path, "w") as f:
                    f.write(f"[✗] Curl request failed: {e}")
                return False
        # TODO: Implement a test for the unikernel without networking

            # Parse and check the curl_log_path for the success of the unikernel run
            with open(curl_log_path, "r") as f:
                log_content = f.read()
                if (
                    "world" in log_content.lower()
                    or "bye" in log_content.lower()
                    or "hello" in log_content.lower()
                ):
                    print("[✓] Unikernel run test passed")
                else:
                    print("[✗] Unikernel run test failed")
                    return False
        else:
            print("[✓] Networking is disabled, skipping curl test")
            return False
        
        return True

    def _write_row_to_csv(self, row_dict: dict, csv_path: str) -> None:
        """
        Appends a row to a CSV file. Writes headers if the file does not exist.
        
        :param row_dict: Dictionary where keys are column names and values are row values
        :param csv_path: Path to the CSV file
        """
        file_exists = os.path.isfile(csv_path)

        with open(csv_path, mode='a', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=row_dict.keys())

            if not file_exists:
                writer.writeheader()  # Write headers only once

            writer.writerow(row_dict)

    def _update_build_report(self, target: TargetSetup, return_code: int, success: bool) -> None:
        """
        Update the build report with the target's build status.

        Args:
            target (TargetSetup): The target setup object.
            return_code (int): The return code from the build process.
            success (bool): Whether the build was successful or not.
        """
        build_config = target.config["build"]
        compiler_info = build_config.pop('compiler', {})
        flat_dict = {
            'test_name': target.id,
            'status': 'pass' if return_code == 0 and success else 'fail',
            'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
            'compiler_type': compiler_info.get('type', ''),
            **build_config
        }

        report_path = os.path.join(self.test_app_dir, "build_report.csv")
        self._write_row_to_csv(flat_dict, report_path)
        print(f"[✓] Build report updated for target {target.id}")

    def _write_log_file(self, directory: str, filename: str, data: str, mode: str = "w") -> str:
        """
        Writes the given data to a file in the specified directory.
        Creates the directory if it does not exist.

        Args:
            directory (str): The directory path where the log file will be saved.
            filename (str): The name of the log file (e.g., 'build.log').
            data (str): The content to write into the log file.
            mode (str): File mode - 'w' for overwrite, 'a+' for append (default: 'w').

        Returns:
            str: The path to the log file if written successfully, otherwise an error message.
        """
        try:
            os.makedirs(directory, exist_ok=True)  # Ensure the directory exists
            file_path = os.path.join(directory, filename)
            with open(file_path, mode, encoding="utf-8") as f:
                f.write(data)
            print(f"[✓] Log {'appended to' if 'a' in mode else 'written to'} {file_path}")
            return file_path
        except Exception as e:
            error_message = f"Failed to write log to {filename} in {directory}: {e}"
            print(f"[✗] {error_message}")
            raise Exception(error_message)
        
    def run_test(self) -> None:
        """
        Run the test for the target setup.

        This method will execute the build and run configurations for the target.
        """
        print(f"Running tests for target: {self.target.id}")
        # Build the target before running tests(upto 2 mins)
        build_return_code = self._build_target()
        # Test if the build was successful
        build_success = self._test_target_build(
            self.target.build_config.kernel_path
        )
        # Update the build status in the test-app-config/build_report.csv 
        self._update_build_report(
            self.target,
            build_return_code,
            build_success
        )

        
        if build_return_code == 0 and build_success:
            print(f"[✓] Build successful for target: {self.target.id}")

            # Iterate over each of the runs
            for idx, run_config in enumerate(self.target.run_configs):

                print(f"Running configuration: {run_config.dir}")
                # print(f"Run configuration of {idx + 1} is {run_config.config}")
                # Execute each run configuration (upto 5 secs)
                self._run_target(run_config.dir)
                # Test the running unikernel

        else:
            print(f"[✗] Build failed for target: {self.target.id}")
            return
