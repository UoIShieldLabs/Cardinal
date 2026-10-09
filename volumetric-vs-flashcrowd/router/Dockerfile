# Debian slim is used
FROM debian:stable-slim

# Update package lists - install networking utilities (all of this may not be needed but I can remove unecessary later)
# iproute2, iptables, tcpdump, iputils-ping are the tools I added - if you guys don't need them for your roles we can remove
RUN apt-get update && \
    apt-get install -y iproute2 iptables tcpdump iputils-ping && \
    rm -rf /var/lib/apt/lists/*

# tail keeps container alive indefinitely.
CMD ["tail", "-f", "/dev/null"]