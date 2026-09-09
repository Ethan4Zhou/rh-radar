#!/usr/bin/env python3
"""Write the corrected token status back to disk.

build.py recomputes it every run from bio + site + tweets, but only for the page —
contract_verify.json kept saying "none" for accounts whose tweets had already shown
a contract. Anything reading that file (deep_scan, priority) was working from the
stale answer.
"""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data"
CA_RE = re.compile(r"0x[a-fA-F0-9]{40}")
DEX = re.compile(r"(dexscreener|dextools|geckoterminal|pump\.fun|birdeye|app\.uniswap|jup\.ag)", re.I)


def is_addr(a):
    try:
        b = bytes.fromhex(a[2:])
    except ValueError:
        return False
    return sum(1 for x in b if 32 <= x < 127) < 16


def main():
    ver = json.load(open(D / "contract_verify.json"))
    onchain = json.load(open(D / "onchain.json")) if (D / "onchain.json").exists() else {}
    moved = []
    for line in open(D / "tweets" / "tweets.jsonl"):
        try:
            r = json.loads(line)
        except Exception:
            continue
        if not r.get("ok"):
            continue
        u = r["u"]
        v = ver.setdefault(u, {"cv": "no_ca", "tok": "none", "own": [], "syms": [],
                               "n_ca": 0, "ca": "", "chains": [], "src": ""})
        cas, dex = [], False
        for t in r.get("tw", []):
            blob = (t.get("t") or "") + " " + (t.get("q") or "")
            for a in CA_RE.findall(blob):
                a = a.lower()
                if is_addr(a) and a not in cas:
                    cas.append(a)
            if DEX.search(blob):
                dex = True
        v["tweet_checked"] = True
        if cas:
            if v.get("tok") == "none":
                moved.append((u, cas[0]))
            v["tok"] = "issued"
            if not v.get("ca"):
                v["ca"] = cas[0]
            src = set(filter(None, (v.get("src") or "").split(",")))
            src.add("tweet")
            v["src"] = ",".join(sorted(src))
            if v.get("cv") == "no_ca":
                v["cv"] = "live_token" if any(onchain.get(a, {}).get("has_code") for a in cas) else "wallet"
        elif dex and v.get("tok") == "none":
            v["tok"] = "likely"
    json.dump(ver, open(D / "contract_verify.json", "w"), ensure_ascii=False)
    import collections
    print("token status now:", dict(collections.Counter(v.get("tok", "none") for v in ver.values())))
    print(f"corrected none -> issued: {len(moved)}")


if __name__ == "__main__":
    main()
