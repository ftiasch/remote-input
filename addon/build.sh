#!/usr/bin/env bash
# Build the addon. Output: addon/remoteinput.so
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
read -ra fcitx5 <<<"$(pkg-config --cflags --libs Fcitx5Core)"
# The dbus module headers live next to the core ones, under the same prefix.
dbus_include="$(pkg-config --variable=prefix Fcitx5Core)/include/Fcitx5/Module/fcitx-module/dbus"

g++ -std=c++20 -O2 -Wall -Wextra -fPIC -shared \
    -I"$dbus_include" \
    "${fcitx5[@]}" \
    -o "$here/remoteinput.so" "$here/remoteinput.cpp"

echo "built $here/remoteinput.so"
