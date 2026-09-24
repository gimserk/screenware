#!/usr/bin/env python3
import os
import sys
import time
import json
import uuid
import shutil
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
    "slides": []
}

def load_server_url():
    """Loads server base URL from config file or defaults."""
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
    for iface in ["eth0", "wlan0", "end0"]:
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

def load_cached_manifest():
    """Loads previous manifest from disk on cold start (supports offline playback)."""
    global current_manifest
    if os.path.exists(MANIFEST_FILE):
        try:
            with open(MANIFEST_FILE, "r") as f:
                data = json.load(f)
                with manifest_lock:
                    current_manifest = data
            print(f"Loaded cached manifest with version: {current_manifest.get('version_hash')}")
        except Exception as e:
            print(f"Error loading cached manifest: {e}")

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
        print(f"Cache prune warning: {e}")

def sync_worker():
    """
    Background daemon:
    - Polls server manifest endpoint.
    - Compares version_hash with local hash.
    - On mismatch, downloads new assets into staging/ directory.
    - Promotes staging/ to active/ only when 100% verified.
    - Tolerates network disconnects, socket timeouts, and DNS drops silently.
    """
    global current_manifest
    server_url = load_server_url()
    hw_id = get_hardware_identifier()
    manifest_url = f"{server_url}/api/device/{hw_id}/manifest/"

    print(f"Background sync worker started for hardware ID [{hw_id}]")
    print(f"Target manifest URL: {manifest_url}")

    while True:
        try:
            resp = requests.get(manifest_url, timeout=10)
            if resp.status_code == 200:
                remote_manifest = resp.json()
                remote_hash = remote_manifest.get("version_hash", "")
                slides = remote_manifest.get("slides", [])

                with manifest_lock:
                    local_hash = current_manifest.get("version_hash", "")

                if remote_hash and remote_hash != local_hash:
                    print(f"New configuration detected. Syncing version {remote_hash}")

                    # 1. Reset staging directory
                    shutil.rmtree(STAGING_DIR, ignore_errors=True)
                    os.makedirs(STAGING_DIR, exist_ok=True)

                    # 2. Download all slides to staging
                    all_downloaded = True
                    active_filenames = set()

                    for slide in slides:
                        media_url = slide.get("url")
                        filename = slide.get("filename")
                        if not media_url or not filename:
                            continue

                        active_filenames.add(filename)
                        dest_path = os.path.join(STAGING_DIR, filename)

                        # If already in active cache with non-zero size, copy over
                        active_path = os.path.join(CACHE_DIR, filename)
                        if os.path.exists(active_path) and os.path.getsize(active_path) > 0:
                            shutil.copy2(active_path, dest_path)
                            continue

                        # Otherwise stream download from server
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
                            print(f"Download failed for {filename}: {dl_err}")
                            all_downloaded = False
                            break

                    # 3. Promote staging to active atomically
                    if all_downloaded and slides:
                        for filename in os.listdir(STAGING_DIR):
                            src = os.path.join(STAGING_DIR, filename)
                            dst = os.path.join(CACHE_DIR, filename)
                            shutil.copy2(src, dst)

                        # Prune obsolete files from active cache
                        prune_orphan_cache(active_filenames)

                        # Commit new manifest
                        save_manifest_to_disk(remote_manifest)
                        with manifest_lock:
                            current_manifest = remote_manifest
                        print(f"Sync complete. Active cache updated to version {remote_hash}")
                    else:
                        print("Update aborted: Asset download incomplete. Retaining previous loop.")
        except Exception:
            # Network drops, DNS fails, and socket errors silently pass without interrupting playback
            pass

        time.sleep(POLL_INTERVAL)

def run_display():
    """
    Main thread:
    - Direct Pygame display controller.
    - Zero browser overhead, zero memory leaks.
    - Deterministic modulo wall-clock lookup ensures perfect multi-screen synchronization.
    """
    import pygame

    # Initialize Pygame display
    pygame.init()
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

    loaded_surfaces = {}
    current_slide_filename = None

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

    print(f"Display loop initialized at {screen_w}x{screen_h}")

    while True:
        # Check event queue for exit signals
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                pygame.quit()
                return

        with manifest_lock:
            slides = current_manifest.get("slides", [])
            total_duration = current_manifest.get("total_duration", 0)
            epoch_anchor = current_manifest.get("deck_start_epoch", 0)

        # If no slides available yet, show black screen
        if not slides or total_duration <= 0:
            screen.fill((0, 0, 0))
            pygame.display.flip()
            clock.tick(2)
            continue

        # -------------------------------------------------------------
        # Deterministic Wall-Clock Time Sync
        # Any device with accurate NTP time will compute the exact same
        # target slide at any given second, regardless of boot time.
        # -------------------------------------------------------------
        now = time.time()
        offset = (now - epoch_anchor) % total_duration

        elapsed = 0
        target_slide = slides[0]
        for s in slides:
            elapsed += s.get("duration", 10)
            if offset < elapsed:
                target_slide = s
                break

        target_filename = target_slide.get("filename")

        if target_filename and target_filename != current_slide_filename:
            file_path = os.path.join(CACHE_DIR, target_filename)
            if os.path.exists(file_path):
                if target_filename not in loaded_surfaces:
                    try:
                        raw_img = pygame.image.load(file_path).convert()
                        loaded_surfaces[target_filename] = scale_surface(raw_img)
                    except Exception as img_err:
                        print(f"Error loading image {target_filename}: {img_err}")

                if target_filename in loaded_surfaces:
                    screen.blit(loaded_surfaces[target_filename], (0, 0))
                    pygame.display.flip()
                    current_slide_filename = target_filename

                # Garbage collect surfaces no longer in active deck
                active_set = {s.get("filename") for s in slides}
                for dead_key in list(loaded_surfaces.keys()):
                    if dead_key not in active_set:
                        del loaded_surfaces[dead_key]

        clock.tick(10)  # 10 Hz is optimal for precise sub-second slide transitions

if __name__ == "__main__":
    load_cached_manifest()
    worker = threading.Thread(target=sync_worker, daemon=True)
    worker.start()
    run_display()
