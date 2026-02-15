import os
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog, font

class CodeEditor(tk.Frame):
    def __init__(self, master=None, on_change=None):
        super().__init__(master)
        self.on_change_callback = on_change
        self.tab_size = 4
        self.use_spaces = True
        self.font_size = 14
        self.font_family = "Consolas"

        # Grid configuration
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1) # Column 1 is the main text

        # 1. Line Number Area (Text widget, disabled)
        self.line_numbers = tk.Text(self, width=4, padx=4, takefocus=0, border=0,
                                    background="#2d2d2d", foreground="#969696", state='disabled')
        self.line_numbers.grid(row=0, column=0, sticky="ns")

        # 2. Main Editor Area
        self.text_area = tk.Text(self, wrap="none", undo=True, border=0,
                                 background="#1e1e1e", foreground="#e6e6e6",
                                 insertbackground="white") # white cursor
        self.text_area.grid(row=0, column=1, sticky="nsew")

        # 3. Scrollbar
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.sync_scroll)
        self.scrollbar.grid(row=0, column=2, sticky="ns")
        self.text_area.config(yscrollcommand=self.update_scroll)

        # 5. Events
        self.text_area.bind("<KeyRelease>", self.on_content_changed)
        self.text_area.bind("<Tab>", self.handle_tab)
        self.text_area.bind("<Shift-Tab>", self.handle_backtab)
        self.text_area.bind("<Shift-Return>", self.handle_shift_enter)
        
        # Mouse wheel sync
        self.line_numbers.bind("<MouseWheel>", self.sync_wheel)
        self.text_area.bind("<MouseWheel>", self.sync_wheel)

        self.setup_font()
        self.redraw_line_numbers()

    def setup_font(self):
        # Try to find a good monospace font
        available = font.families()
        if "Consolas" in available: self.font_family = "Consolas"
        elif "Menlo" in available: self.font_family = "Menlo"
        elif "Monospace" in available: self.font_family = "Monospace"
        else: self.font_family = "Courier New"

        self.custom_font = font.Font(family=self.font_family, size=self.font_size)
        self.text_area.configure(font=self.custom_font)
        self.line_numbers.configure(font=self.custom_font)
        
        # Update tab stops based on font width
        self.update_tab_stops()

    def update_tab_stops(self):
        # Calculate pixel width of a space to set correct tab stops
        space_width = self.custom_font.measure(" ")
        tab_width_pixels = self.tab_size * space_width
        self.text_area.configure(tabs=(tab_width_pixels,))

    def set_tab_settings(self, size, use_spaces):
        self.tab_size = size
        self.use_spaces = use_spaces
        self.update_tab_stops()

    # --- Scrolling & Line Numbers ---

    def sync_scroll(self, *args):
        # Triggered by scrollbar dragging
        self.text_area.yview(*args)
        self.line_numbers.yview(*args)

    def update_scroll(self, first, last):
        # Triggered by text area scrolling (updating the scrollbar)
        self.scrollbar.set(first, last)
        self.line_numbers.yview_moveto(first)

    def sync_wheel(self, event):
        # Triggered by mouse wheel, ensures both scroll together
        # Windows: event.delta, Linux: event.num
        return "break" # Handled natively by binding yview in most cases, 
                       # but if needed we would use self.text_area.yview_scroll(...)

    def on_content_changed(self, event=None):
        self.redraw_line_numbers()
        if self.on_change_callback:
            self.on_change_callback()

    def redraw_line_numbers(self):
        # Get number of lines
        content = self.text_area.get("1.0", "end-1c")
        lines = content.count("\n") + 1
        
        # Generate string "1\n2\n3..."
        line_str = "\n".join(str(i) for i in range(1, lines + 1))
        
        self.line_numbers.config(state='normal')
        self.line_numbers.delete("1.0", "end")
        self.line_numbers.insert("1.0", line_str)
        self.line_numbers.config(state='disabled')
        
        # Resync view position
        first, _ = self.text_area.yview()
        self.line_numbers.yview_moveto(first)

    # --- Key Handling ---

    def handle_tab(self, event):
        if self.use_spaces:
            self.text_area.insert("insert", " " * self.tab_size)
            return "break" # Prevent default tab behavior (moving focus)
        return None # Let default happen (insert \t)

    def handle_backtab(self, event):
        # Shift+Tab: Unindent
        if self.use_spaces:
            # Check previous chars
            cursor_idx = self.text_area.index("insert")
            line, col = map(int, cursor_idx.split('.'))
            
            if col == 0: return "break"

            # Get text before cursor on current line
            line_text = self.text_area.get(f"{line}.0", f"{line}.{col}")
            
            spaces_to_delete = 0
            for char in reversed(line_text):
                if char == ' ':
                    spaces_to_delete += 1
                    if spaces_to_delete == self.tab_size:
                        break
                else:
                    break
            
            if spaces_to_delete > 0:
                self.text_area.delete(f"insert-{spaces_to_delete}c", "insert")
        else:
            # Check for \t
            if self.text_area.get("insert-1c") == "\t":
                self.text_area.delete("insert-1c")
        
        return "break"

    def handle_shift_enter(self, event):
        # Force a real newline
        self.text_area.insert("insert", "\n")
        self.on_content_changed()
        return "break"

    # --- API for Main Window ---
    def get_text(self):
        return self.text_area.get("1.0", "end-1c")

    def set_text(self, text):
        self.text_area.delete("1.0", "end")
        self.text_area.insert("1.0", text)
        self.redraw_line_numbers()
        self.text_area.edit_reset() # Clear undo stack

    def clear(self):
        self.text_area.delete("1.0", "end")
        self.redraw_line_numbers()
        self.text_area.edit_reset()

    def is_modified(self):
        return self.text_area.edit_modified()

    def set_modified(self, value):
        self.text_area.edit_modified(value)

