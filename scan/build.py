#!/usr/bin/env python3
"""Recompute每个账号的发币状态与合约核验，输出网站用的 data.json。

发币证据按可信度排序：链上活着的合约 > 简介/官网/推文里的地址 > 交易站链接。
推文是第三个来源，之前漏掉它导致大量项目被误标成“未发币”。
"""
import json, re, datetime, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data"

CA_RE = re.compile(r"0x[a-fA-F0-9]{40}")
DEX_RE = re.compile(r"(dexscreener|dextools|geckoterminal|pump\.fun|birdeye|app\.uniswap|jup\.ag|four\.meme|bags\.fm)", re.I)
STOCK = set("""NVDA SPY AAPL MSFT TSLA GME AMC COIN HOOD QQQ SPCX INTC LLY RBLX AMZN META GOOG GOOGL NFLX AMD PLTR
SOFI RDDT IBIT USDG USDC USDT ETH BTC WBTC DJT MSTR BABA NIO IWM DIA VOO VTI ARKK TQQQ SOXL GLD SLV TLT
DIS BA JPM V MA PYPL SHOP UBER LYFT ABNB SNAP PINS ROKU ZM CRWD NET DDOG SNOW MDB OKTA TWLO WMT KO PEP
XOM CVX PFE JNJ UNH HD MCD NKE SBUX CRM ORCL CSCO QCOM AVGO MU TSM ASML ARM SMCI DELL HPQ IBM TXN ADBE
PANW ANET LRCX KLAC AMAT NOW RIVN LCID F GM T VZ BAC WFC GS MS C SCHW BLK SPGI CME ICE NDAQ USD EUR
WETH USD1 EURC DAI FRAX GUSD PYUSD BUIDL SPX NDX VIX WBUL BULL""".split())


def is_addr(a):
    """Filter out hex that is really ASCII payload (inscription JSON, etc.)."""
    try:
        b = bytes.fromhex(a[2:])
    except ValueError:
        return False
    return sum(1 for x in b if 32 <= x < 127) < 16


def load(name, default=None):
    p = D / name
    if not p.exists():
        return default if default is not None else {}
    return json.load(open(p))


def load_jsonl(name):
    p = D / name
    out = {}
    if p.exists():
        for line in open(p):
            try:
                r = json.loads(line)
                out[r["u"]] = r
            except Exception:
                pass
    return out


def tweet_signals():
    """Contract addresses and trading links found in an account's recent tweets."""
    tw = load_jsonl("tweets/tweets.jsonl")
    out = {}
    for u, r in tw.items():
        if not r.get("ok"):
            out[u] = {"fetched": False, "ca": [], "dex": False}
            continue
        cas, dex = [], False
        for t in r.get("tw", []):
            txt = (t.get("t") or "") + " " + (t.get("q") or "")
            for a in CA_RE.findall(txt):
                a = a.lower()
                if is_addr(a) and a not in cas:
                    cas.append(a)
            if DEX_RE.search(txt):
                dex = True
        out[u] = {"fetched": True, "ca": cas, "dex": dex, "n": r.get("n", 0)}
    return out


def main():
    accounts = load("accounts.json", [])
    verify = load("contract_verify.json", {})
    onchain = load("onchain.json", {})
    tsig = tweet_signals()

    cats = sorted({a["cat"] for a in accounts})
    ssk = {"ok": 0, "shell": 1, "blocked": 2, "unreachable": 3, "err5xx": 4}
    vk = {"promising": 0, "ok": 1, "weak": 2, "scam_signals": 3}
    mk = {"yes": 0, "partial": 1, "no": 2, "unverifiable": 3}
    CV = ["no_ca", "match", "live_token", "live_other", "mismatch", "other_chain", "wallet", "ghost"]
    TOK = ["none", "issued", "claimed", "likely"]
    SNAP = datetime.date(2026, 9, 8)

    rows, moved = [], []
    for a in accounts:
        u = a["u"]
        v = dict(verify.get(u, {}))
        t = tsig.get(u, {"fetched": False, "ca": [], "dex": False})

        old_tok = v.get("tok", "none")
        tok, cv = old_tok, v.get("cv", "no_ca")
        src = list(v.get("src", []))
        if v.get("in_bio"):
            src = ["bio"] if "bio" not in src else src
        if v.get("in_site") and "site" not in src:
            src.append("site")

        # --- the fix: tweets are a third place a contract address shows up ---
        if t["ca"]:
            if "tweet" not in src:
                src.append("tweet")
            if old_tok == "none":
                tok = "issued"
                moved.append((u, t["ca"][0]))
                live = any(onchain.get(x, {}).get("has_code") for x in t["ca"])
                if cv == "no_ca":
                    cv = "live_token" if live else "wallet"
        elif t["dex"] and old_tok == "none":
            tok = "likely"
            if "tweet" not in src:
                src.append("tweet")

        ca = v.get("ca") or (t["ca"][0] if t["ca"] else "")
        day = datetime.date(int(a["d"][:4]), int(a["d"][5:7]), int(a["d"][8:10]))
        rows.append([
            u, a["n"], 1 if a["v"] == "gold" else 0, a["d"], a["fo"], a["site"],
            ssk[a["ss"]], vk[a["vd"]], mk[a["match"]], cats.index(a["cat"]),
            a["s"], a["note"], TOK.index(tok), CV.index(cv), ca,
            "/".join(v.get("syms", [])[:2]), "/".join(v.get("own", [])[:2]),
            ",".join(v.get("chains", [])), 1 if v.get("renounced") else 0,
            (SNAP - day).days, ",".join(src), 1 if t["fetched"] else 0,
        ])

    wk = collections.defaultdict(lambda: [0, 0, 0, 0])
    for a, r in zip(accounts, rows):
        day = datetime.date(int(a["d"][:4]), int(a["d"][5:7]), int(a["d"][8:10]))
        monday = day - datetime.timedelta(days=day.weekday())
        wk[monday.isoformat()][vk[a["vd"]]] += 1
    hist = [[k] + v for k, v in sorted(wk.items())]

    payload = {"cats": cats, "rows": rows, "hist": hist,
               "builtAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}
    out = ROOT / "docs" / "data.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))

    checked = sum(1 for v in tsig.values() if v.get("fetched"))
    print(f"accounts: {len(rows)}  tweets checked: {checked}  data.json: {out.stat().st_size//1024} KB")
    print(f"reclassified 未发币 -> 已发币 (evidence from tweets): {len(moved)}")
    for u, c in moved[:25]:
        print(f"  @{u:<20} {c}")


if __name__ == "__main__":
    main()
