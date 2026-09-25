# Advanced SQL injection techniques — Cardinal SQLi lab

Beyond the basic auth-bypass / simple-UNION cases, this documents the more
sophisticated SQLi techniques we exercised against the lab, what each one
demonstrates, and the **results actually observed** against the running Kathará
environment (MariaDB 11.8, `portal` DB, concatenated `/search` and `/login`).

Run them yourself from the attacker node:

```bash
kathara connect attacker
/scripts/advanced_payloads.sh        # all technique classes, one shot
python3 /scripts/blind_extract.py    # automated blind password recovery
/scripts/run_sqli_advanced.sh        # aggressive sqlmap (enum, tampers, file-read)
```

Attacked query shapes:
- `/search` (concat): `... FROM directory WHERE name LIKE '%<q>%' ...` — 7 columns, injection sits **inside** a `LIKE '%...%'` string.
- `/login` (concat): `... FROM users WHERE username='<u>' AND password='<p>'` — 5 columns.

## Techniques and observed results

| # | Technique | Payload idea | Observed result |
|---|---|---|---|
| 1 | **Schema enumeration** (`information_schema`) | `UNION SELECT ...FROM information_schema.tables/columns` | ✅ Recovered version `11.8.9-MariaDB`, user `portal@%`, db `portal`, all tables (`users, directory, comments`) and every column. |
| 1d | **Mass exfiltration** (`GROUP_CONCAT`) | `GROUP_CONCAT(username,0x3a,password)` | ✅ Dumped **all** creds in one row, bypassing the `LIMIT 50` (concatenates rows into one value). |
| 2 | **Boolean-based blind** | `Alice%' AND <cond>-- -` (row returns ⇔ cond true) | ✅ Clean true/false oracle; per-character inference confirmed. |
| 3 | **Time-based blind** | `IF(<cond>,SLEEP(3),0)` | ✅ **0.004 s** (false) vs **3.008 s** (true) — unambiguous signal with zero output. |
| 4 | **WAF / signature evasion** | `UNION/**/SELECT`, `uNiOn sElEcT`, `/*!50000UNION*/` | ✅ All three dumped creds. Same **structure**, obfuscated **bytes** — defeats a string filter, not a parser. |
| 5 | **Privilege / file read** | `LOAD_FILE('/etc/passwd')`, `user_privileges` | ⛔ **Blocked** — `portal@%` holds only `USAGE` globally; `LOAD_FILE` → `NULL`. Boundary confirmed. |
| 6a | **Stacked queries** | `'; DROP TABLE comments-- -` | ⛔ **Blocked** — PyMySQL sends a single statement → HTTP 500, table intact. |
| 6b | **Error-based extraction** | `extractvalue(1,concat(0x7e,(SELECT ...)))` | ⛔ **No leak** — payload reaches the DB (HTTP 500) but the app returns a generic error with no SQL text. |
| 7 | **Safe-path control** | any of the above with `?impl=param` | ✅ **0 rows** — parameterization binds the payload as a literal; identical input, neutralized. |

### Highlight — fully automated blind extraction
`blind_extract.py` recovers a secret with **no data and no errors** ever returned
by the app — only the yes/no "did the Alice row come back?" signal, binary-searching
each character's ASCII value (~7 requests/char). Observed:

```
[+] recovered: alice : 'alicepw'   in 0.2s
```

This is the sophisticated case that matters: even a perfectly silent app leaks its
entire database through a boolean side channel.

## Why this matters for the Cardinal thesis (the "low rung")

The research claim is that SQLi is catchable on the **low rung** — from the query's
*structure*, not its raw characters. Section 4 is the direct test:

- `UNION SELECT`, `uNiOn sElEcT`, and `/*!50000UNION*/` are **byte-different** — a
  character-level ("bad word") detector that greps for `UNION SELECT` misses two of
  the three.
- But all three parse to **the same structure**: a query with an appended `UNION`.
  A detector that first *parses* the query (or reads the DB query log) catches all
  of them identically.

So these obfuscation techniques don't move SQLi *up* the ladder — they only defeat
the lowest rung (raw text), confirming that the honest place to detect SQLi is the
structural cut. This is exactly the signal the monitor should capture via the DB
query log (a current gap — see the milestone audit).

## Defenses observed to hold
- **Parameterization** (`?impl=param`) neutralizes every payload.
- **Least privilege** on the DB account blocks `LOAD_FILE`/file access.
- **Single-statement driver** (PyMySQL) blocks stacked queries.
- **Hidden DB errors** defeat error-based *extraction* (UNION/blind still work).

## The structural cut is now captured (DB query log)
The `db` node logs every statement it receives to `/shared/db_query.log`, which
the passive `monitor` ingests into `/captures/db_query.log` (tagged `[DBQUERY]`).
This makes the section-4 argument concrete — the same three evasion payloads, as
the database received them:

```
... WHERE name LIKE '%zzz' UNION/**/SELECT ...FROM users-- -%' ...
... WHERE name LIKE '%zzz' uNiOn sElEcT ...FROM users-- -%' ...
... WHERE name LIKE '%zzz' /*!50000UNION*/ /*!50000SELECT*/ ...FROM users-- -%' ...
```

Byte-different, but all three carry a `UNION` at the structural layer — a text
filter misses two, a parser catches all three. And the concat vs param twin is
visible here too: concat logs `'%x' OR '1'='1%'` (extra clause) while param logs
`'%x\' OR \'1\'=\'1%'` (escaped literal — inert). This is the syntactic-cut
signal the detector experiments consume.

## Suggested next steps
- When the **WAF (ModSecurity/CRS)** lands, re-run section 4 to measure which
  evasions bypass CRS — a concrete signature-vs-structure comparison.
- Extend blind extraction to the **time channel** (`--mode time`) for the case
  where even the boolean/row signal is removed.
