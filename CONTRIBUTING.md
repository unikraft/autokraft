# Contributing to the Unikraft Testing Framework

Thank you for your interest in contributing to this project! Your contributions are welcome and appreciated. This guide outlines how to report bugs, suggest enhancements, and submit pull requests.

## 📂 Repository Structure

This repository contains a modular Python-based testing framework tailored for [Unikraft](https://github.com/unikraft/unikraft), specifically targeting the [catalog](https://github.com/unikraft/catalog) and [catalog-core](https://github.com/unikraft/catalog-core) repositories. It is designed to automatically build and validate unikernel applications and libraries defined within these catalogs, across various configurations such as architectures, VMMs, and boot protocols.

## 🐞 Reporting Issues

- Use GitHub Issues to report bugs.
- Please include details such as:
  - Steps to reproduce the bug
  - The environment (host OS, compiler version, etc.)
  - Logs, stack traces, or screenshots

## 💡 Suggesting Enhancements

- Describe the enhancement clearly.
- Explain why it would be useful.

## 🧑‍💻 Submitting Pull Requests

1. Fork the repository.
2. Create a new branch (`git checkout -b username/typeshort-description`).
3. Set up code quality tools (see below).
4. Make your changes following our coding guidelines.
5. Ensure all pre-commit checks pass.
6. Commit your changes with a meaningful message.
7. Push to your fork.
8. Open a pull request against the `staging` branch.

## ✅ Coding Guidelines

This project enforces strict code quality standards using automated tools. All contributions must adhere to these standards.

### Code Style Standards

We use three main tools to ensure consistent code quality:

- **Black** (v25.1.0): Automatic code formatter with 100 character line limit
- **isort** (v6.0.1): Import statement organizer (Black-compatible)
- **Pylint** (v3.3.7): Static code analyzer and linter

### Setting Up Code Quality Tools

**First-time setup** (run once after cloning):

```bash
# Ensure you're in the virtual environment
source .venv/bin/activate

# Run the setup script
./setup-pre-commit.sh
```

This installs pre-commit hooks that automatically check your code before each commit.

### Before Committing

Pre-commit hooks will automatically run on `git commit`. To manually check your code:

```bash
# Format all code
make format

# Run all checks
make test

# Or use pre-commit directly
pre-commit run --all-files
```

### Manual Tool Usage

```bash
# Format code with Black
black .

# Sort imports
isort .

# Run Pylint
pylint src/ overall_test.py
```

For detailed information about code style standards, see [CODE_STYLE.md](./CODE_STYLE.md).

### General Guidelines

- Keep your commits focused and clean.
- Document your code appropriately (docstrings for public APIs).
- Follow PEP 8 naming conventions (enforced by Pylint):
  - Functions/variables: `snake_case`
  - Classes: `PascalCase`
  - Constants: `UPPER_CASE`
- Maximum line length: 100 characters
- All code must pass Black, isort, and Pylint checks before merging.

## 📄 License

By contributing, you agree that your contributions will be licensed under the BSD 3-Clause License, the same as the project.

## 🙋 Questions?

If you have any questions, feel free to open an issue or join the [Unikraft Discord](https://bit.ly/UnikraftDiscord).
