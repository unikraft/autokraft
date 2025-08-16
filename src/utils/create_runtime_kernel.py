import os
import yaml
import shutil
import subprocess
from .process_utils import terminate_buildkitd

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
            build_tool = target.config['build']['build_tool']
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
                    
                    # Terminate buildkitd process after build script execution
                    if build_tool == "kraft":
                        terminate_buildkitd()
                else:
                    print(f"Build script not found at {build_script_path}")
                    continue

                

                # Separate both the make and kraft logic differently
                if build_tool == "make":
                    # Move the kernel to the desired location
                    cwd = os.getcwd()
                    build_dir = os.path.join(cwd, runtime_kernel_build_path.split("/build")[0], ".unikraft", "build")
                    kernel_filename = find_qemu_x86_64_kernel_file(build_dir)
                    source_kernel_path = os.path.join(build_dir, kernel_filename)
                    print(f"Source kernel path: {source_kernel_path}")
                    
                    if os.path.exists(source_kernel_path):
                        shutil.move(source_kernel_path, destination_kernel_path)
                        print(f"Kernel moved to {destination_kernel_path}")
                    else:
                        print(f"Kernel not found at {source_kernel_path}")
                elif build_tool == "kraft":
                    # Kraft specific logic
                    try:
                        # Package the image
                        package_cmd = [
                            "kraft", "pkg", "--as", "oci", 
                            "--name", f"localhost:5000/{runtime_name}:local", runtime_kernel_build_path.split("/build")[0]
                        ]
                        subprocess.run(package_cmd, check=True)
                        print(f"Successfully packaged kernel {runtime_kernel_name}")
                        
                        # Push it to the repo
                        push_cmd = [
                            "kraft", "pkg", "push", 
                            f"localhost:5000/{runtime_name}:local", runtime_kernel_build_path.split("/build")[0]
                        ]
                        subprocess.run(push_cmd, check=True)
                        print(f"Successfully pushed kernel {runtime_kernel_name} to repository")
                        
                        # Pull the image to temporary directory
                        tmp_kernel_dir = ".tmp-kernel"
                        pull_cmd = [
                            "kraft", "pkg", "pull", "-w", tmp_kernel_dir,
                            f"localhost:5000/{runtime_name}:local"
                        ]
                        subprocess.run(pull_cmd, check=True)
                        print(f"Successfully pulled kernel {runtime_kernel_name}")
                        
                        # Move kernel file to destination
                        cwd = os.getcwd()
                        source_kernel = os.path.join(cwd, tmp_kernel_dir, "unikraft", "bin", "kernel")
                        
                        if os.path.exists(source_kernel):
                            shutil.move(source_kernel, destination_kernel_path)
                            print(f"Kernel moved to {destination_kernel_path}")
                        else:
                            print(f"Kernel not found at {source_kernel}")
                        
                        # Clean up temporary directory
                        if os.path.exists(tmp_kernel_dir):
                            shutil.rmtree(tmp_kernel_dir)
                            print(f"Cleaned up temporary directory {tmp_kernel_dir}")
                        
                    except subprocess.CalledProcessError as e:
                        print(f"Error during kraft packaging/push/pull for {runtime_kernel_name}: {e}")
                        # Clean up temporary directory in case of error
                        if os.path.exists(".tmp-kernel"):
                            shutil.rmtree(".tmp-kernel")
                        continue
                
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

def find_qemu_x86_64_kernel_file(build_dir: str) -> str:
    """
    List all files in build_dir and return the file that contains 'qemu-x86_64' in its name,
    does not have an extension, and is a file.
    """
    for fname in os.listdir(build_dir):
        fpath = os.path.join(build_dir, fname)
        if (
            os.path.isfile(fpath)
            and "qemu-x86_64" in fname
            and "." not in fname
        ):
            return fname
    raise FileNotFoundError(f"No qemu-x86_64 kernel file found in {build_dir}")
