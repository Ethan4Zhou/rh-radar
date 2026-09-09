#!/usr/bin/env python3
"""Order the tweet-reading queue so the rows people actually look at get fixed first.

Reading tweets is the slowest step (X allows roughly 40 calls before a 15 minute
cooldown), so the queue starts with the accounts whose "no token yet" label is
both most consequential and most likely to be wrong.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data"

accounts = {a["u"]: a for a in json.load(open(D / "accounts.json"))}
verify = json.load(open(D / "contract_verify.json"))


def rank(u):
    a = accounts.get(u, {})
    tok = verify.get(u, {}).get("tok", "none")
    vd = a.get("vd", "weak")
    if tok == "none" and vd == "promising":
        return 0        # the bucket the list is read for
    if tok == "none" and vd == "ok":
        return 1
    if tok == "likely":
        return 2
    if tok == "none":
        return 3
    return 4            # already known to have a contract address


order = sorted(accounts, key=lambda u: (rank(u), -accounts[u]["fo"]))
(D / "tweets").mkdir(parents=True, exist_ok=True)
json.dump(order, open(D / "tweets/priority.json", "w"))

import collections
c = collections.Counter(rank(u) for u in order)
print(f"queued {len(order)} accounts: " + ", ".join(f"P{k}={c[k]}" for k in sorted(c)))
