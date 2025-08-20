#!/bin/bash

source testing-fw-venv/bin/activate

CATALOG_PATH=${1:-"/home/machine02/catalog/library/base"}

python src/main.py "$CATALOG_PATH" --tests-dir .runtime_tests --app-dir-name .runtime_app --generate-only