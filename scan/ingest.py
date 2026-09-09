#!/usr/bin/env python3
"""Turn newly discovered followers into rows on the site.

followers.py only records that an account exists. This is the half that decides
whether it is a project worth listing: fetch its site, read its tweets, pull every
contract address out of all three places, check them on chain, then classify.

    python3 scan/ingest.py            # process every unprocessed candidate
    MAX_NEW=20 python3 scan/ingest.py # bound a run
"""
import json, os, re, subprocess, sys, time, html, urllib.request
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

from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data"
BIRD = _node_bin()
RPC = ["https://rpc.mainnet.chain.robinhood.com", "https://robinhood-rpc.publicnode.com",
       "https://rpc.ordofi.network"]
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"

CA_RE = re.compile(r"0x[a-fA-F0-9]{40}")
URL_RE = re.compile(r"https?://[^\s]+", re.I)
BARE_RE = re.compile(r"\b([a-z0-9][a-z0-9-]{1,40}\.(?:com|io|xyz|fun|app|net|org|co|gg|live|finance|market|trade|cash|club|art|money|network|ai|dev|tech|bond|pro|shop|world|space|land|wtf|lol|best|store|fi|meme))\b", re.I)
SOCIAL = re.compile(r"(t\.me/|linktr\.ee|x\.com|twitter\.com|discord|instagram|youtube|tiktok|medium\.com|opensea\.io|dexscreener|dextools|magiceden|beacons|solo\.to|carrd\.co)", re.I)
DEX = re.compile(r"(dexscreener|dextools|geckoterminal|pump\.fun|birdeye|app\.uniswap|jup\.ag|four\.meme|bags\.fm)", re.I)

# a project talks about a thing it is building; a person talks about themselves
PROJECT_HINT = re.compile(r"(launch|protocol|token|mint|nft|dex|swap|stake|staking|vault|yield|liquidity|perp|trading|trade|chain|onchain|on-chain|dapp|airdrop|presale|collection|pfp|game|agent|bot|explorer|scanner|index|treasury|bridge|wallet|marketplace|launchpad|hook|uniswap|robinhood chain|rwa|tokenized|发射|协议|代币|铸造|质押|流动性|链上)", re.I)
PERSON_HINT = re.compile(r"\b(i |i'm|im |my |me\b|father|husband|wife|dad|mom|student|engineer at|founder of|investor|trader|degen|enthusiast|opinions|views are|father of|building at|ex-|he/him|she/her|they/them)\b", re.I)
SCAM_HINT = re.compile(r"(guaranteed|100% safe|risk[- ]free|only win|can'?t lose|1000x guaranteed|official robinhood|robinhood official|send .{0,12}(eth|usdt) .{0,12}receive|claim your|connect wallet to claim|保证收益|稳赚|官方)", re.I)


def bird_env():
    e = dict(os.environ)
    e["NODE_USE_ENV_PROXY"] = "1"
    e["PATH"] = str(Path(BIRD).parent) + ":" + e.get("PATH", "")
    return e


def is_addr(a):
    try:
        b = bytes.fromhex(a[2:])
    except ValueError:
        return False
    return sum(1 for x in b if 32 <= x < 127) < 16


def pick_url(bio):
    """bird's follower payload has no website field, so the bio is all we get.

    Returns (url, is_own_site). A Discord invite or a pump.fun referral is a link
    but not a site of one's own, and treating it as one is how personal accounts
    leak into the list."""
    for u in URL_RE.findall(bio or ""):
        if not SOCIAL.search(u):
            return u.rstrip(".,;)"), True
    m = BARE_RE.search(bio or "")
    if m and not SOCIAL.search(m.group(1)):
        return "https://" + m.group(1), True
    for u in URL_RE.findall(bio or ""):
        return u.rstrip(".,;)"), False
    return "", False