class PlanckEdit(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("planckedit")
        self.geometry("1280x720")
        self.configure(bg="#2d2d2d")
        
        self.current_file = None
        self.is_dirty = False # Track modification state manually for visual logic

        # Paths
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_path = os.path.join(script_dir, "config.json")

        # Layout
        self.editor = CodeEditor(self, on_change=self.on_text_modified)
        self.editor.pack(fill="both", expand=True)

        # Config
        self.config = self.load_config()
        self.apply_settings()

        # Menu Setup
        self.context_menu = tk.Menu(self, tearoff=0, bg="#2d2d2d", fg="#e6e6e6", 
                                    activebackground="#2a82da", activeforeground="white")
        self.create_menu_items()

        # Global Bindings
        self.bind("<Control-n>", lambda e: self.new_file())
        self.bind("<Control-o>", lambda e: self.open_file())
        self.bind("<Control-s>", lambda e: self.save_file())
        self.bind("<Control-S>", lambda e: self.save_file_as()) # Shift often sends capital S
        self.bind("<Control-w>", lambda e: self.close_app())
        self.bind("<Control-Alt-s>", lambda e: self.stash_file())
        self.bind("<Control-Alt-o>", lambda e: self.open_stash())
        self.bind("<Control-Alt-BackSpace>", lambda e: self.clear_stash())
        
        # Context Menu Binding (Ctrl + ` like in PySide version, or Right Click)
        self.bind("<Control-grave>", self.show_context_menu)
        self.editor.text_area.bind("<Button-3>", self.show_context_menu) # Right click

        # Window Close Event
        self.protocol("WM_DELETE_WINDOW", self.close_app)

        # Startup
        self.update_title()
        self.load_startup_stash()

    def on_text_modified(self):
        # Callback from editor when text changes
        if self.editor.is_modified():
            if not self.is_dirty:
                self.is_dirty = True
                self.update_title()
            # Reset the internal modified flag so we catch the next event
            self.editor.set_modified(False)
            # However, keep our logic flag True until saved

    def update_title(self):
        title = "planckedit"
        if self.current_file:
            title += f" - {os.path.basename(self.current_file)}"
        else:
            title += " - Untitled"
        
        if self.is_dirty:
            title += "*"
        
        self.title(title)

    def create_menu_items(self):
        self.context_menu.add_command(label="New (Ctrl+N)", command=self.new_file)
        self.context_menu.add_command(label="Open... (Ctrl+O)", command=self.open_file)
        self.context_menu.add_command(label="Save (Ctrl+S)", command=self.save_file)
        self.context_menu.add_command(label="Save As... (Ctrl+Shift+S)", command=self.save_file_as)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Stash (Ctrl+Alt+S)", command=self.stash_file)
        self.context_menu.add_command(label="Open Stash (Ctrl+Alt+O)", command=self.open_stash)
        self.context_menu.add_command(label="Clear Stash (Ctrl+Alt+BS)", command=self.clear_stash)
        self.context_menu.add_separator()
        
        self.wrap_var = tk.BooleanVar(value=self.config["word_wrap"])
        self.context_menu.add_checkbutton(label="Toggle Word Wrap", variable=self.wrap_var, 
                                          command=self.toggle_word_wrap)
        
        self.space_var = tk.BooleanVar(value=self.config["use_spaces"])
        self.context_menu.add_checkbutton(label="Indent with Spaces", variable=self.space_var,
                                          command=self.toggle_tabs_vs_spaces)
        
        self.context_menu.add_command(label="Set Tab Size...", command=self.change_tab_size)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Close (Ctrl+W)", command=self.close_app)

    def show_context_menu(self, event):
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    # --- File I/O ---

    def new_file(self):
        if not self.maybe_save(): return
        self.editor.clear()
        self.current_file = None
        self.is_dirty = False
        self.update_title()

    def open_file(self):
        if not self.maybe_save(): return
        path = filedialog.askopenfilename(title="Open File", filetypes=[("All Files", "*.*")])
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    text = f.read()
                self.editor.set_text(text)
                self.current_file = path
                self.is_dirty = False
                self.update_title()
            except Exception as e:
                print(f"Error opening file: {e}")

    def save_file(self):
        if self.current_file is None:
            return self.save_file_as()
        
        try:
            with open(self.current_file, 'w', encoding='utf-8') as f:
                f.write(self.editor.get_text())
            self.is_dirty = False
            self.update_title()
            print(f"Saved to {self.current_file}")
            return True
        except Exception as e:
            print(f"Error saving file: {e}")
            return False

    def save_file_as(self):
        was_stash_mode = (self.current_file is None)
        
        # FIX: Changed 'asksavefilename' to 'asksaveasfilename'
        path = filedialog.asksaveasfilename(title="Save File As", filetypes=[("All Files", "*.*")])
        
        if path:
            self.current_file = path
            if self.save_file():
                if was_stash_mode:
                    self.clear_stash_file()
                return True
        return False

    def maybe_save(self):
        if not self.is_dirty:
            return True
        
        # Scratchpad Logic: If Untitled and Dirty -> Auto Stash
        if self.current_file is None:
            self.stash_file()
            return True

        filename = os.path.basename(self.current_file)
        resp = messagebox.askyesnocancel("Unsaved Changes", 
                                         f"The document '{filename}' has been modified.\nDo you want to save your changes?")
        
        if resp is True: # Yes
            return self.save_file()
        elif resp is False: # No (Discard)
            return True
        else: # Cancel
            return False

    # --- Stash ---

    def stash_file(self):
        stash_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stash.txt")
        try:
            with open(stash_path, 'w', encoding='utf-8') as f:
                f.write(self.editor.get_text())
            print(f"Stashed to {stash_path}")
            self.title("planckedit - Stashed!")
        except Exception as e:
            print(f"Error stashing: {e}")

    def open_stash(self):
        # Only check safety if we are in a REAL file. 
        if self.current_file is not None:
            if not self.maybe_save(): return

        stash_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stash.txt")
        if not os.path.exists(stash_path):
            messagebox.showinfo("Stash Empty", "No stash file found.")
            return

        try:
            with open(stash_path, 'r', encoding='utf-8') as f:
                text = f.read()
            self.editor.set_text(text)
            self.current_file = None
            self.is_dirty = False
            self.update_title()
            print(f"Stash reloaded from {stash_path}")
        except Exception as e:
            print(f"Error opening stash: {e}")

    def load_startup_stash(self):
        stash_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stash.txt")
        if os.path.exists(stash_path):
            try:
                with open(stash_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                self.editor.set_text(text)
                self.current_file = None
                self.is_dirty = False
                self.update_title()
            except Exception as e:
                print(f"Error startup stash: {e}")

    def clear_stash_file(self):
        stash_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stash.txt")
        if os.path.exists(stash_path):
            os.remove(stash_path)
            print("Stash file cleared.")

    def clear_stash(self):
        self.clear_stash_file()
        self.editor.clear()
        self.current_file = None
        self.is_dirty = False
        self.update_title()

    # --- Config ---

    def load_config(self):
        default = {"word_wrap": True, "tab_size": 4, "use_spaces": True}
        if not os.path.exists(self.config_path): return default
        try:
            with open(self.config_path, "r") as f:
                default.update(json.load(f))
                return default
        except: return default

    def save_config(self):
        try:
            with open(self.config_path, "w") as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Config save error: {e}")

    def apply_settings(self):
        wrap_mode = "word" if self.config["word_wrap"] else "none"
        self.editor.text_area.configure(wrap=wrap_mode)
        self.editor.set_tab_settings(self.config["tab_size"], self.config["use_spaces"])

    def toggle_word_wrap(self):
        self.config["word_wrap"] = self.wrap_var.get()
        self.save_config()
        self.apply_settings()

    def toggle_tabs_vs_spaces(self):
        self.config["use_spaces"] = self.space_var.get()
        self.save_config()
        self.apply_settings()

    def change_tab_size(self):
        num = simpledialog.askinteger("Tab Size", "Enter tab width:", 
                                      initialvalue=self.config["tab_size"], minvalue=1, maxvalue=16)
        if num:
            self.config["tab_size"] = num
            self.save_config()
            self.apply_settings()

    def close_app(self, event=None):
        if self.maybe_save():
            self.destroy()

if __name__ == "__main__":
    app = PlanckEdit()
    app.mainloop()