FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies and add Zeek repository
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    ca-certificates \
    && echo 'deb http://download.opensuse.org/repositories/security:/zeek/xUbuntu_22.04/ /' | tee /etc/apt/sources.list.d/security:zeek.list \
    && curl -fsSL https://download.opensuse.org/repositories/security:/zeek/xUbuntu_22.04/Release.key | gpg --dearmor | tee /etc/apt/trusted.gpg.d/security_zeek.gpg

# Install IDS sensors and diagnostic tools
RUN apt-get update && apt-get install -y \
    suricata \
    zeek \
    tcpdump \
    tshark \
    iproute2 \
    iputils-ping \
    net-tools \
    iptables \
    procps \
    dnsutils \
    wget \
    nano \
    vim \
    less \
    jq \
    htop \
    && rm -rf /var/lib/apt/lists/*

# Add Zeek binaries to system PATH
ENV PATH="/opt/zeek/bin:${PATH}"

# Create required directories
RUN mkdir -p \
    /logs \
    /logs/suricata \
    /pcaps \
    /rules \
    /etc/suricata/rules

# Copy custom rules to both standard locations for compatibility
COPY rules/local.rules /rules/local.rules
COPY rules/local.rules /etc/suricata/rules/local.rules

# Startup script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]