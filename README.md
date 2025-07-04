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

## Setup and Run the Testing Framework

### Initial Setup

Follow the steps below to set up the testing framework:

1. Clone the Repository

``` Console
git clone https://github.com/shank250/testing-framework-uk-build.git
cd testing-framework-uk-build
```

2. Create a Virtual Environment

```python
python3 -m venv testing-fw-venv
source testing-fw-venv/bin/activate
```

3. Install Python Dependencies

```console
pip install -r requirements.txt
```

4. Configure the Framework
Open the configuration file: `src/tester_config.yaml`. Locate the following section & Update the base path to point to the absolute path of your local Unikraft repository setup.

```yaml
source:
  base: /absolute/path/to/your/unikraft/root
```

### Running the Framework

To run the framework, use the following command:

```console
./main.sh /absolute/path/to/app/dir
```

Make sure the path you provide is absolute (i.e., it starts with /). This should point to the specific application directory inside your catalog repository.

## Sudo Setup 

This project uses a shell script that requires sudo access. To avoid being prompted for a password every time the script runs, follow these steps:

- Open the sudoers file using the safe editor:
    ```
    sudo visudo
    ```

- Add the following line at the end (replace your_username and /path/to/your/script.sh):

    ```
    your_username ALL=(ALL) NOPASSWD: /path/to/pkill /path/to/kraft
    ```
    
    You may use `which pkill` to know the correct path.

