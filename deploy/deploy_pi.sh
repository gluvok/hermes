#!/usr/bin/env bash
set -euo pipefail

# Hermes & Argus Edge Provisioning Script for Raspberry Pi
# ========================================================
# Pulls latest edge release images and starts services with Watchtower.

COMPOSE_FILE="$(dirname "$0")/docker-compose.prod.yml"

echo "=== [Hermes Edge] Provisioning Directories ==="
sudo mkdir -p /var/lib/hermes/data
sudo mkdir -p /var/lib/argus/models
sudo mkdir -p /etc/hermes

# Ensure dialout permissions for UART /dev/ttyAMA0
if [ -e /dev/ttyAMA0 ]; then
    echo "=== [Hermes Edge] Verifying /dev/ttyAMA0 serial permissions ==="
    sudo chmod 660 /dev/ttyAMA0 || true
fi

echo "=== [Hermes Edge] Pulling Release Images ==="
docker compose -f "$COMPOSE_FILE" pull

echo "=== [Hermes Edge] Launching Stack ==="
docker compose -f "$COMPOSE_FILE" up -d --remove-orphans

echo "=== [Hermes Edge] Stack running successfully. ==="
