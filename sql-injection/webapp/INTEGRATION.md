# Integrating webapp into the sql-injection topology

The webapp (Flask, system-under-test) is self-contained in this build context
(`build: ./webapp`). A few points where it meets the surrounding topology —
flagged so the owners of the sibling services can wire them up:

## Database engine — action needed
The webapp targets **MySQL / MariaDB** via PyMySQL (`app/db.py`), per the
Tasklist-1 spec ("db: MySQL / MariaDB"). The current `sql-injection/db/` stub is
`postgres:15-alpine`. Pick one:

- **Recommended:** change `db/` to `mariadb:11` (webapp works unchanged, already
  tested — SQLi concat/param paths, UNION exfil, auth bypass all verified).
- Or port `app/db.py` to `psycopg` (Postgres param style `%s` is the same, but
  the concat SQLi strings and the `init.sql` schema would need a Postgres pass).

## Service wiring
The webapp reads its dependencies from env, defaulting to the compose service
names — no changes needed to hostnames, but **the `webapp` service in
`docker-compose.yml` currently passes no `environment:`**, and the `db` stub
sets `POSTGRES_PASSWORD: shoppassword` (user `postgres`). Add to the webapp
service (adjust to the chosen DB):

```yaml
  webapp:
    build: ./webapp
    environment:
      DB_HOST: db
      DB_USER: portal
      DB_PASSWORD: portal
      DB_NAME: portal
      REDIS_HOST: cache
      DESER_SVC_URL: http://deser-svc:8090/reconstruct
      SQL_IMPL: concat        # concat (vulnerable) | param (safe)
      XSS_ENCODING: raw        # raw (vulnerable) | escape (safe)
      DESER_MODE: unsafe       # unsafe | safe
```

## Data-tier seed
`webapp/db/init.sql` (schema + seed) is included here for reference and for the
standalone dev compose. In this topology the seed belongs in the data tier —
mount/copy it into `sql-injection/db/` so the `db` container initialises with it.

## Network path
`webapp` is on `app_net` (172.31.0.10); `db`/`cache` are on `data_net`. The
webapp→db hop is therefore **routed through `core-router`**, exactly as the
segmented design intends — connectivity depends on core-router forwarding being
up, not on attaching webapp to the data segment.

## Ports
The webapp listens on **8080** (gunicorn, plaintext HTTP). `proxy-waf`
(172.30.0.10) should reverse-proxy to `webapp:8080`.

See `README.md` for the full route/toggle/attack-surface reference.
