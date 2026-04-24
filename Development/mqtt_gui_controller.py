"""
mqtt_gui_controller.py — Tkinter GUI controller for the Surveillance Car (laptop).

Responsibilities:
  1. Connect to the MQTT broker (local or WAN) via ConnectionManager
  2. Publish movement commands to dev/motor
  3. Publish system commands to dev/commands (servo, LED, buzzer)
  4. Subscribe to dev/status and display live feedback
  5. Allow switching between local and cloud broker at runtime

Run on your laptop:
  python mqtt_gui_controller.py

Requirements:
  pip install paho-mqtt
  tkinter is included with standard Python on Windows/macOS/Linux
"""

import json
import time
import os
import tkinter as tk
from tkinter import scrolledtext

import paho.mqtt.client as mqtt
from connection_manager import ConnectionManager

# ─── Config path ──────────────────────────────────────────────────────────────
# Looks for client_config.json in surveillance-car/mqtt-config/ (one level up)
_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "surveillance-car", "mqtt-config", "client_config.json"
)

# ─── Load topics from config ──────────────────────────────────────────────────
def _load_topics() -> dict:
    try:
        with open(_CONFIG_PATH) as f:
            cfg = json.load(f)
        return cfg.get("topics", {})
    except Exception:
        return {}

_topics        = _load_topics()
TOPIC_MOTOR    = _topics.get("motor",    "dev/motor")
TOPIC_LED      = _topics.get("led",      "dev/led")
TOPIC_COMMANDS = _topics.get("commands", "dev/commands")
TOPIC_STATUS   = _topics.get("status",   "dev/status")


# ─── GUI Application ──────────────────────────────────────────────────────────

