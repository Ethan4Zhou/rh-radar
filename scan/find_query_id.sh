#!/usr/bin/env bash
# Find the GraphQL query id X's own web app uses for the Verified Followers list.
#
# bird ships ids for Followers and Following but not BlueVerifiedFollowers, and the
# Followers id it caches currently 404s, which is why bird falls back to the REST
# endpoint that no longer carries the blue/gold flag.
#
# X publishes these ids in its own client bundles. This reads them the same way
# `bird query-ids --fresh` does, and prints whatever it finds.
#
# Run it yourself:   ! ~/Projects/rh-radar/scan/find_query_id.sh
set -uo pipefail
export NODE_USE_ENV_PROXY=1
OUT="$(cd "$(dirname "$0")/.." && pwd)/data/query_ids_found.txt"
exec > >(tee "$OUT") 2>&1        # keep the result on disk, terminal echo is unreliable
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36'
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT

echo "fetching x.com shell…"
curl -s -m 30 -A "$UA" https://x.com/ -o "$TMP/index.html" || { echo "could not reach x.com"; exit 1; }
echo "  $(wc -c < "$TMP/index.html") bytes"

grep -oE 'https://abs\.twimg\.com/responsive-web/client-web[^"'"'"' )]+\.js' "$TMP/index.html" \
  | sort -u > "$TMP/bundles.txt"
echo "bundles referenced inline: $(wc -l < "$TMP/bundles.txt")"

# the manifest lists every lazily-loaded chunk, including the profile ones
for m in $(grep -oE 'https://abs\.twimg\.com/responsive-web/client-web[^"'"'"' )]*(api|main|manifest)[^"'"'"' )]*\.js' "$TMP/index.html" | sort -u); do
  curl -s -m 30 -A "$UA" "$m" \
    | grep -oE '"https://abs\.twimg\.com/responsive-web/client-web[^"]+\.js"' \
    | tr -d '"' >> "$TMP/bundles.txt"
done
sort -u "$TMP/bundles.txt" -o "$TMP/bundles.txt"
echo "bundles to scan: $(wc -l < "$TMP/bundles.txt")"

FOUND=0
while read -r u; do
  [ -z "$u" ] && continue
  body=$(curl -s -m 25 -A "$UA" "$u") || continue
  case "$body" in
    *BlueVerifiedFollowers*|*VerifiedFollowers*)
      echo "--- hit: ${u##*/}"
      printf '%s' "$body" | grep -oE '\{queryId:"[A-Za-z0-9_-]{16,}",operationName:"[A-Za-z]*Followers[A-Za-z]*"' | sed 's/^/    /'
      printf '%s' "$body" | grep -oE 'operationName:"[A-Za-z]*Followers[A-Za-z]*",[^}]{0,120}queryId:"[A-Za-z0-9_-]{16,}"' | sed 's/^/    /'
      FOUND=1
      ;;
  esac
done < "$TMP/bundles.txt"

if [ "$FOUND" = 0 ]; then
  echo "no Verified Followers operation found in the bundles reachable from the logged-out shell"
  echo
  echo "fallback: every operationName/queryId pair seen, for manual picking"
  while read -r u; do
    [ -z "$u" ] && continue
    curl -s -m 25 -A "$UA" "$u" \
      | grep -oE 'queryId:"[A-Za-z0-9_-]{16,}",operationName:"[A-Za-z]+"' \
      | sed 's/^/    /'
  done < "$TMP/bundles.txt" | sort -u | head -80
fi
echo "done — saved to $OUT"
