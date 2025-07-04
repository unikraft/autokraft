#!/usr/bin/env bash

# Check if argument is missing
if [ -z "$1" ]; then
  echo "Usage: $0 <absolute_path_to_app>"
  exit 1
fi

app_path="$1"

# Check if the path is absolute
if [[ "$app_path" != /* ]]; then
  echo "Error: Please provide an absolute path (it should start with '/')"
  exit 1
fi

# Clean up any previous instances.
./scripts/utils/cleanup.sh

# Setup new instance, passing the absolute path.
./scripts/utils/setup.sh "$app_path"

# Run tests.
./scripts/utils/tests_runner.sh
