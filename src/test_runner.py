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
from utils.base import Loggable


class TestRunner(Loggable):
    """
    This TestRunner class is designed to manage the test execution.
    """

    def __init__(self, target: TargetSetup, o_app_dir: str) -> None:
        """
        Initialize the TestRunner with a specific target configrations.

        :param targets: Specific TargetSetup object for TestRunner.
        """
        super().__init__()
        self.target = target
        self.test_app_dir = os.path.join(
            os.getcwd(), "test-app-config", "catalog" + o_app_dir.split("/catalog")[-1]
        )

        if not os.path.exists(self.test_app_dir):
            raise FileNotFoundError(f"Test app directory does not exist: {self.test_app_dir}")

        with open(os.path.join(self.test_app_dir, "BuildConfig.yaml"), "r") as f:
            self.test_build_config = yaml.safe_load(f)

        with open(os.path.join(self.test_app_dir, "RunConfig.yaml"), "r") as f:
            self.test_run_config = yaml.safe_load(f)

        return None

    def _build_target(self) -> int:
        """
        Build the target setup.

        This method will execute the build configuration for the target.
        """

        build_script_path = os.path.join(self.target.build_config.dir, "build")

        if not os.path.exists(build_script_path):
            raise FileNotFoundError(f"Build script directory does not exist: {build_script_path}")

        self.logger.info(f"Building target: {self.target.id}")

        # Initialize log files with headers
        self._write_log_file(
            self.target.build_config.dir,
            "build_stdout.log",
            f"=== BUILD STARTED for {self.target.id} ===\n",
            mode="w",
        )
        self._write_log_file(
            self.target.build_config.dir,
            "build_stderr.log",
            f"=== BUILD STARTED for {self.target.id} ===\n",
            mode="w",
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
                check=False,  # Don't raise exception on non-zero exit codes
            )

            self._write_log_file(
                self.target.build_config.dir, "build_stdout.log", result.stdout, mode="a+"
            )
            self._write_log_file(
                self.target.build_config.dir, "build_stderr.log", result.stderr, mode="a+"
            )
            self._write_log_file(
                self.target.build_config.dir,
                "build_returncode.log",
                str(result.returncode),
                mode="w",
            )

            if result.returncode != 0:
                self.logger.info(
                    f"[!] Build completed with non-zero exit code: {result.returncode}"
                )
                self._write_log_file(
                    self.target.build_config.dir,
                    "build_stdout.log",
                    f"\n=== BUILD FAILED with exit code {result.returncode} ===\n",
                    mode="a+",
                )
            else:
                self.logger.info(f"[✓] Build completed successfully")
                self._write_log_file(
                    self.target.build_config.dir,
                    "build_stdout.log",
                    f"\n=== BUILD COMPLETED SUCCESSFULLY ===\n",
                    mode="a+",
                )

        except subprocess.TimeoutExpired:
            self.logger.info(f"[✗] Build timed out after {threshold_timeout} seconds")
            # Append timeout information to existing logs
            timeout_msg = (
                f"\n=== BUILD TIMEOUT - Process killed after {threshold_timeout} seconds ===\n"
            )
            self._write_log_file(
                self.target.build_config.dir, "build_stderr.log", timeout_msg, mode="a+"
            )
            self._write_log_file(
                self.target.build_config.dir, "build_returncode.log", "-1", mode="w"
            )
        except Exception as e:
            self.logger.info(f"[✗] Build failed with exception: {e}")
            # Append error information to existing logs
            error_msg = f"\n=== BUILD ERROR: {str(e)} ===\n"
            self._write_log_file(
                self.target.build_config.dir, "build_stderr.log", error_msg, mode="a+"
            )
            self._write_log_file(
                self.target.build_config.dir, "build_returncode.log", "-2", mode="w"
            )

        return result.returncode if "result" in locals() else -1

    def _run_target(self, run_target_dir: str) -> Popen[bytes]:
        """
        Run the target setup.

        This method will execute the run configurations for the target.

        Args:
            run_target_dir (str): The directory where the target is running.

        Returns:
            bool: True if the process run was successful, False otherwise.
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

        return process

    def _test_target_build(self, kernel_path: str) -> bool:
        """
        Returns True is the kernel is built successfully. By checking the kernel path.

        Args:
            kernel_path (str): The path to the kernel file.

        Returns:
            bool: True if the kernel is built successfully, False otherwise.
        """

        return True if os.path.exists(kernel_path) else False

    def _test_curl_run(self, run_config) -> tuple[int, str]:
        """
        Test the curl run for the target setup.

        This method will execute the curl command to test the target's run configuration.
        """
        self.logger.info(f"Testing curl run for target: {self.target.id}")

        test_command = self.test_run_config.get("ListOfCommands", ["curl http://localhost:8080"])[0]

        # Check the networking configuration
        network_type = run_config.config.get("networking", "none")
        if network_type == "bridge":
            test_command = test_command.replace("https://", "")
            test_command = test_command.replace("http://", "")
            test_command = test_command.replace("localhost", "172.44.0.2")

        self.logger.info(f"Executing test command: {test_command}")

        try:
            result = subprocess.run(
                list(test_command.split()),
                capture_output=True,
                text=True,
                timeout=4,  # Timeout for the curl command
            )
            run_log = result.stdout + result.stderr
            output = result.stdout.replace("\r", "").replace("\t", "").strip()
            self.logger.info(f"Curl command output: {output}")
            # self.logger.info(f"Curl command error: {result.stderr}")

            if result.returncode == 0:
                self.logger.info("[✓] Curl test passed")
                run_log += "\n[✓] Curl command  executed\n"
            else:
                self.logger.info("[✗] Curl test failed")
                run_log += "\n[✗] Curl command failed\n"

            return_code = result.returncode
        except Exception as e:
            self.logger.info(f"[✗] Curl test encountered an error: {e}")
            run_log = f"[✗] Curl command failed with error: {e}\n"
            return_code = -1

        return return_code, run_log

    def _validate_run(self, run_log: str) -> bool:
        """
        Validate the run log and return code.

        This method will check the run log for specific keywords to determine if the run was successful.
        """
        possible_outputs = self.test_run_config.get(
            "ListOfCommands", ["Hwllo, World!", "Bye world"]
        )
        string_found = False

        for output in possible_outputs:
            for word in output.split():
                if word.lower() in run_log.lower():
                    string_found = True
                    self.logger.info(f"[✓] Found expected output: {output}")
                    break

            if output.lower() in run_log.lower():
                string_found = True
                self.logger.info(f"[✓] Found expected output: {output}")
                break

        return string_found

    def _write_row_to_csv(self, row_dict: dict, csv_path: str) -> None:
        """
        Appends a row to a CSV file. Writes headers if the file does not exist.

        :param row_dict: Dictionary where keys are column names and values are row values
        :param csv_path: Path to the CSV file
        """
        file_exists = os.path.isfile(csv_path)

        with open(csv_path, mode="a", newline="") as file:
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
        compiler_info = build_config.pop("compiler", {})
        flat_dict = {
            "build_no": target.id,
            "status": "pass" if return_code == 0 and success else "fail",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "compiler_type": compiler_info.get("type", ""),
            **build_config,
        }

        report_path = os.path.join(self.test_app_dir, "build_report.csv")
        self._write_row_to_csv(flat_dict, report_path)
        self.logger.info(f"[✓] Build report updated for target {target.id}")

    def _update_run_report(
        self, run_config, build_no: int, run_return_code: int, output_matched: bool
    ) -> None:
        """
        Update the run report with the target's run status.

        Args:
            run_config (RunConfig): The run configuration object.
            run_return_code (int): The return code from the run process.
            output_matched (bool): Whether the output matched the expected output or not.
        """
        status = "fail"

        if run_return_code == 0 and output_matched:
            status = "pass"
        elif run_return_code == 0 and not output_matched:
            status = "partial-pass"

        flat_dict = {
            "build_no": build_no,
            "run_id": run_config.dir.split("/")[-1],
            "status": status,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "return_code": run_return_code,
            "output_matched": output_matched,
            **run_config.config,
        }

        report_path = os.path.join(self.test_app_dir, "run_report.csv")
        self._write_row_to_csv(flat_dict, report_path)
        self.logger.info(
            f"[✓] Run report updated for target {run_config.dir.split('/')[-1]} with status {status}"
        )

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
            self.logger.info(
                f"[✓] Log {'appended to' if 'a' in mode else 'written to'} {file_path}"
            )
            return file_path
        except Exception as e:
            error_message = f"Failed to write log to {filename} in {directory}: {e}"
            self.logger.error(f"[✗] {error_message}")
            raise Exception(error_message)

    def run_test(self) -> None:
        """
        Run the test for the target setup.

        This method will execute the build and run configurations for the target.
        """
        self.logger.info(f"Running tests for target: {self.target.id}")
        # Build the target before running tests(upto 2 mins)
        build_return_code = self._build_target()
        # Test if the build was successful
        build_success = self._test_target_build(self.target.build_config.kernel_path)
        # Update the build status in the test-app-config/build_report.csv
        self._update_build_report(self.target, build_return_code, build_success)

        if build_return_code == 0 and build_success:
            self.logger.info(f"[✓] Build successful for target: {self.target.id} \n\n")

            # Iterate over each of the runs
            for idx, run_config in enumerate(self.target.run_configs):

                self.logger.info(f"Running configuration: {run_config.dir}")
                # self.logger.info(f"\tRun configuration of {idx + 1} is {run_config.config}")
                running_process = self._run_target(run_config.dir)
                self.logger.info(
                    f"[✓] Target {self.target.id} is running with PID: {running_process.pid}"
                )

                self.logger.info(
                    f"Waiting for the unikernel to start...{self.test_run_config.get('UnikernelBootupTime', 20)} seconds"
                )
                time.sleep(self.test_run_config.get("UnikernelBootupTime", 20))

                if self.test_run_config["TestingType"] == "curl":
                    # Complete the curl test
                    run_return_code, run_log = self._test_curl_run(run_config)
                elif self.test_run_config["TestingType"] == "list-of-commands":
                    # complete the list of commands test
                    run_return_code, run_log = (
                        -2,
                        "Implementation for list-of-commands test is pending",
                    )
                else:
                    # Test for no commands
                    run_return_code, run_log = -2, "Implementation for no commands test is pending"

                # Now I need to validate the test
                output_matched = self._validate_run(run_log)

                # Update the run log file
                self._write_log_file(run_config.dir, "complete_run.log", run_log, mode="w")

                # Update the run report
                self._update_run_report(run_config, self.target.id, run_return_code, output_matched)

                # Kill the running process
                running_process.terminate()
                self.logger.info(
                    f"[✓] Target {self.target.id} with PID: {running_process.pid} has been terminated"
                )

        else:
            self.logger.info(f"[✗] Build failed for target: {self.target.id}")

        return