class SurveillanceCarGUI:
    """Main Tkinter window for controlling the surveillance car over MQTT."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Surveillance Car — MQTT Controller")
        self.root.resizable(False, False)

        # MQTT state
        self._client: mqtt.Client = None
        self._manager    = ConnectionManager(config_path=_CONFIG_PATH)
        self._connected  = False
        self._current_speed = 80
        self._current_servo = 90

        self._build_ui()
        self._bind_keys()
        self.root.after(300, self._connect)   # auto-connect after window opens

    # ─── UI construction ──────────────────────────────────────────────────────

    def _build_ui(self):
        PAD = {"padx": 6, "pady": 4}
        self.root.configure(bg="#1e1e2e")

        # ── Title ─────────────────────────────────────────────────────────────
        tk.Label(
            self.root, text="🚗  Surveillance Car Controller",
            font=("Helvetica", 16, "bold"), bg="#1e1e2e", fg="#cdd6f4",
        ).pack(fill="x", ipady=8)

        # ── Connection bar ────────────────────────────────────────────────────
        bar = tk.Frame(self.root, bg="#313244")
        bar.pack(fill="x", padx=8, pady=(4, 0))

        tk.Label(bar, text="Broker:", bg="#313244", fg="#a6adc8").pack(side="left", **PAD)
        self._broker_var = tk.StringVar(value="Loading…")
        tk.Label(bar, textvariable=self._broker_var, bg="#313244", fg="#89b4fa").pack(side="left")

        tk.Label(bar, text="  Status:", bg="#313244", fg="#a6adc8").pack(side="left")
        self._status_var   = tk.StringVar(value="Disconnected")
        self._status_label = tk.Label(
            bar, textvariable=self._status_var,
            bg="#313244", fg="#f38ba8", font=("Helvetica", 10, "bold"),
        )
        self._status_label.pack(side="left", **PAD)

        # Broker mode toggle (Local / Cloud)
        self._mode_var = tk.StringVar(value="cloud")
        tk.Label(bar, text="Mode:", bg="#313244", fg="#a6adc8").pack(side="right")
        tk.Radiobutton(
            bar, text="Cloud", variable=self._mode_var, value="cloud",
            bg="#313244", fg="#fab387", selectcolor="#313244",
            command=self._switch_broker,
        ).pack(side="right", **PAD)
        tk.Radiobutton(
            bar, text="Local", variable=self._mode_var, value="local",
            bg="#313244", fg="#a6e3a1", selectcolor="#313244",
            command=self._switch_broker,
        ).pack(side="right", **PAD)

        # ── D-Pad ─────────────────────────────────────────────────────────────
        dpad = tk.LabelFrame(
            self.root, text=" Movement ", bg="#1e1e2e", fg="#cdd6f4",
            font=("Helvetica", 10, "bold"),
        )
        dpad.pack(padx=10, pady=8, fill="x")

        btn = {"width": 8, "height": 2, "bg": "#45475a", "fg": "#cdd6f4",
               "activebackground": "#89b4fa", "relief": "raised", "bd": 2}

        tk.Button(dpad, text="▲\nForward",  **btn,
                  command=lambda: self._send_motor("forward")).grid(row=0, column=1, padx=4, pady=4)
        tk.Button(dpad, text="◄\nLeft",     **btn,
                  command=lambda: self._send_motor("left")).grid(row=1, column=0, padx=4, pady=4)
        tk.Button(dpad, text="■\nStop",     width=8, height=2,
                  bg="#f38ba8", fg="#1e1e2e", activebackground="#eba0ac",
                  relief="raised", bd=2,
                  command=lambda: self._send_motor("stop")).grid(row=1, column=1, padx=4, pady=4)
        tk.Button(dpad, text="►\nRight",    **btn,
                  command=lambda: self._send_motor("right")).grid(row=1, column=2, padx=4, pady=4)
        tk.Button(dpad, text="▼\nBackward", **btn,
                  command=lambda: self._send_motor("backward")).grid(row=2, column=1, padx=4, pady=4)

        for col in range(3):
            dpad.columnconfigure(col, weight=1)

        # ── Speed slider ──────────────────────────────────────────────────────
        sf = tk.Frame(self.root, bg="#1e1e2e")
        sf.pack(fill="x", padx=10)
        tk.Label(sf, text="Speed:", bg="#1e1e2e", fg="#a6adc8").pack(side="left")
        self._speed_var = tk.IntVar(value=80)
        tk.Scale(
            sf, from_=0, to=100, orient="horizontal", variable=self._speed_var,
            bg="#1e1e2e", fg="#cdd6f4", troughcolor="#313244",
            highlightthickness=0, length=200, command=self._on_speed_change,
        ).pack(side="left", padx=6)
        self._speed_label = tk.Label(sf, text="80%", bg="#1e1e2e", fg="#89b4fa")
        self._speed_label.pack(side="left")

        # ── Servo slider ──────────────────────────────────────────────────────
        svf = tk.Frame(self.root, bg="#1e1e2e")
        svf.pack(fill="x", padx=10, pady=4)
        tk.Label(svf, text="Servo:", bg="#1e1e2e", fg="#a6adc8").pack(side="left")
        self._servo_var = tk.IntVar(value=90)
        tk.Scale(
            svf, from_=0, to=180, orient="horizontal", variable=self._servo_var,
            bg="#1e1e2e", fg="#cdd6f4", troughcolor="#313244",
            highlightthickness=0, length=200, command=self._on_servo_change,
        ).pack(side="left", padx=6)
        self._servo_label = tk.Label(svf, text="90°", bg="#1e1e2e", fg="#89b4fa")
        self._servo_label.pack(side="left")

        # ── Peripheral buttons ────────────────────────────────────────────────
        pf = tk.LabelFrame(
            self.root, text=" Peripherals ", bg="#1e1e2e", fg="#cdd6f4",
            font=("Helvetica", 10, "bold"),
        )
        pf.pack(padx=10, pady=4, fill="x")
        pbtn = {"width": 9, "bg": "#45475a", "fg": "#cdd6f4",
                "activebackground": "#a6e3a1", "relief": "raised", "bd": 2}
        tk.Button(pf, text="💡 LED On",  **pbtn, command=lambda: self._send_led("on")).pack(side="left", padx=4, pady=6)
        tk.Button(pf, text="🌑 LED Off", **pbtn, command=lambda: self._send_led("off")).pack(side="left", padx=4, pady=6)
        tk.Button(pf, text="✨ Blink",   **pbtn, command=lambda: self._send_led("blink")).pack(side="left", padx=4, pady=6)
        tk.Button(pf, text="🔔 Beep",    **pbtn, command=self._send_beep).pack(side="left", padx=4, pady=6)
        tk.Button(pf, text="🎯 Center",  **pbtn, command=self._center_servo).pack(side="left", padx=4, pady=6)

        # ── Pi status ─────────────────────────────────────────────────────────
        inf = tk.LabelFrame(
            self.root, text=" Pi Status ", bg="#1e1e2e", fg="#cdd6f4",
            font=("Helvetica", 10, "bold"),
        )
        inf.pack(padx=10, pady=4, fill="x")
        self._pi_status_var = tk.StringVar(value="—")
        tk.Label(inf, textvariable=self._pi_status_var,
                 bg="#1e1e2e", fg="#a6e3a1", font=("Courier", 9)).pack(anchor="w", padx=6, pady=4)

        # ── Log box ───────────────────────────────────────────────────────────
        lf = tk.LabelFrame(
            self.root, text=" Log ", bg="#1e1e2e", fg="#cdd6f4",
            font=("Helvetica", 10, "bold"),
        )
        lf.pack(padx=10, pady=(4, 8), fill="both", expand=True)
        self._log = scrolledtext.ScrolledText(
            lf, height=8, bg="#181825", fg="#cdd6f4",
            font=("Courier", 9), state="disabled", wrap="word",
        )
        self._log.pack(fill="both", expand=True, padx=4, pady=4)

    # ─── Keyboard bindings ────────────────────────────────────────────────────

    def _bind_keys(self):
        move_map = {
            "<Up>": "forward", "<Down>": "backward",
            "<Left>": "left",  "<Right>": "right",
            "<space>": "stop",
            "w": "forward", "s": "backward", "a": "left", "d": "right",
        }
        for key, direction in move_map.items():
            self.root.bind(key, lambda e, d=direction: self._send_motor(d))

        # Key-release → stop
        for key in ("<Up>", "<Down>", "<Left>", "<Right>", "w", "s", "a", "d"):
            release = key.replace("<", "<KeyRelease-") if "<" in key else f"<KeyRelease-{key}>"
            self.root.bind(release, lambda e: self._send_motor("stop"))

        self.root.bind("q", lambda e: self._adjust_servo(-10))
        self.root.bind("e", lambda e: self._adjust_servo(+10))

    # ─── MQTT connection ──────────────────────────────────────────────────────

    def _connect(self):
        mode = self._mode_var.get()
        self._log_msg(f"Connecting ({mode} mode)…")
        self._client = self._manager.build_client(
            client_id     = "mqtt-gui-controller",
            on_connect    = self._on_connect,
            on_disconnect = self._on_disconnect,
            on_message    = self._on_message,
        )
        self._manager.connect(self._client, mode=mode)
        self._client.loop_start()
        info = self._manager.get_broker_info(mode)
        self._broker_var.set(f"{info['host']}:{info['port']}")

    def _switch_broker(self):
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()
        self._connected = False
        self._update_status_label(False)
        self.root.after(500, self._connect)

    # ─── MQTT callbacks ───────────────────────────────────────────────────────

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self._connected = True
            client.subscribe(TOPIC_STATUS, qos=1)
            self._log_msg(f"Connected ✓  (subscribed to {TOPIC_STATUS})")
            self.root.after(0, lambda: self._update_status_label(True))
        else:
            self._log_msg(f"Connection failed, rc={rc}", level="error")

    def _on_disconnect(self, client, userdata, rc):
        self._connected = False
        self._log_msg(f"Disconnected (rc={rc})", level="warn")
        self.root.after(0, lambda: self._update_status_label(False))

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            self.root.after(0, lambda p=payload: self._display_pi_status(p))
        except Exception as e:
            self._log_msg(f"Status parse error: {e}", level="error")

    # ─── Publish helpers ──────────────────────────────────────────────────────

    def _publish(self, topic: str, payload: dict, qos: int = 1):
        if not self._connected or not self._client:
            self._log_msg("Not connected — command dropped", level="warn")
            return
        self._client.publish(topic, json.dumps(payload), qos=qos)
        self._log_msg(f"→ {topic}: {payload}")

    def _send_motor(self, direction: str):
        self._publish(TOPIC_MOTOR, {"direction": direction, "speed": self._current_speed})

    def _send_led(self, state: str):
        self._publish(TOPIC_LED, {"state": state})

    def _send_beep(self):
        self._publish(TOPIC_COMMANDS, {"command": "BEEP"})

    def _center_servo(self):
        self._servo_var.set(90)
        self._current_servo = 90
        self._servo_label.config(text="90°")
        self._publish(TOPIC_COMMANDS, {"command": "SERVO", "angle": 90})

    def _adjust_servo(self, delta: int):
        new_angle = max(0, min(180, self._current_servo + delta))
        self._servo_var.set(new_angle)
        self._current_servo = new_angle
        self._servo_label.config(text=f"{new_angle}°")
        self._publish(TOPIC_COMMANDS, {"command": "SERVO", "angle": new_angle})

    # ─── Slider callbacks ─────────────────────────────────────────────────────

    def _on_speed_change(self, value):
        self._current_speed = int(float(value))
        self._speed_label.config(text=f"{self._current_speed}%")

    def _on_servo_change(self, value):
        angle = int(float(value))
        self._current_servo = angle
        self._servo_label.config(text=f"{angle}°")
        self._publish(TOPIC_COMMANDS, {"command": "SERVO", "angle": angle})

    # ─── UI helpers ───────────────────────────────────────────────────────────

    def _update_status_label(self, connected: bool):
        if connected:
            self._status_var.set("Connected")
            self._status_label.config(fg="#a6e3a1")
        else:
            self._status_var.set("Disconnected")
            self._status_label.config(fg="#f38ba8")

    def _display_pi_status(self, payload: dict):
        parts = []
        if "status"  in payload: parts.append(f"status={payload['status']}")
        if "command" in payload: parts.append(f"cmd={payload['command']}")
        if "speed"   in payload: parts.append(f"speed={payload['speed']}%")
        if "servo"   in payload: parts.append(f"servo={payload['servo']}°")
        if "type"    in payload: parts.append(f"⚠ {payload.get('message', 'alert')}")
        self._pi_status_var.set("  ".join(parts) if parts else str(payload))

    def _log_msg(self, message: str, level: str = "info"):
        def _append():
            ts     = time.strftime("%H:%M:%S")
            prefix = {"info": "ℹ", "warn": "⚠", "error": "✖"}.get(level, "ℹ")
            self._log.config(state="normal")
            self._log.insert("end", f"[{ts}] {prefix} {message}\n")
            self._log.see("end")
            self._log.config(state="disabled")
        self.root.after(0, _append)

    def on_close(self):
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()
        self.root.destroy()


# ─── Entry point ──────────────────────────────────────────────────────────────

def main():
    root = tk.Tk()
    app  = SurveillanceCarGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
