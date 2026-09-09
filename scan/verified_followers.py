#!/usr/bin/env python3
"""Read the Verified Followers list the way X's own web app does.

Only useful once a query id is known — run scan/find_query_id.sh to get one, then:

    RH_VF_QUERY_ID=<id> python3 scan/verified_followers.py RobinhoodCrypto

Credentials come from bird (the logged-in Chrome session); nothing is stored here.
Unlike the REST endpoint bird falls back to, this response carries is_blue_verified
and verified_type, which is the whole reason for going this way.
"""
import json, os, subprocess, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data"
def _find(pattern, env_key):
    """Locate node and bird's module without pinning one machine's layout."""
    v = os.environ.get(env_key)
    if v and Path(v).exists():
        return v
    for c in sorted(Path.home().glob(pattern), reverse=True):
        return str(c)
    return ""


BIRD_DIR = _find(".nvm/versions/node/*/lib/node_modules/@steipete/bird/dist/index.js", "BIRD_MODULE")
NODE = _find(".nvm/versions/node/*/bin/node", "NODE_BIN") or "node"

SEEDS = {"RobinhoodCrypto": "352518189", "RobinhoodApp": "1265037073", "vladtenev": "605700792"}

FEATURES = {
    "rweb_video_screen_enabled": True,
    "rweb_cashtags_enabled": True,
    "profile_label_improvements_pcf_label_in_post_enabled": False,
    "responsive_web_profile_redirect_enabled": True,
    "rweb_tipjar_consumption_enabled": True,
    "verified_phone_label_enabled": False,
    "creator_subscriptions_tweet_preview_api_enabled": True,
    "responsive_web_graphql_timeline_navigation_enabled": True,
    "premium_content_api_read_enabled": True,
    "communities_web_enable_tweet_community_results_fetch": True,
    "c9s_tweet_anatomy_moderator_badge_enabled": True,
    "responsive_web_grok_analyze_button_fetch_trends_enabled": False,
    "responsive_web_grok_analyze_post_followups_enabled": False,
    "rweb_cashtags_composer_attachment_enabled": True,
    "responsive_web_jetfuel_frame": False,
    "rweb_sports_post_context_enabled": True,
    "responsive_web_grok_share_attachment_enabled": False,
    "responsive_web_grok_annotations_enabled": False,
    "articles_preview_enabled": True,
    "responsive_web_edit_tweet_api_enabled": True,
    "rweb_conversational_replies_downvote_enabled": True,
    "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
    "view_counts_everywhere_api_enabled": True,
    "longform_notetweets_consumption_enabled": True,
    "responsive_web_twitter_article_tweet_consumption_enabled": True,
    "content_disclosure_indicator_enabled": True,
    "content_disclosure_ai_generated_indicator_enabled": True,
    "responsive_web_grok_show_grok_translated_post": False,
    "responsive_web_grok_analysis_button_from_backend": False,
    "post_ctas_fetch_enabled": True,
    "freedom_of_speech_not_reach_fetch_enabled": True,
    "standardized_nudges_misinfo": True,
    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
    "longform_notetweets_rich_text_read_enabled": True,
    "longform_notetweets_inline_media_enabled": True,
    "responsive_web_grok_image_annotation_enabled": False,
    "responsive_web_grok_imagine_annotation_enabled": False,
    "responsive_web_grok_community_note_auto_translation_is_enabled": False,
    "responsive_web_enhance_cards_enabled": True
}
_OLD_FEATURES = {
    "rweb_video_screen_enabled": True, "profile_label_improvements_pcf_label_in_post_enabled": False,
    "responsive_web_profile_redirect_enabled": True, "rweb_tipjar_consumption_enabled": True,
    "verified_phone_label_enabled": False, "creator_subscriptions_tweet_preview_api_enabled": True,
    "responsive_web_graphql_timeline_navigation_enabled": True,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "premium_content_api_read_enabled": True, "communities_web_enable_tweet_community_results_fetch": True,
    "c9s_tweet_anatomy_moderator_badge_enabled": True,
    "responsive_web_grok_analyze_button_fetch_trends_enabled": False,
    "responsive_web_grok_analyze_post_followups_enabled": False,
    "responsive_web_grok_annotations_enabled": False, "responsive_web_jetfuel_frame": False,
    "post_ctas_fetch_enabled": True, "responsive_web_grok_share_attachment_enabled": False,
    "articles_preview_enabled": True, "responsive_web_edit_tweet_api_enabled": True,
    "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
    "view_counts_everywhere_api_enabled": True, "longform_notetweets_consumption_enabled": True,
    "responsive_web_twitter_article_tweet_consumption_enabled": True,
    "tweet_awards_web_tipping_enabled": True, "responsive_web_grok_show_grok_translated_post": False,
    "responsive_web_grok_analysis_button_from_backend": False,
    "creator_subscriptions_quote_tweet_preview_enabled": False,
    "freedom_of_speech_not_reach_fetch_enabled": True, "standardized_nudges_misinfo": True,
    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
    "longform_notetweets_rich_text_read_enabled": True, "longform_notetweets_inline_media_enabled": True,
    "responsive_web_grok_image_annotation_enabled": False,
    "responsive_web_grok_imagine_annotation_enabled": False,
    "responsive_web_grok_community_note_auto_translation_is_enabled": False,
    "responsive_web_enhance_cards_enabled": False,
}

