#!/bin/bash

# Default directories
TESTS_DIR="${1:-.tests}"
APP_DIR="${2:-.app}"

sudo rm -fr "$TESTS_DIR"
sudo rm -fr "$APP_DIR"