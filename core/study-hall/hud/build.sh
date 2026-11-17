#!/bin/zsh
# Builds "Study HUD.app" into ~/Applications. Run again after editing StudyHUD.swift.
# Not next to server.py: the Desktop syncs to iCloud, which evicts the binary and keeps every
# replaced build in Recently Deleted, where Spotlight lists each one as another Study HUD.
# It's built and signed in a temp folder because Desktop adds Finder metadata that codesign rejects.
set -e
cd "$(dirname "$0")"
TMP=$(mktemp -d -t hud.noindex)   # .noindex keeps Spotlight from listing the temp copy as another app
APP="$TMP/Study HUD.app"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp Info.plist "$APP/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Add :StudyHallDir string $(cd .. && pwd)" "$APP/Contents/Info.plist"
swift MakeIcon.swift "$TMP/AppIcon.iconset"
iconutil -c icns "$TMP/AppIcon.iconset" -o "$APP/Contents/Resources/AppIcon.icns"
swiftc -O StudyHUD.swift -o "$APP/Contents/MacOS/Study HUD" -framework Cocoa -framework WebKit
xattr -cr "$APP"
if [[ "${STUDY_HUD_TEST:-0}" == 1 ]]; then
  /usr/libexec/PlistBuddy -c 'Set :CFBundleIdentifier local.studykit.studyhud.geometrytest' "$APP/Contents/Info.plist"
fi
codesign --force --sign - "$APP"
DEST="${STUDY_HUD_DEST:-$HOME/Applications/Study HUD.app}"
mkdir -p "$HOME/Applications"
# Preserve an installed bundle until the new one has built and signed successfully.
codesign --verify --strict "$APP"
if [[ -d "$DEST" ]]; then
  mv "$DEST" "$TMP/previous.app"
fi
ditto "$APP" "$DEST"
rm -rf "$TMP"
echo "Built $DEST"