BEARER = ("Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs"
          "%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA")


def creds():
    """Reuse bird's cookie resolution rather than touching the keychain here."""
    js = (f"import {{ resolveCredentials }} from '{BIRD_DIR}';"
          "const c = await resolveCredentials({}); const k = c.cookies || c;"
          "console.log(JSON.stringify({a:k.authToken||k.auth_token, c:k.ct0}));")
    env = dict(os.environ); env["NODE_USE_ENV_PROXY"] = "1"
    p = subprocess.run([NODE, "--input-type=module", "-e", js],
                       capture_output=True, env=env, timeout=60)
    out = p.stdout.decode().strip().splitlines()
    for line in reversed(out):
        try:
            d = json.loads(line)
            if d.get("a") and d.get("c"):
                return d["a"], d["c"]
        except Exception:
            continue
    raise SystemExit("could not read cookies from bird: " + p.stderr.decode()[:200])


def page(qid, user_id, auth, ct0, cursor=None, count=100):
    v = {"userId": user_id, "count": count, "includePromotedContent": False}
    if cursor:
        v["cursor"] = cursor
    url = (f"https://x.com/i/api/graphql/{qid}/BlueVerifiedFollowers"
           f"?variables={urllib.parse.quote(json.dumps(v))}"
           f"&features={urllib.parse.quote(json.dumps(FEATURES))}")
    req = urllib.request.Request(url, headers={
        "authorization": BEARER, "cookie": f"auth_token={auth}; ct0={ct0}",
        "x-csrf-token": ct0, "x-twitter-active-user": "yes",
        "x-twitter-auth-type": "OAuth2Session", "x-twitter-client-language": "en",
        "content-type": "application/json", "referer": "https://x.com/",
        "user-agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"),
    })
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read()), r.headers.get("x-rate-limit-remaining")


def describe(j):
    """Print the response's shape. The timeline key moves between X releases, so
    when a page yields nothing this says where the users actually are."""
    print("top keys:", list(j.keys()))
    if "errors" in j:
        print("errors:", json.dumps(j["errors"], ensure_ascii=False)[:400])
    d = j.get("data", {})
    print("data keys:", list(d.keys()))
    u = d.get("user")
    if isinstance(u, dict):
        r = u.get("result", {})
        print("user.result keys:", list(r.keys())[:15])
        print("__typename:", r.get("__typename"))
        for k in r:
            if "timeline" in k.lower():
                tl = r[k]
                print(f"  {k}:", list(tl.keys())[:8] if isinstance(tl, dict) else type(tl).__name__)
                inner = tl.get("timeline") if isinstance(tl, dict) else None
                if isinstance(inner, dict):
                    print("    .timeline:", list(inner.keys())[:8])
                    ins = inner.get("instructions") or []
                    print("    instructions:", [x.get("type") for x in ins][:6])
                    for x in ins:
                        ents = x.get("entries") or []
                        if ents:
                            print("    first entryIds:", [e.get("entryId") for e in ents[:4]])
                            break


