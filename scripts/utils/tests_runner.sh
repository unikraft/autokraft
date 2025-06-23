#!/bin/bash

rm -fr .tests/
source testing-fw-venv/bin/activate
python src/main.py src/tester_config.yaml