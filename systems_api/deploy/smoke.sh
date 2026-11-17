#!/bin/sh
# Smoke test for a running SystemsAPI web instance.
#
#   deploy/smoke.sh BASE_URL        (for example http://127.0.0.1:6543)
#
# Prints one "ok <check>" or "FAIL <check>" line per check and exits 1 on the first failure.
# Read-only: it sends GET requests only, and never calls an endpoint that filters
# "name ILIKE" (/nearest_*?name=, /search?name=). On a short term those hold a waitress
# thread for up to the galmap statement_timeout.
set -u

MAX_TIME=10
HEATMAP_MIN_BYTES=1000000

if [ "$#" -ne 1 ] || [ -z "$1" ]; then
    echo "usage: $0 BASE_URL" >&2
    exit 2
fi
BASE_URL=${1%/}

BODY=$(mktemp) || exit 1
trap 'rm -f "$BODY"' EXIT

# fetch PATH: GET BASE_URL/PATH into $BODY and set $CODE to the HTTP status (000 on a curl error).
fetch() {
    CODE=$(curl -s -o "$BODY" -w '%{http_code}' --max-time "$MAX_TIME" "$BASE_URL$1") || CODE=000
}

ok() {
    echo "ok $1"
}

fail() {
    echo "FAIL $1: $2"
    exit 1
}

# expect_status PATH STATUS: fetch PATH and fail unless it answers STATUS.
expect_status() {
    fetch "$1"
    [ "$CODE" = "$2" ] || fail "$1" "HTTP $CODE, expected $2"
}

check='/mecha?name=Sol&fast=1'
expect_status "$check" 200
grep -q '"Perfect match"' "$BODY" || fail "$check" 'body lacks "Perfect match"'
ok "$check"

check='/typeahead?term=Sol'
expect_status "$check" 200
first=$(dd if="$BODY" bs=1 count=1 2>/dev/null)
[ "$first" = "[" ] || fail "$check" 'body does not start with ['
ok "$check"

for check in '/landmark?name=Sol' '/procname?name=Sol' '/api/stats'; do
    expect_status "$check" 200
    ok "$check"
done

check='/heatmap'
expect_status "$check" 200
size=$(wc -c <"$BODY" | tr -d ' ')
[ "$size" -gt "$HEATMAP_MIN_BYTES" ] || fail "$check" "body is $size bytes, expected over $HEATMAP_MIN_BYTES"
ok "$check"

check='/_debug_toolbar/'
expect_status "$check" 404
ok "$check"

check='/'
expect_status "$check" 200
ok "$check"
