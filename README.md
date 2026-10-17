# Pi Desktop

Pi Desktop is a one-click launcher by Syed Abrar Ali for opening a remote desktop session to a Raspberry Pi 5 over a Tailscale tailnet. A Pi running a Wayland desktop has no built-in remote display that "just works" from another machine; this tool installs `wayvnc` on the Pi as a persistent user service bound to localhost, publishes that port only inside the tailnet with `tailscale serve`, writes a matching Remmina VNC profile on the laptop, and gives a tiny Tk window with Connect / Terminal / Setup / Reboot buttons and a live online indicator.

## Where it is used

Abrar keeps a headless Pi 5 on his network as a small always-on server. Pi Desktop is the desktop shortcut on his laptop that gets him to the Pi's graphical session (or an SSH terminal) in one click, wherever the laptop is, as long as both devices are on the tailnet. The first-run "Setup Pi" button does the one-time provisioning on the Pi itself.

## How it works

### `pi_desktop.py` (runs on the laptop)

- Constants at the top: `PI_IP` (the Pi's tailnet IP), `PI_USER`, `VNC_PORT = 5900`. From them it derives the SSH command (`ssh -o ConnectTimeout=6 -o StrictHostKeyChecking=accept-new PI_USER@PI_IP`), the Remmina profile path `~/.local/share/remmina/HOST-tailnet.remmina` and a first-run stamp file `~/.local/share/pi-desktop/setup-done`.
- `write_profile()` (re)writes the Remmina profile on every start: protocol VNC, `server=PI_IP:5900`, 32-bit colour, quality 9, scaled view, maximised window.
- `refresh()` runs every 5 s in a thread: a TCP connect to port 22 means "online", port 5900 means "VNC ready"; the label shows one of online/VNC ready, online/VNC not running, offline.
- **Connect**: if port 22 is closed, report unreachable. If 5900 is closed, SSH in and run `systemctl --user start wayvnc-local.service`, falling back to launching `wayvnc 127.0.0.1 5900` directly with `XDG_RUNTIME_DIR=/run/user/1000` and `WAYLAND_DISPLAY=wayland-0`, then `tailscale serve --bg --tcp 5900 tcp://127.0.0.1:5900`. When 5900 answers, launch `remmina -c <profile>`.
- **Terminal (SSH)**: opens `x-terminal-emulator -e ssh ...`.
- **Setup Pi (first time)**: `scp` copies `pi-setup.sh` to `/tmp` on the Pi, runs it with `ssh -t`, and touches the stamp file on success.
- **Reboot Pi**: `ssh -t ... sudo reboot` in a terminal.

### `pi-setup.sh` (runs once on the Pi)

1. Writes `~/.config/systemd/user/wayvnc-local.service`: waits until `/run/user/1000/wayland-0` exists, then runs `/usr/bin/wayvnc 127.0.0.1 5900`, `Restart=always`. Enables and starts it, and enables linger so the user session (and thus wayvnc) starts at boot without a login.
2. `tailscale set --operator=<user>` so the unprivileged user can run `tailscale serve`, then `tailscale serve --bg --tcp 5900 tcp://127.0.0.1:5900`, which exposes VNC to tailnet peers only (never to the LAN or the Internet). Prints the resulting tailnet address.

| File | Role |
|------|------|
| `pi_desktop.py` | Tk GUI, Remmina profile writer, reachability checks, remote start of wayvnc |
| `pi-setup.sh` | One-time Pi provisioning: wayvnc user service + tailnet-only exposure |

## Setup

Laptop requirements: Python 3 with Tk (`python3-tk`), `remmina` with its VNC plugin (`remmina-plugin-vnc`), OpenSSH client, an `x-terminal-emulator` alternative, and Tailscale logged in to the same tailnet as the Pi. SSH key authentication to the Pi is assumed (the Connect button runs non-interactive `ssh`).

Pi requirements: Raspberry Pi OS (or similar) with a Wayland desktop session for the user, `wayvnc`, `tailscale` joined to the tailnet, `sudo` rights for the user, and the user's runtime dir at `/run/user/1000`.

```bash
git clone <repo-url> ~/pi-desktop
cd ~/pi-desktop
sudo apt install python3-tk remmina remmina-plugin-vnc
```

Edit the constants in `pi_desktop.py`:

```python
PI_IP = "TAILSCALE_IP"      # the Pi's Tailscale IPv4 (tailscale ip -4 on the Pi)
PI_USER = "pi"            # login user on the Pi
VNC_PORT = 5900
```

Also replace the user name used by `loginctl enable-linger` and `tailscale set --operator=` in `pi-setup.sh` with the same `PI_USER`.

## Usage

```bash
python3 pi_desktop.py
```

1. First run: power on the Pi, wait for the status to show "online", click **Setup Pi (first time)** and follow the terminal (it will prompt for `sudo` on the Pi).
2. Afterwards click **Connect**; Remmina opens the Pi's desktop. If wayvnc is not running yet, the tool starts it over SSH first.
3. **Terminal (SSH)** opens a shell; **Reboot Pi** reboots it.

Optional desktop entry (`~/.local/share/applications/pi-desktop.desktop`):

```ini
[Desktop Entry]
Type=Application
Name=Pi Desktop
Exec=python3 /home/USER/pi-desktop/pi_desktop.py
Terminal=false
```

## Project structure

```
pi-desktop/
├── pi_desktop.py     # launcher GUI
└── pi-setup.sh       # provisioning script executed on the Pi
```

## Limitations and notes

- VNC here is unencrypted on the wire but only reachable through Tailscale's WireGuard tunnel; it is never exposed on the LAN or public Internet. Do not change `wayvnc 127.0.0.1` to `0.0.0.0`.
- The Pi's IP, user and UID 1000 are hard-coded; a different user id requires editing both files.
- `wayvnc` needs an active Wayland session; a Pi that boots to the console (no desktop autologin) will show "VNC not running" until a session exists.
- The tool does not configure VNC authentication; it relies on the tailnet as the trust boundary.
- Tested with Remmina on Ubuntu; other VNC viewers would need their own profile.
