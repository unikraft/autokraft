#!/bin/bash

if [ -z "$1" ]; then
  echo "Usage: ./setup.sh <dir_path>"
  exit 1
fi

dir_path="$1"
cp -r "$dir_path" .

folder_name=$(basename "$dir_path")
mv "$folder_name" .app
