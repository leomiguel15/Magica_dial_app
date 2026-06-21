import customtkinter as ctk
import sqlite3
from datetime import datetime
import time
import random
import math
from tkinter import messagebox, filedialog
from PIL import Image, ImageDraw, ImageTk
import os
import sys
import csv
import ctypes

# Set the appearance mode and default color theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Fix Windows taskbar icon grouping so custom icons show correctly down below
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("magica.dialapp.gimmie.1.0")
except Exception:
    pass

# --- UI Helpers ---

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip, add="+")
        self.widget.bind("<Leave>", self.hide_tip, add="+")

    def show_tip(self, event=None):
        if self.tip_window: return
        # Offset dynamically to the right of the button to avoid trapping the mouse cursor
        x = self.widget.winfo_rootx() + self.widget.winfo_width() + 8
        y = self.widget.winfo_rooty() + (self.widget.winfo_height() // 4)
        
        # Using a standard tkinter Toplevel to bypass heavy CTkToplevel rendering delays
        import tkinter as tk
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.attributes("-topmost", True)
        
        label = tk.Label(tw, text=self.text, justify='left',
                         background="#1a2234", foreground="#ffffff",
                         font=("Segoe UI", 11), relief='flat', padx=8, pady=4)
        label.pack()

    def hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None

# --- High-Fidelity Asset Generator --

class AssetFactory:
    @staticmethod
    def create_rounded_panel(width, height, radius, color):
        w, h, r = max(1, int(width)), max(1, int(height)), max(1, int(radius))
        scale = 4 
        img = Image.new("RGBA", (w*scale, h*scale), (0,0,0,0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle((0, 0, w*scale, h*scale), radius=r*scale, fill=color)
        return ImageTk.PhotoImage(img.resize((w, h), Image.LANCZOS)) 

    @staticmethod
    def create_settings_icon(size, color):
        scale = 4
        s = size * scale
        img = Image.new("RGBA", (s, s), (0,0,0,0))
        draw = ImageDraw.Draw(img)
        center = s // 2
        draw.ellipse([s*0.25, s*0.25, s*0.75, s*0.75], outline=color, width=int(2.5*scale))
        for i in range(8):
            angle = math.radians(i * 45)
            x1, y1 = center + math.cos(angle) * (s*0.32), center + math.sin(angle) * (s*0.32)
            x2, y2 = center + math.cos(angle) * (s*0.48), center + math.sin(angle) * (s*0.48)
            draw.line([x1, y1, x2, y2], fill=color, width=int(3.5*scale))
        return ImageTk.PhotoImage(img.resize((size, size), Image.LANCZOS))

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
        w, h = int(max_x - min_x + 20), int(max_y - min_y + 20)
        img = Image.new("RGBA", (w*scale, h*scale), (0,0,0,0))
        draw = ImageDraw.Draw(img)
        for dx, dy, length in offsets:
            start_x, start_y = int((dx - min_x + 10) * scale), int((dy - min_y + 10) * scale)
            end_x = int(start_x + (length * scale))
            draw.rounded_rectangle((start_x, start_y - 10*scale, end_x, start_y + 10*scale), radius=10*scale, fill=color)
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
        self.color1, self.color2 = color1, color2
        self.particles, self.stars, self.meteors, self.counter_bgs = [], [], [], []
        self.dynamic_texts, self.images = {}, {}
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
            self.dynamic_texts[tag]["rel_x"], self.dynamic_texts[tag]["rel_y"] = rel_x, rel_y
        w, h = self.winfo_width(), self.winfo_height()
        if w > 1: self.coords(self.dynamic_texts[tag]["id"], w * rel_x, h * rel_y)
        self.tag_raise("dynamic_text")

    def update_dynamic_text_content(self, tag, text):
        if tag in self.dynamic_texts: self.itemconfig(self.dynamic_texts[tag]["id"], text=text)

    def _on_resize(self, event):
        if self._resize_timer: self.after_cancel(self._resize_timer)
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
        self.images['moon'] = AssetFactory.create_moon(28, "#e2e8f0")
        self.create_image(width * 0.85, height * 0.12, image=self.images['moon'], tags="moon")
        for i, bg in enumerate(self.counter_bgs):
            w, h = width * bg['rel_w'], height * bg['rel_h']
            img = AssetFactory.create_rounded_panel(w, h, bg['r'], bg['color'])
            self.images[f'bg_{i}'] = img
            self.create_image(width / 2, height * bg['rel_cy'], image=img, tags="counter_bg")
        for tag, data in self.dynamic_texts.items(): self.coords(data["id"], width * data["rel_x"], height * data["rel_y"])
        for l in ["gradient", "moon", "cloud", "star", "meteor", "counter_bg", "gear_btn", "dynamic_text", "particle"]:
            if self.find_withtag(l): self.tag_raise(l)

    def _init_clouds(self):
        configs = [{"x": 20, "y": 90, "s": 0.25, "c": "#38476b", "o": [(0,0,70), (20,-12,50)]},
                   {"x": 200, "y": 180, "s": 0.15, "c": "#313f61", "o": [(0,0,90), (30,-14,60)]},
                   {"x": -80, "y": 300, "s": 0.10, "c": "#263252", "o": [(0,0,100), (25,-15,60)]}]
        self.cloud_data = []
        for i, c in enumerate(configs):
            img = AssetFactory.create_cloud(c['c'], c['o'])
            self.images[f'cloud_{i}'] = img
            item = self.create_image(c['x'], c['y'], image=img, anchor="nw", tags="cloud")
            self.cloud_data.append({"id": item, "exact_x": float(c['x']), "y": c['y'], "speed": c['s'], "current_x": int(c['x'])})

    def _animate_clouds(self):
        if not self.winfo_exists(): return
        width = self.winfo_width()
        for c in self.cloud_data:
            c['exact_x'] += c['speed']
            if c['exact_x'] > width + 120: c['exact_x'] = -150 
            new_x = int(c['exact_x'])
            if new_x != c['current_x']:
                c['current_x'] = new_x
                self.coords(c['id'], new_x, c['y'])
        self.after(16, self._animate_clouds)

    def _meteor_spawner(self):
        if not self.winfo_exists(): return
        if random.random() < 0.25: self._spawn_meteor()
        self.after(2000, self._meteor_spawner)

    def _spawn_meteor(self):
        width = self.winfo_width()
        if width <= 1: return
        x, y, length, speed = random.randint(100, width + 200), -20, random.randint(40, 80), random.uniform(12, 20)
        img = AssetFactory.create_meteor(length)
        key = f"meteor_{time.time()}"; self.images[key] = img
        item = self.create_image(x, y, image=img, anchor="sw", tags="meteor")
        self.meteors.append({"id": item, "img_key": key, "exact_x": float(x), "exact_y": float(y), "speed": speed})
        if len(self.meteors) == 1: self._animate_meteors()

    def _animate_meteors(self):
        if not self.meteors: return
        active, height = [], self.winfo_height()
        for m in self.meteors:
            m['exact_x'] -= m['speed']; m['exact_y'] += m['speed']
            self.coords(m['id'], int(m['exact_x']), int(m['exact_y']))
            if m['exact_y'] < height + 100: active.append(m)
            else: self.delete(m['id']); del self.images[m['img_key']]
        self.meteors = active
        if self.meteors: self.after(16, self._animate_meteors)

    def init_stars(self, rel_y):
        for side in [-1, 1]: 
            for _ in range(7):
                ox, oy = side * random.randint(70, 140), random.randint(-20, 20)
                item = self.create_oval(0, 0, 0, 0, fill="#ffffff", outline="", tags="star")
                self.stars.append({"id": item, "rel_y": rel_y, "offset_x": ox, "offset_y": oy, "phase": random.uniform(0, 6.28), "speed": random.uniform(0.02, 0.05)})
        self._animate_stars()

    def _animate_stars(self):
        if not self.winfo_exists(): return
        width, height = self.winfo_width(), self.winfo_height()
        cx, r1, g1, b1 = width / 2, *self.winfo_rgb(self.color1)
        r2, g2, b2 = self.winfo_rgb(self.color2)
        for star in self.stars:
            star['phase'] += star['speed']
            bx, by = int(cx + star['offset_x']), int(height * star['rel_y'] + star['offset_y'])
            op = (math.sin(star['phase']) + 1) / 2
            ratio = by / height if height > 0 else 0
            br, bg, bb = int(r1 + (r2 - r1) * ratio) >> 8, int(g1 + (g2 - g1) * ratio) >> 8, int(b1 + (b2 - b1) * ratio) >> 8
            r, g, b = int(255 * op + br * (1 - op)), int(255 * op + bg * (1 - op)), int(255 * op + bb * (1 - op))
            self.coords(star['id'], bx-1, by-1, bx+1, by+1)
            self.itemconfig(star['id'], fill=f"#{r:02x}{ng:02x}{nb:02x}" if 'ng' in locals() else f"#{r:02x}{g:02x}{b:02x}")
        self.after(35, self._animate_stars)

    def spawn_bubbles(self, x, y, width, height):
        colors = ["#ffffff", "#a8c0ff", "#e2e8f0", "#cbd5e1"]
        for _ in range(12):
            self._add_particle(x + (width if _ > 5 else 0), y + height/2 + random.uniform(-15, 15), random.uniform(-5, 5), random.uniform(-3, 3), random.choice(colors))

    def _add_particle(self, px, py, dx, dy, color):
        r = random.uniform(3, 7)
        item = self.create_oval(px-r, py-r, px+r, py+r, fill=color, outline="", tags="particle")
        self.particles.append({"id": item, "exact_x": px, "exact_y": py, "dx": dx, "dy": dy, "r": r})
        if len(self.particles) == 1: self._animate_particles()

    def _animate_particles(self):
        active = []
        for p in self.particles:
            p['exact_x'] += p['dx']; p['exact_y'] += p['dy']; p['r'] -= 0.25 
            if p['r'] > 0:
                r, px, py = int(p['r']), int(p['exact_x']), int(p['exact_y'])
                self.coords(p['id'], px-r, py-r, px+r, py+r); active.append(p)
            else: self.delete(p['id'])
        self.particles = active
        if self.particles: self.after(16, self._animate_particles)

class ZoomSplashButton(ctk.CTkFrame):
    def __init__(self, master, text, bg_color, command=None, width=200, height=45, **kwargs):
        super().__init__(master, width=width, height=height, fg_color="transparent", bg_color=bg_color)
        self.pack_propagate(False)
        self.btn = ctk.CTkButton(self, text=text, command=command, bg_color=bg_color, corner_radius=18, font=("Segoe UI", 13, "bold"), **kwargs)
        self.btn.place(relx=0.5, rely=0.5, anchor="center", relwidth=1.0, relheight=1.0)
        self.btn.bind("<ButtonPress-1>", self._on_press, add="+")
        self.btn.bind("<ButtonRelease-1>", self._on_release, add="+")
        self.btn.bind("<Leave>", self._on_release, add="+")

    def _on_press(self, event):
        self.btn.place_configure(relwidth=0.92, relheight=0.90)
        root = self.winfo_toplevel()
        if hasattr(root, 'bg'): root.bg.spawn_bubbles(self.winfo_rootx() - root.winfo_rootx(), self.winfo_rooty() - root.winfo_rooty(), self.winfo_width(), self.winfo_height())

    def _on_release(self, event): self.btn.place_configure(relwidth=1.0, relheight=1.0)
    def update_bg_color(self, color): super().configure(bg_color=color); self.btn.configure(bg_color=color)

# --- History Components ---

class HistoryWindow(ctk.CTkToplevel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.geometry("520x500"); self.title("Shift History"); self.attributes('-topmost', True); self.configure(fg_color="#0b0f19")
        ctk.CTkLabel(self, text="WORK HISTORY", font=("Segoe UI", 14, "bold"), text_color="#d8dee9").pack(pady=15)
        
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkButton(btn_frame, text="Export CSV", width=100, fg_color="#34495e", command=self.export_csv).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Import CSV", width=100, fg_color="#34495e", command=self.import_csv).pack(side="left", padx=5)

        self.scroll_frame = ctk.CTkScrollableFrame(self, width=480, height=350, fg_color="transparent")
        self.scroll_frame.pack(pady=10, padx=10, fill="both", expand=True)
        self.load_history()

    def load_history(self):
        for child in self.scroll_frame.winfo_children(): child.destroy()
        try:
            conn = sqlite3.connect('work_data.db')
            rows = conn.execute("SELECT * FROM shifts ORDER BY date DESC").fetchall()
            for row in rows:
                f = ctk.CTkFrame(self.scroll_frame, fg_color="#1d2538", corner_radius=10); f.pack(pady=5, padx=10, fill="x")
                ctk.CTkLabel(f, text=row[0], font=("Segoe UI", 11, "bold")).pack(side="left", padx=10, pady=10)
                ctk.CTkLabel(f, text=f"DPH: {row[4]}", text_color="#3498db").pack(side="right", padx=10)
                ctk.CTkLabel(f, text=f"Time: {row[3]}", text_color="#a3be8c").pack(side="right", padx=10)
                ctk.CTkLabel(f, text=f"P1: {row[2]}", text_color="#ebcb8b").pack(side="right", padx=10)
                ctk.CTkLabel(f, text=f"Dials: {row[1]}", text_color="#88c0d0").pack(side="right", padx=10)
            conn.close()
        except: pass

    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not path: return
        try:
            conn = sqlite3.connect('work_data.db')
            data = conn.execute("SELECT * FROM shifts").fetchall()
            with open(path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Date", "Dials", "P1", "Duration", "DPH"])
                writer.writerows(data)
            conn.close(); messagebox.showinfo("Success", "Exported successfully!")
        except Exception as e: messagebox.showerror("Error", str(e))

    def import_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if not path: return
        try:
            conn = sqlite3.connect('work_data.db')
            with open(path, 'r') as f:
                reader = csv.reader(f); next(reader)
                for row in reader:
                    conn.execute("INSERT INTO shifts VALUES (?, ?, ?, ?, ?)", row)
            conn.commit(); conn.close(); self.load_history(); messagebox.showinfo("Success", "Imported successfully!")
        except Exception as e: messagebox.showerror("Error", str(e))

# --- Main App ---

class GimmieApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Gimmie My Loves"); self.geometry("320x680"); self.attributes('-topmost', True, '-alpha', 0.0)
        
        # Initialize custom window icon tracking
        self.set_window_icon()
        
        self.grad_top, self.grad_bottom = "#2c395c", "#0b0f19"
        self.bg = AnimatedBackgroundCanvas(self, self.grad_top, self.grad_bottom); self.bg.place(relwidth=1, relheight=1)
        self.count, self.p1_count, self.elapsed_time, self.is_running, self.start_time = 0, 0, 0, True, time.time()
        self.dynamic_bg_widgets, self.history_window = [], None
        self.setup_db(); self.bind("<Configure>", self.on_resize); self.run_startup_animation()
        
        # INTERCEPT CLOSE BUTTON
        self.protocol("WM_DELETE_WINDOW", self.on_exit_attempt)

    def set_window_icon(self):
            """Applies application title bar icons gracefully across standard environment runtimes and compiled states."""
            # 1. If running as a compiled .exe, pull the icon directly from the executable's resources!
            if getattr(sys, 'frozen', False):
                try:
                    self.iconbitmap(sys.executable)
                    return
                except Exception as e:
                    print(f"Failed to load icon from executable resource: {e}")

            # 2. Fallback for local development when running the raw main.py script
            possible_ico_paths = [
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "images", "icon.ico"),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "Images", "icon.ico"),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico"),
                os.path.join(os.getcwd(), "images", "icon.ico"),
                os.path.join(os.getcwd(), "Images", "icon.ico"),
                os.path.join(os.getcwd(), "icon.ico"),
                "images/icon.ico",
                "icon.ico"
            ]
            possible_png_paths = [
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "images", "icon.png"),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "Images", "icon.png"),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png"),
                os.path.join(os.getcwd(), "images", "icon.png"),
                os.path.join(os.getcwd(), "Images", "icon.png"),
                os.path.join(os.getcwd(), "icon.png"),
                "images/icon.png",
                "icon.png"
            ]

            # Resolve path safely for local development environment
            resolved_ico = next((p for p in possible_ico_paths if os.path.exists(p)), None)
            resolved_png = next((p for p in possible_png_paths if os.path.exists(p)), None)

            try:
                if resolved_ico:
                    self.iconbitmap(resolved_ico)
                elif resolved_png:
                    img = Image.open(resolved_png)
                    self.wm_iconphoto(False, ImageTk.PhotoImage(img))
            except Exception as e:
                print(f"Failed to apply window icon: {e}")

    def setup_db(self):
        conn = sqlite3.connect('work_data.db')
        conn.execute("CREATE TABLE IF NOT EXISTS shifts (date TEXT, dial_count INTEGER, p1_count INTEGER, duration TEXT, dph REAL)")
        conn.close()

    def run_startup_animation(self):
        self.bg.set_dynamic_text("main_title", 0.5, 0.48, "GIMMIE MY LOVES", ("Segoe UI", 22, "bold"), "#ffffff")
        self.loading_line = ctk.CTkFrame(self, height=2, fg_color="#a8c0ff", corner_radius=2); self.loading_line.place(relx=0.5, rely=0.53, relwidth=0.0, anchor="center")
        self._fade_in(0.0)

    def _fade_in(self, alpha):
        alpha += 0.04; self.attributes('-alpha', alpha)
        if alpha < 1.0: self.after(16, lambda: self._fade_in(alpha))
        else: self._expand_line(0.0)

    def _expand_line(self, w):
        w += 0.02; self.loading_line.place_configure(relwidth=w)
        if w < 0.4: self.after(16, lambda: self._expand_line(w))
        else: self.after(400, lambda: (self.loading_line.destroy(), self._title_up(0.48)))

    def _title_up(self, y):
        if y > 0.06:
            y -= 0.012; prog = (0.48 - y) / 0.42; sz = int(22 - (9 * prog))
            self.bg.set_dynamic_text("main_title", 0.5, y, "GIMMIE MY LOVES", ("Segoe UI", sz, "bold"), "#ffffff")
            self.after(16, lambda: self._title_up(y))
        else: self._build_ui()

    def _build_ui(self):
            self.bg.init_stars(0.06)
            
            # 1. Multi-layer robust search for the manual_icon.png file across common environments
            possible_paths = [
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "images", "manual_icon.png"),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "Images", "manual_icon.png"),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "manual_icon.png"),
                os.path.join(os.getcwd(), "images", "manual_icon.png"),
                os.path.join(os.getcwd(), "Images", "manual_icon.png"),
                os.path.join(os.getcwd(), "manual_icon.png"),
                "images/manual_icon.png",
                "manual_icon.png"
            ]
            
            if hasattr(sys, '_MEIPASS'):
                possible_paths.insert(0, os.path.join(sys._MEIPASS, "images", "manual_icon.png"))
                possible_paths.insert(0, os.path.join(sys._MEIPASS, "manual_icon.png"))

            icon_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    icon_path = path
                    break

            # 2. Try loading the custom PNG asset; fallback gracefully to the asset factory if unavailable
            if icon_path:
                try:
                    self.gear_img = ctk.CTkImage(
                        light_image=Image.open(icon_path),
                        dark_image=Image.open(icon_path),
                        size=(22, 22)
                    )
                except Exception:
                    self.gear_img = AssetFactory.create_settings_icon(22, "#8f9eb3")
            else:
                self.gear_img = AssetFactory.create_settings_icon(22, "#8f9eb3")

            # 3. Calculate the initial background color matching the gradient layout at ratio 0.015 (y=10)
            try:
                r1, g1, b1 = self.winfo_rgb(self.grad_top)
                r2, g2, b2 = self.winfo_rgb(self.grad_bottom)
                rt = 0.015
                init_c = f"#{int(r1+((r2-r1)*rt))>>8:02x}{int(g1+((g2-g1)*rt))>>8:02x}{int(b1+((b2-b1)*rt))>>8:02x}"
            except Exception:
                init_c = self.grad_top

            # 4. Create the button widget and register it into the runtime gradient-tracking update pipeline
            self.gear_btn = ctk.CTkButton(self, image=self.gear_img, text="", width=32, height=32, 
                                        fg_color="transparent", bg_color=init_c, 
                                        hover_color="#1d2538", command=self.open_manual)
            self.gear_btn.place(x=15, y=10)
            self.register_bg(self.gear_btn, 0.015)
            ToolTip(self.gear_btn, "Manual Mode")
            
            # 5. Core UI counter blocks and tracking labels
            self.dial_label = self.create_counter_ui("DIAL COUNTER", "count", 0.22)
            self.p1_label = self.create_counter_ui("P1 COUNTER", "p1_count", 0.40)
            self.bg.set_dynamic_text("session_title", 0.5, 0.52, "SESSION TIME", ("Segoe UI", 10, "bold"), "#8f9eb3")
            self.bg.set_dynamic_text("session_timer", 0.5, 0.56, "00:00:00", ("Segoe UI Light", 24), "#ffffff")
            self.bg.set_dynamic_text("metrics_dph", 0.5, 0.61, "DPH: 0.0", ("Segoe UI", 10, "bold"), "#3498db")
            
            btns = [("Break", "#b86868", 0.69, self.confirm_break), ("Reset Counters", "#c98a6c", 0.77, self.reset_counters),
                    ("View History", "#5b6678", 0.85, self.open_history), ("End Shift & Save", "#9eb586", 0.93, self.save_exit)]
            for t, c, r, cmd in btns:
                b = ZoomSplashButton(self, text=t, bg_color="transparent", fg_color=c, hover_color=c, command=cmd)
                b.place(relx=0.5, rely=r, relwidth=0.8, relheight=0.065, anchor="center")
                self.register_bg(b, r)
            self.update_timer()

    def create_counter_ui(self, title, var, rely):
        frame_color = "#1d2538"; self.bg.add_counter_bg(rely, 0.85, 0.15, 20, frame_color)
        ctk.CTkLabel(self, text=title, font=("Segoe UI", 10, "bold"), text_color="#8f9eb3", bg_color=frame_color).place(relx=0.5, rely=rely-0.04, anchor="center")
        lbl = ctk.CTkLabel(self, text="0", font=("Segoe UI Light", 40), bg_color=frame_color)
        lbl.place(relx=0.5, rely=rely+0.02, anchor="center")
        def chg(a):
            v = max(0, getattr(self, var) + a); setattr(self, var, v); lbl.configure(text=str(v)); self.calc_metrics()
        ZoomSplashButton(self, text="−", command=lambda: chg(-1), width=40, height=40, fg_color="#283145", bg_color=frame_color).place(relx=0.22, rely=rely+0.02, anchor="center")
        ZoomSplashButton(self, text="+", command=lambda: chg(1), width=40, height=40, fg_color="#283145", bg_color=frame_color).place(relx=0.78, rely=rely+0.02, anchor="center")
        return lbl

    def open_manual(self):
        d = ctk.CTkToplevel(self); d.title("Manual Adjust"); d.geometry("280x420"); d.attributes('-topmost', True); d.configure(fg_color="#1d2538")
        ctk.CTkLabel(d, text="ADJUST SESSION", font=("Segoe UI", 14, "bold")).pack(pady=15)
        def inp(l, v):
            ctk.CTkLabel(d, text=l, font=("Segoe UI", 10, "bold"), text_color="#8f9eb3").pack(anchor="w", padx=45)
            e = ctk.CTkEntry(d, width=190, fg_color="#121926"); e.insert(0, str(v)); e.pack(pady=(0, 15)); return e
        de, pe = inp("DIALS", self.count), inp("P1", self.p1_count)
        ctk.CTkLabel(d, text="TIME (HH : MM)", font=("Segoe UI", 10, "bold"), text_color="#8f9eb3").pack(anchor="w", padx=45)
        f = ctk.CTkFrame(d, fg_color="transparent"); f.pack()
        he, me = ctk.CTkEntry(f, width=90), ctk.CTkEntry(f, width=90)
        he.insert(0, str(int(self.elapsed_time//3600))); me.insert(0, str(int((self.elapsed_time%3600)//60)))
        he.pack(side="left", padx=5); me.pack(side="left", padx=5)
        def app():
            try:
                self.count, self.p1_count = int(de.get()), int(pe.get())
                self.elapsed_time = (int(he.get())*3600) + (int(me.get())*60); self.start_time = time.time()-self.elapsed_time
                self.dial_label.configure(text=str(self.count)); self.p1_label.configure(text=str(self.p1_count)); self.calc_metrics(); d.destroy()
            except: messagebox.showerror("Error", "Invalid inputs")
        ctk.CTkButton(d, text="Update", command=app).pack(pady=30)

    def calc_metrics(self):
        h = self.elapsed_time / 3600
        dph = round(self.count / h, 2) if h > 0 else 0.0
        if "metrics_dph" in self.bg.dynamic_texts: self.bg.update_dynamic_text_content("metrics_dph", f"DPH: {dph}")
        return dph

    def on_resize(self, e):
        if e.widget == self:
            h = self.winfo_height()
            for w, r in self.dynamic_bg_widgets:
                r1, g1, b1 = self.winfo_rgb(self.grad_top); r2, g2, b2 = self.winfo_rgb(self.grad_bottom); rt = r
                c = f"#{int(r1+((r2-r1)*rt))>>8:02x}{int(g1+((g2-g1)*rt))>>8:02x}{int(b1+((b2-b1)*rt))>>8:02x}"
                if hasattr(w, 'update_bg_color'): w.update_bg_color(c)
                else: w.configure(bg_color=c)

    def register_bg(self, w, r): self.dynamic_bg_widgets.append((w, r))
    def reset_counters(self):
        if messagebox.askyesno("Reset", "Clear counters?"): self.count=self.p1_count=0; self.dial_label.configure(text="0"); self.p1_label.configure(text="0"); self.calc_metrics()
    def confirm_break(self):
        if self.is_running:
            if messagebox.askyesno("Break", "Start break?"): self.is_running=False
        else: self.is_running=True; self.start_time = time.time()-self.elapsed_time
    def open_history(self):
        if not self.history_window or not self.history_window.winfo_exists(): self.history_window = HistoryWindow(self)
        else: self.history_window.focus(); self.history_window.load_history()

    # Safety Close Logic
    def on_exit_attempt(self):
        ans = messagebox.askyesnocancel("Exit", "Do you want to save your session data before exiting?")
        if ans is True: # Yes, Save
            self.save_exit()
        elif ans is False: # No, Just exit
            self.destroy()
        # If Cancel, do nothing

    def save_exit(self):
        dph = self.calc_metrics(); dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S"); m, s = divmod(int(self.elapsed_time), 60); h, m = divmod(m, 60)
        try:
            conn = sqlite3.connect('work_data.db'); conn.execute("INSERT INTO shifts VALUES (?, ?, ?, ?, ?)", (dt, self.count, self.p1_count, f"{h:02}:{m:02}:{s:02}", dph)); conn.commit(); conn.close()
            messagebox.showinfo("Saved", f"Recorded! DPH: {dph}"); self.destroy()
        except Exception as e: messagebox.showerror("Error", str(e))
    def update_timer(self):
        if self.is_running:
            self.elapsed_time = time.time() - self.start_time; m, s = divmod(int(self.elapsed_time), 60); h, m = divmod(m, 60)
            self.bg.update_dynamic_text_content("session_timer", f"{h:02}:{m:02}:{s:02}"); self.calc_metrics()
        self.after(1000, self.update_timer)

if __name__ == "__main__": GimmieApp().mainloop()