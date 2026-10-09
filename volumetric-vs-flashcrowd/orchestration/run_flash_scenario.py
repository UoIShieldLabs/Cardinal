#!/usr/bin/env python3
"""
run_flash_scenario.py

Host-side orchestrator for benign flash-crowd traffic (Scenario A -> F in
the accompanying paper). Runs OUTSIDE docker, on the host machine, exactly
as the paper's run_scenario.py does - this keeps the experimental harness
out of the network being observed.

What it does:
  1. Lets the steady-state `flash` container run its baseline load (see
     flash-crowd/ramp.sh).
  2. At the configured surge onset, launches N short-lived ephemeral
     containers on the external_net bridge - each is a fresh source IP
     issuing ordinary curl GETs against the victim, widening the source
     population the way a real flash crowd does.
  3. Tears the ephemeral containers down at surge end.
  4. Writes a ground-truth timeline (JSON lines) with UTC timestamps for
     every phase transition, so detector verdicts can be scored against
     ground truth afterward.

This only ever issues real, completed HTTP GET requests. No packet
crafting, spoofing, or raw sockets are used anywhere in this script.

Requirements on host:
    pip install docker

Usage:
    python3 run_flash_scenario.py \
        --network newnetworksim_external_net \
        --target http://10.0.3.10/ \
        --surge-containers 12 \
        --baseline-seconds 60 \
        --surge-seconds 60 \
        --cooldown-seconds 60
"""
import argparse
import json
import time
import uuid
from datetime import datetime, timezone

try:
    import docker
except ImportError:
    raise SystemExit("Install the docker SDK first: pip install docker")


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class Timeline:
    def __init__(self, path):
        self.path = path
        self._fh = open(path, "a", buffering=1)

    def event(self, name, **fields):
        record = {"ts": now_iso(), "event": name, **fields}
        line = json.dumps(record)
        print(line)
        self._fh.write(line + "\n")

    def close(self):
        self._fh.close()


def launch_burst_container(client, network, target, run_seconds, name):
    """
    Launch one short-lived benign client container. Each gets its own IP
    on the bridge network (dynamic allocation), issues a steady stream of
    real curl GETs for run_seconds, then exits and is removed.
    """
    cmd = (
        f"sh -c 'end=$(( $(date +%s) + {run_seconds} )); "
        f"while [ $(date +%s) -lt $end ]; do "
        f"curl -s -o /dev/null -w \"%{{http_code}}\\n\" {target}; sleep 0.2; "
        f"done'"
    )
    container = client.containers.run(
        image="curlimages/curl:latest",
        command=cmd,
        name=name,
        network=network,
        detach=True,
        remove=False,  # we reap explicitly so we can collect exit status
    )
    return container


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--network", required=True,
                     help="Docker network name to attach burst containers to "
                          "(usually '<project>_external_net')")
    ap.add_argument("--target", default="http://10.0.3.10/",
                     help="URL of the victim service")
    ap.add_argument("--surge-containers", type=int, default=12,
                     help="Number of ephemeral benign client containers to "
                          "launch during the surge window")
    ap.add_argument("--baseline-seconds", type=int, default=120,
                     help="Seconds to wait before the surge (flash-crowd "
                          "container's own ramp.sh handles baseline load)")
    ap.add_argument("--surge-seconds", type=int, default=60,
                     help="Duration of the surge window")
    ap.add_argument("--cooldown-seconds", type=int, default=60,
                     help="Seconds to wait after the surge before exiting")
    ap.add_argument("--timeline-out", default="scenario-logs/flash_timeline.jsonl",
                     help="Path to write the ground-truth timeline")
    args = ap.parse_args()

    client = docker.from_env()
    timeline = Timeline(args.timeline_out)
    run_id = uuid.uuid4().hex[:8]

    timeline.event("scenario_start", scenario="flash_crowd", run_id=run_id,
                    target=args.target, surge_containers=args.surge_containers)

    timeline.event("baseline_start", run_id=run_id)
    time.sleep(args.baseline_seconds)
    timeline.event("baseline_end", run_id=run_id)

    timeline.event("surge_onset", run_id=run_id,
                    containers=args.surge_containers)

    burst_containers = []
    for i in range(args.surge_containers):
        name = f"cli-burst-{run_id}-{i}"
        try:
            c = launch_burst_container(
                client, args.network, args.target, args.surge_seconds, name
            )
            burst_containers.append(c)
            timeline.event("burst_container_launched", run_id=run_id, container_name=name)
        except Exception as exc:
            timeline.event("burst_container_error", run_id=run_id, container_name=name,
                            error=str(exc))

    # Wait for the surge window to elapse, then reap the burst containers.
    time.sleep(args.surge_seconds + 2)

    for c in burst_containers:
        try:
            c.reload()
            status = c.status
            c.remove(force=True)
            timeline.event("burst_container_removed", run_id=run_id,
                           container_name=c.name, final_status=status)
        except Exception as exc:
            timeline.event("burst_container_cleanup_error", run_id=run_id,
                            container_name=c.name, error=str(exc))

    timeline.event("surge_end", run_id=run_id)

    timeline.event("cooldown_start", run_id=run_id)
    time.sleep(args.cooldown_seconds)
    timeline.event("cooldown_end", run_id=run_id)

    timeline.event("scenario_end", run_id=run_id)
    timeline.close()


if __name__ == "__main__":
    main()
