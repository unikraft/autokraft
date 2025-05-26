#!/bin/sh

rm -fr {target_dir}/.unikraft/build
rm -f {target_dir}/.config.*
kraft build --log-level debug --log-type basic --no-cache --no-update --plat {plat} --arch {arch} {target_dir}
