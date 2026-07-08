#!/usr/bin/env bash
# ACTAP release script.
#
# Usage:
#   ./deploy/scripts/release.sh <version>
# Example:
#   ./deploy/scripts/release.sh v1.2.3
#
# What it does:
#   1. Pulls new image with the given tag
#   2. Backs up the SQLite database
#   3. Stops the running containers gracefully
#   4. Starts new containers
#   5. Waits for health check
#   6. Rolls back automatically on health-check failure

set -euo pipefail

VERSION="${1:?usage: release.sh <version, e.g. v1.2.3>}"
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.prod"
HEALTH_URL="http://localhost:8001/api/health/ready"
HEALTH_TIMEOUT=60

log() { echo "[$(date +'%Y-%m-%dT%H:%M:%S%z')] $*"; }
fail() { log "ERROR: $*"; exit 1; }

cd "$(dirname "$0")/../.."

# 1. Verify env file exists
[[ -f "$ENV_FILE" ]] || fail "$ENV_FILE not found"

# 2. Backup database
log "Backing up database..."
DATA_DIR="${DATA_DIR:-/var/lib/actap/data}"
BACKUP_DIR="/var/backups/actap/$(date +'%Y%m%d-%H%M%S')"
mkdir -p "$BACKUP_DIR"
if [[ -f "$DATA_DIR/actap.db" ]]; then
    cp "$DATA_DIR/actap.db" "$BACKUP_DIR/actap.db"
    log "DB backup: $BACKUP_DIR/actap.db"
fi

# 3. Pull new image
log "Pulling actap-backend:$VERSION"
docker pull "actap-backend:$VERSION" || fail "image pull failed"

# 4. Export version for compose
export APP_VERSION="$VERSION"

# 5. Capture previous version for rollback
PREVIOUS_VERSION=$(docker inspect actap-backend-prod \
    --format='{{index .Config.Env}}' 2>/dev/null | \
    grep -oP 'APP_VERSION=\K\S+' || echo "")

# 6. Graceful restart
log "Recreating containers..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --no-deps backend frontend

# 7. Wait for healthy
log "Waiting for health check..."
elapsed=0
while (( elapsed < HEALTH_TIMEOUT )); do
    if curl -fsS "$HEALTH_URL" > /dev/null 2>&1; then
        log "Health check OK after ${elapsed}s"
        log "Release $VERSION complete. Previous: ${PREVIOUS_VERSION:-none}"
        exit 0
    fi
    sleep 2
    elapsed=$((elapsed + 2))
done

# 8. Health check failed -> rollback
log "Health check failed. Rolling back..."
if [[ -n "$PREVIOUS_VERSION" ]]; then
    export APP_VERSION="$PREVIOUS_VERSION"
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --no-deps backend frontend
    log "Rolled back to $PREVIOUS_VERSION"
else
    log "No previous version recorded; manual intervention required"
fi
fail "Release $VERSION failed; see logs"
