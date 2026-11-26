#!/usr/bin/env bash
# Coder autostart hook (docker-basic template): serve the Pages layout on the workspace's dev port, built from
# symlinks so edits under powerbank-station/site/ show up on reload. The template already provides the virtual
# display (DISPLAY=:99) for the Python render scripts.
set -eu
REPO="$(cd "$(dirname "$0")/.." && pwd)"
P=/tmp/pages
rm -rf "$P" && mkdir -p "$P/powerbank-station"
ln -s "$REPO/pages/"* "$P/"
ln -s "$REPO/powerbank-station/site/"* "$P/powerbank-station/"
ln -s "$REPO/powerbank-station/tools/petg_hf06.ini" "$P/powerbank-station/printer.ini"
exec python3 -m http.server "${WORKSPACE_DEV_PORT:-8000}" --directory "$P"
