# Screenware

Screenware is an open-source digital signage platform utilizing a Django web server and Raspberry Pi client displays.

## Features
- **Centralized Web Dashboard**: Manage multiple slide decks, individual slides (images, text, video, calendars, weather), and connected hardware displays.
- **API-Driven Sync**: Deterministic JSON manifest endpoint with SHA-256 version hashing and epoch wall-clock modulo synchronization.
- **Native Lightweight Client**: Dedicated Python daemon (`client/client.py`) using direct Pygame framebuffer rendering—bypassing browser overhead, memory leaks, and drift.
- **100% Autonomous Offline Recovery**: Local two-stage atomic cache (`cache/staging` -> `cache/active`). Devices continue displaying without stutter during network drops and reboot directly into offline playback.
- **Zero-Intervention Systemd Service**: Unconditional respawn on failure and clean recovery on power restoration.

## Architecture

```
[ Django Server ]
       │
       ▼ (JSON Manifest: version_hash, durations, epoch anchor)
[ Background Sync Worker ] ──(Polls API / Downloads to Staging)──► [ Cache Staging Area ]
       │                                                                  │
       │ (Atomic Promotion on Verified Hash)                              ▼
       └──────────────────────────────────────────────────────────► [ Active Cache Dir ]
                                                                          │
[ Pygame Framebuffer Engine ] ◄──(Zero-Network Clock Modulo Lookup)───────┘
```

## Setup Instructions

### Server
1. Clone the repository and navigate to the project directory:
   ```bash
   git clone https://github.com/gimserk/screenware.git
   cd screenware
   ```
2. Install Python requirements:
   ```bash
   pip install -r requirements.txt
   ```
3. Run migrations and create superuser:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```
4. Start the development server:
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```

### Raspberry Pi Client
1. Transfer the `client/` folder to the Raspberry Pi (or place in `/opt/screenware`).
2. Run the automated setup script with your Django server URL:
   ```bash
   sudo ./client/setup_client.sh http://YOUR_SERVER_IP:8000
   ```
3. Start the systemd service:
   ```bash
   sudo systemctl start screenware.service
   ```
