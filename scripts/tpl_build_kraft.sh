#!/bin/sh

sudo rm -fr {target_dir}/.unikraft/build
sudo rm -f {target_dir}/.config.*
kraft build --log-level debug --log-type basic --no-cache --no-update --plat {plat} --arch {arch} {target_dir}
