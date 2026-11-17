#!/bin/zsh
# Smoke test: installs the kit into a throwaway folder, starts Study Hall on a spare port,
# and runs one question through the Study Room. Your real ~/Study, ~/.claude and ~/.codex are never touched.
#   zsh test.sh          run it
#   zsh test.sh --keep   leave the throwaway install behind to look at
cd "$(dirname "$0")"
exec python3 core/smoke_test.py "$@"
