#!/bin/bash

# Ensure required log and runtime directories exist
mkdir -p /logs/suricata /var/log/suricata /pcaps/T1 /pcaps/T2 /rules

echo "=== IDS Container Started ==="

ip addr
echo
ip route
echo

# Add cross-subnet route back to flash via router
ip route add 10.0.1.0/24 via 10.0.3.100 || true

# --- Locate the two tap interfaces by subnet instead of assuming eth0/eth1 ---
# (interface enumeration order isn't guaranteed across Docker versions/platforms)
# T1 = dmz_net (10.0.2.0/24): traffic as it enters the edge segment -- what the IDS sees
# T2 = protected_net (10.0.3.0/24): traffic as it reaches the application segment
IFACE_T1=$(ip -o -4 addr show | awk '$4 ~ /^10\.0\.2\./ {print $2; exit}')
IFACE_T2=$(ip -o -4 addr show | awk '$4 ~ /^10\.0\.3\./ {print $2; exit}')

if [ -z "$IFACE_T1" ] || [ -z "$IFACE_T2" ]; then
    echo "!! Could not resolve both tap interfaces by subnet (T1=$IFACE_T1 T2=$IFACE_T2)."
    echo "!! Falling back to eth0/eth1."
    IFACE_T1=${IFACE_T1:-eth0}
    IFACE_T2=${IFACE_T2:-eth1}
fi

echo "T1 (edge / dmz_net) tap interface:        $IFACE_T1"
echo "T2 (application / protected_net) tap interface: $IFACE_T2"

# --- Raw packet capture on both taps (L1 raw data, guide section 3.1) ---
# Passive only: this container is already inline for forwarding, but tcpdump
# here only reads a copy of what crosses each NIC -- it never blocks traffic.
# Rotated in 5-minute files, ring-buffered to the last hour (12 files) per tap
# so disk usage stays bounded across long scenario runs.
tcpdump -i "$IFACE_T1" -s 0 -U -w /pcaps/T1/T1_%Y%m%d_%H%M%S.pcap -G 300 -W 12 \
    >/logs/tcpdump_t1.log 2>&1 &

tcpdump -i "$IFACE_T2" -s 0 -U -w /pcaps/T2/T2_%Y%m%d_%H%M%S.pcap -G 300 -W 12 \
    >/logs/tcpdump_t2.log 2>&1 &

# Start Suricata in daemon mode using local.rules on the T1 (edge) interface only
# -- the guide has the IDS stack "read a mirror of the edge traffic only"
suricata -c /etc/suricata/suricata.yaml -s /etc/suricata/rules/local.rules -i "$IFACE_T1" -D

# Start Zeek in background mode loading default/local scripts, also on T1
if command -v zeek >/dev/null 2>&1; then
    zeek -i "$IFACE_T1" local &
elif command -v /opt/zeek/bin/zeek >/dev/null 2>&1; then
    /opt/zeek/bin/zeek -i "$IFACE_T1" local &
fi

# Ensure log file exists before tailing
touch /var/log/suricata/fast.log

# Stream Suricata fast.log to stdout to keep container running and outputting logs
exec tail -f /var/log/suricata/fast.log