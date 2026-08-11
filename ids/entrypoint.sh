#!/bin/bash

mkdir -p /logs/suricata
mkdir -p /pcaps
mkdir -p /rules

echo "=== IDS Container Started ==="

ip addr
echo
ip route
echo

tail -f /dev/null