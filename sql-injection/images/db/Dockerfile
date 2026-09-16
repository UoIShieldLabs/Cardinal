# cardinal/db — MariaDB.
# Kathara bypasses the official image entrypoint, so db.startup starts
# `mariadbd` and imports /seed.sql by hand (see db.startup). This image just
# guarantees the server + client binaries and `ip` are present.
FROM mariadb:11

RUN apt-get update \
    && apt-get install -y --no-install-recommends iproute2 \
    && rm -rf /var/lib/apt/lists/*

# Kathara runs each machine's .startup script itself. Neutralize the base
# image's entrypoint/command so it does NOT launch a competing service as PID 1
# (stock nginx grabbing :80, the mariadb entrypoint aborting, a python REPL...).
# PID 1 is just a keepalive; the .startup script owns all service launches.
ENTRYPOINT []
CMD ["tail", "-f", "/dev/null"]
