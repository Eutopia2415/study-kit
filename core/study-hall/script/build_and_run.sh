#!/bin/zsh
set -euo pipefail
cd "${0:A:h:h}"
mode="${1:-run}"
case "$mode" in run|--verify) ;; *) print -u2 'Usage: build_and_run.sh [--verify]'; exit 2 ;; esac
# Request a normal termination before replacing the installed app.
swift -e 'import AppKit; for app in NSRunningApplication.runningApplications(withBundleIdentifier:"local.studykit.studyhud") { _ = app.terminate() }'
./hud/build.sh
open "$HOME/Applications/Study HUD.app"
if [[ "$mode" == --verify ]]; then
  sleep 1
  pgrep -x 'Study HUD' >/dev/null
fi
