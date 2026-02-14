"""
Hyper optimized tkinter approach to plankedit
"""

import tkinter as tk
import ctypes
from tkinter import filedialog, messagebox

class PlanckEdit:
    def __init__(self, root):
        self.root = root
        self.root.title("PlanckEdit")
        self.root.configure(bg="#1E1E1E")
        
        # 1. REMOVE NATIVE WINDOW FRAME (Always on)
        self.root.overrideredirect(True)

        # 2. FORCE TASKBAR & PREPARE FOR MINIMIZE
        # We delay 10ms to let the window handle (HWND) initialize
        self.root.after(10, self.set_app_window)

        # 3. Dynamic Centering
        width = 400
        height = 600
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

        # --- CUSTOM TITLE BAR ---
        self.title_bar = tk.Frame(self.root, bg="#2D2D2D", relief="flat", bd=0)
        self.title_bar.pack(side="top", fill="x")

        # Title Label
        self.title_label = tk.Label(self.title_bar, text="PlanckEdit", bg="#2D2D2D", fg="#888888", font=("Segoe UI", 9))
        self.title_label.pack(side="left", padx=10)

        # Close Button
        self.close_btn = tk.Button(self.title_bar, text="✕", command=self.close_app, 
                                   bg="#2D2D2D", fg="#CCCCCC", bd=0, 
                                   font=("Arial", 10), activebackground="#C42B1C", activeforeground="white")
        self.close_btn.pack(side="right", padx=5, pady=2)

        # Minimize Button
        self.min_btn = tk.Button(self.title_bar, text="—", command=self.minimize_app, 
                                 bg="#2D2D2D", fg="#CCCCCC", bd=0, 
                                 font=("Arial", 10), activebackground="#3E3E42", activeforeground="white")
        self.min_btn.pack(side="right", padx=0, pady=2)

        # --- DRAGGING LOGIC ---
        self.title_bar.bind("<Button-1>", self.get_pos)
        self.title_bar.bind("<B1-Motion>", self.drag_window)
        self.title_label.bind("<Button-1>", self.get_pos)
        self.title_label.bind("<B1-Motion>", self.drag_window)
        
        # --- FOCUS FIX ---
        # When the user clicks back into the window, force focus to the text area
        self.root.bind("<FocusIn>", self.force_focus)

        # --- MAIN TEXT AREA ---
        self.text_area = tk.Text(
            self.root, 
            wrap="word", 
            undo=True,
            font=("Consolas", 11),
            bg="#1E1E1E",
            fg="#D4D4D4",
            insertbackground="white", 
            selectbackground="#264F78",
            selectforeground="white",
            relief=tk.FLAT,
            padx=10,
            pady=10
        )
        self.text_area.pack(side="top", fill="both", expand=True)

    def set_app_window(self):
        # Force the window to be a "real" app in the taskbar
        GWL_EXSTYLE = -20
        WS_EX_APPWINDOW = 0x00040000
        WS_EX_TOOLWINDOW = 0x00000080

        # Get the wrapper window handle
        hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
        
        # Get current style and modify it
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style = style & ~WS_EX_TOOLWINDOW
        style = style | WS_EX_APPWINDOW
        
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        
        # Update taskbar
        self.root.wm_withdraw()
        self.root.after(10, lambda: self.root.wm_deiconify())

    def minimize_app(self):
        # DIRECT WIN32 MINIMIZE
        # Instead of self.root.iconify(), we send the SW_MINIMIZE command (6) directly.
        hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
        ctypes.windll.user32.ShowWindow(hwnd, 6) 

    def get_pos(self, event):
        self.x_offset = event.x
        self.y_offset = event.y

    def drag_window(self, event):
        x = self.root.winfo_x() + event.x - self.x_offset
        y = self.root.winfo_y() + event.y - self.y_offset
        self.root.geometry(f'+{x}+{y}')

    def close_app(self):
        self.root.destroy()
        
    def force_focus(self, event):
        # Ensure the text area gets the blinking cursor when window is clicked
        self.text_area.focus_set()

    def new_file(self):
        self.text_area.delete(1.0, tk.END)

    def open_file(self):
        pass

    def save_file(self):
        pass

if __name__ == "__main__":
    root = tk.Tk()
    app = PlanckEdit(root)
    root.mainloop()