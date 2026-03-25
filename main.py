import customtkinter as ctk
import sqlite3
from datetime import datetime
import time
import random
import math
from tkinter import messagebox

# Set the appearance mode and default color theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# --- Custom UI & Animation Components ---

class AnimatedBackgroundCanvas(ctk.CTkCanvas):
    """Draws a dynamic vertical gradient, scalable counter backgrounds, and handles animations."""
    def __init__(self, master, color1, color2, **kwargs):
        super().__init__(master, highlightthickness=0, **kwargs)
        self.color1 = color1
        self.color2 = color2
        self.particles = []
        self.stars = []
        self.counter_bgs = []
        self.bind("<Configure>", self._draw_canvas_elements)

    def add_counter_bg(self, rel_cy, rel_w, rel_h, r, color):
        self.counter_bgs.append({"rel_cy": rel_cy, "rel_w": rel_w, "rel_h": rel_h, "r": r, "color": color})

    def _create_rounded_rect(self, x1, y1, x2, y2, r, **kwargs):
        points = (
            x1+r, y1, x1+r, y1, x2-r, y1, x2-r, y1, x2, y1, x2, y1+r, x2, y1+r,
            x2, y2-r, x2, y2-r, x2, y2, x2-r, y2, x2-r, y2, x1+r, y2, x1+r, y2,
            x1, y2, x1, y2-r, x1, y2-r, x1, y1+r, x1, y1+r, x1, y1
        )
        return self.create_polygon(points, **kwargs, smooth=True)

    def _draw_canvas_elements(self, event=None):
        self.delete("gradient")
        self.delete("counter_bg")
        width = self.winfo_width()
        height = self.winfo_height()
        if height <= 1: return
        
        r1, g1, b1 = self.winfo_rgb(self.color1)
        r2, g2, b2 = self.winfo_rgb(self.color2)
        r_step, g_step, b_step = (r2 - r1) / height, (g2 - g1) / height, (b2 - b1) / height

        for i in range(height):
            nr, ng, nb = int(r1 + (r_step * i)) >> 8, int(g1 + (g_step * i)) >> 8, int(b1 + (b_step * i)) >> 8
            self.create_line(0, i, width, i, tags=("gradient",), fill=f"#{nr:02x}{ng:02x}{nb:02x}")
            
        for bg in self.counter_bgs:
            cx, cy = width / 2, height * bg['rel_cy']
            w, h = width * bg['rel_w'], height * bg['rel_h']
            self._create_rounded_rect(cx - w/2, cy - h/2, cx + w/2, cy + h/2, r=bg['r'], fill=bg['color'], tags=("counter_bg",))
            
        self.tag_lower("counter_bg")
        self.tag_lower("gradient")

    def init_stars(self, rel_y):
        colors = ["#ffffff", "#e2e8f0", "#a8c0ff"]
        for side_offset in [-1, 1]: 
            for _ in range(6):
                offset_x = side_offset * random.randint(70, 130)
                offset_y = random.randint(-15, 15)
                item = self.create_oval(0, 0, 0, 0, fill=random.choice(colors), outline="", tags="star")
                self.stars.append({
                    "id": item, "rel_y": rel_y, "offset_x": offset_x, "offset_y": offset_y,
                    "phase": random.uniform(0, 6.28), "speed": random.uniform(0.03, 0.08)
                })
        self._animate_stars()

    def _animate_stars(self):
        if not self.winfo_exists(): return
        width, height = self.winfo_width(), self.winfo_height()
        cx = width / 2
        for star in self.stars:
            star['phase'] += star['speed']
            r = 1.2 + math.sin(star['phase']) * 1.0 
            bx = cx + star['offset_x']
            by = height * star['rel_y'] + star['offset_y']
            self.coords(star['id'], bx-r, by-r, bx+r, by+r)
        self.after(35, self._animate_stars)

    def spawn_bubbles(self, x, y, width, height):
        colors = ["#ffffff", "#a8c0ff", "#e2e8f0", "#cbd5e1"]
        for _ in range(6): 
            self._add_particle(x, y + height / 2 + random.uniform(-15, 15), 
                               dx=random.uniform(-5, -1.5), dy=random.uniform(-3, 3), color=random.choice(colors))
        for _ in range(6): 
            self._add_particle(x + width, y + height / 2 + random.uniform(-15, 15), 
                               dx=random.uniform(1.5, 5), dy=random.uniform(-3, 3), color=random.choice(colors))

    def _add_particle(self, px, py, dx, dy, color):
        r = random.uniform(3, 7)
        item = self.create_oval(px-r, py-r, px+r, py+r, fill=color, outline="", tags="particle")
        self.particles.append({"id": item, "x": px, "y": py, "dx": dx, "dy": dy, "r": r})
        if len(self.particles) == 1:
            self._animate_particles()

    def _animate_particles(self):
        if not self.particles: return
        active_particles = []
        for p in self.particles:
            p['x'] += p['dx']
            p['y'] += p['dy']
            p['r'] -= 0.25 
            if p['r'] > 0:
                self.coords(p['id'], p['x']-p['r'], p['y']-p['r'], p['x']+p['r'], p['y']+p['r'])
                active_particles.append(p)
            else:
                self.delete(p['id'])
                
        self.particles = active_particles
        if self.particles:
            self.after(16, self._animate_particles)

