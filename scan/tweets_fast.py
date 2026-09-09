#!/usr/bin/env python3
"""Read recent tweets through X's own UserTweets operation, paced by the quota it
reports.

The bird-driven reader backs off blindly: it guesses a delay, trips a 429, sleeps
five minutes, and repeats. X tells you exactly how much budget is left in every
response header, so this spends it evenly and sleeps only until the window
actually resets.

    python3 scan/tweets_fast.py            # work the priority queue
    MAX_ACCOUNTS=300 python3 scan/tweets_fast.py
"""
import json, os, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data"
sys.path.insert(0, str(ROOT / "scan"))
from verified_followers import creds, BEARER   # same logged-in session bird uses

OUT = D / "tweets" / "tweets.jsonl"
LOCK = D / "tweets" / ".fetch.lock"
QIDS = Path.home() / ".config" / "bird" / "query-ids-cache.json"

FEATURES = {
    "rweb_video_screen_enabled": True, "payments_enabled": False,
    "profile_label_improvements_pcf_label_in_post_enabled": True,
    "rweb_tipjar_consumption_enabled": True, "verified_phone_label_enabled": False,
    "creator_subscriptions_tweet_preview_api_enabled": True,
    "responsive_web_graphql_timeline_navigation_enabled": True,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "premium_content_api_read_enabled": True,
    "communities_web_enable_tweet_community_results_fetch": True,
    "c9s_tweet_anatomy_moderator_badge_enabled": True,
    "responsive_web_grok_analyze_button_fetch_trends_enabled": False,
    "responsive_web_grok_analyze_post_followups_enabled": False,
    "responsive_web_jetfuel_frame": False,
    "responsive_web_grok_share_attachment_enabled": False,
    "articles_preview_enabled": True, "responsive_web_edit_tweet_api_enabled": True,
    "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
    "view_counts_everywhere_api_enabled": True,
    "longform_notetweets_consumption_enabled": True,
    "responsive_web_twitter_article_tweet_consumption_enabled": True,
    "tweet_awards_web_tipping_enabled": True,
    "responsive_web_grok_show_grok_translated_post": False,
    "responsive_web_grok_analysis_button_from_backend": False,
    "creator_subscriptions_quote_tweet_preview_enabled": False,
    "freedom_of_speech_not_reach_fetch_enabled": True,
    "standardized_nudges_misinfo": True,
    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
    "longform_notetweets_rich_text_read_enabled": True,
    "longform_notetweets_inline_media_enabled": True,
    "responsive_web_grok_image_annotation_enabled": True,
    "responsive_web_grok_community_note_auto_translation_is_enabled": False,
    "responsive_web_enhance_cards_enabled": False,
}
FIELD_TOGGLES = {"withArticlePlainText": False}
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")


def headers(auth, ct0):
    return {"authorization": BEARER, "cookie": f"auth_token={auth}; ct0={ct0}",
            "x-csrf-token": ct0, "x-twitter-active-user": "yes",
            "x-twitter-auth-type": "OAuth2Session", "x-twitter-client-language": "en",
            "content-type": "application/json", "referer": "https://x.com/", "user-agent": UA}


def user_id_map():
    """Resolve handles to ids from what we already have on disk."""
    m = {}
    for name in ("verified_followers_RobinhoodCrypto.jsonl",
                 "verified_followers_RobinhoodApp.jsonl",
                 "verified_followers_vladtenev.jsonl"):
        p = D / name
        if not p.exists():
            continue
        for line in p:
            pass
    return m


def fetch(uid_or_handle, qid, h, count=20):
    """UserTweets needs a numeric id; UserByScreenName resolves one when needed."""
    v = {"userId": uid_or_handle, "count": count, "includePromotedContent": False,
         "withQuickPromoteEligibilityTweetFields": False, "withVoice": False}
    url = (f"https://x.com/i/api/graphql/{qid}/UserTweets"
           f"?variables={urllib.parse.quote(json.dumps(v))}"
           f"&features={urllib.parse.quote(json.dumps(FEATURES))}"
           f"&fieldToggles={urllib.parse.quote(json.dumps(FIELD_TOGGLES))}")
    req = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            body = json.loads(r.read())
            return body, {"remaining": r.headers.get("x-rate-limit-remaining"),
                          "reset": r.headers.get("x-rate-limit-reset"),
                          "limit": r.headers.get("x-rate-limit-limit")}, None
    except urllib.error.HTTPError as e:
        return None, {"remaining": e.headers.get("x-rate-limit-remaining"),
                      "reset": e.headers.get("x-rate-limit-reset"),
                      "limit": e.headers.get("x-rate-limit-limit")}, e.code
    except Exception as e:
        return None, {}, str(e)[:80]


