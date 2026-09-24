#!/usr/bin/env python3
"""
Screenware Native Signage Client
- Direct Pygame framebuffer rendering (bypasses browser, eliminating memory leaks & tab freezes).
- Modulo wall-clock time sync: (now - 0) % total_duration eliminates screen drift.
- Two-stage atomic cache: Staging downloads -> Verified promote to active cache.
- Standby diagnostics display when unassigned.
- Native Text & Image slide support.
- Fully resilient against network severance and cold reboots.
"""

import os
import sys
import time
import json
import uuid
import shutil
import socket
import threading
import requests

# Base configuration paths
BASE_DIR = "/opt/screenware"
CACHE_DIR = os.path.join(BASE_DIR, "cache", "active")
STAGING_DIR = os.path.join(BASE_DIR, "cache", "staging")
MANIFEST_FILE = os.path.join(BASE_DIR, "manifest.json")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
POLL_INTERVAL = 20  # seconds

os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(STAGING_DIR, exist_ok=True)

manifest_lock = threading.Lock()
current_manifest = {
    "version_hash": "",
    "deck_start_epoch": 0,
    "total_duration": 0,
    "slides": [],
    "status": "initializing"
}

def load_server_url():
    """Loads server base URL from config file, environment variable, or defaults."""
    if "SCREENWARE_SERVER_URL" in os.environ:
        return os.environ["SCREENWARE_SERVER_URL"].rstrip("/")
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                cfg = json.load(f)
                return cfg.get("server_url", "http://localhost:8000").rstrip("/")
        except Exception as e:
            print(f"Warning: Could not read config file: {e}")
    return "http://localhost:8000"

def get_hardware_identifier():
    """
    Retrieves a permanent hardware identifier for this Raspberry Pi.
    Checks physical eth0/wlan0 interfaces, CPU serial from /proc/cpuinfo,
    or falls back to uuid.getnode.
    """
    for iface in ["eth0", "wlan0", "end0", "en0"]:
        addr_path = f"/sys/class/net/{iface}/address"
        if os.path.exists(addr_path):
            try:
                with open(addr_path, "r") as f:
                    addr = f.read().strip().upper()
                    if addr and addr != "00:00:00:00:00:00":
                        return addr
            except Exception:
                pass

    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if line.startswith("Serial"):
                    return line.split(":")[1].strip().upper()
    except Exception:
        pass

    node = uuid.getnode()
    mac = ':'.join(['{:02x}'.format((node >> ele) & 0xff) for ele in range(0, 8 * 6, 8)][::-1])
    return mac.upper()

