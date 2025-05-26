#!/bin/sh

config={run_dir}/config.json

{{
# Clean up any previous instances.
sudo pkill -f qemu-system
sudo pkill -f firecracker
kraft stop --all
kraft rm --all
sudo KRAFTKIT_NO_WARN_SUDO=1 kraft stop --all
sudo KRAFTKIT_NO_WARN_SUDO=1 kraft rm --all
}} > /dev/null 2>&1

# Remove previously created files.
sudo rm -f /tmp/firecracker.log
touch /tmp/firecracker.log
sudo rm -f /tmp/firecracker.socket
sudo {vmm} \
        --api-sock /tmp/firecracker.socket \
        --config-file "$config"
