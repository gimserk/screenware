Create and activate a virtual environment:


python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000

Note: For production, we recommend deploying behind Nginx and Gunicorn.

📺 Client Installation (Raspberry Pi)
The client is designed to be as "dumb" and resilient as possible. It only requires a basic OS installation and a network connection.

Prerequisites
A Raspberry Pi (3B, 4, or Zero 2 W recommended)

Raspberry Pi OS (Lite or Desktop with UI)

Internet/Network access to the Django server

Setup Steps
Flash your SD Card with Raspberry Pi OS and boot the device.

Configure Kiosk Mode:
If using the Desktop version, configure your Pi to auto-login and disable screen blanking/sleep modes in raspi-config.

Clone the client script:

Bash
git clone [https://github.com/yourusername/screenware.git](https://github.com/yourusername/screenware.git)
cd screenware/client
Install client dependencies:

Bash
pip3 install -r requirements.txt
Configure the Client:
Edit the .env file in the client directory to point to your Django server's IP address and assign the unique Screen ID for this specific Pi.

Ini, TOML
SERVER_URL=http://<YOUR_DJANGO_SERVER_IP>:8000
SCREEN_ID=lobby_display_01
Run as a Service:
To ensure Screenware starts automatically on boot, copy the provided systemd service file:

Bash
sudo cp screenware.service /etc/systemd/system/
sudo systemctl enable screenware.service
sudo systemctl start screenware.service
📖 Usage
Navigate to http://<YOUR_DJANGO_SERVER_IP>:8000/admin in your web browser.

Log in with the superuser credentials you created.

Add a new Screen record matching the SCREEN_ID you set on your Raspberry Pi.

Start uploading Slides or configuring Widgets (like the Weather module) and assign them to your screens.

The Pi will automatically pick up the new content on its next polling cycle.

🤝 Contributing
Contributions are always welcome. Whether it's fixing a bug, adding a new weather widget, or improving the documentation, feel free to open a Pull Request. Let's keep building the tools we need.

📄 License
This project is licensed under the MIT License - see the LICENSE file for details.
"""

file_path = "/mnt/data/Screenware-README.md"
with open(file_path, "w") as f:
f.write(readme_content)

print(f"File generated successfully at {file_path}")


```text?code_stdout&code_event_index=1
File generated successfully at /mnt/data/Screenware-README.md

Your Markdown file is ready
MD icon
Screenware-README
 MD 
Open

I have drafted a clean, professional README file for the repository. It outlines the core philosophy of the project, breaks down the architecture, and provides clear, step-by-step instructions for getting both the Django server and the edge nodes up and running. It’s structured to make deployment as straightforward as possible for anyone looking to adopt the platform.




Gemini is AI and can make mistakes.

# Screenware

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![Django](https://img.shields.io/badge/django-4.x-green)

**Screenware** is an open-source, lightweight digital signage solution built for spaces that need reliable information displays without the bloated subscriptions or proprietary hardware. Whether you're projecting live announcements across a college campus, displaying the daily Cheyenne weather forecast in the office, or running live metrics for a local tech meetup, Screenware gives you full control of the glass.

Built with a philosophy that infrastructure should be accessible, this system uses a robust **Django** backend to manage content and simple, cheap **Raspberry Pi** nodes at the edge to drive the displays.

---

## 🚀 Features

* **Centralized Django Management:** A clean, easy-to-use web dashboard to schedule slides, text updates, and weather widgets across multiple screens.
* **Resilient Edge Clients:** Runs on standard Raspberry Pi hardware. If a node dies, just image a new SD card and plug it in.
* **Real-Time Updates:** Push announcements and alerts to all screens instantly.
* **100% Free and Open Source:** No per-screen licensing fees, no vendor lock-in. Just code.

---

## 🏗️ Architecture

Screenware is split into two primary components:

1. **The Server (`/server`)**: A Django application that serves as the command center. It manages the database, provides the administrative UI, and exposes an API endpoint for the clients.
2. **The Client (`/client`)**: A lightweight Python script configured to run on a Raspberry Pi in "kiosk mode." It periodically polls the Django server for its assigned content and renders it cleanly on the connected HDMI display.

---

## 🛠️ Server Installation (Django)

We recommend deploying the server on a dedicated VM, Proxmox container, or cloud instance.

### Prerequisites
* Python 3.8+
* `pip` and `virtualenv`

### Setup Steps

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/screenware.git
   cd screenware/server
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run database migrations:**
   ```bash
   python manage.py migrate
   ```

5. **Create an admin account:**
   ```bash
   python manage.py createsuperuser
   ```

6. **Start the server (for development):**
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```
   *Note: For production, we recommend deploying behind Nginx and Gunicorn.*

---

## 📺 Client Installation (Raspberry Pi)

The client is designed to be as "dumb" and resilient as possible. It only requires a basic OS installation and a network connection.

### Prerequisites
* A Raspberry Pi (3B, 4, or Zero 2 W recommended)
* Raspberry Pi OS (Lite or Desktop with UI)
* Internet/Network access to the Django server

### Setup Steps

1. **Flash your SD Card** with Raspberry Pi OS and boot the device.
2. **Configure Kiosk Mode:**
   If using the Desktop version, configure your Pi to auto-login and disable screen blanking/sleep modes in `raspi-config`.

3. **Clone the client script:**
   ```bash
   git clone https://github.com/yourusername/screenware.git
   cd screenware/client
   ```

4. **Install client dependencies:**
   ```bash
   pip3 install -r requirements.txt
   ```

5. **Configure the Client:**
   Edit the `.env` file in the client directory to point to your Django server's IP address and assign the unique Screen ID for this specific Pi.
   ```ini
   SERVER_URL=http://<YOUR_DJANGO_SERVER_IP>:8000
   SCREEN_ID=lobby_display_01
   ```

6. **Run as a Service:**
   To ensure Screenware starts automatically on boot, copy the provided systemd service file:
   ```bash
   sudo cp screenware.service /etc/systemd/system/
   sudo systemctl enable screenware.service
   sudo systemctl start screenware.service
   ```

---

## 📖 Usage

1. Navigate to `http://<YOUR_DJANGO_SERVER_IP>:8000/admin` in your web browser.
2. Log in with the superuser credentials you created.
3. Add a new **Screen** record matching the `SCREEN_ID` you set on your Raspberry Pi.
4. Start uploading **Slides** or configuring **Widgets** (like the Weather module) and assign them to your screens.
5. The Pi will automatically pick up the new content on its next polling cycle.

---

## 🤝 Contributing

Contributions are always welcome. Whether it's fixing a bug, adding a new weather widget, or improving the documentation, feel free to open a Pull Request. Let's keep building the tools we need.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
Screenware-README.md
Displaying Screenware-README.md.