class ZoomSplashButton(ctk.CTkFrame):
    """Scalable button that zooms in smoothly on press and triggers the bubble splash."""
    def __init__(self, master, text, bg_color, command=None, width=200, height=45, **kwargs):
        super().__init__(master, width=width, height=height, fg_color="transparent", bg_color=bg_color)
        self.pack_propagate(False)
        kwargs.setdefault("corner_radius", 18)
        kwargs.setdefault("font", ("Segoe UI", 13, "bold"))
        
        self.btn = ctk.CTkButton(self, text=text, command=command, bg_color=bg_color, **kwargs)
        self.btn.place(relx=0.5, rely=0.5, anchor="center", relwidth=1.0, relheight=1.0)
        
        self.btn.bind("<ButtonPress-1>", self._on_press, add="+")
        self.btn.bind("<ButtonRelease-1>", self._on_release, add="+")
        self.btn.bind("<Leave>", self._on_release, add="+")

    def _on_press(self, event):
        self.btn.place_configure(relwidth=0.92, relheight=0.90)
        root = self.winfo_toplevel()
        if hasattr(root, 'bg'):
            x = self.winfo_rootx() - root.winfo_rootx()
            y = self.winfo_rooty() - root.winfo_rooty()
            root.bg.spawn_bubbles(x, y, self.winfo_width(), self.winfo_height())

    def _on_release(self, event):
        self.btn.place_configure(relwidth=1.0, relheight=1.0)
        
    def update_bg_color(self, color):
        super().configure(bg_color=color)
        self.btn.configure(bg_color=color)

    def configure(self, **kwargs):
        """Routes configuration correctly to either the Frame or the inner Button."""
        if "bg_color" in kwargs:
            super().configure(bg_color=kwargs["bg_color"])
            
        # Pass all other arguments (like text, fg_color, hover_color) to the actual button
        btn_kwargs = {k: v for k, v in kwargs.items() if k not in ["width", "height"]}
        if btn_kwargs:
            self.btn.configure(**btn_kwargs)

# --- Application Classes ---

