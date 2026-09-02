#!/bin/sh
set -e

cat > /etc/tor/torrc <<EOF
SocksPort 0.0.0.0:9050
Log notice stdout
EOF

exec tor -f /etc/tor/torrc
