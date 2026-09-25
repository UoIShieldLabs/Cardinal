#!/bin/bash
# Cardinal Phase 1 — passive traffic capture on both collision domains.
# Writes a per-interface pcap and tails live HTTP requests/responses so you can
# watch benign (Locust) and attack (sqlmap/curl) traffic on the same endpoints.

CAPTURE_DIR="/captures"
LIVE_LOG="$CAPTURE_DIR/http_live.log"
mkdir -p "$CAPTURE_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Kathara runs this script via a separate exec, so its stdout does NOT reach
# `docker logs` or `kathara connect`. We therefore mirror the live HTTP view to
# a file: to watch traffic, run `kathara connect monitor` then
#   tail -f /captures/http_live.log
echo "[*] Capturing on eth0 (edge-net) and eth1 (app-net). PCAPs + live log in $CAPTURE_DIR/" | tee "$LIVE_LOG"

# Full packet capture per interface (raw bytes — the L1 view).
tcpdump -i eth0 -w "$CAPTURE_DIR/edge-net_${TIMESTAMP}.pcap" -U >/dev/null 2>&1 &
EDGE_PID=$!
tcpdump -i eth1 -w "$CAPTURE_DIR/app-net_${TIMESTAMP}.pcap" -U >/dev/null 2>&1 &
APP_PID=$!

# DB query log (the L1.5 structural cut): the db node writes every statement it
# received to /shared/db_query.log. Mirror it into the capture set and interleave
# it into the live view, tagged [DBQUERY], so you can watch each HTTP request
# land as a SQL statement at the database — where the concat vs param difference
# (and the injected clause) is plainly visible. Passive: we only read the file.
( tail -F -n +1 /shared/db_query.log 2>/dev/null \
    | stdbuf -oL grep --line-buffered -iE 'select|insert|update|delete|union|drop' \
    | stdbuf -oL sed 's/^/[DBQUERY]  /' \
    | tee -a "$CAPTURE_DIR/db_query.log" >> "$LIVE_LOG" ) &
DBLOG_PID=$!

trap "kill $EDGE_PID $APP_PID $DBLOG_PID 2>/dev/null" EXIT

# Live structured HTTP view across both interfaces, line-buffered and tee'd to
# the log file (and stdout, for `kathara connect` sessions that run this).
stdbuf -oL -eL tshark -i eth0 -i eth1 \
    -l \
    -Y "http.request or http.response" \
    -T fields \
    -e frame.time_relative \
    -e ip.src \
    -e ip.dst \
    -e http.request.method \
    -e http.request.uri \
    -e http.response.code \
    -E separator='  |  ' 2>/dev/null | tee -a "$LIVE_LOG"

# --- Fallback if tshark misbehaves in the container ---
# tcpdump -i any -l -A -s 0 'tcp port 80' | grep --line-buffered -E '(GET|POST|HTTP/)' | tee -a "$LIVE_LOG"

wait
