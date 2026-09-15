# Cardinal — webapp (system under test)

The small internal staff portal that carries every attack scenario and its
benign twin. Login, directory search, profiles, comments, and settings
import/export — ordinary features, each one an attack surface. Everything runs
over **plaintext HTTP** by design (see the tasklist "Why no TLS").

## Attack surfaces & toggles

Every surface is real but **toggleable**. Each toggle has a per-deployment
default (env var) and a per-request override (query arg), so one deployment can
serve the vulnerable path and its byte-identical benign twin on the same route.

| Scenario | Route(s) | Toggle | Values (default first) | Per-request arg |
|---|---|---|---|---|
| **SQL injection** | `/login`, `/search` | `SQL_IMPL` | `concat` (vulnerable) / `param` (safe) | `?impl=` |
| **XSS** (reflected + stored) | `/search`, `/profile`, `/records/<id>` | `XSS_ENCODING` | `raw` (vulnerable) / `escape` (safe) | `?enc=` |
| **Insecure deserialization** | `/settings/import` | `DESER_MODE` | `unsafe` / `safe` | `?deser=` |

- **SQL**: `app/db.py` holds both a string-concatenated query and a
  parameterized query for search and login; the toggle picks which runs.
- **XSS**: `app/encoding.py` provides `enc(value, context)` for the four sinks —
  `html`, `attr`, `js`, `uri`. Templates render the same value into all four, so
  the *same bytes* are inert in one context and executable in another. Jinja
  autoescaping is off; `enc` is the single encoding authority.
- **Deserialization**: `/settings/export` emits a benign pickled blob; `/settings/import`
  forwards the raw bytes to `deser-svc` for reconstruction (the webapp never
  deserializes the object itself). Sessions are also stored as pickled blobs in
  Redis (`app/session.py`) — a realistic second vector and benign noise.

`GET /state` reports the effective toggles for a request (handy for the capture
harness to label the experimental condition).

## JSON API (`/api/*`)

A scriptable mirror of the HTML app for the Locust benign generator and the
attacker tooling: JSON in/out, same SQL paths, same object-import forwarding,
and the **same toggles** (`?impl` / `?enc` / `?deser`). Auth is a bearer token
(the session id) returned by `POST /api/login`; send it as
`Authorization: Bearer <token>` (or `?token=`).

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/state` | effective toggles for this request |
| POST | `/api/login` | `{username,password}` → `{token,user,executed_sql}` (SQLi surface) |
| POST | `/api/logout` | end session |
| GET | `/api/directory?q=` | search (SQLi surface) / browse; reflects `query` |
| GET/PUT | `/api/profile` | read / update own profile (stored values) |
| GET/POST | `/api/records/<id>` | record + comments; POST a comment (stored values) |
| GET | `/api/settings/export` | benign serialized blob |
| POST | `/api/settings/import` | forwards bytes to deser-svc (deser surface) |

```bash
# SQLi login bypass via JSON:
curl -s -X POST 'localhost:8080/api/login?impl=concat' \
  -H 'Content-Type: application/json' \
  -d '{"username":"'"'"' OR '"'"'1'"'"'='"'"'1'"'"' #","password":"x"}'
# same on ?impl=param → 401
```

Note: a JSON API has no HTML rendering context, so the four XSS *sinks* stay in
the HTML app; the API faithfully reflects/stores the raw payloads (and flags
`reflected`) so a downstream HTML client still receives them.

## Run locally

```bash
docker compose -f ../docker-compose.dev.yml up --build
# portal at http://localhost:8080  (login: alice / alicepw)
```

This dev compose stands up `webapp + db + cache + a stub deser-svc` only — it is
**not** the network-faithful VLAN/proxy/monitor topology (that's the networking
task's Compose/ContainerLab file). The stub deser-svc lives in
`../deser-svc-stub/` and must not be shipped as the real backend.

## Quick manual checks

```
# SQLi (concatenated path) — auth bypass:
#   username:  ' OR '1'='1' --      password: anything     with ?impl=concat
# Same input on ?impl=param fails cleanly.

# Reflected XSS — same term, different sink outcomes:
#   /search?q=<script>alert(1)</script>&enc=raw
#   /search?q=<script>alert(1)</script>&enc=escape   (neutralised)

# Deserialization — export a blob, re-import it:
#   GET /settings/export  ->  paste into /settings/import
```

## Layout

```
webapp/
  wsgi.py            entrypoint (gunicorn / python)
  app/
    __init__.py      app factory, session + enc wiring
    config.py        toggles (env default + per-request override)
    db.py            two SQL paths (concat / param)
    encoding.py      contextual output encoding (the four XSS sinks)
    session.py       pickled sessions in Redis
    routes/          auth, directory, profile, comments, settings, core
    templates/       Jinja templates (autoescape off; enc owns encoding)
  db/init.sql        schema + seed
  Dockerfile
```
