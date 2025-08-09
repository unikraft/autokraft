#!/bin/bash

source testing-fw-venv/bin/activate

# TODO: Later need to add runtime path
python src/main.py  /home/machine02/catalog/library/base --tests-dir .runtime_tests --app-dir-name .runtime_app --generate-only