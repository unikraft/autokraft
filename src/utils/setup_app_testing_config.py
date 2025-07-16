import os
from pathlib import Path
from typing import Optional, Tuple

from base import Loggable
from load_llm import LLMLoader


class TestAppConfig(Loggable):
    """
    A class to handle test application configuration setup from catalog directories.
    """

    def __init__(self, base_test_dir: Optional[str] = None):
        """
        Initialize TestAppConfig.

        Args:
            base_test_dir: Base directory for test configuration (default: ./test-app-config)
        """
        super().__init__()
        if base_test_dir is None:
            self.base_test_dir = os.path.join(os.getcwd(), "test-app-config")
        else:
            self.base_test_dir = base_test_dir

    def check_directory_exists(self, directory_path: Path) -> bool:
        """
        Check if the given directory exists.

        Args:
            directory_path: Path to the directory to check

        Returns:
            bool: True if directory exists, False otherwise
        """
        catalog_type, relative_path = self._extract_catalog_info(directory_path)

        if not catalog_type or not relative_path:
            raise ValueError(
                f"Could not identify catalog or catalog-core in path: {directory_path}"
            )
        
        filename = "RunConfig.yaml"
        target_path = Path(self.base_test_dir) / catalog_type / relative_path / filename

        if target_path.exists():         
            self.logger.info(f"RunConfig.yaml already exists at {target_path}, skipping generation.")
            return True

        return False
    
    def setup_config(self, source_directory: str) -> dict:
        """
        Process a catalog directory path and create a replica structure for testing.

        Args:
            source_directory: Path like /home/machine/catalog/library/helloworld/1.2

        Returns:
            dict: Configuration data including paths and README content
        """
        source_path = Path(source_directory)

        # Extract catalog type and remaining path
        catalog_type, relative_path = self._extract_catalog_info(source_path)

        if not catalog_type or not relative_path:
            raise ValueError(
                f"Could not identify catalog or catalog-core in path: {source_directory}"
            )

        # First, try to load README data
        readme_content = self._load_readme_data(source_path)

        if readme_content is None:
            raise FileNotFoundError(f"No README file found in source directory: {source_directory}")

        # Only if README is successfully loaded, create the directory structure
        target_path = Path(self.base_test_dir) / catalog_type / relative_path
        self._create_directory_structure_only(target_path)

        # Generate RunConfig.yaml using LLM
        run_config_content = self._generate_run_config(readme_content, relative_path)

        # Save RunConfig.yaml to target directory
        run_config_path = target_path / "RunConfig.yaml"
        self._save_config(run_config_path, run_config_content)

        # creating BuildConfig.yaml
        build_config_path = target_path / "BuildConfig.yaml"
        self._save_config(build_config_path, "th_time: 300")

        return {
            "source_directory": str(source_path),
            "catalog_type": catalog_type,
            "relative_path": str(relative_path),
            "target_directory": str(target_path),
            "readme_content": readme_content,
            "run_config_content": run_config_content,
            "run_config_path": str(run_config_path),
        }

    def _extract_catalog_info(self, source_path: Path) -> Tuple[Optional[str], Optional[Path]]:
        """
        Extract catalog type and relative path from source directory.

        Returns:
            Tuple of (catalog_type, relative_path_after_catalog)
        """
        parts = source_path.parts

        for i, part in enumerate(parts):
            if part == "catalog-core":
                return "catalog-core", Path(*parts[i + 1 :])
            elif part == "catalog":
                return "catalog", Path(*parts[i + 1 :])

        return None, None

    def _create_directory_structure_only(self, target_path: Path) -> None:
        """
        Create only the directory structure without copying any files.
        """
        target_path.mkdir(parents=True, exist_ok=True)
        self.logger.debug(f"Created directory structure: {target_path}")

    def _load_readme_data(self, source_path: Path) -> Optional[str]:
        """
        Load content from README file in the source directory.

        Returns:
            README content as string, or None if not found
        """
        readme_files = ["README.md", "README.txt", "README", "readme.md", "readme.txt", "readme"]

        for readme_name in readme_files:
            readme_path = source_path / readme_name
            if readme_path.exists() and readme_path.is_file():
                try:
                    with open(readme_path, "r", encoding="utf-8") as f:
                        return f.read()
                except UnicodeDecodeError:
                    # Try with different encoding if UTF-8 fails
                    try:
                        with open(readme_path, "r", encoding="latin-1") as f:
                            return f.read()
                    except Exception as e:
                        self.logger.warning(f"Warning: Could not read {readme_path}: {e}")
                        continue
                except Exception as e:
                    self.logger.warning(f"Warning: Could not read {readme_path}: {e}")
                    continue

        return None

    def _generate_run_config(self, readme_content: str, relative_path: Path) -> str:
        """
        Generate RunConfig.yaml content using LLM based on README content.

        Args:
            readme_content: Content from README file
            relative_path: Relative path of the application

        Returns:
            Generated RunConfig.yaml content as string
        """
        try:
            # Initialize LLM
            llm_loader = LLMLoader()
            model = llm_loader.get_model()

            # Create prompt for RunConfig generation
            prompt = self._create_run_config_prompt(readme_content, relative_path)

            # Generate RunConfig using LLM
            response = model.invoke(prompt)

            return str(response.content)

        except Exception as e:
            self.logger.warning(f"Warning: Could not generate RunConfig using LLM: {e}")
            return "LLM generation failed. Please check the README content and try again."

    def _create_run_config_prompt(self, readme_content: str, relative_path: Path) -> str:
        """
        Create a prompt for LLM to generate RunConfig.yaml.

        Args:
            readme_content: README file content
            relative_path: Application relative path

        Returns:
            Formatted prompt string
        """
        app_name = relative_path.name if relative_path.parts else "unknown"

        prompt = f"""
You are an expert AI assistant familiar with:

1. **Unikraft & Unikernels**
   – VMMs (QEMU, Firecracker, etc.)
   – Memory, networking and hypervisor configuration options

2. **Unikraft Catalog Applications**
   – Core catalog apps (hello‑world, redis, httpd, etc.)
   – Typical directory layouts and required build/run steps

3. **Custom Testing Framework**
   – Uses isolated `.app` fixture directories
   – Captures `build.log`, `run.log`, `summary.json`
   – Integrates with CI/CD for parallel matrix runs and artifact upload

---

## Your Task

Given the contents of an application’s `README.md` (inserted below), **generate a `RunConfig.yaml`** that will:

* **Launch** the unikernel with proper VMM, memory, and networking settings
* **Define** post‑run validation steps to confirm success

Do **not** include any commentary—only output the YAML.

```markdown
{readme_content}
```

---

## RunConfig Schema

```yaml
  RunMetadata: # extract most of these info from the kraft run command
    Memory:         # integer in MB (e.g. 256)
    Networking:     # true or false
    ExposedPort:   # integer, only if Networking: true else 0
    PublicPort:     # integer, only if Networking: true else 0

  TestingType:      # “no-command” | “curl” | “list-of-commands”
  ListOfCommands:   # only if TestingType: list-of-commands or curl
    - "<shell command 1> or complete curl command with localhost"
    - "<shell command 2>"

  ExpectedOutput:   # array of strings to match in test output
    # mostly like hello / world / bye / world or other based on application 
    # Add too many possible phrases to match
    - "Possible phrase 1"
    - "Possible phrase 2"
```

---

## Behavior Guidelines

* **Hello‑world or console apps**

  * `Networking: false`
  * `TestingType: no-command`
  * `ExpectedOutput`: the exact console message

* **HTTP services (nginx, httpd, etc.)**

  * `Networking: true`
  * `TestingType: curl`
  * `NetworkingType`: choose NAT (e.g. `curl localhost:<PublicPort>`) or Bridge (e.g. `curl http://<ExternalIP>:<PublicPort>`)
  * `ExpectedOutput`: e.g. “HTTP/1.1 200 OK”

* **Stateful services (redis, mysql, etc.)**

  * `Networking: true`
  * `TestingType: list-of-commands`
  * `ListOfCommands`: e.g. `redis-cli -h localhost -p <PublicPort> PING`
  * `ExpectedOutput`: e.g. “PONG”

* **Complex multi‑step apps**

  * Use `list-of-commands` for setup, health-check, and teardown
  * Ensure `ExpectedOutput` covers key success markers

---

**Generate only the final `RunConfig.yaml`**, populated with values inferred from the README.
Do **not** include any commentary—only output the raw YAML.  
**Do not** include any code fences (```), headings, or extra formatting—output raw YAML only.

"""
        return prompt

    def _save_config(self, config_path: Path, content: str) -> None:
        """
        Save configuration content to file.

        Args:
            config_path: Path where to save the configuration file
            content: Configuration content to save
        """
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                f.write(content)
            self.logger.info(f"Configuration file saved at: {config_path}")
        except Exception as e:
            self.logger.warning(f"Warning: Could not save configuration file {config_path}: {e}")


def main(directory_path: str) -> dict:
    """
    Main function to process a catalog directory path using TestAppConfig class.
    """
    try:
        test_config = TestAppConfig()
        if test_config.check_directory_exists(Path(directory_path)):
            return {}
        test_app_config = test_config.setup_config(directory_path)
        return test_app_config
    except Exception as e:
        print(f"Error processing directory: {e}")
        raise


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python setup_app_testing_config.py <directory_path>")
        sys.exit(1)

    directory_path = sys.argv[1]
    main(directory_path)
