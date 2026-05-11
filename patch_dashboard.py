import re
with open('gui_tracker.py', 'r', encoding='utf-8') as f:
    gui = f.read()

dashboard_code = '''    def _build_motor_dashboard(self, parent):
        """Right-side car motor telemetry panel."""
        parent.columnconfigure(0, weight=1)
        CW = 234   # inner canvas / bar width

        # ── Title ─────────────────────────────────────────────────────────────
        ttk.Label(parent, text="Car Motor Dashboard",
                  style="Sidebar.TLabel",
                  font=("Segoe UI", 13, "bold"),
                  anchor="center").pack(fill="x", pady=(18, 4), padx=12)

        ttk.Separator(parent, orient="horizontal").pack(fill="x", padx=12, pady=(0, 10))

        # ── Zone badge ────────────────────────────────────────────────────────
        self._zone_badge = tk.Label(parent, text="IDLE",
                                    bg=MotorDashboard.ZONE_COLOR["IDLE"],
                                    fg="white",
                                    font=("Segoe UI", 14, "bold"),
                                    pady=6)
        self._zone_badge.pack(fill="x", padx=12, pady=(0, 6))

        # ── Distance row ──────────────────────────────────────────────────────
        dist_row = ttk.Frame(parent, style="Sidebar.TFrame")
        dist_row.pack(fill="x", padx=16, pady=(0, 10))
        ttk.Label(dist_row, text="Distance:", style="Sidebar.TLabel",
                  foreground=FG2, font=("Segoe UI", 10)).pack(side="left")
        self._dist_var = tk.StringVar(value="-- cm")
        ttk.Label(dist_row, textvariable=self._dist_var, style="Sidebar.TLabel",
                  font=("Segoe UI", 11, "bold")).pack(side="right")

        # ── Face Position section ─────────────────────────────────────────────
        pos_frame = ttk.LabelFrame(parent, text="Face Position",
                                   style="Sidebar.TLabelframe")
        pos_frame.pack(fill="x", padx=12, pady=(0, 10))

        # Coordinate canvas  (crosshair + deadzone + face dot + arrow)
        self._coord_canvas = tk.Canvas(pos_frame, width=CW, height=110,
                                       bg=BG3, highlightthickness=0)
        self._coord_canvas.pack(padx=8, pady=(8, 4))
        self._draw_coord_canvas()   # draw idle state immediately

        # Numeric readouts
        info_grid = ttk.Frame(pos_frame, style="Sidebar.TFrame")
        info_grid.pack(fill="x", padx=12, pady=(0, 8))
        info_grid.columnconfigure(1, weight=1)

        self._pos_var  = tk.StringVar(value="cx -- / cy --")
        self._errx_var = tk.StringVar(value="--")
        self._erry_var = tk.StringVar(value="--")

        for r, (lbl, var) in enumerate([
            ("Position", self._pos_var),
            ("Error X",  self._errx_var),
            ("Error Y",  self._erry_var),
        ]):
            ttk.Label(info_grid, text=lbl, style="Sidebar.TLabel",
                      foreground=FG2, font=("Segoe UI", 9)).grid(
                      row=r, column=0, sticky="w", pady=1)
            ttk.Label(info_grid, textvariable=var, style="Sidebar.TLabel",
                      font=("Segoe UI", 10, "bold")).grid(
                      row=r, column=1, sticky="e", pady=1)

        # ── Motor Commands section ────────────────────────────────────────────
        cmd_frame = ttk.LabelFrame(parent, text="Motor Commands",
                                   style="Sidebar.TLabelframe")
        cmd_frame.pack(fill="x", padx=12, pady=(0, 10))

        bars_grid = ttk.Frame(cmd_frame, style="Sidebar.TFrame")
        bars_grid.pack(fill="x", padx=8, pady=8)
        bars_grid.columnconfigure(1, weight=1)

        self._left_spd_var  = tk.StringVar(value="0")
        self._right_spd_var = tk.StringVar(value="0")

        for r, (side, var) in enumerate([("L", self._left_spd_var),
                                          ("R", self._right_spd_var)]):
            ttk.Label(bars_grid, text=side, style="Sidebar.TLabel",
                      foreground=FG2, font=("Segoe UI", 10, "bold")).grid(
                      row=r, column=0, sticky="w", padx=(0, 6), pady=3)

            bar_canvas = tk.Canvas(bars_grid, width=CW - 56, height=18,
                                   bg=BG3, highlightthickness=0)
            bar_canvas.grid(row=r, column=1, sticky="ew", pady=3)
            if r == 0:
                self._left_bar_canvas  = bar_canvas
            else:
                self._right_bar_canvas = bar_canvas

            ttk.Label(bars_grid, textvariable=var, style="Sidebar.TLabel",
                      font=("Segoe UI", 10, "bold"), width=4).grid(
                      row=r, column=2, sticky="e", padx=(6, 0), pady=3)

        # ── Steering indicator ────────────────────────────────────────────────
        steer_frame = ttk.LabelFrame(parent, text="Steering",
                                     style="Sidebar.TLabelframe")
        steer_frame.pack(fill="x", padx=12, pady=(0, 12))

        self._steer_canvas = tk.Canvas(steer_frame, width=CW, height=36,
                                       bg=BG3, highlightthickness=0)
        self._steer_canvas.pack(padx=8, pady=8)
        self._draw_steer_canvas(0.0, "#94a3b8")

    # ── Motor display helpers ─────────────────────────────────────────────────

    def _draw_coord_canvas(self):
        c  = self._coord_canvas
        c.delete("all")
        W, H  = 234, 110
        cx, cy = W // 2, H // 2

        # Grid lines
        c.create_line(cx, 0, cx, H, fill=BG2, width=1)
        c.create_line(0, cy, W, cy, fill=BG2, width=1)

        # Dead-zone box
        SCALE_X = (W // 2 - 6) / 320.0
        SCALE_Y = (H // 2 - 6) / 240.0
        dz_px = int(MotorDashboard.DEAD_PX * SCALE_X)
        dz_py = int(MotorDashboard.DEAD_PX * SCALE_Y)
        c.create_rectangle(cx - dz_px, cy - dz_py, cx + dz_px, cy + dz_py,
                           outline="#475569", width=1, dash=(4, 3))

        m = self.motor
        if m.state == "IDLE":
            c.create_oval(cx - 4, cy - 4, cx + 4, cy + 4,
                          fill="#475569", outline="")
            return

        color = MotorDashboard.ZONE_COLOR.get(m.state, "#94a3b8")
        fx = int(cx + m.error_x * SCALE_X)
        fy = int(cy + m.error_y * SCALE_Y)
        fx = max(6, min(W - 6, fx))
        fy = max(6, min(H - 6, fy))

        # Arrow from center to face position
        if abs(m.error_x) > 4 or abs(m.error_y) > 4:
            c.create_line(cx, cy, fx, fy, fill=color, width=2,
                          arrow=tk.LAST, arrowshape=(8, 10, 4))

        # Center dot
        c.create_oval(cx - 3, cy - 3, cx + 3, cy + 3,
                      fill="#64748b", outline="")
        # Face dot
        c.create_oval(fx - 6, fy - 6, fx + 6, fy + 6,
                      fill=color, outline="white", width=1)

    def _draw_speed_bar(self, canvas: tk.Canvas, speed: int, color: str):
        canvas.delete("all")
        W = canvas.winfo_width() or (234 - 56)
        H = 18
        fill_w = int(speed / 255.0 * W)
        canvas.create_rectangle(0, 0, W, H, fill=BG2, outline="")
        if fill_w > 0:
            canvas.create_rectangle(0, 0, fill_w, H, fill=color, outline="")

    def _draw_steer_canvas(self, error_x: float, color: str):
        c  = self._steer_canvas
        c.delete("all")
        W, H = 234, 36
        cx, cy = W // 2, H // 2

        # Track line
        c.create_line(10, cy, W - 10, cy, fill="#334155", width=2)
        # Center tick
        c.create_line(cx, cy - 6, cx, cy + 6, fill="#475569", width=1)

        # Clamp and scale steering arrow
        clamped = max(-320.0, min(320.0, error_x))
        tip_x   = int(cx + clamped * ((W // 2 - 12) / 320.0))
        tip_x   = max(12, min(W - 12, tip_x))

        if abs(error_x) < MotorDashboard.DEAD_PX:
            c.create_oval(cx - 5, cy - 5, cx + 5, cy + 5,
                          fill=color, outline="")
        else:
            c.create_line(cx, cy, tip_x, cy, fill=color, width=3,
                          arrow=tk.LAST, arrowshape=(10, 12, 5))

    def _update_motor_display(self):
        """Refresh all motor dashboard widgets from current self.motor state."""
        m     = self.motor
        color = MotorDashboard.ZONE_COLOR.get(m.state, "#94a3b8")

        # Zone badge
        self._zone_badge.config(text=m.state, bg=color)

        # Distance
        if m.distance_cm < 9000:
            self._dist_var.set(f"{m.distance_cm:.0f} cm")
        else:
            self._dist_var.set("-- cm")

        # Coordinate readouts
        if m.state != "IDLE":
            sign_x = "+" if m.error_x >= 0 else ""
            sign_y = "+" if m.error_y >= 0 else ""
            self._pos_var.set(f"cx {m.cx}  /  cy {m.cy}")
            self._errx_var.set(f"{sign_x}{m.error_x:.0f} px")
            self._erry_var.set(f"{sign_y}{m.error_y:.0f} px")
        else:
            self._pos_var.set("cx --  /  cy --")
            self._errx_var.set("--")
            self._erry_var.set("--")

        # Coordinate canvas
        self._draw_coord_canvas()

        # Speed bar values
        self._left_spd_var.set(str(m.left_speed))
        self._right_spd_var.set(str(m.right_speed))
        self._draw_speed_bar(self._left_bar_canvas,  m.left_speed,  color)
        self._draw_speed_bar(self._right_bar_canvas, m.right_speed, color)

        # Steering canvas
        self._draw_steer_canvas(m.error_x, color)

'''

if 'def _build_motor_dashboard' not in gui:
    gui = gui.replace('    # =========================================================================\n    # Camera loop (background thread)', dashboard_code + '\n    # =========================================================================\n    # Camera loop (background thread)')

with open('gui_tracker.py', 'w', encoding='utf-8') as f:
    f.write(gui)
print("Dashboard patch completed")
