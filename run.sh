#!/usr/bin/env bash
# One scan cycle: find new followers, verify them, rebuild the page.
set -euo pipefail
cd "$(dirname "$0")"
export NODE_USE_ENV_PROXY=1          # Node's fetch ignores the system proxy otherwise
python3 scan/vf_scan.py            # verified followers of the three seeds, newest first
MAX_NEW=${MAX_NEW:-25} python3 scan/ingest.py   # crawl + chain-check them, keep the projects
python3 scan/priority.py           # requeue tweet reading with the new arrivals
python3 scan/build.py              # recompute token status from bio + site + tweets
python3 site/build_site.py         # one self-contained page
if [[ -n "$(git status --porcelain data site)" ]]; then
  git add -A data site
  git commit -q -m "scan: $(date '+%Y-%m-%d %H:%M')"
  # Once other people push to this repo, a plain push starts failing and the scan
  # silently stops publishing. Rebase onto whatever they pushed first. The data
  # files are regenerated every cycle, so on conflict theirs can win and the next
  # run rewrites them anyway — except data/excluded.json, which is human-authored.
  if ! git push -q origin main 2>/dev/null; then
    git fetch -q origin main || true
    if git rebase -q origin/main 2>/dev/null; then
      git push -q origin main 2>/dev/null || echo "push failed after rebase"
    else
      git checkout --theirs data/excluded.json 2>/dev/null || true
      git checkout --ours  data/accounts.json data/contract_verify.json site/data.json site/index.html 2>/dev/null || true
      git add -A data site 2>/dev/null || true
      if git -c core.editor=true rebase --continue 2>/dev/null; then
        git push -q origin main 2>/dev/null || echo "push failed after conflict resolve"
      else
        git rebase --abort 2>/dev/null || true
        echo "push skipped: rebase needs a human, run 'git pull --rebase' here"
      fi
    fi
  fi
fi
