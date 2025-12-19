# management/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from datetime import timedelta
import json
from django.http import JsonResponse
from django.db import transaction

from .forms import SlideForm
from slideshow.models import Device, SlideDeck, Slide

# --- Dashboard View ---
@login_required
def dashboard_view(request):
    devices = Device.objects.all().order_by('-last_seen')
    
    for device in devices:
        device.is_online = (timezone.now() - device.last_seen) < timedelta(minutes=5)

    return render(request, 'management/dashboard.html', {'devices': devices})

def logout_view(request):
    logout(request)
    return redirect('login')

# --- Device Management Views ---
class DeviceListView(LoginRequiredMixin, ListView):
    model = Device
    template_name = 'management/device_list.html'
    context_object_name = 'devices'

class DeviceUpdateView(LoginRequiredMixin, UpdateView):
    model = Device
    fields = ['name', 'assigned_slidedeck']
    template_name = 'management/device_form.html'
    success_url = reverse_lazy('dashboard')

class DeviceDeleteView(LoginRequiredMixin, DeleteView):
    model = Device
    template_name = 'management/device_confirm_delete.html'
    success_url = reverse_lazy('manage_device_list')

# --- Slide Deck Management Views ---
class SlideDeckListView(LoginRequiredMixin, ListView):
    model = SlideDeck
    template_name = 'management/slidedeck_list.html'
    context_object_name = 'slidedecks'

class SlideDeckCreateView(LoginRequiredMixin, CreateView):
    model = SlideDeck
    fields = ['name', 'slug']
    template_name = 'management/slidedeck_form.html' 
    success_url = reverse_lazy('manage_slidedeck_list')

class SlideDeckUpdateView(LoginRequiredMixin, UpdateView):
    model = SlideDeck
    fields = ['name', 'slug']
    template_name = 'management/slidedeck_form.html'
    success_url = reverse_lazy('manage_slidedeck_list')

class SlideDeckDeleteView(LoginRequiredMixin, DeleteView):
    model = SlideDeck
    template_name = 'management/slidedeck_confirm_delete.html'
    success_url = reverse_lazy('manage_slidedeck_list')

# --- Slide Management Views ---
@login_required
def manage_slides_view(request, deck_pk):
    slidedeck = get_object_or_404(SlideDeck, pk=deck_pk)
    
    if request.method == 'POST':
        form = SlideForm(request.POST, request.FILES)
        if form.is_valid():
            new_slide = form.save(commit=False)
            new_slide.slide_deck = slidedeck
            new_slide.save()
            return redirect('manage_slides', deck_pk=slidedeck.pk)
    else:
        form = SlideForm()

    slides = slidedeck.slides.all().order_by('order')
    context = {
        'slidedeck': slidedeck,
        'slides': slides,
        'form': form,
    }
    return render(request, 'management/manage_slides.html', context)

class SlideUpdateView(LoginRequiredMixin, UpdateView):
    model = Slide
    form_class = SlideForm
    template_name = 'management/slide_form.html'

    def get_success_url(self):
        return reverse_lazy('manage_slides', kwargs={'deck_pk': self.object.slide_deck.pk})

class SlideDeleteView(LoginRequiredMixin, DeleteView):
    model = Slide
    template_name = 'management/slide_confirm_delete.html'
    
    def get_success_url(self):
        return reverse_lazy('manage_slides', kwargs={'deck_pk': self.object.slide_deck.pk})

@login_required
@transaction.atomic
def reorder_slides_view(request, deck_pk):
    """
    Receives a POST request with the new order of slides and updates the database.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            new_order_pks = data.get('new_order', [])
            
            # Update the order for each slide
            for index, pk in enumerate(new_order_pks):
                Slide.objects.filter(pk=pk, slide_deck_id=deck_pk).update(order=index)
            
            return JsonResponse({'status': 'success', 'message': 'Slide order updated successfully.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)

@login_required
def download_setup_script_view(request):
    """
    This view serves the complete, self-updating setup_kiosk.sh script 
    as a downloadable file.
    """
    # Using a raw triple-quoted string (r"""...""") to preserve all special characters.
    script_content = r"""#!/bin/bash

