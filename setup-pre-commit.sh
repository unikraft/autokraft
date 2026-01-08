#!/usr/bin/env bash
#
# Setup script for installing and configuring pre-commit hooks
# This script automates the installation of code quality tools
#

set -e

echo "================================================"
echo "Setting up code quality tools for autokraft"
echo "================================================"
echo ""

# Check if we're in a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Warning: No virtual environment detected!"
    echo "   It's recommended to run this in a virtual environment."
    echo ""
    echo "   To create and activate one:"
    echo "   $ python -m venv .venv"
    echo "   $ source .venv/bin/activate"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Install pre-commit if not already installed
echo "📦 Installing pre-commit..."
pip install pre-commit==4.0.1

# Install pre-commit hooks
echo ""
echo "🔧 Installing pre-commit git hooks..."
pre-commit install

# Run pre-commit on all files to verify setup
echo ""
echo "✅ Running pre-commit checks on all files..."
echo "   (This may take a moment on first run)"
pre-commit run --all-files || true

echo ""
echo "================================================"
echo "✅ Setup complete!"
echo "================================================"
echo ""
echo "Pre-commit hooks are now installed and will run automatically"
echo "on every commit to ensure code quality."
echo ""
echo "Available commands:"
echo "  - Run checks manually: pre-commit run --all-files"
echo "  - Update hooks: pre-commit autoupdate"
echo "  - Run specific hook: pre-commit run <hook-id>"
echo ""
echo "Code formatting tools:"
echo "  - black: Code formatter (line length: 100)"
echo "  - isort: Import sorter (compatible with black)"
echo "  - pylint: Code linter and analyzer"
echo ""
