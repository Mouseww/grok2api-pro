#!/usr/bin/env sh
set -eu

# Ensure mount points exist for common deployments (docker volume/bind mounts).
mkdir -p /app/data /app/logs

exec "$@"

