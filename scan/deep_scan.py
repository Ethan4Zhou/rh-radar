#!/usr/bin/env python3
"""Rank the not-yet-launched projects by how much of a real product is actually there.

The label "promising" only says a site loaded and looked like a product. This asks
the questions that separated Cluby from the rest: does the site reference contracts
that are really deployed, does it name the protocol it is built on, does it publish
docs and a risk page, and does it say plainly what it does not hold.

    python3 scan/deep_scan.py               # every not-yet-launched candidate
    LIMIT=40 python3 scan/deep_scan.py
"""
import json, os, re, subprocess, sys, time, html, urllib.request
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124 Safari/537.36")
RPC = ["https://rpc.mainnet.chain.robinhood.com", "https://robinhood-rpc.publicnode.com",
       "https://rpc.ordofi.network"]
CA_RE = re.compile(r"0x[a-fA-F0-9]{40}")

# what a protocol is built on — naming one is a claim that can be checked
STACK = re.compile(r"(morpho|uniswap\s*v4|uniswap|chainlink|pyth|aave|compound|erc-?4626|"
                   r"orderly|steer|permit2|safe\{|gnosis safe|the graph|layerzero|axelar)", re.I)
# language a project uses when it has thought about being wrong
CANDOUR = re.compile(r"(not investment advice|can be liquidated|holds no user funds|"
                     r"we do not hold|never leaves|unaudited|not audited|no performance fee|"
                     r"risk framework|what can go wrong|caps? (are|of)|start small|"
                     r"immutable once|withdraw whatever|自负风险|非投资建议)", re.I)
HYPE = re.compile(r"(guaranteed|risk[- ]free|100% safe|only win|moon|1000x|next 100x|"
                  r"passive income forever|no risk)", re.I)
DOCS = re.compile(r"(docs?\.|/docs|gitbook|whitepaper|litepaper|/learn|risk framework)", re.I)


def is_addr(a):
    try:
        b = bytes.fromhex(a[2:])
    except ValueError:
        return False
    return sum(1 for x in b if 32 <= x < 127) < 16


def fetch(url):
    try:
        p = subprocess.run(["curl", "-sSL", "-m", "25", "--max-filesize", "900000",
                            "-A", UA, "-w", "\n@@%{http_code}", url],
                           capture_output=True, timeout=40)
        out = p.stdout.decode("utf-8", "ignore")
        body, _, code = out.rpartition("\n@@")
        return body, (code or "000").strip()
    except Exception:
        return "", "000"


def same_origin_scripts(body, base):
    """Client-rendered apps keep their addresses in the bundle, not the HTML. Cluby
    happened to be server-rendered; most are not, and judging them on the empty
    shell would rank a real dapp below a static NFT page."""
    from urllib.parse import urljoin, urlparse
    host = urlparse(base).netloc
    out = []
    for m in re.finditer(r'<script[^>]+src=["\']([^"\']+\.js[^"\']*)["\']', body, re.I):
        u = urljoin(base, m.group(1))
        if urlparse(u).netloc == host:
            out.append(u)
    return out[:5]


def visible(body):
    b = re.sub(r"<(script|style|noscript|svg)[^>]*>.*?</\1>", "", body, flags=re.I | re.S)
    b = re.sub(r"<[^>]+>", " ", b)
    return re.sub(r"\s+", " ", html.unescape(b)).strip()


def rpc(batch):
    for u in RPC:
        try:
            r = urllib.request.Request(u, data=json.dumps(batch).encode(),
                                       headers={"Content-Type": "application/json", "User-Agent": UA})
            with urllib.request.urlopen(r, timeout=45) as x:
                return json.loads(x.read())
        except Exception:
            time.sleep(0.6)
    return None


def dec_sym(h):
    if not h or h == "0x":
        return None
    try:
        b = bytes.fromhex(h[2:])
    except ValueError:
        return None
    if len(b) >= 64 and int.from_bytes(b[:32], "big") == 32:
        n = int.from_bytes(b[32:64], "big")
        if 0 < n <= 100 and len(b) >= 64 + n:
            return b[64:64 + n].decode("utf-8", "replace").strip("\x00").strip() or None
    if len(b) == 32:
        return b.rstrip(b"\x00").decode("utf-8", "replace").strip() or None
    return None


def check_chain(addrs):
    live, syms = 0, set()
    for i in range(0, len(addrs), 15):
        g = addrs[i:i + 15]
        batch, meta = [], []
        for a in g:
            batch.append({"jsonrpc": "2.0", "id": len(batch), "method": "eth_getCode",
                          "params": [a, "latest"]})
            meta.append((a, "code"))
            batch.append({"jsonrpc": "2.0", "id": len(batch), "method": "eth_call",
                          "params": [{"to": a, "data": "0x95d89b41"}, "latest"]})
            meta.append((a, "sym"))
        r = rpc(batch)
        if not r:
            continue
        by = {x["id"]: x.get("result") for x in r if isinstance(x, dict) and "id" in x}
        for j, (a, k) in enumerate(meta):
            v = by.get(j)
            if v is None:
                continue
            if k == "code" and v != "0x":
                live += 1
            elif k == "sym":
                s = dec_sym(v)
                if s:
                    syms.add(s)
        time.sleep(0.3)
    return live, sorted(syms)


