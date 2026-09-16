# cardinal/locust — benign traffic generator with web UI.
# The locustfile is mounted from the Kathara machine directory (locust/).
FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends iproute2 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir locust==2.31.8

# Kathara runs each machine's .startup script itself. Neutralize the base
# image's entrypoint/command so it does NOT launch a competing service as PID 1
# (stock nginx grabbing :80, the mariadb entrypoint aborting, a python REPL...).
# PID 1 is just a keepalive; the .startup script owns all service launches.
ENTRYPOINT []
CMD ["tail", "-f", "/dev/null"]
