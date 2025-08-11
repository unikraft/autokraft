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
}} > /dev/null 2>&1

{vmm} \
    {hypervisor_option} \
    {machine} \
    -kernel "$kernel" \
    -nographic \
    -m {memory}M \
    -device virtio-net-pci,mac=02:b0:b0:1d:be:01,netdev=hostnet0 \
    -netdev user,id=hostnet0,hostfwd=tcp::{port_ext}-:{port_int} \
    -append "{name} vfs.fstab=[ \"initrd0:/:extract::ramfs={ramfs}:\" ] -- $cmd" \
    -initrd {app_dir}/initrd.cpio \
    -cpu max
