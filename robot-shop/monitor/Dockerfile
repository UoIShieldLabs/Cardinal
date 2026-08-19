FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    tcpdump \
    tshark \
    iproute2 \
    iputils-ping \
    curl \
    jq \
    python3 \
    procps \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /dataset/pcaps /dataset/logs /dataset/metrics

# Ensure both files are copied into the container root
COPY collect_metrics.py /collect_metrics.py
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]