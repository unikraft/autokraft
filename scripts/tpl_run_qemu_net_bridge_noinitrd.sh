#!/bin/sh

kernel="{kernel}"
cmd="{cmd}"

if test $# -eq 1; then
    kernel="$1"
fi

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

# Create bridge interface for QEMU networking.
sudo ip link add dev virbr0 type bridge
sudo ip address add 172.44.0.1/24 dev virbr0
sudo ip link set dev virbr0 up

sudo {vmm} \
    {hypervisor_option} \
    {machine} \
    -kernel "$kernel" \
    -nographic \
    -m {memory}M \
    -netdev bridge,id=en0,br=virbr0 -device virtio-net-pci,netdev=en0 \
    -append "{name} netdev.ip=172.44.0.2/24:172.44.0.1::: -- $cmd" \
    -cpu max
