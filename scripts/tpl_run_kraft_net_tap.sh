#!/bin/sh

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

# Create bridge interface for KraftKit networking.
sudo KRAFTKIT_NO_WARN_SUDO=1 kraft net create -n 172.44.0.1/24 virbr0

sudo \
    KRAFTKIT_BUILDKIT_HOST=docker-container://buildkitd \
    KRAFTKIT_NO_WARN_SUDO=1 \
    kraft run \
      --log-level debug --log-type basic \
      --rm \
      {hypervisor_option} \
      --memory {memory}Mi \
      --network virbr0:172.44.0.2/24:172.44.0.1:::: \
      --arch {arch} --plat {plat} \
      {target_dir}