def fetch_site(url):
    if not url:
        return {"status": "none", "title": "", "meta": "", "text": "", "flags": []}
    try:
        p = subprocess.run(["curl", "-sSL", "-m", "25", "--max-filesize", "400000",
                            "-A", UA, "-w", "\n@@%{http_code}", url],
                           capture_output=True, timeout=40)
        out = p.stdout.decode("utf-8", "ignore")
        body, _, code = out.rpartition("\n@@")
        code = (code or "000").strip()
    except Exception:
        return {"status": "unreachable", "title": "", "meta": "", "text": "", "flags": []}
    t = re.search(r"<title[^>]*>(.*?)</title>", body, re.I | re.S)
    md = re.search(r'<meta[^>]+(?:name|property)=["\'](?:description|og:description)["\'][^>]+content=["\']([^"\']*)', body, re.I)
    clean = re.sub(r"<(script|style|noscript|svg)[^>]*>.*?</\1>", "", body, flags=re.I | re.S)
    clean = re.sub(r"<[^>]+>", " ", clean)
    clean = re.sub(r"\s+", " ", html.unescape(clean)).strip()
    low = body.lower()
    checks = {
        "wallet": r"connect wallet|walletconnect|rainbowkit|wagmi|privy|metamask",
        "docs": r"docs\.|/docs|gitbook|whitepaper|litepaper",
        "github": r"github\.com/",
        "audit": r"audit",
        "presale": r"presale|pre-sale|whitelist|allowlist",
        "buy": r"dexscreener|dextools|uniswap\.org|geckoterminal",
        "coming_soon": r"coming soon|launching soon|stay tuned",
    }
    flags = [k for k, v in checks.items() if re.search(v, low)]
    if not code.startswith("2"):
        st = "blocked" if code.startswith("4") else ("err5xx" if code.startswith("5") else "unreachable")
    else:
        st = "ok" if len(clean) >= 200 else "shell"
    return {"status": st,
            "title": html.unescape(t.group(1)).strip()[:150] if t else "",
            "meta": html.unescape(md.group(1)).strip()[:300] if md else "",
            "text": clean[:2500], "flags": flags}


def fetch_tweets(handle, n=20):
    try:
        p = subprocess.run([BIRD, "user-tweets", handle, "-n", str(n), "--json",
                            "--timeout", "45000", "--no-color", "--no-emoji"],
                           capture_output=True, env=bird_env(), timeout=110)
        out = p.stdout.decode("utf-8", "ignore")
        err = p.stderr.decode("utf-8", "ignore")
        i = out.find("[")
        if i < 0:
            return None, ("rate" if "429" in err else "err")
        arr = json.loads(out[i:])
        return [{"t": x.get("text", ""), "d": x.get("createdAt", ""),
                 "q": (x.get("quotedTweet") or {}).get("text", "")} for x in arr], None
    except Exception:
        return None, "err"


def rpc(batch):
    for u in RPC:
        try:
            r = urllib.request.Request(u, data=json.dumps(batch).encode(),
                                       headers={"Content-Type": "application/json", "User-Agent": UA})
            with urllib.request.urlopen(r, timeout=40) as resp:
                return json.loads(resp.read())
        except Exception:
            time.sleep(0.4)
    return None


def dec_str(h):
    if not h or h == "0x":
        return None
    try:
        b = bytes.fromhex(h[2:])
    except ValueError:
        return None
    if len(b) >= 64 and int.from_bytes(b[:32], "big") == 32:
        ln = int.from_bytes(b[32:64], "big")
        if 0 < ln <= 200 and len(b) >= 64 + ln:
            return b[64:64 + ln].decode("utf-8", "replace").strip("\x00").strip() or None
    if len(b) == 32:
        return b.rstrip(b"\x00").decode("utf-8", "replace").strip() or None
    return None


def check_chain(addrs):
    """eth_getCode + symbol() for each address, with the canary bird taught us to use."""
    out = {a: {} for a in addrs}
    if not addrs:
        return out
    batch, meta = [], []
    for a in addrs:
        batch.append({"jsonrpc": "2.0", "id": len(batch), "method": "eth_getCode", "params": [a, "latest"]})
        meta.append((a, "code"))
        batch.append({"jsonrpc": "2.0", "id": len(batch), "method": "eth_call",
                      "params": [{"to": a, "data": "0x95d89b41"}, "latest"]})
        meta.append((a, "sym"))
    res = rpc(batch)
    if not res:
        return out
    by = {x["id"]: x.get("result") for x in res if isinstance(x, dict) and "id" in x}
    for i, (a, k) in enumerate(meta):
        v = by.get(i)
        if v is None:
            continue
        if k == "code":
            out[a]["has_code"] = v != "0x"
        else:
            out[a]["symbol"] = dec_str(v)
    return out