def texts(body):
    out = []
    insts = []
    r = ((body.get("data") or {}).get("user") or {}).get("result") or {}
    for k, v in r.items():
        if "timeline" in k.lower() and isinstance(v, dict):
            inner = v.get("timeline") if isinstance(v.get("timeline"), dict) else v
            insts = inner.get("instructions") or []
            if insts:
                break
    for i in insts:
        for e in (i.get("entries") or []):
            c = (e.get("content") or {})
            items = [c.get("itemContent")] if c.get("itemContent") else \
                    [x.get("item", {}).get("itemContent") for x in (c.get("items") or [])]
            for it in items:
                if not it:
                    continue
                res = (it.get("tweet_results") or {}).get("result") or {}
                res = res.get("tweet", res)
                lg = res.get("legacy") or {}
                note = (((res.get("note_tweet") or {}).get("note_tweet_results") or {})
                        .get("result") or {}).get("text")
                q = (((res.get("quoted_status_result") or {}).get("result") or {})
                     .get("legacy") or {}).get("full_text", "")
                t = note or lg.get("full_text") or ""
                if t or q:
                    out.append({"t": t, "d": lg.get("created_at", ""), "q": q})
    return out


def main():
    if LOCK.exists():
        try:
            os.kill(int(LOCK.read_text().strip() or 0), 0)
            print("the bird-based reader holds the lock; stop it first "
                  "(launchctl unload ~/Library/LaunchAgents/com.ethanzhou.rhradar.tweets.plist)")
            return 1
        except Exception:
            LOCK.unlink(missing_ok=True)
    LOCK.write_text(str(os.getpid()))
    try:
        return run()
    finally:
        LOCK.unlink(missing_ok=True)


def run():
    qid = json.load(open(QIDS))["ids"]["UserTweets"]
    auth, ct0 = creds()
    h = headers(auth, ct0)

    # UserTweets takes a numeric id, never a handle. The source dataset carries one
    # for every account it shipped with; anything discovered later needs a lookup.
    ids = {}
    raw = D / "accounts_raw.json"
    if raw.exists():
        src = json.load(open(raw))
        for p in src.get("projects", []) + src.get("excluded", []):
            if p.get("id") and p.get("username"):
                ids[p["username"]] = str(p["id"])
    for name in ("RobinhoodCrypto", "RobinhoodApp", "vladtenev"):
        p = D / f"verified_followers_{name}.jsonl"
        if p.exists():
            for line in open(p):
                try:
                    r = json.loads(line)
                    if r.get("id") and r.get("username"):
                        ids[r["username"]] = str(r["id"])
                except Exception:
                    pass
    print(f"resolved ids for {len(ids)} handles", flush=True)

    done = set()
    if OUT.exists():
        for line in open(OUT):
            try:
                r = json.loads(line)
                if r.get("ok") or r.get("e") == "notfound":
                    done.add(r["u"])
            except Exception:
                pass
    queue = [u for u in json.load(open(D / "tweets" / "priority.json")) if u not in done]
    cap = int(os.environ.get("MAX_ACCOUNTS", "0"))
    if cap:
        queue = queue[:cap]
    print(f"queue: {len(queue)} accounts (already read: {len(done)})", flush=True)

    f = open(OUT, "a")
    i = ok = miss = 0
    while i < len(queue):
        u = queue[i]
        target = ids.get(u)
        if not target:
            f.write(json.dumps({"u": u, "ok": False, "e": "no_id"}) + "\n")
            f.flush(); i += 1; miss += 1; continue
        body, rl, err = fetch(target, qid, h)
        if err == 429:
            reset = int(rl.get("reset") or 0)
            wait = max(10, reset - int(time.time()) + 5) if reset else 300
            print(f"quota spent, sleeping {wait}s until the window resets", flush=True)
            time.sleep(min(wait, 960))
            continue
        if body is None:
            f.write(json.dumps({"u": u, "ok": False, "e": "err", "msg": str(err)[:80]}) + "\n")
            f.flush(); i += 1; miss += 1; continue
        tw = texts(body)
        if not tw and not ((body.get("data") or {}).get("user") or {}).get("result"):
            f.write(json.dumps({"u": u, "ok": False, "e": "notfound"}) + "\n")
            f.flush(); i += 1; miss += 1; continue
        f.write(json.dumps({"u": u, "ok": True, "n": len(tw), "tw": tw}, ensure_ascii=False) + "\n")
        f.flush(); i += 1; ok += 1

        rem = int(rl.get("remaining") or 0)
        reset = int(rl.get("reset") or 0)
        if rem <= 1 and reset:
            wait = max(5, reset - int(time.time()) + 5)
            print(f"  {i}/{len(queue)} · quota exhausted, sleeping {wait}s", flush=True)
            time.sleep(min(wait, 960))
        elif rem and reset:
            # spread what is left evenly across the rest of the window
            left = max(1, reset - int(time.time()))
            time.sleep(max(0.4, min(8.0, left / max(1, rem))))
        else:
            time.sleep(2)
        if i % 50 == 0:
            print(f"  {i}/{len(queue)} ok={ok} miss={miss} quota={rl.get('remaining')}/{rl.get('limit')}", flush=True)
    f.close()
    print(f"done: {ok} read, {miss} unavailable")
    return 0


if __name__ == "__main__":
    sys.exit(main())