# SCREENWARE KIOSK INSTALLER - FIXED DEPENDENCY LOGIC
# Prioritizes 'chromium' over 'chromium-browser' for Debian Trixie/Bookworm compliance.

set -e

INSTALL_DIR="/opt/screenware"

echo "=================================================="
echo "      Screenware Kiosk Setup (Trixie/Bookworm)    "
echo "=================================================="

# --- 1. Gather Configuration ---
if [ ! -f "$INSTALL_DIR/config.json" ]; then
    read -p "Enter Django Server IP (e.g., 192.168.1.50:8000): " SERVER_IP
    read -p "Enter Initial Slide Deck Slug: " DECK_SLUG
else
    echo "Existing configuration found. Preserving..."
    SERVER_IP=$(grep -oP '"server": "\K[^"]+' $INSTALL_DIR/config.json || echo "127.0.0.1")
    DECK_SLUG=$(grep -oP '"slug": "\K[^"]+' $INSTALL_DIR/config.json || echo "default")
fi

# --- 2. Robust Dependency Installation ---
echo "--- Detecting Browser Package ---"
apt-get update

# Logic: Check if 'chromium' exists and has an installation candidate. 
# This fixes the issue where 'chromium-browser' exists as a dummy package but can't be installed.
if apt-cache policy chromium | grep -q "Candidate:"; then
    echo "Detected modern package: chromium"
    BROWSER_PKG="chromium"
else
    echo "Falling back to legacy package: chromium-browser"
    BROWSER_PKG="chromium-browser"
fi

echo "--- Installing Dependencies ($BROWSER_PKG) ---"
# We add --fix-missing to handle potential repo sync issues
apt-get install -y cage $BROWSER_PKG python3-requests python3-venv fonts-liberation --fix-missing

# Locate the binary path for Python script
if [ -f "/usr/bin/chromium" ]; then
    BROWSER_BIN="/usr/bin/chromium"
elif [ -f "/usr/bin/chromium-browser" ]; then
    BROWSER_BIN="/usr/bin/chromium-browser"
else
    # Fallback search
    BROWSER_BIN=$(command -v chromium || command -v chromium-browser)
fi

if [ -z "$BROWSER_BIN" ]; then
    echo "CRITICAL ERROR: Could not locate chromium binary after install."
    exit 1
fi
echo "Browser binary confirmed at: $BROWSER_BIN"

# --- 3. System Cleanup ---
echo "--- Cleaning up conflicting display services ---"
systemctl stop lightdm 2>/dev/null || true
systemctl disable lightdm 2>/dev/null || true
systemctl stop gdm3 2>/dev/null || true
systemctl disable gdm3 2>/dev/null || true

echo "--- Disabling Boot Splash ---"
if grep -q "splash" /boot/firmware/cmdline.txt 2>/dev/null; then
    sed -i 's/splash//g' /boot/firmware/cmdline.txt
fi
if grep -q "quiet" /boot/firmware/cmdline.txt 2>/dev/null; then
    sed -i 's/quiet//g' /boot/firmware/cmdline.txt
fi

# --- 4. Setup Directories ---
mkdir -p "$INSTALL_DIR"

# --- 5. Create Offline Page ---
cat <<EOF > "$INSTALL_DIR/offline.html"
<!DOCTYPE html>
<html>
<head>
<style>
  body { background-color: #000; color: #fff; font-family: sans-serif; 
         display: flex; justify-content: center; align-items: center; height: 100vh; text-align: center; }
  h1 { font-size: 4em; color: #e74c3c; margin-bottom: 0.2em;}
  p { font-size: 2em; color: #aaa; }
</style>
</head>
<body>
  <div>
    <h1>Connection Lost</h1>
    <p>Waiting for Screenware Server...</p>
  </div>
</body>
</html>
EOF

# --- 6. Create Guardian Script ---
cat <<EOF > "$INSTALL_DIR/guardian.py"
#!/usr/bin/python3
import time, requests, subprocess, os, signal, sys, json

# Configuration
SERVER_IP = "$SERVER_IP"
CONFIG_FILE = "$INSTALL_DIR/config.json"
OFFLINE_URL = "file://$INSTALL_DIR/offline.html"
BROWSER_BIN = "$BROWSER_BIN" 

# Initialize Config
if not os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, 'w') as f:
        json.dump({"slug": "$DECK_SLUG", "server": SERVER_IP}, f)

def get_config():
    with open(CONFIG_FILE, 'r') as f: return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, 'w') as f: json.dump(data, f)

