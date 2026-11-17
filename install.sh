#!/bin/zsh
# One-line install or update of the study kit, no git needed:
#   zsh -c "$(curl -fsSL https://raw.githubusercontent.com/Eutopia2415/study-kit/main/install.sh)"
# Options go after a _ :
#   zsh -c "$(curl -fsSL https://raw.githubusercontent.com/Eutopia2415/study-kit/main/install.sh)" _ --agent codex --subjects calc,lit
# Running it again later updates the kit and keeps your own files.
set -e
REPO="https://github.com/Eutopia2415/study-kit"
if ! command -v python3 >/dev/null; then
  echo "python3 is missing. Run: xcode-select --install   (then run this again)"
  exit 1
fi
TMP=$(mktemp -d /tmp/study-kit.XXXXXX)
trap 'rm -rf "$TMP"' EXIT
echo "Downloading the study kit…"
curl -fsSL "$REPO/archive/refs/heads/main.tar.gz" | tar -xz -C "$TMP"
zsh "$TMP/study-kit-main/setup.sh" "$@"
