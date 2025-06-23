#!/usr/bin/env bash
if [ -z "$1" ]; then
  echo "Usage: $0 <app_name_ver>"
  exit 1
fi

app_name_ver="$1"

# Clean up any previous instances.
./scripts/utils/cleanup.sh

# Setup new instance, passing the versioned path.
./scripts/utils/setup.sh "/home/machine02/catalog/library/${app_name_ver}/"

# Run tests.
./scripts/utils/tests_runner.sh