def get_device_serial():
    try:
        with open('/proc/cpuinfo', 'r') as f:
            for line in f:
                if line.startswith('Serial'): return line.split(':')[1].strip()
    except: return "unknown_pi"

def check_connection(server_ip):
    try:
        requests.get(f"http://{server_ip}", timeout=5)
        return True
    except: return False

def get_server_assignment(server_ip, current_slug):
    url = f"http://{server_ip}/api/heartbeat/"
    serial = get_device_serial()
    try:
        resp = requests.post(url, json={"device_id": serial}, timeout=5)
        if resp.status_code == 200:
            return resp.json().get("assigned_slidedeck_slug", current_slug)
    except: pass
    return current_slug

def launch_browser(url):
    cmd = [
        "/usr/bin/cage",
        "--", 
        BROWSER_BIN,
        "--kiosk",
        "--noerrdialogs",
        "--disable-infobars",
        "--no-sandbox",
        "--disable-gpu-compositing",
        "--user-data-dir=/tmp/chromium-kiosk-profile",
        url
    ]
    log_file = open('$INSTALL_DIR/browser.log', 'w')
    return subprocess.Popen(cmd, stdout=log_file, stderr=log_file)

def main():
    print("--- Guardian Started ---")
    
    config = get_config()
    current_slug = config.get('slug', 'default')
    server_ip = config.get('server', '127.0.0.1')
    
    is_online = check_connection(server_ip)
    
    if is_online:
        target_url = f"http://{server_ip}/deck/{current_slug}/"
    else:
        target_url = OFFLINE_URL

    print(f"Launching: {target_url}")
    browser_process = launch_browser(target_url)

    while True:
        try:
            time.sleep(10)
            
            if browser_process.poll() is not None:
                print("Browser process died. Restarting loop.")
                break 

            now_online = check_connection(server_ip)
            if is_online != now_online:
                print("Network state changed. Rebooting browser.")
                break

            if now_online:
                new_slug = get_server_assignment(server_ip, current_slug)
                if new_slug != current_slug:
                    print(f"Slug changed to {new_slug}. Saving and restarting.")
                    config['slug'] = new_slug
                    save_config(config)
                    break 

        except KeyboardInterrupt:
            browser_process.terminate()
            sys.exit(0)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

    print("Terminating browser...")
    browser_process.terminate()
    try: browser_process.wait(timeout=5)
    except: browser_process.kill()
    sys.exit(0)

if __name__ == "__main__":
    main()
EOF

# --- 7. Create Systemd Service ---
echo "--- Creating Systemd Service ---"
cat <<EOF > /etc/systemd/system/screenware.service
[Unit]
Description=Screenware Kiosk Guardian (Root)
After=network-online.target
Wants=network-online.target

[Service]
User=root
Group=root
Environment=XDG_RUNTIME_DIR=/run/user/0
Environment=WLR_LIBINPUT_NO_DEVICES=1
ExecStartPre=/bin/mkdir -p /run/user/0
ExecStartPre=/bin/chmod 700 /run/user/0
ExecStart=/usr/bin/python3 $INSTALL_DIR/guardian.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# --- 8. Finalize ---
chmod +x "$INSTALL_DIR/guardian.py"
systemctl daemon-reload
systemctl enable screenware.service

echo "=================================================="
echo "Setup Complete! Rebooting in 5 seconds..."
echo "=================================================="
sleep 5
reboot"""
    response = HttpResponse(script_content, content_type='text/x-shellscript')
    response['Content-Disposition'] = 'attachment; filename="setup_kiosk.sh"'
    return response
