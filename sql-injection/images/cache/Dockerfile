# cardinal/cache — Redis (session + object cache for the webapp).
# Kathara drives the node via cache.startup, so we only guarantee the server
# and `ip` are present and neutralize the base entrypoint.
FROM redis:7-alpine

RUN apk add --no-cache iproute2 bash

# Kathara runs each machine's .startup script itself. Neutralize the base
# image's entrypoint/command so it does NOT launch a competing service as PID 1.
# PID 1 is just a keepalive; the .startup script owns all service launches.
ENTRYPOINT []
CMD ["tail", "-f", "/dev/null"]