def classify(c, site, tweets, chain, cas, own_site):
    bio = c.get("bio", "")
    blob = " ".join([bio, site["title"], site["meta"], site["text"][:1200]])
    tw_text = " ".join((t["t"] + " " + t["q"]) for t in (tweets or []))
    full = blob + " " + tw_text
    live = any(chain.get(a, {}).get("has_code") for a in cas)

    # A person writes about themselves in the first person. That, with no site of
    # their own and no contract, is the shape of every personal account we saw.
    first_person = bool(re.search(r"\b(i|i'm|im|my|me)\b", bio, re.I))
    self_described = bool(PERSON_HINT.search(bio))

    evidence = 0
    if live:                                   evidence += 3   # a deployed contract
    elif cas:                                  evidence += 1   # an address, unverified
    if own_site and site["status"] == "ok":    evidence += 2
    if own_site and site["status"] == "shell": evidence += 1
    if {"docs", "github"} & set(site["flags"]):evidence += 2
    if "wallet" in site["flags"]:              evidence += 1
    if re.search(r"\b\d{3,5}\s*(nft|pfp|collection|piece)", full, re.I): evidence += 2
    if PROJECT_HINT.search(bio):               evidence += 1
    if first_person or self_described:         evidence -= 2
    if not own_site:                           evidence -= 1

    # A site of one's own that actually loads is the strongest single signal a new
    # account can give, so it carries a borderline score over the line.
    own_live = own_site and site["status"] in ("ok", "shell")
    is_project = evidence >= 3 or (evidence >= 2 and own_live)
    confidence = "high" if evidence >= 5 else ("mid" if evidence >= 3 else "low")
    tok = "issued" if cas else ("likely" if DEX.search(full) else "none")
    cv = ("live_token" if live else ("wallet" if cas else "no_ca"))

    if SCAM_HINT.search(full):
        vd = "scam_signals"
    elif site["status"] == "ok" and ({"docs", "github"} & set(site["flags"]) or "wallet" in site["flags"]):
        vd = "promising"
    elif site["status"] in ("unreachable", "none") or "coming_soon" in site["flags"]:
        vd = "weak"
    elif site["status"] == "ok":
        vd = "ok"
    else:
        vd = "weak"

    cat = "其他"
    for pat, name in [(r"launchpad|发射|launch a|deploy.*token", "发射台"),
                      (r"perp|leverage|杠杆", "永续-杠杆"), (r"\bdex\b|swap|aggregat|exchange", "DEX交易"),
                      (r"explorer|scanner|analytics|tracker|扫描", "浏览器-数据"),
                      (r"nft|pfp|collection|mint|铸造", "NFT"), (r"game|play|mmo|游戏", "游戏"),
                      (r"predict|bet|casino|投注", "预测-博彩"), (r"\bai\b|agent|mcp", "AI-Agent"),
                      (r"privacy|zk|隐私", "隐私"), (r"wallet|bot|钱包", "钱包-工具"),
                      (r"yield|vault|lend|stake|rwa|tokenized|stock|收益|金库", "DeFi-RWA"),
                      (r"meme|coin", "Meme币")]:
        if re.search(pat, full, re.I):
            cat = name
            break
    return is_project, vd, cat, tok, cv, live, confidence, evidence


