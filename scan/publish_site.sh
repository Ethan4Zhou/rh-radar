#!/usr/bin/env bash
# Push the freshly built page to the public repo that GitHub Pages serves.
#
# The private repo keeps the scrapers, the raw data and the research notes; only
# the rendered single file goes public, because Pages will not serve a private
# repo on a free plan.
set -uo pipefail
cd "$(dirname "$0")/.."
MIRROR="${RH_SITE_MIRROR:-$HOME/Projects/.rh-radar-site}"
REMOTE="https://github.com/Ethan4Zhou/rh-radar-site.git"

[ -f site/index.html ] || { echo "site/index.html missing — run site/build_site.py first"; exit 1; }

if [ ! -d "$MIRROR/.git" ]; then
  git clone -q "$REMOTE" "$MIRROR" || { echo "clone failed"; exit 1; }
fi

cp site/index.html "$MIRROR/index.html"
cd "$MIRROR"
git add index.html
if git diff --cached --quiet; then
  echo "site unchanged, nothing to publish"
  exit 0
fi
git -c user.name="Ethan4Zhou" -c user.email="web30xez@gmail.com" \
    -c commit.gpgsign=false commit -q -m "site: $(date '+%Y-%m-%d %H:%M')"
if git push -q origin main 2>/dev/null; then
  echo "published to https://ethan4zhou.github.io/rh-radar-site/"
else
  git pull -q --rebase origin main 2>/dev/null && git push -q origin main 2>/dev/null \
    && echo "published after rebase" || echo "publish failed"
fi
