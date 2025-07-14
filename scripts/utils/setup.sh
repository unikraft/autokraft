#!/bin/bash

if [ -z "$1" ]; then
  echo "Usage: ./setup.sh <dir_path>"
  exit 1
fi

dir_path="$1"
cp -r "$dir_path" .

folder_name=$(basename "$dir_path")
mv "$folder_name" .app

source testing-fw-venv/bin/activate
python3 src/utils/setup_app_testing_config.py "$dir_path"