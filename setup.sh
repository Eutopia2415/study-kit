#!/bin/zsh
# Installs or updates the study kit. Run it from Terminal:  zsh setup.sh
# Safe to run again after an update: it replaces the kit and leaves your own files alone.
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null; then
  echo "python3 is missing. Run: xcode-select --install   (then run this again)"
  exit 1
fi
exec python3 core/setup.py "$@"
