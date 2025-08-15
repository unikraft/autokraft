import os
import yaml
import shutil
import subprocess

def create_examples_runtime(selected_targets, targets, runtime_name) -> None:
    """
    Create the key target runtimes for example applications.
    This function generates the runtime kernel and other necessary files
    for the selected targets.
    """

    """
    Traverse each of the subdirectory in .runtime_tests
    example .runtime_tests/00001 and load the content of the config.yaml file present in that directory
    following after that add that config data into a dictionary of loaded config data: path to that config file
    """
    loaded_configs = {}  # Dictionary to store config data: path -> config content

    # Processing all the runtime_kernels configs and build path
    runtime_tests_dir = ".runtime_tests"
    for subdir in os.listdir(runtime_tests_dir):
        subdir_path = os.path.join(runtime_tests_dir, subdir)
        if os.path.isdir(subdir_path):
            config_path = os.path.join(subdir_path, "config.yaml")
            runtime_kernel_build_path = os.path.join(subdir_path, "build")
            if os.path.exists(config_path):
                with open(config_path, "r") as config_file:
                    config_data = yaml.safe_load(config_file)
                    kernel_name = generate_kernel_name(config_data)
                    loaded_configs[kernel_name] = runtime_kernel_build_path


    for target in targets:
        print(f"Processing target {target.id} and searching in {selected_targets}")
        if target.id - 1 in selected_targets:
            example_target_config = target.config['build']
            print(f"Processing target {target.id} with config: {example_target_config}")
            runtime_kernel_name = generate_kernel_name(example_target_config)
            # Check if given kernel is to be build or not
            if runtime_kernel_name in loaded_configs:
                runtime_kernel_build_path = loaded_configs[runtime_kernel_name]
                
                # Define the destination path early and ensure runtime_name directory exists
                destination_dir = os.path.join(os.getcwd(), "runtime_kernels", runtime_name)
                os.makedirs(destination_dir, exist_ok=True)
                destination_kernel_path = os.path.join(destination_dir, runtime_kernel_name)
                
                # Check if this runtime_kernel is already created
                if os.path.exists(destination_kernel_path):
                    print(f"Runtime kernel {runtime_kernel_name} already exists at {destination_kernel_path}, skipping generation")
                    continue
                
                # Call the build script
                build_script_path = runtime_kernel_build_path
                if os.path.exists(build_script_path):
                    subprocess.run(["bash", build_script_path], check=True)
                else:
                    print(f"Build script not found at {build_script_path}")
                    continue

                # Move the kernel to the desired location
                cwd = os.getcwd()
                source_kernel_path = os.path.join(cwd, runtime_kernel_build_path.split("/build")[0], ".unikraft", "build", "learning_testing_fw_qemu-x86_64")
                print(f"Source kernel path: {source_kernel_path}")
                
                if os.path.exists(source_kernel_path):
                    shutil.move(source_kernel_path, destination_kernel_path)
                    print(f"Kernel moved to {destination_kernel_path}")
                else:
                    print(f"Kernel not found at {source_kernel_path}")
            else:
                print(f"No configuration found for target {target.id} with kernel name {runtime_kernel_name}")

def generate_kernel_name(config_data: dict) -> str:
    """
    Generate a unique kernel name based on the provided config data.
    The kernel name is a string containing parameter values in the specified order:
    Arch, Bootloader, Build_tool, Compiler.type, Debug, Platform.
    """
    # TODO: Raise error if we didnt receive some keys in config_data
    # Extract required parameters from the config data
    arch = config_data.get("arch", "")
    bootloader = config_data.get("bootloader", "")
    build_tool = config_data.get("build_tool", "")
    compiler_type = config_data.get("compiler", {}).get("type", "")
    debug = config_data.get("debug", "")
    platform = config_data.get("platform", "")

    # Create the kernel name string
    kernel_name = f"{arch}_{bootloader}_{build_tool}_{compiler_type}_{debug}_{platform}"
    return kernel_name
