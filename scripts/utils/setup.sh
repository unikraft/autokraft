#!/bin/bash

if [ -z "$1" ]; then
  echo "Usage: ./setup.sh <dir_path> [app_dir_name]"
  exit 1
fi

dir_path="$1"
# Use custom app directory name if provided, otherwise default to .app
app_dir_name="${2:-.app}"

cp -r "$dir_path" .

folder_name=$(basename "$dir_path")
mv "$folder_name" "$app_dir_name"

source testing-fw-venv/bin/activate
python3 src/utils/setup_app_testing_config.py "$dir_path"