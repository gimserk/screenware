#!/bin/bash
# ==============================================================================
# Screenware Standalone Python Caching Player Setup & Migration
# Replaces legacy Chromium browser kiosk with native Pygame player.
# ==============================================================================

set -e

if [ "$EUID" -ne 0 ]; then
  echo "[-] Please run as root: sudo ./setup_client.sh"
  exit 1
fi

echo "========================================================"
echo "    Screenware Native Player Installation & Migration   "
echo "========================================================"

if [ -n "$1" ]; then
    SERVER_URL="$1"
else
    read -p "Enter Django Server Base URL (e.g., http://192.168.1.100:8000): " SERVER_URL
fi

if [ -z "$SERVER_URL" ]; then
    echo "[-] Server URL cannot be empty. Aborting."
    exit 1
fi

if [[ ! "$SERVER_URL" =~ ^https?:// ]]; then
    SERVER_URL="http://$SERVER_URL"
fi
SERVER_URL="${SERVER_URL%/}"

echo "[+] Target Django Server: $SERVER_URL"

# --- 1. Clean up legacy browser-based kiosk services and cron tasks ---
echo "[+] Cleaning legacy browser kiosk services and cron tasks..."
if systemctl is-active --quiet kiosk.service 2>/dev/null; then
    systemctl stop kiosk.service || true
fi
if systemctl is-enabled --quiet kiosk.service 2>/dev/null; then
    systemctl disable kiosk.service || true
fi
rm -f /etc/systemd/system/kiosk.service
crontab -u pi -r 2>/dev/null || true

# --- 2. Install Required Dependencies ---
echo "[+] Updating apt repositories and installing packages..."
apt-get update
apt-get install -y python3-pygame python3-requests systemd-timesyncd xserver-xorg xinit openbox

# Enable systemd-timesyncd for clock synchronization
systemctl enable systemd-timesyncd
systemctl start systemd-timesyncd

# Configure Xorg wrapper permissions
cat << 'XWRAP_EOF' > /etc/X11/Xwrapper.config
allowed_users=anybody
needs_root_rights=yes
XWRAP_EOF

# Set default boot mode to graphical
systemctl set-default graphical.target

# --- 3. Setup Application Directories & Permissions ---
echo "[+] Setting up /opt/screenware directories and scripts..."
mkdir -p /opt/screenware/cache/active
mkdir -p /opt/screenware/cache/staging

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Deploy client scripts
cp "$SCRIPT_DIR/client.py" /opt/screenware/client.py
cp "$SCRIPT_DIR/start_player.sh" /opt/screenware/start_player.sh
chmod +x /opt/screenware/client.py /opt/screenware/start_player.sh

# Write server configuration
cat << CONFIG_EOF > /opt/screenware/config.json
{
  "server_url": "$SERVER_URL"
}
CONFIG_EOF

chown -R pi:pi /opt/screenware
chmod 755 /opt/screenware/cache
chmod 755 /opt/screenware/cache/active
chmod 755 /opt/screenware/cache/staging

# --- 4. Deploy Native Client Service ---
echo "[+] Configuring systemd service (/etc/systemd/system/screenware.service)..."
cp "$SCRIPT_DIR/screenware.service" /etc/systemd/system/screenware.service

systemctl daemon-reload
systemctl enable screenware.service

echo ""
echo "========================================================"
echo " [✓] Installation complete!"
echo " - Configured server URL: $SERVER_URL"
echo " - Cache directory      : /opt/screenware/cache/active/"
echo " - Systemd service      : screenware.service (enabled)"
echo " To start immediately   : sudo systemctl start screenware.service"
echo "========================================================"