def main():
    acc = {a["u"]: a for a in json.load(open(D / "accounts.json"))}
    ver = json.load(open(D / "contract_verify.json"))
    tweets = {}
    for line in open(D / "tweets" / "tweets.jsonl"):
        try:
            r = json.loads(line)
            if r.get("ok"):
                tweets[r["u"]] = r
        except Exception:
            pass

    pool = [u for u, a in acc.items()
            if ver.get(u, {}).get("tok") == "none" and u in tweets
            and a["ss"] == "ok" and a["vd"] in ("promising", "ok") and a.get("site")]
    pool.sort(key=lambda u: (acc[u]["vd"] != "promising", -acc[u]["fo"]))
    lim = int(os.environ.get("LIMIT", "0"))
    if lim:
        pool = pool[:lim]
    print(f"scanning {len(pool)} not-yet-launched candidates one by one", flush=True)

    def work(u):
        a = acc[u]
        body, code = fetch(a["site"])
        if not code.startswith("2") or len(body) < 300:
            return None
        blob = body
        for js in same_origin_scripts(body, a["site"]):
            b2, c2 = fetch(js)
            if c2.startswith("2"):
                blob += "\n" + b2
        txt = visible(body)
        if len(txt) < 500:
            txt += " " + visible(blob)[:6000]      # shells describe themselves in the bundle
        addrs = [x.lower() for x in dict.fromkeys(CA_RE.findall(blob)) if is_addr(x.lower())]
        return u, a, blob, txt, addrs

    fetched = []
    with ThreadPoolExecutor(8) as ex:
        for n, r in enumerate(ex.map(work, pool), 1):
            if r:
                fetched.append(r)
            if n % 40 == 0:
                print(f"  fetched {n}/{len(pool)}", flush=True)
    print(f"sites reachable: {len(fetched)}", flush=True)

    rows = []
    for n, (u, a, body, txt, addrs) in enumerate(fetched, 1):
        live, syms = check_chain(addrs[:40]) if addrs else (0, [])
        tw = tweets.get(u, {})
        tws = tw.get("tw", [])
        newest = tws[0].get("d", "") if tws else ""
        stack = sorted({m.group(0).lower() for m in STACK.finditer(txt)})
        candour = len(set(m.group(0).lower() for m in CANDOUR.finditer(txt)))
        hype = len(CANDOUR.findall("")) + len(set(m.group(0).lower() for m in HYPE.finditer(txt)))
        docs = bool(DOCS.search(body))
        github = "github.com/" in body.lower()

        score = 0
        score += min(live, 12) * 2          # deployed contracts the site actually points at
        score += min(len(syms), 8)          # real tokens it reads back
        score += 4 if docs else 0
        score += 3 if github else 0
        score += min(candour, 5) * 2        # says what it does not hold, what can go wrong
        score += min(len(stack), 4) * 2     # names the protocol it is built on
        score += 3 if len(txt) > 3000 else (1 if len(txt) > 1200 else 0)
        score += 2 if len(tws) >= 10 else 0
        score -= hype * 4
        rows.append({"u": u, "name": a["n"], "site": a["site"], "cat": a["cat"],
                     "fo": a["fo"], "d": a["d"], "vd": a["vd"], "score": score,
                     "live": live, "syms": syms[:6], "docs": docs, "github": github,
                     "candour": candour, "hype": hype, "stack": stack, "text": len(txt),
                     "tweets": len(tws), "newest": newest[:16], "s": a["s"]})
        if n % 25 == 0:
            print(f"  chain-checked {n}/{len(fetched)}", flush=True)

    rows.sort(key=lambda r: -r["score"])
    json.dump(rows, open(D / "deep_scan.json", "w"), ensure_ascii=False, indent=1)
    print(f"\nwrote data/deep_scan.json — {len(rows)} scanned\n")
    print(f"{'score':>5} {'live':>4} {'tok':>3} {'@handle':<20} {'cat':<10} site")
    for r in rows[:40]:
        flags = ("D" if r["docs"] else "-") + ("G" if r["github"] else "-") + f"c{r['candour']}"
        print(f"{r['score']:>5} {r['live']:>4} {len(r['syms']):>3} @{r['u']:<19} {r['cat']:<10} "
              f"{flags:<6} {r['site'][:38]}")


if __name__ == "__main__":
    main()
