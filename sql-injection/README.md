# Cardinal — Phase 1 (SQL injection, Kathara lab)

A minimal, self-contained [Kathara](https://www.kathara.org/) lab for the SQL
injection scenario: a vulnerable staff-portal webapp behind an nginx choke
point, a seeded MariaDB, a Locust benign-traffic generator, and an attacker node
with sqlmap — all observed by a passive monitor.

This is the trimmed Phase-1 slice of the larger Cardinal testbed design (SQLi +
XSS + insecure-deserialization under live benign traffic). The full segmented
topology (WAF, IDS, XSS/deser sinks, firewall/router) is deferred to later phases.

> **New here? See [`TUTORIAL.md`](TUTORIAL.md)** for a full walkthrough — start it,
> browse the portal, run the attacks (automated *and* by hand in the browser),
> and find the captured pcaps/dumps.

## Topology

Two collision domains; only `proxy` bridges them, so it is the sole path from
the external tier to the application — the choke point is enforced by topology.

```
        [Host browser :8089]
               │
   ===== edgenet (172.30.0.0/24) =====
      │         │          │         │
   locust    attacker    proxy    monitor
    .20        .30        .10       .99
                           │         │
   ===== appnet (172.31.0.0/24) =====
                 │         │         │
              webapp      db      monitor
               .20        .30       .99
```

| Node     | edgenet     | appnet      | Role                              |
|----------|-------------|-------------|-----------------------------------|
| proxy    | 172.30.0.10 | 172.31.0.10 | nginx reverse proxy (choke point) |
| locust   | 172.30.0.20 | —           | benign traffic (web UI :8089)     |
| attacker | 172.30.0.30 | —           | sqlmap / curl                     |
| webapp   | —           | 172.31.0.20 | Flask app (gunicorn :5000)        |
| db       | —           | 172.31.0.30 | MariaDB (seeded `portal` DB)      |
| monitor  | 172.30.0.99 | 172.31.0.99 | passive tcpdump/tshark capture    |

## Prerequisites

- Docker Desktop running.
- Kathara: `pip install kathara` (or `brew install kathara`). See
  <https://www.kathara.org/download.html>.

## Run

```bash
cd sql-injection
./build-images.sh      # build the 6 cardinal/* images (once, or after image changes)
kathara lstart         # boot all 6 nodes (~30s; db seeds on first boot)
./expose-ui.sh         # publish portal -> :8080 and Locust UI -> :8089 (Docker Desktop)
```

### Use it

0. **Browse the portal** — after `./expose-ui.sh`, open <http://localhost:8080>
   (served through the proxy). Log in as `alice` / `alicepw`, search the directory,
   view profiles. This is the same app the attacks target.
1. **Benign traffic** — open <http://localhost:8089> (Locust UI). Set ~10 users,
   spawn rate 2, Start. Requests should succeed with no failures.
2. **Watch traffic** — `kathara connect monitor`, then `tail -f /captures/http_live.log`
   for a live HTTP view of both segments. Full pcaps are written to `/captures/`
   (`edge-net_*.pcap`, `app-net_*.pcap`).
3. **Attack** — in another terminal:
   ```bash
   kathara connect attacker
   /scripts/run_sqli.sh          # automated sqlmap (dumps the DB once injection is found)
   /scripts/manual_payloads.sh   # hand-crafted payloads (auth bypass, UNION, error, time, stacked)
   ```
4. **Observe** — the monitor shows the attacker's injections interleaved with
   Locust's benign requests on the *same* `/search` and `/login` endpoints.

### Manual checks (from the attacker node)

```bash
curl "http://172.30.0.10/search?q=Alice"                 # benign: seeded results
curl -G http://172.30.0.10/search --data-urlencode "q=' OR '1'='1"   # injection: all rows
curl -G http://172.30.0.10/search --data-urlencode "q=Alice&impl=param"  # safe path (same route)
```

The webapp defaults to the vulnerable **concat** path (`SQL_MODE=concat`). Any
request can flip to the safe path per-request with `?impl=param`, so an attack
and its benign twin traverse the identical route — only the parse tree differs.

### Stop / reset

```bash
kathara lclean          # tear down; next lstart re-seeds a clean DB
```

### Extract pcaps (while running)

```bash
docker cp $(kathara list | grep monitor | awk '{print $NF}'):/captures/ ./pcaps/
```

## Notes & gotchas

- **Web UIs on the host.** Kathara collision domains are pure L2 and, on Docker
  Desktop, `machine[port]` does not actually publish to the host. So `lab.conf`
  gives the `proxy` and `locust` a default-bridge NIC (`…[bridged]="true"`) and
  **`./expose-ui.sh`** runs published `socat` sidecars forwarding the host ports to
  their bridge IPs: portal (via proxy) on `:8080` and Locust on `:8089`. Run it
  after `kathara lstart`; stop with `docker rm -f cardinal-webapp-ui cardinal-locust-ui`.
  (On native-Linux Kathara you can instead use `proxy[port]`/`locust[port]` and skip
  the helper.) The portal is only reachable *inside* the lab otherwise — attacks
  target the proxy's in-lab IP `172.30.0.10`, not a host URL.
- **DB init.** Kathara does not run the mariadb image entrypoint, so `db.startup`
  initialises the data dir, starts `mariadbd`, and imports `/seed.sql` itself.
  The seed also creates the `portal` app user (the entrypoint normally would).
- **App user password** is `portal`; seeded logins are `alice`/`alicepw`,
  `bob`/`bobpw`, `carol`/`carolpw`.
- **UNION arity.** The directory search selects **7** columns
  (`id,name,title,department,email,phone,location`) — UNION payloads must match.
- **Choke point.** `webapp` and `db` share app-net (direct hop, no routing); the
  edge nodes can reach the app *only* through the proxy.

## Layout

```
sql-injection/
├── lab.conf / lab.dep          # Kathara topology + boot order
├── build-images.sh             # builds cardinal/{proxy,webapp,db,locust,attacker,monitor}
├── expose-ui.sh                # publishes the Locust UI to the host (socat sidecar)
├── *.startup                   # per-node boot scripts (IPs + service launch)
├── images/*/Dockerfile         # custom image definitions
├── proxy/etc/nginx/nginx.conf  # reverse proxy → webapp:5000
├── webapp/app/                 # Flask app (app.py + templates) — mounted at /app
├── db/seed.sql                 # schema + seed (+ portal user) — mounted at /seed.sql
├── locust/locustfile.py        # benign employee workload
├── attacker/scripts/           # run_sqli.sh, manual_payloads.sh
└── monitor/scripts/capture.sh  # tcpdump pcaps + live tshark
```
