# cardinal/proxy — plain nginx reverse proxy (the choke point).
# No WAF/ModSecurity in Phase 1; the config is mounted from the Kathara
# machine directory (proxy/etc/nginx/nginx.conf), not baked in here.
FROM nginx:stable-alpine

# Kathara drives the container via its own startup mechanism, so we need a
# shell and the `ip` tool to assign addresses in proxy.startup.
RUN apk add --no-cache iproute2 bash

# Kathara runs each machine's .startup script itself. Neutralize the base
# image's entrypoint/command so it does NOT launch a competing service as PID 1
# (stock nginx grabbing :80, the mariadb entrypoint aborting, a python REPL...).
# PID 1 is just a keepalive; the .startup script owns all service launches.
ENTRYPOINT []
CMD ["tail", "-f", "/dev/null"]