class HistoryWindow(ctk.CTkToplevel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.geometry("480x400")
        self.title("Shift History")
        self.attributes('-topmost', True)
        self.configure(fg_color="#0b0f19") 

        ctk.CTkLabel(self, text="WORK HISTORY", font=("Segoe UI", 14, "bold"), text_color="#d8dee9").pack(pady=20)
        self.scroll_frame = ctk.CTkScrollableFrame(self, width=440, height=300, fg_color="transparent")
        self.scroll_frame.pack(pady=10, padx=10, fill="both", expand=True)
        self.load_history()

    def load_history(self):
        for child in self.scroll_frame.winfo_children(): child.destroy()
        try:
            conn = sqlite3.connect('work_data.db')
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM shifts ORDER BY date DESC")
            rows = cursor.fetchall()
            if not rows:
                ctk.CTkLabel(self.scroll_frame, text="No history found yet.", text_color="gray").pack(pady=20)
            for row in rows:
                frame = ctk.CTkFrame(self.scroll_frame, fg_color="#1d2538", corner_radius=10)
                frame.pack(pady=5, padx=10, fill="x")
                ctk.CTkLabel(frame, text=row[0], font=("Segoe UI", 11, "bold"), text_color="#ecf0f1").pack(side="left", padx=10, pady=10)
                ctk.CTkLabel(frame, text=f"Time: {row[3]}", font=("Segoe UI", 12), text_color="#a3be8c").pack(side="right", padx=10)
                ctk.CTkLabel(frame, text=f"P1: {row[2]}", text_color="#ebcb8b", font=("Segoe UI", 12)).pack(side="right", padx=10)
                ctk.CTkLabel(frame, text=f"Dials: {row[1]}", text_color="#88c0d0", font=("Segoe UI", 12)).pack(side="right", padx=10)
            conn.close()
        except Exception as e:
            pass

class GimmieApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Gimmie My Loves")
        self.geometry("320x680")
        self.minsize(300, 600) 
        self.attributes('-topmost', True)

        self.grad_top = "#2c395c"
        self.grad_bottom = "#0b0f19"

        self.bg = AnimatedBackgroundCanvas(self, self.grad_top, self.grad_bottom)
        self.bg.place(relwidth=1, relheight=1)

        self.count = 0
        self.p1_count = 0
        self.start_time = time.time()
        self.elapsed_time = 0
        self.is_running = True
        self.history_window = None
        self.dynamic_bg_widgets = [] 
        
        self.setup_db()
        self.init_ui()
        self.update_timer()
        
        self.bind("<Configure>", self.on_resize)

    def get_bg_color(self, y_pos, total_height):
        if total_height <= 0: return self.grad_top
        y_pos = max(0, min(int(y_pos), total_height))
        r1, g1, b1 = self.winfo_rgb(self.grad_top)
        r2, g2, b2 = self.winfo_rgb(self.grad_bottom)
        ratio = y_pos / float(total_height)
        r, g, b = int(r1 + ((r2 - r1) * ratio)) >> 8, int(g1 + ((g2 - g1) * ratio)) >> 8, int(b1 + ((b2 - b1) * ratio)) >> 8
        return f"#{r:02x}{g:02x}{b:02x}"

    def register_dynamic_bg(self, widget, rely):
        self.dynamic_bg_widgets.append((widget, rely))
        color = self.get_bg_color(rely * 680, 680) 
        if hasattr(widget, 'update_bg_color'):
            widget.update_bg_color(color)
        else:
            widget.configure(bg_color=color)

    def on_resize(self, event):
        if event.widget == self:
            h = self.winfo_height()
            for widget, rely in self.dynamic_bg_widgets:
                color = self.get_bg_color(rely * h, h)
                if hasattr(widget, 'update_bg_color'):
                    widget.update_bg_color(color)
                else:
                    widget.configure(bg_color=color)

    def setup_db(self):
        conn = sqlite3.connect('work_data.db')
        conn.execute('''CREATE TABLE IF NOT EXISTS shifts 
                        (date TEXT, dial_count INTEGER, p1_count INTEGER, duration TEXT)''')
        conn.close()

    def init_ui(self):
        title = ctk.CTkLabel(self, text="GIMMIE MY LOVES", font=("Segoe UI", 13, "bold"), text_color="#ffffff", fg_color="transparent")
        title.place(relx=0.5, rely=0.06, anchor="center")
        self.register_dynamic_bg(title, 0.06)
        
        self.bg.init_stars(rel_y=0.06)

        self.dial_label = self.create_counter_ui("DIAL COUNTER", "count", 0.22)
        self.p1_label = self.create_counter_ui("P1 COUNTER", "p1_count", 0.40)

        session_title = ctk.CTkLabel(self, text="SESSION TIME", font=("Segoe UI", 10, "bold"), text_color="#8f9eb3", fg_color="transparent")
        session_title.place(relx=0.5, rely=0.52, anchor="center")
        self.register_dynamic_bg(session_title, 0.52)

        self.timer_label = ctk.CTkLabel(self, text="00:00:00", font=("Segoe UI Light", 34), text_color="#ffffff", fg_color="transparent")
        self.timer_label.place(relx=0.5, rely=0.58, anchor="center")
        self.register_dynamic_bg(self.timer_label, 0.58)

        self.break_btn = ZoomSplashButton(self, text="Break", bg_color="transparent", fg_color="#b86868", hover_color="#c97a7a", command=self.confirm_break)
        self.break_btn.place(relx=0.5, rely=0.69, relwidth=0.8, relheight=0.065, anchor="center")
        self.register_dynamic_bg(self.break_btn, 0.69)

        self.reset_btn = ZoomSplashButton(self, text="Reset Counters", bg_color="transparent", fg_color="#c98a6c", hover_color="#db9c7e", command=self.reset_counters)
        self.reset_btn.place(relx=0.5, rely=0.77, relwidth=0.8, relheight=0.065, anchor="center")
        self.register_dynamic_bg(self.reset_btn, 0.77)

        self.history_btn = ZoomSplashButton(self, text="View History", bg_color="transparent", fg_color="#5b6678", hover_color="#6c788c", command=self.open_history)
        self.history_btn.place(relx=0.5, rely=0.85, relwidth=0.8, relheight=0.065, anchor="center")
        self.register_dynamic_bg(self.history_btn, 0.85)

        self.save_btn = ZoomSplashButton(self, text="End Shift & Save", bg_color="transparent", fg_color="#9eb586", hover_color="#b0c797", command=self.save_data_and_exit)
        self.save_btn.place(relx=0.5, rely=0.93, relwidth=0.8, relheight=0.065, anchor="center")
        self.register_dynamic_bg(self.save_btn, 0.93)

    def create_counter_ui(self, title, var_name, rely_center):
        frame_color = "#1d2538" 
        
        self.bg.add_counter_bg(rel_cy=rely_center, rel_w=0.85, rel_h=0.15, r=20, color=frame_color)
        
        ctk.CTkLabel(self, text=title, font=("Segoe UI", 10, "bold"), text_color="#8f9eb3", 
                     fg_color="transparent", bg_color=frame_color).place(relx=0.5, rely=rely_center-0.04, anchor="center")
        
        val_label = ctk.CTkLabel(self, text="0", font=("Segoe UI Light", 40), text_color="#ffffff", 
                                 fg_color="transparent", bg_color=frame_color)
        val_label.place(relx=0.5, rely=rely_center+0.02, anchor="center")
        
        def change(amt):
            new_val = max(0, getattr(self, var_name) + amt)
            setattr(self, var_name, new_val)
            val_label.configure(text=str(new_val))

        btn_kwargs = {"corner_radius": 14, "font": ("Segoe UI", 20), "fg_color": "#283145", "hover_color": "#344059", "bg_color": frame_color}
        
        minus = ZoomSplashButton(self, text="−", command=lambda: change(-1), width=40, height=40, **btn_kwargs)
        minus.place(relx=0.22, rely=rely_center+0.02, anchor="center")
        
        plus = ZoomSplashButton(self, text="+", command=lambda: change(1), width=40, height=40, **btn_kwargs)
        plus.place(relx=0.78, rely=rely_center+0.02, anchor="center")
        
        return val_label

    def reset_counters(self):
        if messagebox.askyesno("Reset", "Are you sure you want to clear the counters?"):
            self.count = 0
            self.p1_count = 0
            self.dial_label.configure(text="0")
            self.p1_label.configure(text="0")

    def confirm_break(self):
        if self.is_running:
            if messagebox.askyesno("Confirm Break", "Are you sure you want to start your break?"):
                self.is_running = False
                self.break_btn.configure(text="Resume Shift", fg_color="#9eb586", hover_color="#b0c797")
        else:
            self.is_running = True
            self.break_btn.configure(text="Break", fg_color="#b86868", hover_color="#c97a7a")
            self.start_time = time.time() - self.elapsed_time

    def open_history(self):
        if self.history_window is None or not self.history_window.winfo_exists():
            self.history_window = HistoryWindow(self)
        else:
            self.history_window.focus()
            self.history_window.load_history()

    def save_data_and_exit(self):
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        duration_str = self.timer_label.cget("text")
        try:
            conn = sqlite3.connect('work_data.db')
            conn.execute("INSERT INTO shifts VALUES (?, ?, ?, ?)", (date_str, self.count, self.p1_count, duration_str))
            conn.commit()
            conn.close()
            messagebox.showinfo("Saved", "Shift data has been recorded successfully!")
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Could not save data: {e}")

    def update_timer(self):
        if self.is_running:
            self.elapsed_time = time.time() - self.start_time
            mins, secs = divmod(int(self.elapsed_time), 60)
            hours, mins = divmod(mins, 60)
            self.timer_label.configure(text=f"{hours:02}:{mins:02}:{secs:02}")
        self.after(1000, self.update_timer)

if __name__ == "__main__":
    app = GimmieApp()
    app.mainloop()