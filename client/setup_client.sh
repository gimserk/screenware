#!/bin/bash
# ==============================================================================
# Screenware Standalone Python Caching Player Setup
# Replaces legacy browser/xdotool kiosk with zero-browser Pygame engine.
# Provides 100% autonomous recovery, local cache fallback, and modulo clock sync.
# ==============================================================================

set -e

if [ "$EUID" -ne 0 ]; then
  echo "[-] Please run as root: sudo ./setup_client.sh"
  exit 1
fi

echo "========================================================"
echo "    Screenware Native Player Installation & Migration   "
echo "========================================================"

# Prompt for Django Server URL
if [ -n "$1" ]; then
    SERVER_URL="$1"
else
    read -p "Enter Django Server Base URL (e.g., http://192.168.1.100:8000): " SERVER_URL
fi

if [ -z "$SERVER_URL" ]; then
    echo "[-] Server URL cannot be empty. Aborting."
    exit 1
fi

# Ensure URL has http/https protocol prefix and no trailing slash
if [[ ! "$SERVER_URL" =~ ^https?:// ]]; then
    SERVER_URL="http://$SERVER_URL"
fi
SERVER_URL="${SERVER_URL%/}"

echo "[+] Target Django Server: $SERVER_URL"

# --- 1. Clean up legacy browser-based kiosk service and cron jobs ---
echo "[+] Cleaning legacy kiosk services and cron tasks..."
if systemctl is-active --quiet kiosk.service 2>/dev/null; then
    systemctl stop kiosk.service || true
fi
if systemctl is-enabled --quiet kiosk.service 2>/dev/null; then
    systemctl disable kiosk.service || true
fi
rm -f /etc/systemd/system/kiosk.service

# Remove legacy cron jobs for pi user
crontab -u pi -r 2>/dev/null || true

# --- 2. Install Required Dependencies ---
echo "[+] Updating apt repositories and installing packages..."
apt-get update
apt-get install -y python3-pygame python3-requests systemd-timesyncd xserver-xorg xinit openbox

# Enable systemd-timesyncd for clock synchronization
systemctl enable systemd-timesyncd
systemctl start systemd-timesyncd

# Configure Xorg wrapper for non-root execution if under X11
cat << 'XWRAP_EOF' > /etc/X11/Xwrapper.config
allowed_users=anybody
needs_root_rights=yes
XWRAP_EOF

# Ensure default boot mode is graphical
systemctl set-default graphical.target

# --- 3. Setup Application Directories & Permissions ---
echo "[+] Setting up /opt/screenware directories..."
mkdir -p /opt/screenware/cache/active
mkdir -p /opt/screenware/cache/staging

# Write config.json
cat << CONFIG_EOF > /opt/screenware/config.json
{
  "server_url": "$SERVER_URL"
}
CONFIG_EOF

# Set permissions
chown -R pi:pi /opt/screenware
chmod 755 /opt/screenware/cache
chmod 755 /opt/screenware/cache/active
chmod 755 /opt/screenware/cache/staging

# --- 4. Deploy Native Client Service ---
echo "[+] Configuring systemd service (/etc/systemd/system/screenware.service)..."
cat << 'SERVICE_EOF' > /etc/systemd/system/screenware.service
[Unit]
Description=Screenware Native Digital Signage Player
After=systemd-timesyncd.service
Wants=systemd-timesyncd.service

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/opt/screenware
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/pi/.Xauthority
ExecStart=/usr/bin/xinit /usr/bin/python3 /opt/screenware/client.py -- vt1
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=graphical.target
SERVICE_EOF

systemctl daemon-reload
systemctl enable screenware.service

echo ""
echo "========================================================"
echo " [✓] Installation complete!"
echo " - Configured server URL: $SERVER_URL"
echo " - Caching directory: /opt/screenware/cache/active/"
echo " - Native player service: screenware.service (enabled)"
echo " To start immediately: sudo systemctl start screenware.service"
echo "========================================================"
