#!/usr/bin/env bash
# Install the two launchd agents on this machine.
#   ./deploy/install.sh                 # no proxy
#   PROXY=127.0.0.1:7890 ./deploy/install.sh
set -euo pipefail
cd "$(dirname "$0")/.."
REPO="$(pwd)"; USER_TAG="$(id -un)"; PROXY="${PROXY:-}"
mkdir -p logs "$HOME/Library/LaunchAgents"
for t in deploy/*.template; do
  name="$(basename "$t" .template | sed "s/com\.example\./com.$USER_TAG./")"
  out="$HOME/Library/LaunchAgents/$name"
  sed -e "s#__HOME__#$HOME#g" -e "s#com\.__USER__\.#com.$USER_TAG.#g" \
      -e "s#__PROXY_HOST_PORT__#${PROXY:-127.0.0.1:0}#g" "$t" > "$out"
  # a machine with no proxy should not inherit a dead one
  [ -z "$PROXY" ] && /usr/libexec/PlistBuddy -c "Delete :EnvironmentVariables:HTTP_PROXY" "$out" 2>/dev/null || true
  [ -z "$PROXY" ] && /usr/libexec/PlistBuddy -c "Delete :EnvironmentVariables:HTTPS_PROXY" "$out" 2>/dev/null || true
  [ -z "$PROXY" ] && /usr/libexec/PlistBuddy -c "Delete :EnvironmentVariables:ALL_PROXY" "$out" 2>/dev/null || true
  sed -i '' "s#$REPO/#$REPO/#g" "$out" 2>/dev/null || true
  launchctl unload "$out" 2>/dev/null || true
  launchctl load "$out" && echo "loaded $name"
done
