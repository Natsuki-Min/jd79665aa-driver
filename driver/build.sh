#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
configure_args=()

# Local defaults from the original working setup; explicit arguments below
# override them. On other machines pass the corresponding -D paths.
sdk_path="${PICO_SDK_PATH:-${HOME}/.pico-sdk/sdk/2.3.1}"
toolchain_path="${PICO_TOOLCHAIN_PATH:-${HOME}/.pico-sdk/toolchain/15_2_Rel1}"
picotool_path="${PICO_PICOTOOL_DIR:-${HOME}/.pico-sdk/picotool/2.3.1/picotool}"
if [[ -d "$sdk_path" ]]; then configure_args+=("-DPICO_SDK_PATH=$sdk_path"); fi
if [[ -d "$toolchain_path" ]]; then configure_args+=("-DPICO_TOOLCHAIN_PATH=$toolchain_path"); fi
if [[ -d "$picotool_path" ]]; then configure_args+=("-Dpicotool_DIR=$picotool_path"); fi

cmake -S "$project_dir" -B "$project_dir/build" -G Ninja \
    -DPICO_BOARD=pico -DCMAKE_BUILD_TYPE=Release "${configure_args[@]}" "$@"
cmake --build "$project_dir/build" --parallel 4
