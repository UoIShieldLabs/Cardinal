# cardinal/monitor — passive observer on both collision domains.
# Capture scripts are mounted from the Kathara machine directory (monitor/).
FROM debian:bookworm-slim

# tshark's non-interactive install (avoids the "should non-root capture?" prompt).
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        tcpdump tshark net-tools iproute2 \
    && rm -rf /var/lib/apt/lists/*

# Kathara runs each machine's .startup script itself. Neutralize the base
# image's entrypoint/command so it does NOT launch a competing service as PID 1
# (stock nginx grabbing :80, the mariadb entrypoint aborting, a python REPL...).
# PID 1 is just a keepalive; the .startup script owns all service launches.
ENTRYPOINT []
CMD ["tail", "-f", "/dev/null"]
