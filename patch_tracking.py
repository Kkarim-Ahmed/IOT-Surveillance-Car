import re
with open('gui_tracker.py', 'r', encoding='utf-8') as f:
    gui = f.read()

tracking_update = '''        # Step 1: Try face tracking first
        if self.face_locations:
            # Always update motor dashboard with the largest face
            best_i, best_area = 0, 0
            for i, (top, right, bottom, left) in enumerate(self.face_locations):
                a = (right - left) * (bottom - top)
                if a > best_area:
                    best_area, best_i = a, i
            t, r, b, l = self.face_locations[best_i]
            fw = getattr(config, 'FRAME_WIDTH', 640)
            fh = getattr(config, 'FRAME_HEIGHT', 480)
            self.motor.update((l, t, r, b), fw, fh)

            # Face detected - do face tracking
            if self.servo_var.get():'''

if 'self.motor.update(' not in gui:
    gui = gui.replace('''        # Step 1: Try face tracking first
        if self.face_locations:
            # Face detected - do face tracking
            if self.servo_var.get():''', tracking_update)

search_update = '''                        self.tracking_mode = "lost"
                        self.target_body_box = None
                        self.motor.search()
                        print(f"❌ Lost tracking of {self.target_identity} completely")'''

if 'self.motor.search()' not in gui:
    gui = gui.replace('''                        self.tracking_mode = "lost"
                        self.target_body_box = None
                        print(f"❌ Lost tracking of {self.target_identity} completely")''', search_update)

search_update2 = '''                try:
                    if self.mode == "tracking":
                        self._process_enhanced_tracking()
                        self._update_tracking_llm_event()
                        
                        # If no face found in tracking mode, spin toward last-known side
                        if not self.face_locations:
                            self.motor.search(last_error_x=self.motor.error_x)
                except Exception as e:'''

if 'self.motor.search(last_error_x' not in gui:
    gui = gui.replace('''                try:
                    if self.mode == "tracking":
                        self._process_enhanced_tracking()
                        self._update_tracking_llm_event()
                except Exception as e:''', search_update2)

refresh_update = '''                # Performance tracking ──────────────────────────────────────────
                try:
                    elapsed = time.time() - start_time
                    fps = 1.0 / elapsed if elapsed > 0 else 0
                    self.fps_queue.append(fps)
                    self._update_performance_stats(detection_time, recognition_time)
                    self.root.after(0, self._update_performance_display)
                except Exception as e:
                    print(f"Performance tracking error: {e}")
                    
                # Always refresh motor dashboard regardless of other errors
                self.root.after(0, self._update_motor_display)

                self.frame_count += 1'''

if 'self._update_motor_display' not in gui:
    gui = re.sub(r'                # Performance tracking ──────────────────────────────────────────.*?self\.frame_count \+= 1', refresh_update, gui, flags=re.DOTALL)

with open('gui_tracker.py', 'w', encoding='utf-8') as f:
    f.write(gui)
print("Tracking patch completed")
