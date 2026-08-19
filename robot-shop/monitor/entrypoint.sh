#!/bin/bash
set -e

echo "=== Monitor/Collector Container Active ==="

# 1. Ensure output folders exist inside the mounted volume
mkdir -p /dataset/pcaps /dataset/logs /dataset/metrics

# 2. Start passive packet capture across network interfaces
tcpdump -i any -w /dataset/pcaps/capture_%Y%m%d_%H%M%S.pcap -G 300 -z gzip -s 0 &

# 3. Start host-side container resource telemetry collector
python3 /collect_metrics.py &

exec tail -f /dev/null