def main():
    max_new = int(os.environ.get("MAX_NEW", "0"))
    accounts = json.load(open(D / "accounts.json"))
    known = {a["u"] for a in accounts}
    verify = json.load(open(D / "contract_verify.json"))
    processed_p = D / "ingested.json"
    processed = set(json.load(open(processed_p))) if processed_p.exists() else set()

    cands, seen = [], set()
    for line in open(D / "candidates.jsonl"):
        try:
            r = json.loads(line)
        except Exception:
            continue
        u = r["username"]
        if u in known or u in processed or u in seen:
            continue
        if not r.get("hasLink"):
            continue                      # gate 2: a link in the bio
        seen.add(u)
        cands.append(r)
    if max_new:
        cands = cands[:max_new]
    print(f"candidates to ingest: {len(cands)}", flush=True)
    if not cands:
        return

    added, skipped, rate_skipped = [], [], 0
    for c in cands:
        u = c["username"]
        if c.get("website"):
            url, own_site = c["website"], not bool(SOCIAL.search(c["website"]))
        else:
            url, own_site = pick_url(c.get("bio", ""))
        site = fetch_site(url)
        # Tweets share a rate-limit budget with the backfill job. If they are not
        # available now, judge on the site and the chain; scan/tweets.py fills them
        # in later and scan/build.py picks the contract up then.
        tweets, terr = fetch_tweets(u)
        if terr:
            tweets = None
            rate_skipped += 1
        cas = []
        blob = c.get("bio", "") + " " + site["text"] + " " + site["meta"]
        for t in (tweets or []):
            blob += " " + t["t"] + " " + t["q"]
        for a in CA_RE.findall(blob):
            a = a.lower()
            if is_addr(a) and a not in cas:
                cas.append(a)
        chain = check_chain(cas[:6])
        is_project, vd, cat, tok, cv, live, conf, ev = classify(c, site, tweets, chain, cas, own_site)
        processed.add(u)
        if not is_project:
            skipped.append((u, ev, (c.get("bio") or "")[:44]))
            continue
        syms = [s for s in (chain.get(a, {}).get("symbol") for a in cas) if s]
        accounts.append({
            "u": u, "n": c.get("name") or u, "v": c.get("verified", "unknown"),
            "d": time.strftime("%Y-%m-%d", time.strptime(c["createdAt"], "%a %b %d %H:%M:%S %z %Y"))
                 if c.get("createdAt") else time.strftime("%Y-%m-%d"),
            "fo": c.get("followers") or 0, "site": url,
            "ss": site["status"] if site["status"] in ("ok", "shell", "blocked", "unreachable", "err5xx") else "unreachable",
            "vd": vd, "match": "unverifiable" if site["status"] != "ok" else "partial",
            "cat": cat,
            "s": (site["meta"] or site["title"] or c.get("bio", ""))[:34],
            "note": f"自动归类({conf})·关注 @{c['seedFrom']} 后发现·待人工复核",
            "flags": site["flags"],
        })
        verify[u] = {"cv": cv, "tok": tok, "own": [], "syms": syms[:2], "n_ca": len(cas),
                     "ca": cas[0] if cas else "", "chains": [], "in_bio": bool(CA_RE.search(c.get("bio", ""))),
                     "in_site": bool(CA_RE.search(site["text"])), "buy": bool(DEX.search(blob)),
                     "renounced": False, "e721": False,
                     "src": ",".join(x for x, cond in
                                     [("bio", CA_RE.search(c.get("bio", ""))),
                                      ("site", CA_RE.search(site["text"])),
                                      ("tweet", any(CA_RE.search(t["t"] + t["q"]) for t in (tweets or [])))] if cond)}
        added.append((u, vd, cat, tok, url, conf, ev))
        time.sleep(2.0)

    json.dump(sorted(processed), open(processed_p, "w"))
    if added:
        json.dump(accounts, open(D / "accounts.json", "w"), ensure_ascii=False)
        json.dump(verify, open(D / "contract_verify.json", "w"), ensure_ascii=False)
    print(f"\nadded {len(added)} project accounts, skipped {len(skipped)} personal/unclear"
          + (f", {rate_skipped} judged without tweets (backfill will fill them in)" if rate_skipped else ""))
    for u, vd, cat, tok, url, conf, ev in added:
        print(f"  + @{u:<19} ev={ev:<2} {conf:<4} {vd:<12} {cat:<10} {tok:<7} {url[:38]}")
    for u, ev, bio in skipped[:12]:
        print(f"  - @{u:<19} ev={ev:<2} {bio}")


if __name__ == "__main__":
    main()
