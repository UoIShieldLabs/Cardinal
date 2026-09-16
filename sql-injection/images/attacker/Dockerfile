# cardinal/attacker — sqlmap + curl for the SQLi scenario.
# Attack scripts are mounted from the Kathara machine directory (attacker/).
FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends iproute2 curl git \
    && rm -rf /var/lib/apt/lists/*

# sqlmap from pip gives us a stable `sqlmap` on PATH.
RUN pip install --no-cache-dir sqlmap==1.8.9

# Kathara runs each machine's .startup script itself. Neutralize the base
# image's entrypoint/command so it does NOT launch a competing service as PID 1
# (stock nginx grabbing :80, the mariadb entrypoint aborting, a python REPL...).
# PID 1 is just a keepalive; the .startup script owns all service launches.
ENTRYPOINT []
CMD ["tail", "-f", "/dev/null"]
