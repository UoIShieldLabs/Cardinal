# Flash-crowd benign traffic generator

Implements Scenario A (steady baseline) -> Scenario F (flash-crowd surge)
from the paper, as the "legitimate surge" control condition for evaluating
the SYN-flood detectors. Every request is a real, completed HTTP GET
against nginx - there is no packet crafting, spoofing, or raw sockets
anywhere in this container.

## What runs automatically (in-container)

`ramp.sh` runs three phases against `TARGET_URL` (defaults to the
`victim` container at `http://10.0.3.10/`):

1. **baseline** - low thread/connection count, steady-state load
   (`BASELINE_THREADS` / `BASELINE_CONNS` / `BASELINE_SECONDS`)
2. **surge** - a sharp increase in threads and concurrent connections,
   simulating a real traffic spike (`SURGE_THREADS` / `SURGE_CONNS` /
   `SURGE_SECONDS`)
3. **cooldown** - back to baseline levels (`COOLDOWN_SECONDS`)

Phase transitions and `wrk` output are written to `/scripts/logs`, which
is bind-mounted to `./scenario-logs` on the host via docker-compose, so
you can align detector alerts against ground truth afterward.

Tune via the `environment:` block in `docker-compose.yml`, or override at
runtime:

```
docker compose run -e SURGE_CONNS=200 -e SURGE_SECONDS=90 flash
```

## Widening the source population (host-side)

A single container only has one source IP. To simulate a real flash
crowd - many distinct residential-looking sources arriving at once,
which is the harder case for entropy/threshold-based detectors - use
`orchestration/run_flash_scenario.py` from the **host**, not from inside
a container:

```bash
pip install docker
cd orchestration
python3 run_flash_scenario.py \
  --network newnetworksim_external_net \
  --target http://10.0.3.10/ \
  --surge-containers 12 \
  --baseline-seconds 120 \
  --surge-seconds 60 \
  --cooldown-seconds 60
```

This spins up N short-lived `curlimages/curl` containers on the same
bridge network as `flash`/`ddos`, each with its own dynamically-assigned
IP, each issuing plain `curl` GETs on a loop for the surge duration, then
removes them. It writes a JSON-lines ground-truth timeline to
`scenario-logs/flash_timeline.jsonl` marking baseline/surge/cooldown
onset and every container's lifecycle - the same role `run_scenario.py`
plays in the paper's harness.

Find your actual network name with:

```bash
docker network ls | grep external_net
```

(Compose usually prefixes it with the project/folder name, e.g.
`newnetworksim_external_net`.)
