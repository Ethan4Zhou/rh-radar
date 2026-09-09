# rh-radar

Tracks new project accounts on Robinhood Chain (chain id 4663) and checks whether
what they say matches what is actually there.

## Where the accounts come from

Verified followers of three seed accounts:

| seed | user id |
|---|---|
| @RobinhoodCrypto | 352518189 |
| @RobinhoodApp | 1265037073 |
| @vladtenev | 605700792 |

X returns followers newest-first, so an incremental scan only reads the first
pages and stops when it stops seeing new handles.

## Filters

1. account created within the last three months
2. a link in the bio or the website field
3. the profile or its site describes a project, not a person

## Pipeline

```
scan/followers.py    poll the three seeds via bird, dedupe against data/seen.json
scan/site_crawl.py   fetch each account's website, keep title/meta/text/flags
scan/chain.py        every 0x address -> eth_getCode + ERC-20 reads across 8 chains
scan/priority.py     order the tweet queue so the read rows get corrected first
scan/tweets.py       read recent tweets (resumable, backs off on 429)
scan/build.py        recompute token status and write site/data.json
site/build_site.py   inline data.json into a single self-contained index.html
```

`./run.sh` does one cycle: new followers, ingest, rebuild, publish, commit, push.

## Where the page is served

GitHub Pages serves `docs/` from this repo:

  https://ethan4zhou.github.io/rh-radar/

Every scan cycle rebuilds `docs/index.html` and pushes it, and Pages redeploys
within a minute or so.

## What is and is not in this repo

Tracked: the scripts, the derived account table, and the rendered page — the same
rows the site already shows.

Not tracked (see `.gitignore`): the raw captures. `data/site_crawl.jsonl` is the
scraped text of several thousand third-party sites, `data/tweets/tweets.jsonl` the
tweets behind the contract-address check, and `data/accounts_raw.json` the profile
dump the first pass started from. They regenerate from the three seeds, and
republishing bulk scrapes of other people's sites and profiles serves no one.

## Setting it up on another machine

```bash
git clone https://github.com/Ethan4Zhou/rh-radar.git && cd rh-radar
npm i -g @steipete/bird          # reads X through your logged-in Chrome session
./run.sh                         # one cycle
PROXY=127.0.0.1:7897 ./deploy/install.sh   # optional: the two launchd agents
```

Nothing here stores a credential. `bird` reads the cookies from your own browser,
and every script that talks to X goes through it.

## Running it

```bash
./run.sh                       # one cycle
python3 scan/tweets.py         # backfill tweets, resumable, safe to Ctrl-C
python3 scan/build.py          # recompute after new tweets land
```

Two launchd agents keep it going. The scan cycle runs every 30 minutes; the
tweet reader runs continuously and restarts itself if it dies.

```bash
launchctl load ~/Library/LaunchAgents/com.ethanzhou.rhradar.plist          # scan cycle
launchctl load ~/Library/LaunchAgents/com.ethanzhou.rhradar.tweets.plist   # tweet reader

launchctl unload ~/Library/LaunchAgents/com.ethanzhou.rhradar.tweets.plist # stop either one
tail -f logs/scan.log logs/tweets.log
```

`scan/tweets.py` holds a lock file so two readers never share the same
rate-limit budget, and `MAX_ACCOUNTS=200 python3 scan/tweets.py` bounds a run.

## Sharing the exclusion list

`data/excluded.json` is the team baseline: who removed a project, when, and why.
It is inlined into the page at build time, so everyone who opens the page starts
from the same list. What a person removes in their own browser stays local until
they choose to promote it.

```bash
scan/exclude.py add @foo 已归零        # RH_USER=name to sign it
scan/exclude.py rm @foo
scan/exclude.py list
scan/exclude.py merge exported.json    # take what the page exported
```

In the page, "管理名单 → 复制为仓库格式" yields exactly this file's shape.
Restoring a team entry only affects that browser; the repo is the only way to
change what everyone sees.

## Why a contract address can hide

An account can announce its token in three places, and they disagree often:
the X bio, the website, and the tweets. Reading only the first two labelled 42
accounts "no token yet" that had in fact already launched — including several
with working products. `scan/build.py` now treats all three as evidence and
records which one it came from, and the page marks any account whose tweets have
not been read yet, so an unchecked "no token yet" is never mistaken for a
verified one.

## Credentials

Everything on X goes through `bird`, which reads the logged-in cookies from
Chrome. Node's fetch ignores the system proxy unless `NODE_USE_ENV_PROXY=1` is
set, which every script here does.

## Rate limits

`followers` runs on the REST endpoint (1000 requests / 15 min, 200 users per
page). `user-tweets` runs on GraphQL and is far tighter — roughly 40-50 calls
before a 429, then a 15 minute window. `scan/tweets.py` backs off and resumes,
and works through accounts in priority order so the list you actually read gets
corrected first.

## Where verification comes from

Discovery reads X's **Verified Followers** list — the same list the original
55,633-account pass came from. bird's `followers` command falls back to a REST
endpoint that no longer carries the blue or gold flag and drops the website field,
which left every newly found account unverified and half of them without a site to
crawl.

`scan/find_query_id.sh` reads the operation's query id out of X's own client
bundles (the way `bird query-ids --fresh` does; the id lives in `main.*.js`, which
is reachable from `x.com/settings/profile` — the logged-out home page no longer
references it). The id is cached in `data/bvf_query.json`; re-run the finder if X
rotates it. `scan/verified_followers.py` then pages the list with bird's cookies,
and `scan/vf_scan.py` applies the three gates.

That endpoint allows 500 requests per 15 minutes at 100 users a page, so the walk
is limited by patience rather than by quota.

## Known limits

- bird's follower output comes from the REST endpoint, which no longer carries
  blue or gold verification, so newly discovered accounts start as unknown.
- The website field is not in that response either. Only the bio is searched for
  a link, so a project whose link lives only in the website field can be missed
  until its tweets are read.
