import customtkinter as ctk
import sqlite3
from datetime import datetime
import time
import random
import math
from tkinter import messagebox, simpledialog
from PIL import Image, ImageDraw, ImageTk
import os

# Set the appearance mode and default color theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# --- High-Fidelity Asset Generator --

class AssetFactory:
    """Generates perfectly anti-aliased images for the canvas to prevent pixelated edges."""
    
    @staticmethod
    def create_rounded_panel(width, height, radius, color):
        w, h, r = max(1, int(width)), max(1, int(height)), max(1, int(radius))
        scale = 4 
        img = Image.new("RGBA", (w*scale, h*scale), (0,0,0,0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle((0, 0, w*scale, h*scale), radius=r*scale, fill=color)
        return ImageTk.PhotoImage(img.resize((w, h), Image.LANCZOS)) 

    @staticmethod
    def create_moon(radius, color):
        r = int(radius)
        scale = 4
        img = Image.new("RGBA", (r*2*scale, r*2*scale), (0,0,0,0))
        draw = ImageDraw.Draw(img)
        draw.ellipse((0, 0, r*2*scale, r*2*scale), fill=color)
        return ImageTk.PhotoImage(img.resize((r*2, r*2), Image.LANCZOS))

    @staticmethod
    def create_cloud(color, offsets):
        scale = 4
        min_x = min(dx for dx, dy, length in offsets)
        max_x = max(dx + length for dx, dy, length in offsets)
        min_y = min(dy for dx, dy, length in offsets) - 10
        max_y = max(dy for dx, dy, length in offsets) + 10
        
        w = int(max_x - min_x + 20)
        h = int(max_y - min_y + 20)
        
        img = Image.new("RGBA", (w*scale, h*scale), (0,0,0,0))
        draw = ImageDraw.Draw(img)
        
        for dx, dy, length in offsets:
            start_x = int((dx - min_x + 10) * scale)
            start_y = int((dy - min_y + 10) * scale)
            end_x = int(start_x + (length * scale))
            draw.rounded_rectangle(
                (start_x, start_y - 10*scale, end_x, start_y + 10*scale), 
                radius=10*scale, fill=color
            )
            
        return ImageTk.PhotoImage(img.resize((w, h), Image.LANCZOS))

    @staticmethod
    def create_meteor(length):
        scale = 4
        w, h = int(length), int(length)
        img = Image.new("RGBA", (w*scale, h*scale), (0,0,0,0))
        draw = ImageDraw.Draw(img)
        draw.line([(w*scale, 0), (0, h*scale)], fill="#ffffff", width=2*scale)
        return ImageTk.PhotoImage(img.resize((w, h), Image.LANCZOS))


# --- Custom UI & Animation Components ---

class AnimatedBackgroundCanvas(ctk.CTkCanvas):
    def __init__(self, master, color1, color2, **kwargs):
        super().__init__(master, highlightthickness=0, **kwargs)
        self.color1 = color1
        self.color2 = color2
        self.particles = []
        self.stars = []
        self.meteors = []
        self.counter_bgs = []
        self.dynamic_texts = {} 
        self.images = {} 
        self._resize_timer = None
        
        self._init_clouds()
        self._animate_clouds()
        self._meteor_spawner()
        
        self.bind("<Configure>", self._on_resize)

    def add_counter_bg(self, rel_cy, rel_w, rel_h, r, color):
        self.counter_bgs.append({"rel_cy": rel_cy, "rel_w": rel_w, "rel_h": rel_h, "r": r, "color": color})
        self._draw_canvas_elements() 

    def set_dynamic_text(self, tag, rel_x, rel_y, text, font, fill):
        if tag not in self.dynamic_texts:
            item = self.create_text(0, 0, text=text, font=font, fill=fill, tags=("dynamic_text", tag), justify="center")
            self.dynamic_texts[tag] = {"id": item, "rel_x": rel_x, "rel_y": rel_y}
        else:
            self.itemconfig(self.dynamic_texts[tag]["id"], text=text, font=font, fill=fill)
            self.dynamic_texts[tag]["rel_x"] = rel_x
            self.dynamic_texts[tag]["rel_y"] = rel_y
        
        w, h = self.winfo_width(), self.winfo_height()
        self.coords(self.dynamic_texts[tag]["id"], w * rel_x, h * rel_y)
        self.tag_raise("dynamic_text")
        self.tag_raise("particle")

    def update_dynamic_text_content(self, tag, text):
        if tag in self.dynamic_texts:
            self.itemconfig(self.dynamic_texts[tag]["id"], text=text)

    def _on_resize(self, event):
        if self._resize_timer:
            self.after_cancel(self._resize_timer)
        self._resize_timer = self.after(50, self._draw_canvas_elements)

    def _draw_canvas_elements(self):
        self.delete("gradient", "counter_bg", "moon")
        
        width, height = self.winfo_width(), self.winfo_height()
        if height <= 1: return
        
        r1, g1, b1 = self.winfo_rgb(self.color1)
        r2, g2, b2 = self.winfo_rgb(self.color2)
        r_step, g_step, b_step = (r2 - r1) / height, (g2 - g1) / height, (b2 - b1) / height

        for i in range(height):
            nr, ng, nb = int(r1 + (r_step * i)) >> 8, int(g1 + (g_step * i)) >> 8, int(b1 + (b_step * i)) >> 8
            self.create_line(0, i, width, i, tags=("gradient",), fill=f"#{nr:02x}{ng:02x}{nb:02x}")
            
        moon_r = 28
        self.images['moon'] = AssetFactory.create_moon(moon_r, "#e2e8f0")
        self.create_image(width * 0.85, height * 0.12, image=self.images['moon'], tags="moon")
            
        for i, bg in enumerate(self.counter_bgs):
            w, h = width * bg['rel_w'], height * bg['rel_h']
            img = AssetFactory.create_rounded_panel(w, h, bg['r'], bg['color'])
            self.images[f'bg_{i}'] = img
            self.create_image(width / 2, height * bg['rel_cy'], image=img, tags="counter_bg")

        for tag, data in self.dynamic_texts.items():
            self.coords(data["id"], width * data["rel_x"], height * data["rel_y"])
            
        layers = ["gradient", "moon", "cloud", "star", "meteor", "counter_bg", "dynamic_text", "particle"]
        for layer in layers:
            if self.find_withtag(layer):
                self.tag_raise(layer)

    def _init_clouds(self):
        cloud_configs = [
            {"x": 20, "y": 90, "speed": 0.25, "color": "#38476b", "offsets": [(0,0,70), (20,-12,50)]},
            {"x": 200, "y": 180, "speed": 0.15, "color": "#313f61", "offsets": [(0,0,90), (30,-14,60), (10,12,50)]},
            {"x": -80, "y": 300, "speed": 0.10, "color": "#263252", "offsets": [(0,0,100), (25,-15,60)]}
        ]
        self.cloud_data = []
        for i, c in enumerate(cloud_configs):
            img = AssetFactory.create_cloud(c['color'], c['offsets'])
            self.images[f'cloud_{i}'] = img
            item_id = self.create_image(c['x'], c['y'], image=img, anchor="nw", tags="cloud")
            self.cloud_data.append({
                "id": item_id, "exact_x": float(c['x']), "y": c['y'], 
                "speed": c['speed'], "current_x": int(c['x'])
            })

    def _animate_clouds(self):
        if not self.winfo_exists(): return
        width = self.winfo_width()
        for c in self.cloud_data:
            c['exact_x'] += c['speed']
            if c['exact_x'] > width + 120: 
                c['exact_x'] = -150 
            
            new_x = int(c['exact_x'])
            if new_x != c['current_x']:
                c['current_x'] = new_x
                self.coords(c['id'], new_x, c['y'])
                
        self.after(16, self._animate_clouds)

    def _meteor_spawner(self):
        if not self.winfo_exists(): return
        if random.random() < 0.25: 
            self._spawn_meteor()
        self.after(2000, self._meteor_spawner)

    def _spawn_meteor(self):
        width = self.winfo_width()
        if width <= 1: return
        x = random.randint(100, width + 200)
        y = -20
        length = random.randint(40, 80)
        speed = random.uniform(12, 20)
        
        img = AssetFactory.create_meteor(length)
        img_key = f"meteor_{time.time()}" 
        self.images[img_key] = img
        
        item = self.create_image(x, y, image=img, anchor="sw", tags="meteor")
        self.meteors.append({"id": item, "img_key": img_key, "exact_x": float(x), "exact_y": float(y), "speed": speed})
        if len(self.meteors) == 1:
            self._animate_meteors()

    def _animate_meteors(self):
        if not self.meteors: return
        active = []
        height = self.winfo_height()
        for m in self.meteors:
            m['exact_x'] -= m['speed']
            m['exact_y'] += m['speed']
            self.coords(m['id'], int(m['exact_x']), int(m['exact_y']))
            
            if m['exact_y'] < height + 100:
                active.append(m)
            else:
                self.delete(m['id'])
                if m['img_key'] in self.images:
                    del self.images[m['img_key']]
        self.meteors = active
        if self.meteors:
            self.after(16, self._animate_meteors)

    def init_stars(self, rel_y):
        for side_offset in [-1, 1]: 
            for _ in range(7):
                offset_x = side_offset * random.randint(70, 140)
                offset_y = random.randint(-20, 20)
                item = self.create_oval(0, 0, 0, 0, fill="#ffffff", outline="", tags="star")
                self.stars.append({
                    "id": item, "rel_y": rel_y, "offset_x": offset_x, "offset_y": offset_y,
                    "phase": random.uniform(0, 6.28), "speed": random.uniform(0.02, 0.05)
                })
        self._animate_stars()

    def _animate_stars(self):
        if not self.winfo_exists(): return
        width, height = self.winfo_width(), self.winfo_height()
        cx = width / 2
        
        r1, g1, b1 = self.winfo_rgb(self.color1)
        r2, g2, b2 = self.winfo_rgb(self.color2)
        
        for star in self.stars:
            star['phase'] += star['speed']
            bx = int(cx + star['offset_x'])
            by = int(height * star['rel_y'] + star['offset_y'])
            
            opacity = (math.sin(star['phase']) + 1) / 2
            ratio = by / height if height > 0 else 0
            bg_r = int(r1 + (r2 - r1) * ratio) >> 8
            bg_g = int(g1 + (g2 - g1) * ratio) >> 8
            bg_b = int(b1 + (b2 - b1) * ratio) >> 8
            
            r = int(255 * opacity + bg_r * (1 - opacity))
            g = int(255 * opacity + bg_g * (1 - opacity))
            b = int(255 * opacity + bg_b * (1 - opacity))
            
            self.coords(star['id'], bx-1, by-1, bx+1, by+1)
            self.itemconfig(star['id'], fill=f"#{r:02x}{g:02x}{b:02x}")
            
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
        self.particles.append({"id": item, "exact_x": px, "exact_y": py, "dx": dx, "dy": dy, "r": r})
        if len(self.particles) == 1:
            self._animate_particles()

    def _animate_particles(self):
        if not self.particles: return
        active_particles = []
        for p in self.particles:
            p['exact_x'] += p['dx']
            p['exact_y'] += p['dy']
            p['r'] -= 0.25 
            if p['r'] > 0:
                r, px, py = int(p['r']), int(p['exact_x']), int(p['exact_y'])
                self.coords(p['id'], px-r, py-r, px+r, py+r)
                active_particles.append(p)
            else:
                self.delete(p['id'])
                
        self.particles = active_particles
        if self.particles:
            self.after(16, self._animate_particles)

class ZoomSplashButton(ctk.CTkFrame):
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
        if "bg_color" in kwargs:
            super().configure(bg_color=kwargs["bg_color"])
        btn_kwargs = {k: v for k, v in kwargs.items() if k not in ["width", "height"]}
        if btn_kwargs:
            self.btn.configure(**btn_kwargs)

# --- Application Classes ---

class HistoryWindow(ctk.CTkToplevel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.geometry("520x400")
        self.title("Shift History")
        self.attributes('-topmost', True)
        self.configure(fg_color="#0b0f19") 

        ctk.CTkLabel(self, text="WORK HISTORY", font=("Segoe UI", 14, "bold"), text_color="#d8dee9").pack(pady=20)
        self.scroll_frame = ctk.CTkScrollableFrame(self, width=480, height=300, fg_color="transparent")
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
                
                # Check for DPH column in display logic
                dph_val = row[4] if len(row) > 4 else 0.0
                ctk.CTkLabel(frame, text=f"DPH: {dph_val}", font=("Segoe UI", 11), text_color="#3498db").pack(side="right", padx=10)
                ctk.CTkLabel(frame, text=f"Time: {row[3]}", font=("Segoe UI", 11), text_color="#a3be8c").pack(side="right", padx=10)
                ctk.CTkLabel(frame, text=f"P1: {row[2]}", text_color="#ebcb8b", font=("Segoe UI", 11)).pack(side="right", padx=10)
                ctk.CTkLabel(frame, text=f"Dials: {row[1]}", text_color="#88c0d0", font=("Segoe UI", 11)).pack(side="right", padx=10)
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
        self.attributes('-alpha', 0.0) 

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

        # Metrics
        self.dials_per_hour = 0.0
        self.avg_dial_speed = 0.0
        
        self.setup_db()
        self.bind("<Configure>", self.on_resize)
        
        self.run_startup_animation()

    def run_startup_animation(self):
        self.bg.set_dynamic_text("main_title", 0.5, 0.48, "GIMMIE MY LOVES", ("Segoe UI", 22, "bold"), "#ffffff")
        
        self.loading_line = ctk.CTkFrame(self, height=2, fg_color="#a8c0ff", corner_radius=2)
        self.loading_line.place(relx=0.5, rely=0.53, relwidth=0.0, anchor="center")
        
        self._fade_in_window(0.0)

    def _fade_in_window(self, alpha):
        alpha += 0.04
        self.attributes('-alpha', alpha)
        if alpha < 1.0:
            self.after(16, lambda: self._fade_in_window(alpha))
        else:
            self._expand_loading_line(0.0)

    def _expand_loading_line(self, current_width):
        current_width += 0.02
        self.loading_line.place_configure(relwidth=current_width)
        if current_width < 0.4:
            self.after(16, lambda: self._expand_loading_line(current_width))
        else:
            self.after(400, self._hide_loading_line)

    def _hide_loading_line(self):
        self.loading_line.destroy()
        self._animate_title_up(0.48)

    def _animate_title_up(self, current_rely):
        target_rely = 0.06
        speed = 0.012
        
        if current_rely > target_rely:
            current_rely -= speed
            if current_rely < target_rely: current_rely = target_rely
            
            progress = (0.48 - current_rely) / (0.48 - 0.06)
            new_size = int(22 - (9 * progress))
            
            self.bg.set_dynamic_text("main_title", 0.5, current_rely, "GIMMIE MY LOVES", ("Segoe UI", new_size, "bold"), "#ffffff")
            
            self.after(16, lambda: self._animate_title_up(current_rely))
        else:
            self._start_staggered_ui_build()

    def _start_staggered_ui_build(self):
        self.bg.init_stars(rel_y=0.06)
        
        self.ui_build_queue = [
            lambda: setattr(self, 'dial_label', self.create_counter_ui("DIAL COUNTER", "count", 0.22)),
            lambda: setattr(self, 'p1_label', self.create_counter_ui("P1 COUNTER", "p1_count", 0.40)),
            self._build_session_timer,
            self._build_productivity_metrics, # New Metric Display
            self._build_buttons,
            self.update_timer 
        ]
        self._execute_build_step()

    def _execute_build_step(self):
        if self.ui_build_queue:
            step = self.ui_build_queue.pop(0)
            step()
            self.after(100, self._execute_build_step) 

    def _build_session_timer(self):
        self.bg.set_dynamic_text("session_title", 0.5, 0.52, "SESSION TIME", ("Segoe UI", 10, "bold"), "#8f9eb3")
        self.bg.set_dynamic_text("session_timer", 0.5, 0.56, "00:00:00", ("Segoe UI Light", 24), "#ffffff")

    def _build_productivity_metrics(self):
        # Positioned right below the timer
        self.bg.set_dynamic_text("metrics_dph", 0.35, 0.61, "DPH: 0.0", ("Segoe UI", 10, "bold"), "#3498db")
        self.bg.set_dynamic_text("metrics_speed", 0.65, 0.61, "SPD: 0s/d", ("Segoe UI", 10, "bold"), "#2ecc71")

    def _build_buttons(self):
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
        color = self.get_bg_color(rely * self.winfo_height(), self.winfo_height()) 
        if hasattr(widget, 'update_bg_color'):
            widget.update_bg_color(color)
        else:
            widget.configure(bg_color=color)

    def on_resize(self, event):
        if event.widget == self:
            h = self.winfo_height()
            for widget, rely in self.dynamic_bg_widgets:
                try:
                    color = self.get_bg_color(rely * h, h)
                    if hasattr(widget, 'update_bg_color'):
                        widget.update_bg_color(color)
                    else:
                        widget.configure(bg_color=color)
                except Exception:
                    pass

    def setup_db(self):
        conn = sqlite3.connect('work_data.db')
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS shifts 
                        (date TEXT, dial_count INTEGER, p1_count INTEGER, duration TEXT)''')
        
        # Safe migration for DPH column[cite: 1]
        cursor.execute("PRAGMA table_info(shifts)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'dph' not in columns:
            cursor.execute("ALTER TABLE shifts ADD COLUMN dph REAL DEFAULT 0.0")
        
        conn.commit()
        conn.close()

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
            self.calculate_metrics() # Instant update on count change

        btn_kwargs = {"corner_radius": 14, "font": ("Segoe UI", 20), "fg_color": "#283145", "hover_color": "#344059", "bg_color": frame_color}
        
        minus = ZoomSplashButton(self, text="−", command=lambda: change(-1), width=40, height=40, **btn_kwargs)
        minus.place(relx=0.22, rely=rely_center+0.02, anchor="center")
        
        plus = ZoomSplashButton(self, text="+", command=lambda: change(1), width=40, height=40, **btn_kwargs)
        plus.place(relx=0.78, rely=rely_center+0.02, anchor="center")
        
        return val_label

    def calculate_metrics(self):
        """Computes dials per hour and average speed[cite: 1]."""
        hours = self.elapsed_time / 3600
        self.dials_per_hour = round(self.count / hours, 2) if hours > 0 else 0.0
        self.avg_dial_speed = round(self.elapsed_time / self.count, 1) if self.count > 0 else 0.0
        
        if "metrics_dph" in self.bg.dynamic_texts:
            self.bg.update_dynamic_text_content("metrics_dph", f"DPH: {self.dials_per_hour}")
        if "metrics_speed" in self.bg.dynamic_texts:
            self.bg.update_dynamic_text_content("metrics_speed", f"SPD: {self.avg_dial_speed}s/d")

    def reset_counters(self):
        if messagebox.askyesno("Reset", "Are you sure you want to clear the counters?"):
            self.count = 0
            self.p1_count = 0
            self.dial_label.configure(text="0")
            self.p1_label.configure(text="0")
            self.calculate_metrics()

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
        
        mins, secs = divmod(int(self.elapsed_time), 60)
        hours, mins = divmod(mins, 60)
        duration_str = f"{hours:02}:{mins:02}:{secs:02}"
        
        # Ensure final metrics are computed[cite: 1]
        self.calculate_metrics()
        
        try:
            conn = sqlite3.connect('work_data.db')
            # Added dph to insert[cite: 1]
            conn.execute("INSERT INTO shifts VALUES (?, ?, ?, ?, ?)", 
                         (date_str, self.count, self.p1_count, duration_str, self.dials_per_hour))
            conn.commit()
            conn.close()
            messagebox.showinfo("Saved", f"Shift data recorded!\nFinal DPH: {self.dials_per_hour}")
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Could not save data: {e}")

    def update_timer(self):
        if self.is_running:
            self.elapsed_time = time.time() - self.start_time
            mins, secs = divmod(int(self.elapsed_time), 60)
            hours, mins = divmod(mins, 60)
            time_str = f"{hours:02}:{mins:02}:{secs:02}"
            
            if "session_timer" in self.bg.dynamic_texts:
                self.bg.update_dynamic_text_content("session_timer", time_str)
            
            self.calculate_metrics() # Keep metrics live
                
        self.after(1000, self.update_timer)

if __name__ == "__main__":
    app = GimmieApp()
    app.mainloop()