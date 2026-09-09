#!/usr/bin/env python3
"""Discovery through X's Verified Followers list — the same list the original
55,633-account pipeline came from.

This replaces the REST follower walk for discovery. The REST endpoint no longer
carries the blue or gold flag and drops the website field, so accounts found that
way arrived with verification unknown. This one returns both, which makes the two
gates the product actually asks for enforceable:

  1. verified (blue or gold)
  2. a link in the bio or the website field
  3. created within the last three months

Newest followers come first, so an incremental run reads a few pages and stops.
"""
import json, os, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data"
SEEDS = ["RobinhoodCrypto", "RobinhoodApp", "vladtenev"]
STATE = D / "vf_seen.json"
OUT = D / "candidates.jsonl"
MAX_AGE = float(os.environ.get("MAX_AGE_DAYS", "92"))


def age_days(created):
    try:
        t = time.strptime(created, "%a %b %d %H:%M:%S %z %Y")
    except Exception:
        return None
    return (time.time() - time.mktime(t)) / 86400


def has_link(r):
    return bool(r.get("website") or r.get("bioUrls") or "http" in (r.get("bio") or ""))


def main():
    pages = os.environ.get("MAX_PAGES", "3")
    seen = set(json.load(open(STATE))) if STATE.exists() else set()
    fresh = []
    for h in SEEDS:
        f = D / f"verified_followers_{h}.jsonl"
        before = f.stat().st_size if f.exists() else 0
        env = dict(os.environ, MAX_PAGES=pages)
        subprocess.run([sys.executable, str(ROOT / "scan" / "verified_followers.py"), h],
                       env=env, cwd=str(ROOT))
        if not f.exists():
            continue
        for line in open(f):
            try:
                r = json.loads(line)
            except Exception:
                continue
            u = r.get("username")
            if not u or u in seen:
                continue
            seen.add(u)
            age = age_days(r.get("createdAt") or "")
            if age is None or age > MAX_AGE:
                continue          # gate 3: created recently
            if not has_link(r):
                continue          # gate 2: has a link
            fresh.append({
                "username": u, "name": r.get("name"), "bio": r.get("bio") or "",
                "createdAt": r.get("createdAt"), "ageDays": round(age, 1),
                "followers": r.get("followers") or 0, "seedFrom": h,
                "verified": "gold" if r.get("gold") else "blue",
                "website": r.get("website") or (r.get("bioUrls") or [None])[0],
                "hasLink": True,
                "foundAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            })
    json.dump(sorted(seen), open(STATE, "w"))
    if fresh:
        with open(OUT, "a") as f:
            for r in fresh:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\nverified followers tracked: {len(seen)} | new candidates passing all gates: {len(fresh)}")
    for r in fresh[:25]:
        print(f"  @{r['username']:<20} {r['verified']:<5} {r['ageDays']:>5}d  {(r['website'] or '')[:30]:<30} {r['bio'][:34]}")


if __name__ == "__main__":
    main()
