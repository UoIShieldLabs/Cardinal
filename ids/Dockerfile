FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    suricata \
    tcpdump \
    tshark \
    iproute2 \
    iputils-ping \
    net-tools \
    iptables \
    procps \
    dnsutils \
    curl \
    wget \
    nano \
    vim \
    less \
    jq \
    htop \
    && rm -rf /var/lib/apt/lists/*

# Create directories
RUN mkdir -p \
    /logs \
    /logs/suricata \
    /pcaps \
    /rules

# Custom rules
COPY rules/local.rules /rules/local.rules

# Startup script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]