#!/bin/bash
# Install the auto-update service on the VM (run as root)

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$REPO_DIR/scripts/auto-update.sh"
SERVICE_NAME="azure-aifoundry-autoupdate"

chmod +x "$SCRIPT"

# --- systemd timer (preferred) ---
if command -v systemctl &>/dev/null && systemctl --version &>/dev/null 2>&1; then
    cat > /etc/systemd/system/${SERVICE_NAME}.service <<EOF
[Unit]
Description=Azure AI Foundry - Auto Update from Git
After=docker.service network-online.target
Requires=docker.service

[Service]
Type=oneshot
ExecStart=$SCRIPT
Environment=DOCKER_API_VERSION=1.41
Environment=GIT_BRANCH=claude/ai-document-management-app-2SJOy
StandardOutput=append:/var/log/azure-aifoundry-autoupdate.log
StandardError=append:/var/log/azure-aifoundry-autoupdate.log
EOF

    cat > /etc/systemd/system/${SERVICE_NAME}.timer <<EOF
[Unit]
Description=Run Azure AI Foundry auto-update every minute

[Timer]
OnBootSec=30s
OnUnitActiveSec=60s
Unit=${SERVICE_NAME}.service

[Install]
WantedBy=timers.target
EOF

    systemctl daemon-reload
    systemctl enable --now ${SERVICE_NAME}.timer
    echo "systemd timer installed and started. Checks every 60 seconds."

# --- fallback: cron ---
else
    CRON_LINE="* * * * * DOCKER_API_VERSION=1.41 GIT_BRANCH=claude/ai-document-management-app-2SJOy $SCRIPT >> /var/log/azure-aifoundry-autoupdate.log 2>&1"
    (crontab -l 2>/dev/null | grep -v "$SCRIPT"; echo "$CRON_LINE") | crontab -
    echo "Cron job installed. Checks every minute."
fi

echo "Auto-update installed. Logs: /var/log/azure-aifoundry-autoupdate.log"
