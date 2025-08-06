#!/bin/sh

test -d {target_dir}/.unikraft/build || mkdir -p {target_dir}/.unikraft/build
make -f {target_dir}/Makefile distclean
UK_DEFCONFIG={target_dir}/defconfig make -f {target_dir}/Makefile defconfig
touch Makefile.uk
make -f {target_dir}/Makefile prepare
make CC={compiler} LD={compiler} -f {target_dir}/Makefile -j $(nproc)
