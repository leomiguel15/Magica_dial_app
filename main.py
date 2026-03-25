import customtkinter as ctk
import sqlite3
from datetime import datetime
import time
from tkinter import messagebox

# Set the appearance mode and default color theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class HistoryRow(ctk.CTkFrame):
    """A custom frame to display a single row of history data nicely"""
    def __init__(self, master, date, dials, p1, duration):
        # Using a slightly lighter blue for the 'cards' to make them pop
        super().__init__(master, fg_color="#243b55", corner_radius=8)
        self.pack(pady=5, padx=10, fill="x")

        # Date Label (Left side)
        ctk.CTkLabel(self, text=date, font=("Helvetica", 11, "bold"), 
                     text_color="#ecf0f1").pack(side="left", padx=10, pady=10)
        
        # Stats Container (Right side)
        stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        stats_frame.pack(side="right", padx=10)

        ctk.CTkLabel(stats_frame, text=f"Dials: {dials}", text_color="#3498db", font=("Helvetica", 12, "bold")).pack(side="left", padx=8)
        ctk.CTkLabel(stats_frame, text=f"P1: {p1}", text_color="#e67e22", font=("Helvetica", 12, "bold")).pack(side="left", padx=8)
        ctk.CTkLabel(stats_frame, text=f"Time: {duration}", font=("Consolas", 12), text_color="#2ecc71").pack(side="left", padx=8)

class HistoryWindow(ctk.CTkToplevel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.geometry("480x400")
        self.title("Shift History Log")
        self.attributes('-topmost', True)
        self.configure(fg_color="#1a2a6c")

        # Header
        header = ctk.CTkLabel(self, text="📊 WORK HISTORY LOG", font=("Helvetica", 18, "bold"))
        header.pack(pady=15)

        # Scrollable Frame for data entries
        self.scroll_frame = ctk.CTkScrollableFrame(self, width=440, height=300, fg_color="#1a2a6c")
        self.scroll_frame.pack(pady=10, padx=10, fill="both", expand=True)
        
        self.load_history()

    def load_history(self):
        # Clear existing rows to refresh data
        for child in self.scroll_frame.winfo_children():
            child.destroy()
        
        try:
            conn = sqlite3.connect('work_data.db')
            cursor = conn.cursor()
            # Get latest shifts first
            cursor.execute("SELECT * FROM shifts ORDER BY date DESC")
            rows = cursor.fetchall()
            
            if not rows:
                ctk.CTkLabel(self.scroll_frame, text="No history found yet.", text_color="gray").pack(pady=20)
            
            for row in rows:
                HistoryRow(self.scroll_frame, row[0], row[1], row[2], row[3])
                
            conn.close()
        except Exception as e:
            ctk.CTkLabel(self.scroll_frame, text=f"Database Error: {e}").pack()

class GimmieApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Window Setup
        self.title("Gimmie My Loves")
        self.geometry("320x650")
        self.attributes('-topmost', True)  # Always on top
        self.configure(fg_color="#1a2a6c") # Dark Blue background

        # App Variables
        self.count = 0
        self.p1_count = 0
        self.start_time = time.time()
        self.elapsed_time = 0
        self.is_running = True
        self.history_window = None
        
        self.setup_db()
        self.init_ui()
        self.update_timer()

    def setup_db(self):
        conn = sqlite3.connect('work_data.db')
        conn.execute('''CREATE TABLE IF NOT EXISTS shifts 
                        (date TEXT, dial_count INTEGER, p1_count INTEGER, duration TEXT)''')
        conn.close()

    def init_ui(self):
        # App Title
        ctk.CTkLabel(self, text="Welcome: Gimmie My loves", font=("Helvetica", 18, "bold")).pack(pady=20)

        # UI Counter Components
        self.dial_label = self.create_counter_ui("Dial Counter", "count")
        self.p1_label = self.create_counter_ui("P1 Counter", "p1_count")

        # Real-time Timer
        self.timer_label = ctk.CTkLabel(self, text="Session: 00:00:00", font=("Consolas", 16))
        self.timer_label.pack(pady=15)

        # Action Buttons
        self.break_btn = ctk.CTkButton(self, text="Break", fg_color="#b21f1f", hover_color="#921a1a", command=self.confirm_break)
        self.break_btn.pack(pady=8, padx=20, fill="x")

        self.reset_btn = ctk.CTkButton(self, text="Reset Counters", fg_color="#d35400", hover_color="#a34100", command=self.reset_counters)
        self.reset_btn.pack(pady=8, padx=20, fill="x")

        self.history_btn = ctk.CTkButton(self, text="View History", fg_color="#34495e", hover_color="#2c3e50", command=self.open_history)
        self.history_btn.pack(pady=8, padx=20, fill="x")

        # Save and Exit Button
        self.save_btn = ctk.CTkButton(self, text="End Shift & Save", fg_color="#27ae60", hover_color="#1e8449", command=self.save_data_and_exit)
        self.save_btn.pack(pady=25, padx=20, fill="x")

    def create_counter_ui(self, title, var_name):
        frame = ctk.CTkFrame(self, fg_color="#162447", corner_radius=10)
        frame.pack(pady=10, padx=20, fill="x")
        
        ctk.CTkLabel(frame, text=title, font=("Helvetica", 12)).pack(pady=(5,0))
        
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(pady=10)

        val_label = ctk.CTkLabel(btn_frame, text="0", font=("Helvetica", 24, "bold"))
        
        def change(amt):
            new_val = max(0, getattr(self, var_name) + amt)
            setattr(self, var_name, new_val)
            val_label.configure(text=str(new_val))

        ctk.CTkButton(btn_frame, text="-", width=40, font=("bold", 18), command=lambda: change(-1)).pack(side="left", padx=10)
        val_label.pack(side="left", padx=20)
        ctk.CTkButton(btn_frame, text="+", width=40, font=("bold", 18), command=lambda: change(1)).pack(side="left", padx=10)
        
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
                self.break_btn.configure(text="Resume Shift", fg_color="#2ecc71")
        else:
            self.is_running = True
            self.break_btn.configure(text="Break", fg_color="#b21f1f")
            # Adjust start_time to resume from where it paused
            self.start_time = time.time() - self.elapsed_time

    def open_history(self):
        if self.history_window is None or not self.history_window.winfo_exists():
            self.history_window = HistoryWindow(self)
        else:
            self.history_window.focus()
            self.history_window.load_history()

    def save_data_and_exit(self):
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        duration_str = self.timer_label.cget("text").replace("Session: ", "")
        
        try:
            conn = sqlite3.connect('work_data.db')
            conn.execute("INSERT INTO shifts VALUES (?, ?, ?, ?)", 
                         (date_str, self.count, self.p1_count, duration_str))
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
            self.timer_label.configure(text=f"Session: {hours:02}:{mins:02}:{secs:02}")
        self.after(1000, self.update_timer)

if __name__ == "__main__":
    app = GimmieApp()
    app.mainloop()