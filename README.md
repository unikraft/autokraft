# autokraft
Automate Unikraft testing

#  Testing Framework for Unikraft Builds

A modular and extensible Python-based testing framework for validating Unikraft unikernel builds across various configurations, platforms, and environments. This tool is designed to be seamlessly integrated into the CI/CD pipelines of the Unikraft ecosystem.

##  Overview

This project aims to:

- Automate configuration, building, and testing of Unikraft unikernels.
- Support a wide range of configuration options: VMMs, hypervisors, architectures, and boot protocols.
- Integrate tightly with the `catalog` and `catalog-core` repositories.
- Run as part of Unikraft’s CI/CD workflows to validate pull requests automatically.

## Sudo Setup 

This project uses a shell script that requires sudo access. To avoid being prompted for a password every time the script runs, follow these steps:

- Open the sudoers file using the safe editor:
    `sudo visudo`

- Add the following line at the end (replace your_username and /path/to/your/script.sh):
    `your_username ALL=(ALL) NOPASSWD: /path/to/your/script.sh or /path/to/pkill`
    You may use `which pkill` to know the correct path.

