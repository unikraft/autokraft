"""
Enhanced README parser that extracts memory, port mappings, and curl URLs
from README files and updates config.yaml with the extracted information.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple, Union, Optional
from dataclasses import dataclass

import yaml


@dataclass
class ParsedReadmeData:
    """Data class to hold parsed README information."""
    memory_values: List[str]  # e.g., ["256M", "512M"]
    port_mappings: List[Tuple[int, int]]  # e.g., [(8080, 80), (3000, 3000)]
    curl_urls: List[str]  # e.g., ["localhost:8888", "localhost:3000/api"]


class ReadmeParser:
    """Enhanced README parser for extracting various configuration values."""

    def __init__(self):
        # Regex patterns for different extractions
        self.memory_pattern = re.compile(
            r"""
            -M\s+                     # '-M' followed by whitespace
            ["\']?                    # optional quote
            (?P<memory>\d+[KMG]?)     # memory value with optional unit
            ["\']?                    # optional closing quote
            """,
            re.VERBOSE | re.IGNORECASE
        )
        
        self.port_p_pattern = re.compile(
            r"""
            -p\s+                     # '-p' followed by whitespace
            (?P<host>\d+)\s*:\s*(?P<container>\d+)  # host:container
            """,
            re.VERBOSE
        )
        
        self.port_long_pattern = re.compile(
            r"""
            --port(?:=|\s+)           # '--port' followed by '=' or whitespace
            (?P<host2>\d+)\s*:\s*(?P<container2>\d+)
            """,
            re.VERBOSE
        )
        
        self.port_single_pattern = re.compile(
            r"""
            --port(?:=|\s+)           # '--port' followed by '=' or whitespace
            (?P<port>\d+)\b           # single port
            """,
            re.VERBOSE
        )
        
        # self.curl_pattern = re.compile(
        #     r"""
        #     curl\s+                   # 'curl' followed by whitespace
        #     (?:(?:-[a-zA-Z]\s+\S+\s+)*)  # optional curl flags
        #     (?P<url>localhost:\d+(?:/\S*)?)  # localhost URL with port
        #     """,
        #     re.VERBOSE | re.IGNORECASE
        # )
        self.curl_pattern = re.compile(
            r"""
            curl\s+                   # 'curl' followed by whitespace
            (?:(?:-[a-zA-Z]+(?:\s+\S+)?)\s+)*  # optional curl flags (short form like -X, -H, etc.)
            (?:(?:--[a-zA-Z-]+(?:=\S+|\s+\S+)?)\s+)*  # optional curl flags (long form like --header)
            (?P<url>\S+)              # capture the URL (any non-whitespace characters)
            """,
            re.VERBOSE | re.IGNORECASE
        )

    def find_readme_file(self, readme_dir: Union[str, Path]) -> Path:
        """Find README file in the given directory, preferring README.md."""
        readme_dir = Path(readme_dir)
        if not readme_dir.is_dir():
            raise ValueError(f"Provided path is not a directory: {readme_dir!r}")

        candidates = []
        for fname in os.listdir(readme_dir):
            if re.match(r"(?i)^readme(\.[a-z0-9]+)?$", fname):
                candidates.append(readme_dir / fname)
        
        if not candidates:
            raise FileNotFoundError(f"No README file found in directory: {readme_dir!r}")

        # Prefer README.md if present
        for candidate in candidates:
            if candidate.name.lower() == "readme.md":
                return candidate
        
        # Return first candidate alphabetically for determinism
        candidates.sort(key=lambda p: p.name.lower())
        return candidates[0]

    def parse_readme(self, readme_path: Union[str, Path]) -> ParsedReadmeData:
        """Parse README file and extract memory, ports, and curl URLs."""
        readme_path = Path(readme_path)
        
        try:
            text = readme_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            raise IOError(f"Could not read README file {readme_path}: {e}")

        # Extract memory values
        memory_values = []
        for match in self.memory_pattern.finditer(text):
            memory = match.group("memory")
            if memory not in memory_values:
                memory_values.append(memory)

        # Extract port mappings
        port_mappings = []
        seen_ports = set()

        # -p HOST:CONTAINER
        for match in self.port_p_pattern.finditer(text):
            host = int(match.group("host"))
            container = int(match.group("container"))
            mapping = (host, container)
            if mapping not in seen_ports:
                seen_ports.add(mapping)
                port_mappings.append(mapping)

        # --port HOST:CONTAINER
        for match in self.port_long_pattern.finditer(text):
            host = int(match.group("host2"))
            container = int(match.group("container2"))
            mapping = (host, container)
            if mapping not in seen_ports:
                seen_ports.add(mapping)
                port_mappings.append(mapping)

        # --port PORT (single port)
        for match in self.port_single_pattern.finditer(text):
            port = int(match.group("port"))
            mapping = (port, port)
            if mapping not in seen_ports:
                seen_ports.add(mapping)
                port_mappings.append(mapping)

        # Extract curl URLs
        curl_urls = []
        for match in self.curl_pattern.finditer(text):
            url = match.group("url")
            if url not in curl_urls:
                curl_urls.append(url)

        return ParsedReadmeData(
            memory_values=memory_values,
            port_mappings=port_mappings,
            curl_urls=curl_urls
        )

    def update_config_from_readme(
        self,
        readme_dir: Union[str, Path],
        config_filename: str = "config.yaml",
        port_mapping_index: int = 0,
        memory_index: int = 0,
        curl_index: int = 0
    ) -> None:
        """
        Parse README and update config.yaml with extracted information.
        
        Args:
            readme_dir: Directory containing README file
            config_filename: Name of config file to update
            port_mapping_index: Index of port mapping to use (0-based)
            memory_index: Index of memory value to use (0-based)
            curl_index: Index of curl URL to use (0-based)
        """
        readme_dir = Path(readme_dir)
        
        # Find and parse README
        readme_path = self.find_readme_file(readme_dir)
        parsed_data = self.parse_readme(readme_path)
        
        # Locate config.yaml in parent directory
        parent = readme_dir.parent
        config_path = parent / config_filename
        
        if not config_path.is_file():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        # Load existing YAML
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
        except Exception as e:
            raise IOError(f"Failed to read/parse YAML {config_path}: {e}")

        # Update config with parsed data
        updates = {}
        
        # Update port mappings
        if parsed_data.port_mappings:
            try:
                public_port, exposed_port = parsed_data.port_mappings[port_mapping_index]
                config["public_port"] = public_port
                config["exposed_port"] = exposed_port
                updates["ports"] = f"public_port={public_port}, exposed_port={exposed_port}"
            except IndexError:
                raise IndexError(
                    f"port_mapping_index {port_mapping_index} out of range; "
                    f"only {len(parsed_data.port_mappings)} mapping(s) found"
                )
        
        # Update memory
        if parsed_data.memory_values:
            try:
                memory = parsed_data.memory_values[memory_index]
                memory = memory[:-1] if memory.endswith("M") else memory
                config["memory"] = memory
                updates["memory"] = memory
            except IndexError:
                raise IndexError(
                    f"memory_index {memory_index} out of range; "
                    f"only {len(parsed_data.memory_values)} memory value(s) found"
                )
        else:
            memory = config.get("memory", "256M")
            updates["memory"] = memory
        
        
        # Update curl URL
        if parsed_data.curl_urls:
            try:
                curl_url = parsed_data.curl_urls[curl_index]
                config["testing_command"] = "curl " + curl_url
                updates["testing_command"] = "curl " + curl_url
            except IndexError:
                raise IndexError(
                    f"curl_index {curl_index} out of range; "
                    f"only {len(parsed_data.curl_urls)} curl URL(s) found"
                )
        else:
            if parsed_data.port_mappings:
                # Default to first port mapping if no curl URLs found
                default_port = parsed_data.port_mappings[0][0]
                config["testing_command"] = f"curl localhost:{default_port}"
                updates["testing_command"] = f"curl localhost:{default_port}"
            else:
                config["testing_command"] = None
                updates["testing_command"] = None
                config["networking"] = False
                updates["networking"] = False
        # Write updated config
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            raise IOError(f"Failed to write updated YAML to {config_path}: {e}")

        # Print summary
        update_summary = ", ".join(f"{k}={v}" for k, v in updates.items())
        print(
            f"Updated {config_path} with {update_summary} "
            f"(from README: {readme_path})."
        )


def update_config_from_readme(
    readme_dir: Union[str, Path],
    config_filename: str = "config.yaml",
    port_mapping_index: int = 0,
    memory_index: int = 0,
    curl_index: int = 0
) -> None:
    """
    Convenience function to parse README and update config.yaml.
    
    Args:
        readme_dir: Directory containing README file
        config_filename: Name of config file to update
        port_mapping_index: Index of port mapping to use (0-based)
        memory_index: Index of memory value to use (0-based)
        curl_index: Index of curl URL to use (0-based)
    """
    parser = ReadmeParser()
    parser.update_config_from_readme(
        readme_dir, config_filename, port_mapping_index, memory_index, curl_index
    )


if __name__ == "__main__":
    try:
        update_config_from_readme("./.app")
    except Exception as e:
        print("Error:", e)