def parse(j):
    r = (j.get("data", {}) or {}).get("user", {}) or {}
    r = r.get("result", {}) or {}
    # X nests this as timeline.timeline.instructions on some releases and
    # timeline.instructions on others; accept either, under any timeline-ish key.
    insts = []
    for k, v in r.items():
        if "timeline" not in k.lower() or not isinstance(v, dict):
            continue
        inner = v.get("timeline") if isinstance(v.get("timeline"), dict) else v
        got = inner.get("instructions")
        if got:
            insts = got
            break
    users, cursor = [], None
    for i in insts:
        for e in i.get("entries", []) or []:
            if str(e.get("entryId", "")).startswith("cursor-bottom"):
                cursor = e.get("content", {}).get("value")
            u = (e.get("content", {}).get("itemContent", {})
                  .get("user_results", {}).get("result"))
            if not u:
                continue
            users.append(flatten_user(u))
    return users, cursor


def flatten_user(u):
    """X keeps moving these fields between `legacy`, `core`, `verification` and the
    top level, so look everywhere rather than pinning one release's shape."""
    boxes = [u] + [v for v in u.values() if isinstance(v, dict)]

    def pick(*names):
        for b in boxes:
            for n in names:
                if b.get(n) not in (None, ""):
                    return b[n]
        return None

    def entities():
        for b in boxes:
            e = b.get("entities")
            if isinstance(e, dict):
                return e
        return {}

    ent = entities()
    site = ((ent.get("url") or {}).get("urls") or [{}])[0].get("expanded_url")
    bio_urls = [x.get("expanded_url") for x in ((ent.get("description") or {}).get("urls") or [])]
    vt = pick("verified_type", "verifiedType")
    return {
        "username": pick("screen_name", "screenName"),
        "name": pick("name"),
        "bio": pick("description", "bio") or "",
        "createdAt": pick("created_at", "createdAt"),
        "followers": pick("followers_count", "followersCount"),
        "blue": bool(pick("is_blue_verified", "isBlueVerified") or False),
        "verifiedType": vt,
        "gold": vt == "Business",
        "website": site,
        "bioUrls": [x for x in bio_urls if x],
    }


def main():
    qid = os.environ.get("RH_VF_QUERY_ID") or json.load(open(D / "bvf_query.json"))["queryId"]
    if not qid:
        print(__doc__)
        print("RH_VF_QUERY_ID is not set — run scan/find_query_id.sh first.")
        return 1
    handle = sys.argv[1] if len(sys.argv) > 1 else "RobinhoodCrypto"
    uid = SEEDS.get(handle, handle)
    max_pages = int(os.environ.get("MAX_PAGES", "5"))
    auth, ct0 = creds()
    out = D / f"verified_followers_{handle}.jsonl"
    seen, cursor = set(), None
    if out.exists():
        for line in open(out):
            try:
                seen.add(json.loads(line)["username"])
            except Exception:
                pass
    with open(out, "a") as f:
        for p in range(max_pages):
            try:
                j, rem = page(qid, uid, auth, ct0, cursor)
            except Exception as e:
                print(f"page {p+1} failed: {e}")
                break
            if os.environ.get("RH_VF_DEBUG"):
                describe(j)
            users, cursor = parse(j)
            new = 0
            for u in users:
                if u["username"] and u["username"] not in seen:
                    seen.add(u["username"])
                    f.write(json.dumps(u, ensure_ascii=False) + "\n")
                    new += 1
            print(f"page {p+1}: {len(users)} users, {new} new, blue={sum(1 for u in users if u['blue'])}, rl_left={rem}")
            if not users or not cursor:
                break
            time.sleep(2)
    print(f"\n{len(seen)} verified followers recorded in {out.name}")
    return 0


if __name__ == "__main__":
    import urllib.parse
    sys.exit(main())
