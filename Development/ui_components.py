"""
ui_components.py — Reusable Tkinter button components for the surveillance car GUI.

Provides a ready-made D-pad control panel that can be embedded into any
Tkinter window. Import and use DpadPanel in mqtt_gui_controller.py or
any other Tkinter application.

Usage:
    import tkinter as tk
    from ui_components import DpadPanel

    root = tk.Tk()
    panel = DpadPanel(root, on_command=lambda cmd, spd: print(cmd, spd))
    panel.pack()
    root.mainloop()
"""

import tkinter as tk
from tkinter import ttk


# ── Colour palette ─────────────────────────────────────────────────────────────
COLORS = {
    "bg"      : "#1e1e2e",
    "btn"     : "#45475a",
    "btn_fg"  : "#cdd6f4",
    "btn_stop": "#f38ba8",
    "active"  : "#89b4fa",
    "label"   : "#a6adc8",
}


class DpadPanel(tk.Frame):
    """
    D-pad movement control panel.

    Parameters
    ----------
    parent      : Tkinter parent widget
    on_command  : callable(direction: str, speed: int)
                  Called whenever a button is pressed or released.
    """

    DIRECTIONS = ("forward", "backward", "left", "right", "stop")

    def __init__(self, parent, on_command=None, **kwargs):
        super().__init__(parent, bg=COLORS["bg"], **kwargs)
        self._on_command = on_command or (lambda d, s: None)
        self._speed      = 80
        self._build()

    # ── Internal builders ──────────────────────────────────────────────────────

    def _build(self):
        """Lay out the D-pad grid and speed slider."""
        btn_cfg = {
            "width" : 8, "height": 2,
            "bg"    : COLORS["btn"], "fg": COLORS["btn_fg"],
            "activebackground": COLORS["active"],
            "relief": "raised", "bd": 2, "font": ("Helvetica", 10),
        }

        # ── Forward ───────────────────────────────────────────────────────────
        self._btn_fwd = tk.Button(
            self, text="▲\nForward", **btn_cfg,
            command=lambda: self._send("forward"),
        )
        self._btn_fwd.grid(row=0, column=1, padx=4, pady=4)

        # ── Left ──────────────────────────────────────────────────────────────
        self._btn_left = tk.Button(
            self, text="◄\nLeft", **btn_cfg,
            command=lambda: self._send("left"),
        )
        self._btn_left.grid(row=1, column=0, padx=4, pady=4)

        # ── Stop ──────────────────────────────────────────────────────────────
        self._btn_stop = tk.Button(
            self, text="■\nStop",
            width=8, height=2,
            bg=COLORS["btn_stop"], fg="#1e1e2e",
            activebackground="#eba0ac",
            relief="raised", bd=2, font=("Helvetica", 10, "bold"),
            command=lambda: self._send("stop"),
        )
        self._btn_stop.grid(row=1, column=1, padx=4, pady=4)

        # ── Right ─────────────────────────────────────────────────────────────
        self._btn_right = tk.Button(
            self, text="►\nRight", **btn_cfg,
            command=lambda: self._send("right"),
        )
        self._btn_right.grid(row=1, column=2, padx=4, pady=4)

        # ── Backward ──────────────────────────────────────────────────────────
        self._btn_bwd = tk.Button(
            self, text="▼\nBackward", **btn_cfg,
            command=lambda: self._send("backward"),
        )
        self._btn_bwd.grid(row=2, column=1, padx=4, pady=4)

        # ── Speed slider ──────────────────────────────────────────────────────
        speed_frame = tk.Frame(self, bg=COLORS["bg"])
        speed_frame.grid(row=3, column=0, columnspan=3, pady=(8, 4), sticky="ew")

        tk.Label(
            speed_frame, text="Speed:", bg=COLORS["bg"], fg=COLORS["label"],
        ).pack(side="left", padx=(4, 2))

        self._speed_var = tk.IntVar(value=self._speed)
        tk.Scale(
            speed_frame, from_=0, to=100, orient="horizontal",
            variable=self._speed_var, bg=COLORS["bg"], fg=COLORS["btn_fg"],
            troughcolor="#313244", highlightthickness=0, length=160,
            command=self._on_speed_change,
        ).pack(side="left")

        self._speed_label = tk.Label(
            speed_frame, text="80%", bg=COLORS["bg"], fg=COLORS["active"],
            width=4,
        )
        self._speed_label.pack(side="left")

        # Centre columns
        for col in range(3):
            self.columnconfigure(col, weight=1)

    # ── Callbacks ──────────────────────────────────────────────────────────────

    def _send(self, direction: str):
        self._on_command(direction, self._speed)

    def _on_speed_change(self, value):
        self._speed = int(float(value))
        self._speed_label.config(text=f"{self._speed}%")

    # ── Public API ─────────────────────────────────────────────────────────────

    def set_speed(self, speed: int):
        """Programmatically update the speed slider."""
        self._speed = max(0, min(100, speed))
        self._speed_var.set(self._speed)
        self._speed_label.config(text=f"{self._speed}%")


class StatusBar(tk.Frame):
    """
    Simple one-line status bar showing the last command and connection state.
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg="#313244", **kwargs)
        self._text = tk.StringVar(value="Ready")
        tk.Label(
            self, textvariable=self._text,
            bg="#313244", fg="#cdd6f4", anchor="w",
            font=("Courier", 9), padx=6,
        ).pack(fill="x")

    def update(self, message: str):
        self._text.set(message)


# ── Standalone demo ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    def _demo_handler(direction, speed):
        print(f"[DEMO] direction={direction}  speed={speed}")
        status.update(f"Last: {direction}  speed={speed}%")

    root = tk.Tk()
    root.title("UI Components Demo")
    root.configure(bg=COLORS["bg"])

    tk.Label(
        root, text="D-Pad Demo", bg=COLORS["bg"], fg="#cdd6f4",
        font=("Helvetica", 14, "bold"),
    ).pack(pady=8)

    panel = DpadPanel(root, on_command=_demo_handler)
    panel.pack(padx=16, pady=8)

    status = StatusBar(root)
    status.pack(fill="x", side="bottom")

    root.mainloop()
