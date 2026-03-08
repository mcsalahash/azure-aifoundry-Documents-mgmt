#!/bin/bash
# Auto-update script: pulls latest changes and rebuilds Docker if needed

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BRANCH="${GIT_BRANCH:-claude/ai-document-management-app-2SJOy}"
LOG_FILE="/var/log/azure-aifoundry-autoupdate.log"
LOCK_FILE="/tmp/azure-aifoundry-autoupdate.lock"

export DOCKER_API_VERSION="${DOCKER_API_VERSION:-1.41}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Prevent concurrent runs
if [ -e "$LOCK_FILE" ]; then
    log "Another update is already running, skipping."
    exit 0
fi
trap 'rm -f "$LOCK_FILE"' EXIT
touch "$LOCK_FILE"

cd "$REPO_DIR"

# Fetch remote changes
git fetch origin "$BRANCH" >> "$LOG_FILE" 2>&1

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse "origin/$BRANCH")

if [ "$LOCAL" = "$REMOTE" ]; then
    log "Already up to date ($LOCAL). No action needed."
    exit 0
fi

log "New commit detected: $LOCAL -> $REMOTE. Pulling and rebuilding..."

git pull origin "$BRANCH" >> "$LOG_FILE" 2>&1

docker compose up --build -d >> "$LOG_FILE" 2>&1

log "Update complete. Running commit: $(git rev-parse --short HEAD)"
