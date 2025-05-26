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

{{
# Remove previously created network interfaces.
sudo ip link set dev tap0 down
sudo ip link del dev tap0
sudo ip link set dev virbr0 down
sudo ip link del dev virbr0
}} > /dev/null 2>&1

# Create bridge and tap interface for Firecracker networking.
sudo ip link add dev virbr0 type bridge
sudo ip link set dev virbr0 up
sudo ip tuntap add dev virbr0@if0 mode tap
sudo ip link set dev virbr0@if0 up

# Add tap interface to bridge.
sudo ip link set dev virbr0@if0 master virbr0

# Add IP address to bridge interface
sudo ip address add 172.44.0.1/24 dev virbr0

# Remove previously created files.
sudo rm -f /tmp/firecracker.log
touch /tmp/firecracker.log
sudo rm -f /tmp/firecracker.socket
sudo {vmm} \
        --api-sock /tmp/firecracker.socket \
        --config-file "$config"
