#!/usr/bin/env python3
"""Maintain the shared exclusion list from the command line.

    scan/exclude.py add @foo 已归零
    scan/exclude.py add foo bar baz --reason 已跑路
    scan/exclude.py rm @foo
    scan/exclude.py list
    scan/exclude.py merge exported.json      # take what the page exported

The page loads this file as the team baseline, so a change here shows up for
everyone on the next build.
"""
import json, sys, datetime, os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
F = ROOT / "data" / "excluded.json"


def load():
    if F.exists():
        d = json.load(open(F))
        d.setdefault("items", {})
        return d
    return {"items": {}}


def save(d):
    F.write_text(json.dumps(d, ensure_ascii=False, indent=1))


def who():
    return os.environ.get("RH_USER") or os.environ.get("USER") or "unknown"


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    cmd = argv[1]
    d = load()
    items = d["items"]
    today = datetime.date.today().isoformat()

    if cmd == "add":
        rest = argv[2:]
        reason = ""
        if "--reason" in rest:
            i = rest.index("--reason")
            reason = " ".join(rest[i + 1:])
            rest = rest[:i]
        elif len(rest) >= 2 and not rest[-1].startswith("@") and len(rest) == 2:
            rest, reason = rest[:1], rest[1]
        names = [x.lstrip("@") for x in rest if x]
        if not names:
            print("usage: exclude.py add @handle [reason]")
            return 1
        for n in names:
            items[n] = {"r": reason, "t": today, "by": who()}
        save(d)
        print(f"excluded {len(names)}: {', '.join('@'+n for n in names)}")

    elif cmd == "rm":
        gone = 0
        for x in argv[2:]:
            if items.pop(x.lstrip("@"), None) is not None:
                gone += 1
        save(d)
        print(f"restored {gone}")

    elif cmd == "list":
        if not items:
            print("list is empty")
        for n, v in sorted(items.items(), key=lambda kv: kv[1].get("t", "")):
            print(f"  @{n:<22} {v.get('t','')}  {v.get('by',''):<10} {v.get('r','')}")
        print(f"\n{len(items)} excluded")

    elif cmd == "merge":
        src = json.load(open(argv[2]))
        incoming = src.get("items", src)
        added = 0
        for n, v in incoming.items():
            if n not in items:
                items[n] = v if isinstance(v, dict) else {"r": str(v), "t": today, "by": who()}
                added += 1
        save(d)
        print(f"merged {added} new entries, {len(items)} total")

    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
