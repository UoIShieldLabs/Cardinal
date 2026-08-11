#!/bin/bash
# ramp.sh - benign HTTP load generator for the flash-crowd container using Locust.
#
# Simulates Scenario A (steady baseline) followed by Scenario F
# (flash-crowd surge) from the paper[cite: 5]. Every request is driven by a simulated 
# user navigating the site, fetching sub-resources, and dwelling[cite: 10].
#
# Env vars (all optional, sensible defaults given):
#   TARGET_URL         URL to hit                (default: http://10.0.3.10)
#   BASELINE_SECONDS   duration of baseline phase(default: 120)
#   BASELINE_USERS     Locust users at baseline  (default: 10)
#   SURGE_SECONDS      duration of surge phase   (default: 60)
#   SURGE_USERS        Locust users during surge (default: 100)
#   SPAWN_RATE         Users spawned per second  (default: 10)
#   COOLDOWN_SECONDS   duration of cooldown phase(default: 60)
#   LOG_DIR            where to write phase markers (default: /scripts/logs)

set -uo pipefail

TARGET_URL="${TARGET_URL:-http://10.0.3.10}"
BASELINE_SECONDS="${BASELINE_SECONDS:-120}"
BASELINE_USERS="${BASELINE_USERS:-10}"
SURGE_SECONDS="${SURGE_SECONDS:-60}"
SURGE_USERS="${SURGE_USERS:-100}"
SPAWN_RATE="${SPAWN_RATE:-10}"
COOLDOWN_SECONDS="${COOLDOWN_SECONDS:-60}"
LOG_DIR="${LOG_DIR:-/scripts/logs}"

mkdir -p "$LOG_DIR"
TIMELINE="$LOG_DIR/timeline.log"

log_event() {
  echo "$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ) $1" | tee -a "$TIMELINE"
}

run_locust_phase() {
  local label="$1" duration="$2" users="$3" spawn_rate="$4"
  log_event "PHASE_START ${label} duration=${duration}s users=${users} spawn_rate=${spawn_rate}"
  
  # Run locust headlessly without the web UI, outputting stats to CSV files
  locust -f /scripts/locustfile.py --headless \
      -u "${users}" -r "${spawn_rate}" \
      --run-time "${duration}s" \
      --host "${TARGET_URL}" \
      --csv "$LOG_DIR/${label}_locust" > "$LOG_DIR/${label}.log" 2>&1
      
  log_event "PHASE_END ${label}"
}

log_event "RUN_START target=${TARGET_URL}"

# 1. Baseline Phase: Low user count, steady-state load
run_locust_phase "baseline" "$BASELINE_SECONDS" "$BASELINE_USERS" "$SPAWN_RATE"

# 2. Surge Phase: Sharp increase in concurrent users to simulate the flash crowd
run_locust_phase "surge" "$SURGE_SECONDS" "$SURGE_USERS" "$SPAWN_RATE"

# 3. Cooldown Phase: Back to baseline user levels
run_locust_phase "cooldown" "$COOLDOWN_SECONDS" "$BASELINE_USERS" "$SPAWN_RATE"

log_event "RUN_END"

# Keep the container alive after the ramp finishes so it can be re-triggered
# or inspected (docker exec) rather than exiting immediately[cite: 5].
tail -f /dev/null