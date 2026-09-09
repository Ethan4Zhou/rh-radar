#!/usr/bin/env python3
"""Poll the followers of the seed accounts via bird, newest first.

X returns followers in reverse-chronological follow order, so an incremental
scan only needs the first few pages. Anything already in state/seen.json is
skipped, and the run stops early once a page yields nothing new.
"""
import json, os, re, subprocess, sys, time
from pathlib import Path
import shutil

def _node_bin():
    """Find the node/bird install without hardcoding one machine's paths."""
    for c in (os.environ.get("BIRD_BIN"), shutil.which("bird")):
        if c and Path(c).exists():
            return str(Path(c).resolve())
    for p in sorted(Path.home().glob(".nvm/versions/node/*/bin/bird"), reverse=True):
        return str(p)
    return "bird"


ROOT = Path(__file__).resolve().parent.parent
BIRD = _node_bin()
NODE_BIN = str(Path(BIRD).parent)

SEEDS = {
    "RobinhoodCrypto": "352518189",
    "RobinhoodApp":    "1265037073",
    "vladtenev":       "605700792",
}

STATE = ROOT / "data" / "seen.json"
OUT   = ROOT / "data" / "candidates.jsonl"
URL_RE = re.compile(r"https?://[^\s]+|[a-z0-9-]+\.(?:com|io|xyz|fun|app|net|org|co|gg|live|finance|market|trade|cash|club|art|money|network|so|ai|dev|tech|bond|pro|shop|world|space|land|wtf|lol|best|store)\b", re.I)


def bird_env():
    env = dict(os.environ)
    env["NODE_USE_ENV_PROXY"] = "1"          # Node's fetch ignores *_PROXY without this
    env["PATH"] = NODE_BIN + ":" + env.get("PATH", "")
    return env


def fetch_pages(user_id, pages=3, count=200, timeout=300):
    """bird handles the cursor itself with --all; its JSON output has no cursor field."""
    cmd = [BIRD, "followers", "--user", user_id, "-n", str(count), "--json",
           "--all", "--max-pages", str(pages),
           "--timeout", "45000", "--no-color", "--no-emoji"]
    p = subprocess.run(cmd, capture_output=True, env=bird_env(), timeout=timeout)
    out = p.stdout.decode("utf-8", "ignore")
    err = p.stderr.decode("utf-8", "ignore")
    if "429" in err or "Rate limit" in err:
        return None, "rate_limit"
    i = out.find("[")
    if i < 0:
        return None, err.strip()[-200:]
    # --all emits one JSON array per page, concatenated; read them all
    dec = json.JSONDecoder()
    users, idx = [], i
    text = out
    while idx < len(text):
        while idx < len(text) and text[idx] not in "[":
            idx += 1
        if idx >= len(text):
            break
        try:
            arr, end = dec.raw_decode(text, idx)
        except Exception:
            break
        if isinstance(arr, list):
            users.extend(arr)
        idx = end
    return (users, None) if users else (None, "no users parsed")


def has_link(u):
    """A project account puts a link in the bio or the website field."""
    return bool(URL_RE.search(u.get("description") or ""))


def account_age_days(created_at, now=None):
    # "Tue Sep 08 18:57:52 +0000 2026"
    try:
        t = time.strptime(created_at, "%a %b %d %H:%M:%S %z %Y")
    except Exception:
        try:
            t = time.strptime(created_at.replace(" +0000", ""), "%a %b %d %H:%M:%S %Y")
        except Exception:
            return None
    return (time.time() - time.mktime(t)) / 86400


def load_seen():
    if STATE.exists():
        try:
            return json.load(open(STATE))
        except Exception:
            pass
    return {"users": {}, "cursors": {}}


def main():
    max_pages = int(os.environ.get("MAX_PAGES", "3"))
    max_age   = float(os.environ.get("MAX_AGE_DAYS", "92"))
    seen = load_seen()
    users = seen.setdefault("users", {})
    fresh = []
    for handle, uid in SEEDS.items():
            arr, err = None, None
            for attempt in range(3):
                arr, err = fetch_pages(uid, max_pages)
                if arr is not None:
                    break
                if err == "rate_limit":
                    wait = 90 * (attempt + 1)
                    print(f"[{handle}] rate limited, waiting {wait}s", flush=True)
                    time.sleep(wait)
                else:
                    break
            if arr is None:
                print(f"[{handle}] failed: {err}", flush=True)
                continue
            new_here = 0
            recent = 0
            for u in arr:
                un = u.get("username")
                if not un:
                    continue
                key = un.lower()
                if key in users:
                    continue
                new_here += 1
                age = account_age_days(u.get("createdAt") or "")
                rec = {
                    "username": un,
                    "name": u.get("name"),
                    "bio": u.get("description") or "",
                    "createdAt": u.get("createdAt"),
                    "ageDays": None if age is None else round(age, 1),
                    "followers": u.get("followersCount"),
                    "seedFrom": handle,
                    "foundAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                }
                users[key] = {"t": rec["foundAt"], "s": handle}
                # the two gates that survive on REST data
                if age is not None and age <= max_age:
                    recent += 1
                    rec["hasLink"] = has_link(u)
                    fresh.append(rec)
            print(f"[{handle}] {len(arr)} users, {new_here} new, {recent} created within {max_age:.0f}d", flush=True)
            time.sleep(1.5)
    STATE.parent.mkdir(parents=True, exist_ok=True)
    json.dump(seen, open(STATE, "w"))
    if fresh:
        with open(OUT, "a") as f:
            for r in fresh:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    withlink = sum(1 for r in fresh if r.get("hasLink"))
    print(f"\ntracked users: {len(users)} | new recent accounts: {len(fresh)} | of which bio has a link: {withlink}")
    for r in fresh[:25]:
        mark = "*" if r.get("hasLink") else " "
        print(f" {mark} @{r['username']:<20} {r['ageDays']}d  {r['bio'][:58]}")


if __name__ == "__main__":
    main()
