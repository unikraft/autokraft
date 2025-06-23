"""
This module is responsible for extracting port mappings from a README file
and updating config.yaml file with the extracted ports.
"""

import os
import re
from pathlib import Path
from typing import Tuple, Union

import yaml


def update_config_ports_from_readme(
    readme_dir: Union[str, Path], config_filename: str = "config.yaml", mapping_index: int = 0
) -> None:
    """
    Search for a README file in readme_dir (top-level). Extract the mapping HOST:CONTAINER
    from flags '-p HOST:CONTAINER' or '--port HOST:CONTAINER' / '--port=HOST:CONTAINER'.
    If only single '--port PORT' is found, treat host=container=PORT.
    Then update (or create) config_filename in the parent directory of readme_dir,
    setting:
        public_port: HOST
        exposed_port: CONTAINER
    If multiple mappings are found, picks the one at position mapping_index (0-based).
    Raises:
      - FileNotFoundError if no README is found.
      - FileNotFoundError if config.yaml not found in parent directory.
      - IndexError if mapping_index is out of range of found mappings.
      - ValueError if readme_dir is not a directory.
    """
    readme_dir = Path(readme_dir)
    if not readme_dir.is_dir():
        raise ValueError(f"Provided path is not a directory: {readme_dir!r}")

    # 1. Locate README files at top-level
    # Prefer README.md (case-insensitive), otherwise any README with extension or without.
    candidates = []
    for fname in os.listdir(readme_dir):
        # case-insensitive match README or README.*
        if re.match(r"(?i)^readme(\.[a-z0-9]+)?$", fname):
            candidates.append(readme_dir / fname)
    if not candidates:
        raise FileNotFoundError(f"No README file found in directory: {readme_dir!r}")

    # Prefer README.md if present
    readme_path = None
    for p in candidates:
        if p.name.lower() == "readme.md":
            readme_path = p
            break
    if readme_path is None:
        # pick the first candidate alphabetically for determinism
        candidates.sort(key=lambda p: p.name.lower())
        readme_path = candidates[0]

    # 2. Read README content
    try:
        text = readme_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        raise IOError(f"Could not read README file {readme_path}: {e}")

    # 3. Regex patterns
    pat_p_mapping = re.compile(
        r"""
        -p\s+                     # '-p' followed by whitespace
        (?P<host>\d+)\s*:\s*(?P<container>\d+)  # host:container
    """,
        re.VERBOSE,
    )
    pat_port_mapping = re.compile(
        r"""
        --port(?:=|\s+)           # '--port' followed by '=' or whitespace
        (?P<host2>\d+)\s*:\s*(?P<container2>\d+)
    """,
        re.VERBOSE,
    )
    pat_port_single = re.compile(
        r"""
        --port(?:=|\s+)           # '--port' followed by '=' or whitespace
        (?P<port>\d+)\b           # single port
    """,
        re.VERBOSE,
    )

    mappings: list[Tuple[int, int]] = []
    seen = set()

    # a) '-p HOST:CONTAINER'
    for m in pat_p_mapping.finditer(text):
        host = int(m.group("host"))
        container = int(m.group("container"))
        tup = (host, container)
        if tup not in seen:
            seen.add(tup)
            mappings.append(tup)
    # b) '--port HOST:CONTAINER'
    for m in pat_port_mapping.finditer(text):
        host = int(m.group("host2"))
        container = int(m.group("container2"))
        tup = (host, container)
        if tup not in seen:
            seen.add(tup)
            mappings.append(tup)
    # c) single '--port PORT'
    for m in pat_port_single.finditer(text):
        port = int(m.group("port"))
        tup = (port, port)
        if tup not in seen:
            seen.add(tup)
            mappings.append(tup)

    if not mappings:
        raise ValueError(f"No port mappings (-p or --port) found in README: {readme_path}")

    # 4. Select mapping
    try:
        public_port, exposed_port = mappings[mapping_index]
    except IndexError:
        raise IndexError(
            f"mapping_index {mapping_index} out of range; only {len(mappings)} mapping(s) found"
        )

    # 5. Locate config.yaml in parent directory
    parent = readme_dir.parent
    config_path = parent / config_filename
    if not config_path.is_file():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    # 6. Load existing YAML
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
    except Exception as e:
        raise IOError(f"Failed to read/parse YAML {config_path}: {e}")

    # 7. Update ports
    # Overwrite or set the keys 'public_port' and 'exposed_port'.
    cfg["public_port"] = public_port
    cfg["exposed_port"] = exposed_port

    # 8. Write back YAML
    # Note: safe_dump may reorder keys; if you need to preserve comments/ordering, consider ruamel.yaml.
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(cfg, f, default_flow_style=False, sort_keys=False)
    except Exception as e:
        raise IOError(f"Failed to write updated YAML to {config_path}: {e}")

    print(
        f"Updated {config_path} with public_port={public_port}, exposed_port={exposed_port} "
        f"(from README: {readme_path}, mapping index {mapping_index})."
    )


# Example usage:
if __name__ == "__main__":
    # Suppose your README is in './service' and config.yaml is in './'
    # This will:
    #  - Look for './service/README.md' (or README.*),
    #  - Extract the first port mapping found,
    #  - Update './config.yaml'.
    try:
        update_config_ports_from_readme("./.app", mapping_index=0)
    except Exception as e:
        print("Error:", e)
