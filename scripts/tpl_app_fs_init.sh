#!/bin/sh

init_rootfs="{rootfs}"
testing_rootfs="{init_dir}/.rootfs-for-testing"

# If no root filesystem, exit.
if test -z "$init_rootfs"; then
    exit 0
fi

# Use $testing_rootfs as the rootfs for testing.
rm -fr "$testing_rootfs"
mkdir "$testing_rootfs"

# If rootfs is Dockerfile, create directory from Dockerfile.
if test "$(basename "$init_rootfs")" = "Dockerfile"; then
    image_name="uk-{name}"
    d=$(pwd)
    cd {test_app_dir}
    docker build -o "$testing_rootfs" -f "$init_rootfs" -t "$image_name" .
    cd "$d"
else
    cp -r "$init_rootfs"/* "$testing_rootfs"
fi

# Create CPIO archive to be used as the embedded initrd.
{base}/unikraft/support/scripts/mkcpio {app_dir}/initrd.cpio "$testing_rootfs"
