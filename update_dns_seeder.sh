#!/bin/bash

set -e

echo "🔧 Updating MinersWorldCoin Lightweight DNS Seeder..."

# 1. Install/Upgrade dependencies
echo "📦 Installing/Upgrading Python packages..."
pip install --upgrade pip
pip install --upgrade dnslib requests

# 2. Seeder directory and script
SEEDER_DIR="/opt/mwc-dnsseeder"
SEEDER_SCRIPT="$SEEDER_DIR/api_dns_seeder.py"
GITHUB_SCRIPT_URL="https://raw.githubusercontent.com/Miners-World-Coin-MWC/Lightweight_DNS_Seeder/main/api_dns_seeder.py"

# 3. Backup the existing script
echo "🗂️ Backing up existing seeder script..."
BACKUP_SCRIPT="$SEEDER_DIR/api_dns_seeder_backup.py"
if [ -f "$SEEDER_SCRIPT" ]; then
    sudo cp "$SEEDER_SCRIPT" "$BACKUP_SCRIPT"
    echo "🔙 Existing script backed up as api_dns_seeder_backup.py"
else
    echo "⚠️ No existing script found, proceeding with the update."
fi

# 4. Download the latest seeder script from GitHub
echo "🌐 Downloading latest seeder script from GitHub..."
sudo curl -fsSL "$GITHUB_SCRIPT_URL" -o "$SEEDER_SCRIPT"
sudo chmod +x "$SEEDER_SCRIPT"

# 5. Ensure the script is executable
echo "🛠️ Ensuring the script is executable..."
sudo chmod +x "$SEEDER_SCRIPT"

# 6. Restart systemd service to apply the new script
echo "🔄 Restarting DNS Seeder service..."
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl restart mwc-dnsseeder.service

# 7. Check DNS Seeder service status
echo "🔍 Checking DNS Seeder service status..."
sudo systemctl status mwc-dnsseeder.service

echo "✅ DNS Seeder has been updated and restarted!"