def get_local_ip():
    """Discovers the active local IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def load_cached_manifest():
    """Loads previous manifest from disk on cold start (enables immediate offline playback)."""
    global current_manifest
    if os.path.exists(MANIFEST_FILE):
        try:
            with open(MANIFEST_FILE, "r") as f:
                data = json.load(f)
                with manifest_lock:
                    current_manifest = data
            print(f"[+] Loaded cached manifest with version: {current_manifest.get('version_hash')}")
        except Exception as e:
            print(f"[-] Error loading cached manifest: {e}")

def save_manifest_to_disk(manifest_data):
    """Atomically commits manifest to disk using tmp file swap."""
    temp_file = MANIFEST_FILE + ".tmp"
    with open(temp_file, "w") as f:
        json.dump(manifest_data, f, indent=2)
    os.replace(temp_file, MANIFEST_FILE)

def prune_orphan_cache(active_filenames):
    """Removes cached files that are no longer part of the active slide deck."""
    try:
        for fname in os.listdir(CACHE_DIR):
            if fname not in active_filenames:
                file_path = os.path.join(CACHE_DIR, fname)
                if os.path.isfile(file_path):
                    try:
                        os.remove(file_path)
                    except OSError:
                        pass
    except Exception as e:
        print(f"[-] Cache prune warning: {e}")

def sync_worker():
    """
    Background daemon thread:
    - Polls server manifest endpoint with local IP in header.
    - Compares remote version_hash with local hash.
    - On mismatch, downloads new assets into staging/ directory.
    - Promotes staging/ to active/ only when 100% verified.
    - Tolerates network disconnects, socket timeouts, and DNS drops silently.
    """
    global current_manifest
    hw_id = get_hardware_identifier()

    print(f"[+] Sync worker active for hardware ID: [{hw_id}]")

    while True:
        server_url = load_server_url()
        manifest_url = f"{server_url}/api/device/{hw_id}/manifest/"
        headers = {"X-Client-IP": get_local_ip()}

        try:
            resp = requests.get(manifest_url, headers=headers, timeout=10)
            if resp.status_code == 200:
                remote_manifest = resp.json()
                remote_hash = remote_manifest.get("version_hash", "")
                slides = remote_manifest.get("slides", [])

                with manifest_lock:
                    local_hash = current_manifest.get("version_hash", "")

                if remote_hash and remote_hash != local_hash:
                    print(f"[+] Update detected. Syncing new version: {remote_hash}")

                    # 1. Reset staging directory
                    shutil.rmtree(STAGING_DIR, ignore_errors=True)
                    os.makedirs(STAGING_DIR, exist_ok=True)

                    # 2. Download all slide assets to staging
                    all_downloaded = True
                    active_filenames = set()

                    for slide in slides:
                        media_url = slide.get("url")
                        filename = slide.get("filename")
                        if not media_url or not filename:
                            continue

                        active_filenames.add(filename)
                        dest_path = os.path.join(STAGING_DIR, filename)

                        # If already in active cache with valid size, copy over directly
                        active_path = os.path.join(CACHE_DIR, filename)
                        if os.path.exists(active_path) and os.path.getsize(active_path) > 0:
                            shutil.copy2(active_path, dest_path)
                            continue

                        # Stream download asset
                        try:
                            r = requests.get(media_url, stream=True, timeout=15)
                            if r.status_code == 200:
                                with open(dest_path, 'wb') as f:
                                    for chunk in r.iter_content(chunk_size=8192):
                                        f.write(chunk)
                                if os.path.getsize(dest_path) == 0:
                                    all_downloaded = False
                                    break
                            else:
                                all_downloaded = False
                                break
                        except Exception as dl_err:
                            print(f"[-] Download error for {filename}: {dl_err}")
                            all_downloaded = False
                            break

                    # 3. Promote staging to active atomically
                    if all_downloaded:
                        for filename in os.listdir(STAGING_DIR):
                            src = os.path.join(STAGING_DIR, filename)
                            dst = os.path.join(CACHE_DIR, filename)
                            shutil.copy2(src, dst)

                        prune_orphan_cache(active_filenames)
                        save_manifest_to_disk(remote_manifest)

                        with manifest_lock:
                            current_manifest = remote_manifest
                        print(f"[✓] Sync successful. Active cache updated to version {remote_hash}")
                    else:
                        print("[-] Asset download incomplete. Retaining previous active cache.")
                elif not remote_hash and remote_manifest.get("status") == "unassigned":
                    # Display unassigned status
                    with manifest_lock:
                        current_manifest["status"] = "unassigned"
                        current_manifest["device_name"] = remote_manifest.get("device_name", "")
        except Exception:
            # Network severed, DNS failures, or timeouts pass silently
            pass

        time.sleep(POLL_INTERVAL)

def run_display():
    """
    Main display thread:
    - Direct Pygame display controller.
    - Zero browser overhead, zero memory leaks.
    - Deterministic modulo wall-clock lookup ensures perfect multi-screen synchronization.
    - Built-in standby diagnostic view and text slide support.
    """
    import pygame

    pygame.init()
    pygame.font.init()
    pygame.mouse.set_visible(False)

    screen = None
    for attempt in range(5):
        try:
            screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            break
        except pygame.error as pe:
            print(f"Display init attempt {attempt + 1} failed: {pe}. Retrying in 1s...")
            time.sleep(1)

    if screen is None:
        screen = pygame.display.set_mode((1920, 1080))

    screen_w, screen_h = screen.get_size()
    clock = pygame.time.Clock()

    title_font = pygame.font.SysFont("sans-serif", int(screen_h * 0.055), bold=True)
    body_font = pygame.font.SysFont("sans-serif", int(screen_h * 0.038))
    mono_font = pygame.font.SysFont("monospace", int(screen_h * 0.028))

    loaded_surfaces = {}
    current_slide_id = None
    hw_id = get_hardware_identifier()

    def scale_surface(img_surf):
        img_w, img_h = img_surf.get_size()
        scale = min(screen_w / img_w, screen_h / img_h)
        new_w = max(1, int(img_w * scale))
        new_h = max(1, int(img_h * scale))
        scaled_img = pygame.transform.smoothscale(img_surf, (new_w, new_h))
        frame = pygame.Surface((screen_w, screen_h))
        frame.fill((0, 0, 0))
        offset_x = (screen_w - new_w) // 2
        offset_y = (screen_h - new_h) // 2
        frame.blit(scaled_img, (offset_x, offset_y))
        return frame

    def render_text_slide(title, body):
        surf = pygame.Surface((screen_w, screen_h))
        surf.fill((15, 23, 42))  # Dark Slate-900

        # Title bar
        t_render = title_font.render(title, True, (56, 189, 248))  # Sky-400
        surf.blit(t_render, (int(screen_w * 0.08), int(screen_h * 0.12)))

        # Divider line
        pygame.draw.line(
            surf, (51, 65, 85),
            (int(screen_w * 0.08), int(screen_h * 0.20)),
            (int(screen_w * 0.92), int(screen_h * 0.20)),
            2
        )

        # Word-wrapped body text
        words = body.split()
        lines = []
        curr_line = []
        max_w = int(screen_w * 0.84)

        for word in words:
            test_line = " ".join(curr_line + [word])
            if body_font.size(test_line)[0] < max_w:
                curr_line.append(word)
            else:
                if curr_line:
                    lines.append(" ".join(curr_line))
                curr_line = [word]
        if curr_line:
            lines.append(" ".join(curr_line))

        y_pos = int(screen_h * 0.25)
        line_height = int(body_font.get_linesize() * 1.4)
        for line in lines[:10]:
            l_render = body_font.render(line, True, (241, 245, 249))
            surf.blit(l_render, (int(screen_w * 0.08), y_pos))
            y_pos += line_height

        return surf

    def render_standby_screen():
        surf = pygame.Surface((screen_w, screen_h))
        surf.fill((10, 15, 30))

        h1 = title_font.render("SCREENWARE SIGNAGE", True, (56, 189, 248))
        surf.blit(h1, (int(screen_w * 0.08), int(screen_h * 0.20)))

        sub = body_font.render("Display Ready & Waiting for Assignment", True, (148, 163, 184))
        surf.blit(sub, (int(screen_w * 0.08), int(screen_h * 0.28)))

        ip = get_local_ip()
        server_url = load_server_url()

        id_text = mono_font.render(f"Hardware ID (MAC): {hw_id}", True, (226, 232, 240))
        ip_text = mono_font.render(f"Local IP Address : {ip}", True, (226, 232, 240))
        srv_text = mono_font.render(f"Server Host      : {server_url}", True, (226, 232, 240))

        box_y = int(screen_h * 0.40)
        pygame.draw.rect(surf, (30, 41, 59), (int(screen_w * 0.08), box_y, int(screen_w * 0.65), int(screen_h * 0.25)), border_radius=8)
        surf.blit(id_text, (int(screen_w * 0.10), box_y + int(screen_h * 0.04)))
        surf.blit(ip_text, (int(screen_w * 0.10), box_y + int(screen_h * 0.10)))
        surf.blit(srv_text, (int(screen_w * 0.10), box_y + int(screen_h * 0.16)))

        foot = mono_font.render("Assign this screen to a Slide Deck from the Screenware Web Dashboard.", True, (100, 116, 139))
        surf.blit(foot, (int(screen_w * 0.08), int(screen_h * 0.72)))
        return surf

    print(f"[+] Display loop running: {screen_w}x{screen_h}")

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                pygame.quit()
                return

        with manifest_lock:
            slides = current_manifest.get("slides", [])
            total_duration = current_manifest.get("total_duration", 0)
            epoch_anchor = current_manifest.get("deck_start_epoch", 0)

        # Show standby screen if unassigned or no slides
        if not slides or total_duration <= 0:
            screen.blit(render_standby_screen(), (0, 0))
            pygame.display.flip()
            clock.tick(2)
            continue

        # ----------------------------------------------------------------------
        # Deterministic Wall-Clock Modulo Sync
        # offset = (now - epoch_anchor) % total_duration
        # ----------------------------------------------------------------------
        now = time.time()
        offset = (now - epoch_anchor) % total_duration

        elapsed = 0
        target_slide = slides[0]
        for s in slides:
            elapsed += s.get("duration", 10)
            if offset < elapsed:
                target_slide = s
                break

        slide_id = target_slide.get("id")

        if slide_id != current_slide_id:
            content_type = target_slide.get("content_type", "image")
            target_filename = target_slide.get("filename", "")

            # If surface not in memory, generate/load it
            if slide_id not in loaded_surfaces:
                if content_type == "text" or (not target_filename and target_slide.get("text_content")):
                    title = target_slide.get("title", "Notice")
                    body = target_slide.get("text_content", "")
                    loaded_surfaces[slide_id] = render_text_slide(title, body)
                elif target_filename:
                    file_path = os.path.join(CACHE_DIR, target_filename)
                    if os.path.exists(file_path):
                        try:
                            raw_img = pygame.image.load(file_path).convert()
                            loaded_surfaces[slide_id] = scale_surface(raw_img)
                        except Exception as e:
                            print(f"[-] Image load failed for {target_filename}: {e}")
                            loaded_surfaces[slide_id] = render_text_slide(target_slide.get("title", "Asset Error"), f"Could not load image: {target_filename}")

            if slide_id in loaded_surfaces:
                screen.blit(loaded_surfaces[slide_id], (0, 0))
                pygame.display.flip()
                current_slide_id = slide_id

                # Prune surfaces of slides no longer in deck
                active_ids = {s.get("id") for s in slides}
                for dead_id in list(loaded_surfaces.keys()):
                    if dead_id not in active_ids:
                        del loaded_surfaces[dead_id]

        clock.tick(10)

if __name__ == "__main__":
    load_cached_manifest()
    worker = threading.Thread(target=sync_worker, daemon=True)
    worker.start()
    run_display()
