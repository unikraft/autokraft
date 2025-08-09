#!/bin/bash

# Default tests directory
TESTS_DIR="${1:-.tests}"

sudo rm -fr "$TESTS_DIR"
sudo rm -fr .app