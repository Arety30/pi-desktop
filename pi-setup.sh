#!/bin/bash
# Runs ON the Pi (once). Makes wayvnc persistent and exposes it on the tailnet only.
set -e
echo "== HOST VNC setup =="

# 1. wayvnc as a user service that waits for the Wayland desktop
mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/wayvnc-local.service <<'UNIT'
[Unit]
Description=wayvnc on 127.0.0.1:5900 (tailnet access via tailscale serve)
After=default.target

[Service]
Environment=XDG_RUNTIME_DIR=/run/user/1000
Environment=WAYLAND_DISPLAY=wayland-0
ExecStartPre=/bin/sh -c 'until [ -S /run/user/1000/wayland-0 ]; do sleep 2; done'
ExecStart=/usr/bin/wayvnc 127.0.0.1 5900
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
UNIT
systemctl --user daemon-reload
systemctl --user enable --now wayvnc-local.service
sudo loginctl enable-linger abrar

# 2. Expose port 5900 to the tailnet only (WireGuard-encrypted, never public)
sudo tailscale set --operator=abrar
tailscale serve --bg --tcp 5900 tcp://127.0.0.1:5900
tailscale serve status

echo "== done: VNC reachable at $(tailscale ip -4):5900 from any tailnet device =="
