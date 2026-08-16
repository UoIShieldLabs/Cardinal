#!/bin/bash

# Ensure required log and runtime directories exist
mkdir -p /logs/suricata /var/log/suricata /pcaps /rules

echo "=== IDS Container Started ==="

ip addr
echo
ip route
echo

# Add cross-subnet route back to flash via router
ip route add 10.0.1.0/24 via 10.0.3.100 || true

# Start Suricata in daemon mode using local.rules on primary interface
suricata -c /etc/suricata/suricata.yaml -s /etc/suricata/rules/local.rules -i eth0 -D

# Start Zeek in background mode loading default/local scripts
if command -v zeek >/dev/null 2>&1; then
    zeek -i eth0 local &
elif command -v /opt/zeek/bin/zeek >/dev/null 2>&1; then
    /opt/zeek/bin/zeek -i eth0 local &
fi

# Ensure log file exists before tailing
touch /var/log/suricata/fast.log

# Stream Suricata fast.log to stdout to keep container running and outputting logs
exec tail -f /var/log/suricata/fast.log