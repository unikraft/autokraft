#!/bin/bash

if [ -z "$1" ]; then
  echo "Usage: ./tests_runner.sh <app_dir_path>"
  exit 1
fi

app_dir_path="$1"

rm -fr .tests/
source testing-fw-venv/bin/activate
python src/main.py "$app_dir_path"