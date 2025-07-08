import os
from pathlib import Path
from typing import Optional, Tuple


class TestAppConfig:
    """
    A class to handle test application configuration setup from catalog directories.
    """
    
    def __init__(self, base_test_dir: Optional[str] = None):
        """
        Initialize TestAppConfig.
        
        Args:
            base_test_dir: Base directory for test configuration (default: ./test-app-config)
        """
        if base_test_dir is None:
            self.base_test_dir = os.path.join(os.getcwd(), "test-app-config")
        else:
            self.base_test_dir = base_test_dir
    
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
            raise ValueError(f"Could not identify catalog or catalog-core in path: {source_directory}")
        
        # First, try to load README data
        readme_content = self._load_readme_data(source_path)
        
        if readme_content is None:
            raise FileNotFoundError(f"No README file found in source directory: {source_directory}")
        
        # Only if README is successfully loaded, create the directory structure
        target_path = Path(self.base_test_dir) / catalog_type / relative_path
        self._create_directory_structure_only(target_path)
        
        return {
            "source_directory": str(source_path),
            "catalog_type": catalog_type,
            "relative_path": str(relative_path),
            "target_directory": str(target_path),
            "readme_content": readme_content
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
                return "catalog-core", Path(*parts[i+1:])
            elif part == "catalog":
                return "catalog", Path(*parts[i+1:])
        
        return None, None

    def _create_directory_structure_only(self, target_path: Path) -> None:
        """
        Create only the directory structure without copying any files.
        """
        target_path.mkdir(parents=True, exist_ok=True)
        print(f"Created directory structure: {target_path}")

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
                    with open(readme_path, 'r', encoding='utf-8') as f:
                        return f.read()
                except UnicodeDecodeError:
                    # Try with different encoding if UTF-8 fails
                    try:
                        with open(readme_path, 'r', encoding='latin-1') as f:
                            return f.read()
                    except Exception as e:
                        print(f"Warning: Could not read {readme_path}: {e}")
                        continue
                except Exception as e:
                    print(f"Warning: Could not read {readme_path}: {e}")
                    continue
        
        return None


def main(directory_path: str) -> dict:
    """
    Main function to process a catalog directory path using TestAppConfig class.
    """
    try:
        test_config = TestAppConfig()
        config = test_config.setup_config(directory_path)
        print(f"Successfully processed: {directory_path}")
        print(f"Catalog type: {config['catalog_type']}")
        print(f"Target created at: {config['target_directory']}")
        print(f"README content loaded: {len(config['readme_content'])} characters")
        return config
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
