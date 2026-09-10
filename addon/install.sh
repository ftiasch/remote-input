#!/usr/bin/env bash
# Install the addon into the user's home directory -- no root needed.
#
# Details: fcitx5 looks for addon libraries only in FCITX_ADDON_DIRS plus the built-in
# /usr/lib/fcitx5, and once FCITX_ADDON_DIRS is set the built-in directory is NOT
# appended any more -- so it has to be listed explicitly. Addon .conf files, on the
# other hand, are found through the regular XDG user dir ~/.local/share/fcitx5/addon.
#
# fcitx5 has to be restarted before it loads the addon:
#   busctl --user call org.fcitx.Fcitx5 /controller org.fcitx.Fcitx.Controller1 Exit
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
lib_dir="$HOME/.local/lib/fcitx5"
addon_dirs="$lib_dir:$(pkg-config --variable=libdir Fcitx5Core)/fcitx5"

bash "$here/build.sh"

install -Dm755 "$here/remoteinput.so" "$lib_dir/remoteinput.so"
install -Dm644 "$here/remoteinput.conf" "$HOME/.local/share/fcitx5/addon/remoteinput.conf"

mkdir -p "$HOME/.config/environment.d"
printf 'FCITX_ADDON_DIRS=%s\n' "$addon_dirs" \
    >"$HOME/.config/environment.d/50-remote-input.conf"
systemctl --user set-environment FCITX_ADDON_DIRS="$addon_dirs"

echo "installed to $lib_dir, FCITX_ADDON_DIRS=$addon_dirs"
