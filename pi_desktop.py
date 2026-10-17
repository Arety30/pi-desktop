#!/usr/bin/python3
"""Pi Desktop – one-click Remmina session to HOST over Tailscale."""
import os, socket, subprocess, threading, tkinter as tk
from tkinter import ttk

PI_IP = "TAILSCALE_IP"
PI_USER = "user"
VNC_PORT = 5900
HERE = os.path.dirname(os.path.abspath(__file__))
SETUP = os.path.join(HERE, "pi-setup.sh")
PROFILE = os.path.expanduser("~/.local/share/remmina/HOST-tailnet.remmina")
STAMP = os.path.expanduser("~/.local/share/pi-desktop/setup-done")
SSH = ["ssh", "-o", "ConnectTimeout=6", "-o", "StrictHostKeyChecking=accept-new", f"{PI_USER}@{PI_IP}"]


def port_open(host, port, t=2):
    try:
        with socket.create_connection((host, port), timeout=t):
            return True
    except OSError:
        return False


def write_profile():
    os.makedirs(os.path.dirname(PROFILE), exist_ok=True)
    with open(PROFILE, "w") as f:
        f.write(f"""[remmina]
name=HOST (Tailscale)
protocol=VNC
server={PI_IP}:{VNC_PORT}
colordepth=32
quality=9
viewmode=1
scale=1
showcursor=1
window_maximize=1
""")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Pi Desktop")
        self.resizable(False, False)
        self.configure(bg="#1e1e2e")
        s = ttk.Style(self); s.theme_use("clam")
        s.configure("TLabel", background="#1e1e2e", foreground="#cdd6f4", font=("Sans", 11))
        s.configure("H.TLabel", font=("Sans", 16, "bold"))
        s.configure("TButton", font=("Sans", 11), padding=8)
        f = ttk.Frame(self, padding=20, style="TFrame"); s.configure("TFrame", background="#1e1e2e"); f.pack()
        ttk.Label(f, text="🍓  HOST", style="H.TLabel").pack(pady=(0, 6))
        self.status = ttk.Label(f, text="checking…"); self.status.pack(pady=(0, 14))
        self.btn = ttk.Button(f, text="Connect", command=self.connect, width=28); self.btn.pack(pady=3)
        ttk.Button(f, text="Terminal (SSH)", command=self.terminal, width=28).pack(pady=3)
        ttk.Button(f, text="Setup Pi (first time)", command=self.setup, width=28).pack(pady=3)
        ttk.Button(f, text="Reboot Pi", command=self.reboot, width=28).pack(pady=3)
        self.log = ttk.Label(f, text="", font=("Sans", 9), foreground="#a6adc8"); self.log.pack(pady=(12, 0))
        write_profile()
        self.refresh()
        if not os.path.exists(STAMP):
            self.log.config(text="first run: click 'Setup Pi' once the Pi is on")

    def say(self, t): self.after(0, lambda: self.log.config(text=t))

    def refresh(self):
        def go():
            online = port_open(PI_IP, 22)
            vnc = online and port_open(PI_IP, VNC_PORT)
            txt = "🟢 online · VNC ready" if vnc else "🟡 online · VNC not running" if online else "🔴 offline (powered off?)"
            self.after(0, lambda: self.status.config(text=txt))
        threading.Thread(target=go, daemon=True).start()
        self.after(5000, self.refresh)

    def connect(self):
        def go():
            if not port_open(PI_IP, 22):
                self.say("Pi is not reachable on the tailnet"); return
            if not port_open(PI_IP, VNC_PORT):
                self.say("starting wayvnc on the Pi…")
                subprocess.run(SSH + ["systemctl --user start wayvnc-local.service 2>/dev/null || "
                    "(XDG_RUNTIME_DIR=/run/user/1000 WAYLAND_DISPLAY=wayland-0 nohup wayvnc 127.0.0.1 5900 >/dev/null 2>&1 &); "
                    "tailscale serve --bg --tcp 5900 tcp://127.0.0.1:5900 >/dev/null 2>&1; sleep 3"], timeout=40)
                if not port_open(PI_IP, VNC_PORT, 4):
                    self.say("VNC still not reachable – run 'Setup Pi'"); return
            self.say("opening Remmina…")
            subprocess.Popen(["remmina", "-c", PROFILE], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        threading.Thread(target=go, daemon=True).start()

    def terminal(self):
        subprocess.Popen(["x-terminal-emulator", "-e", " ".join(SSH)])

    def setup(self):
        os.makedirs(os.path.dirname(STAMP), exist_ok=True)
        cmd = (f"scp -o StrictHostKeyChecking=accept-new '{SETUP}' {PI_USER}@{PI_IP}:/tmp/pi-setup.sh && "
               f"ssh -t {PI_USER}@{PI_IP} 'bash /tmp/pi-setup.sh' && touch '{STAMP}'; "
               "echo; read -p 'press Enter to close'")
        subprocess.Popen(["x-terminal-emulator", "-e", f"bash -c \"{cmd}\""])

    def reboot(self):
        subprocess.Popen(["x-terminal-emulator", "-e", " ".join(SSH + ["-t", "sudo reboot"])])


if __name__ == "__main__":
    App().mainloop()
