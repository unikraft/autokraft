#!/bin/bash
#
# Generate the build configurations of a runtime application (e.g. catalog/library/node/18)
# in .runtime_tests/ and .runtime_app/, without running any test.
#
# src/main.py does this itself for example applications (see src/utils/runtime_manager.py);
# this script is only a helper for running the step by hand.
#
# Usage: ./scripts/utils/new_session.sh <path/to/catalog/library/runtime>
# Set PYTHON to use a specific interpreter, e.g. PYTHON=.venv/bin/python.

if [ -z "$1" ]; then
    echo "Usage: $0 <path/to/catalog/library/runtime>" >&2
    exit 1
fi

CATALOG_PATH="$1"

"${PYTHON:-python3}" src/main.py "$CATALOG_PATH" \
    --tests-dir .runtime_tests \
    --app-dir-name .runtime_app \
    --generate-only
