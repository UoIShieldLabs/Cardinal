# cardinal/desersvc — object-reconstruction backend (Python/Flask).
# The service code (svc.py) is mounted from the Kathara machine directory
# (desersvc/), so only the runtime is baked here.
FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends iproute2 curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir flask==3.0.3 gunicorn==23.0.0

# Kathara runs each machine's .startup script itself. Neutralize the base
# image's entrypoint/command so it does NOT launch a competing service as PID 1.
# PID 1 is just a keepalive; the .startup script owns all service launches.
ENTRYPOINT []
CMD ["tail", "-f", "/dev/null"]
