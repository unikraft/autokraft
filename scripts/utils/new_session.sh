#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Get the autokraft root directory (two levels up from scripts/utils)
AUTOKRAFT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Activate virtual environment if it exists
if [ -f "$AUTOKRAFT_DIR/testing-fw-venv/bin/activate" ]; then
    source "$AUTOKRAFT_DIR/testing-fw-venv/bin/activate"
elif [ -f "$AUTOKRAFT_DIR/venv/bin/activate" ]; then
    source "$AUTOKRAFT_DIR/venv/bin/activate"
elif [ -f "$AUTOKRAFT_DIR/.venv/bin/activate" ]; then
    source "$AUTOKRAFT_DIR/.venv/bin/activate"
fi
# If no venv found, continue with system Python (assuming dependencies are installed)

CATALOG_PATH=${1:-"/home/machine02/catalog/library/base"}

cd "$AUTOKRAFT_DIR"
python src/main.py "$CATALOG_PATH" --tests-dir .runtime_tests --app-dir-name .runtime_app --generate-only