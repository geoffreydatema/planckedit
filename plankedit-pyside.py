import sys
import json
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QPlainTextEdit, 
                               QWidget, QMenu, QTextEdit, QInputDialog, 
                               QFileDialog, QMessageBox) # <--- Added QMessageBox
from PySide6.QtGui import (QPalette, QColor, QFont, QAction, QPainter, 
                           QTextFormat, QCloseEvent, QKeySequence)
from PySide6.QtCore import Qt, QRect, QSize

# --- 1. The Line Number Sidebar Widget ---
class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.codeEditor = editor

    def sizeHint(self):
        return QSize(self.codeEditor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.codeEditor.lineNumberAreaPaintEvent(event)


# --- 2. The Custom Editor Engine ---
class CodeEditor(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        
        # Default settings (will be overwritten by config on load)
        self.tab_size = 4
        self.use_spaces = True

        self.line_number_area = LineNumberArea(self)

        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)

        self.update_line_number_area_width(0)

    def line_number_area_width(self):
        """Calculates the width needed for the line number sidebar."""
        digits = 1
        max_num = max(1, self.blockCount())
        while max_num >= 10:
            max_num //= 10
            digits += 1
        
        # Width of a character '9' in the current font
        space = 3 + self.fontMetrics().horizontalAdvance('9') * digits + 10 
        return space

    def update_line_number_area_width(self, _):
        """Updates the sidebar width when the number of lines changes (e.g. 99 -> 100)."""
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        """Handles scrolling of the sidebar."""
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        """Ensures the sidebar stays the correct size/pos when window resizes."""
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def lineNumberAreaPaintEvent(self, event):
        """
        The core logic: Draws the line numbers.
        This handles the mapping between Logical Lines (blocks) and Visual coordinates.
        """
        painter = QPainter(self.line_number_area)
        
        # Color the sidebar background slightly lighter than the editor
        painter.fillRect(event.rect(), QColor(40, 40, 40))

        # Get the first visible block
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        
        # Calculate the top/bottom geometry of the current block
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        # Loop through all visible blocks
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                
                # Draw the number
                painter.setPen(QColor(150, 150, 150)) # Grey text for numbers
                painter.drawText(0, int(top), self.line_number_area.width() - 5, self.fontMetrics().height(),
                                 Qt.AlignRight, number)

            # Move to the next block
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1

    def set_tab_settings(self, size, use_spaces):
        """Updates the internal tab settings and the visual tab width."""
        self.tab_size = size
        self.use_spaces = use_spaces
        
        # Update how existing \t characters are rendered
        metrics = self.fontMetrics()
        self.setTabStopDistance(self.tab_size * metrics.horizontalAdvance(' '))

    def keyPressEvent(self, event):
        # 1. Handle Tab (Indent)
        if event.key() == Qt.Key_Tab and event.modifiers() == Qt.NoModifier:
            if self.use_spaces:
                self.insertPlainText(" " * self.tab_size)
            else:
                self.insertPlainText("\t")
            return 

        # 2. Handle Shift + Tab (Unindent / Smart Backspace)
        if event.key() == Qt.Key_Backtab:
            cursor = self.textCursor()
            position_in_block = cursor.positionInBlock()
            block_text = cursor.block().text()

            if self.use_spaces:
                # SPACES MODE: Check for spaces before cursor
                # Slice the text up to the cursor position
                text_before_cursor = block_text[:position_in_block]
                
                # Count consecutive spaces backwards (up to tab_size)
                space_count = 0
                for char in reversed(text_before_cursor):
                    if char == ' ':
                        space_count += 1
                        if space_count == self.tab_size:
                            break
                    else:
                        break
                
                # Delete the counted spaces
                if space_count > 0:
                    for _ in range(space_count):
                        cursor.deletePreviousChar()

            else:
                # TAB MODE: Check if previous char is a tab
                if position_in_block > 0 and block_text[position_in_block - 1] == '\t':
                    cursor.deletePreviousChar()
            
            return

        # 3. Default Handler
        super().keyPressEvent(event)

    def highlight_current_line(self):
        """Highlights the line where the cursor currently is."""
        extra_selections = []
        
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            
            line_color = QColor(50, 50, 50) 
            selection.format.setBackground(line_color)
            
            # FIX IS HERE: Use QTextFormat instead of QTextOption
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)
        
        self.setExtraSelections(extra_selections)


# --- 3. The Main Application Window ---
class PlanckEdit(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("planckedit")
        self.resize(1280, 720)

        self.current_file = None

        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_path = os.path.join(script_dir, "config.json")

        self.editor = CodeEditor()
        self.setCentralWidget(self.editor)

        self.editor.modificationChanged.connect(lambda _: self.update_title())
        
        # Load Config (with new defaults)
        self.config = self.load_config()
        
        # Setup Font (Must happen before applying tab settings)
        self.setup_font(size=14)

        # Apply settings to the Editor
        self.apply_settings()

        # --- Menu Setup ---
        self.context_menu = QMenu(self)
        
        # FILE OPERATIONS
        new_action = QAction("New", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_file)
        self.context_menu.addAction(new_action)
        self.addAction(new_action)

        open_action = QAction("Open...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_file)
        self.context_menu.addAction(open_action)
        self.addAction(open_action)

        save_action = QAction("Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_file)
        self.context_menu.addAction(save_action)
        self.addAction(save_action)

        save_as_action = QAction("Save As...", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.save_file_as)
        self.context_menu.addAction(save_as_action)
        self.addAction(save_as_action)

        self.context_menu.addSeparator()

        # STASH (Ctrl + Alt + S)
        stash_action = QAction("Stash", self)
        stash_action.setShortcut(QKeySequence("Ctrl+Alt+S"))
        stash_action.triggered.connect(self.stash_file)
        self.context_menu.addAction(stash_action)
        self.addAction(stash_action)

        # OPEN STASH (Ctrl + Alt + O)
        open_stash_action = QAction("Open Stash", self)
        open_stash_action.setShortcut(QKeySequence("Ctrl+Alt+O"))
        open_stash_action.triggered.connect(self.open_stash)
        self.context_menu.addAction(open_stash_action)
        self.addAction(open_stash_action)

        self.context_menu.addSeparator()

        # 1. Word Wrap Action
        self.wrap_action = QAction("Toggle Word Wrap", self)
        self.wrap_action.setCheckable(True)
        self.wrap_action.setChecked(self.config["word_wrap"])
        self.wrap_action.triggered.connect(self.toggle_word_wrap)
        self.context_menu.addAction(self.wrap_action)

        self.context_menu.addSeparator()

        # 2. Indent with Spaces Action (Toggle)
        self.space_action = QAction("Indent with Spaces", self)
        self.space_action.setCheckable(True)
        self.space_action.setChecked(self.config["use_spaces"])
        self.space_action.triggered.connect(self.toggle_tabs_vs_spaces)
        self.context_menu.addAction(self.space_action)

        # 3. Set Tab Size Action
        self.tab_size_action = QAction(f"Set Tab Size ({self.config['tab_size']})", self)
        self.tab_size_action.triggered.connect(self.change_tab_size)
        self.context_menu.addAction(self.tab_size_action)

        self.context_menu.addSeparator()

        close_action = QAction("Close", self)
        close_action.setShortcut(QKeySequence("Ctrl+W")) # Standard shortcut
        close_action.triggered.connect(self.close)       # Calls the window's .close() method
        self.context_menu.addAction(close_action)
        self.addAction(close_action)

        self.load_startup_stash()

    def new_file(self):
        # 1. Check for unsaved changes first
        if not self.maybe_save():
            return # User cancelled

        # 2. Reset the editor state
        self.editor.clear()
        self.current_file = None 
        
        # 3. Reset the "dirty" flag so it doesn't think the blank file is modified
        self.editor.document().setModified(False)
        
        # 4. Update the UI
        self.update_title()

    def open_file(self):
        # NEW: Check for unsaved changes before opening a new file
        if not self.maybe_save():
            return

        path, _ = QFileDialog.getOpenFileName(self, "Open File", "", "All Files (*)")
        
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    text = f.read()
                
                self.editor.setPlainText(text)
                self.current_file = path
                self.editor.document().setModified(False) # Reset modified flag
                self.update_title()
            except Exception as e:
                print(f"Error opening file: {e}")

    def save_file(self):
        """Returns True if saved successfully, False if cancelled or failed."""
        if self.current_file is None:
            return self.save_file_as()
        
        try:
            with open(self.current_file, 'w', encoding='utf-8') as f:
                f.write(self.editor.toPlainText())
            
            self.editor.document().setModified(False) # Reset modified flag
            self.update_title()
            print(f"Saved to {self.current_file}")
            return True
        except Exception as e:
            print(f"Error saving file: {e}")
            return False

    def save_file_as(self):
        """
        Prompts for a filename and saves the content.
        If we were working on an Untitled file (stash) and successfully saved,
        it clears the stash file to prevent 'zombie' notes reappearing.
        """
        # 1. Capture state BEFORE the save: Are we currently editing the stash/untitled?
        was_stash_mode = (self.current_file is None)

        path, _ = QFileDialog.getSaveFileName(self, "Save File As", "", "All Files (*)")
        
        if path:
            self.current_file = path
            
            # 2. Attempt the save
            if self.save_file():
                # 3. If successful AND we came from stash mode, wipe the old stash file
                if was_stash_mode:
                    self.clear_stash_file()
                return True
        
        return False # User pressed Cancel
    
    def maybe_save(self):
        """
        Checks if there are unsaved changes.
        - If Untitled & Modified: Silently Stash and proceed.
        - If File Open & Modified: Ask user to Save/Discard/Cancel.
        """
        if not self.editor.document().isModified():
            return True

        # CASE 1: Untitled Document (Scratchpad mode)
        # "Just stash it and don't bother me."
        if self.current_file is None:
            self.stash_file()
            return True 

        # CASE 2: Existing File (Strict mode)
        # "I am editing a real file, please ask me before you lose my work."
        filename = os.path.basename(self.current_file)
        text = f"The document '{filename}' has been modified.\nDo you want to save your changes?"

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Unsaved Changes")
        msg_box.setText(text)
        msg_box.setIcon(QMessageBox.NoIcon) 
        msg_box.setStandardButtons(QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
        msg_box.setDefaultButton(QMessageBox.Save)
        
        ret = msg_box.exec()

        if ret == QMessageBox.Save:
            return self.save_file()
        elif ret == QMessageBox.Cancel:
            return False
        
        return True # User chose Discard

    def stash_file(self):
        """
        Saves the current editor content to 'stash.txt' in the script directory.
        Does NOT change the current filename context.
        """
        stash_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stash.txt")
        
        try:
            with open(stash_path, 'w', encoding='utf-8') as f:
                f.write(self.editor.toPlainText())
            
            # Flash a message on the status bar or just print for now
            # (Since we don't have a status bar, we can use a temporary title change or just console)
            print(f"Stashed to {stash_path}")
            
            # Optional: Visual feedback (flash the window title briefly)
            original_title = self.windowTitle()
            self.setWindowTitle("planckedit - Stashed!")
            # Restore title after 1 second (requires QTimer, but let's keep it simple for now)
            # You could also just use a QMessageBox.information if you want explicit confirmation
            
        except Exception as e:
            print(f"Error stashing file: {e}")

    def open_stash(self):
        """
        Opens 'stash.txt' into the editor.
        Sets current_file to None so 'Save' triggers 'Save As'.
        """
        # 1. Check for unsaved changes in current doc
        if not self.maybe_save():
            return

        stash_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stash.txt")

        if not os.path.exists(stash_path):
            QMessageBox.information(self, "Stash Empty", "No stash file found.")
            return

        try:
            with open(stash_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            self.editor.setPlainText(text)
            
            # CRITICAL: We do NOT set self.current_file to stash_path.
            # We set it to None. This ensures "Ctrl+S" triggers "Save As".
            self.current_file = None 
            self.editor.document().setModified(False)
            self.update_title()
            
        except Exception as e:
            print(f"Error opening stash: {e}")

    def load_startup_stash(self):
        """
        Checks for stash.txt at startup and loads it if found.
        """
        stash_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stash.txt")
        
        if os.path.exists(stash_path):
            try:
                with open(stash_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                
                self.editor.setPlainText(text)
                self.current_file = None # Ensure it stays in "Scratchpad" mode
                self.editor.document().setModified(False) # Reset dirty flag
                self.update_title()
            except Exception as e:
                print(f"Error loading stash on startup: {e}")

    def clear_stash_file(self):
        """
        Removes the stash file from disk. 
        Used when the stash content has been successfully promoted to a real file.
        """
        stash_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stash.txt")
        if os.path.exists(stash_path):
            try:
                os.remove(stash_path)
                print("Stash file cleared (content saved to new file).")
            except Exception as e:
                print(f"Error clearing stash: {e}")
    
    def update_title(self):
        """Updates the window title with filename and asterisk."""
        title = "planckedit"
        
        if self.current_file:
            filename = os.path.basename(self.current_file)
            title = f"planckedit - {filename}"
        else:
            title = "planckedit - Untitled"
            
        # Add asterisk if modified
        if self.editor.document().isModified():
            title += "*"
            
        self.setWindowTitle(title)

    def closeEvent(self, event: QCloseEvent):
        """Intercepts the application close event."""
        if self.maybe_save():
            event.accept()
        else:
            event.ignore()

    def load_config(self):
        # New defaults included
        default_config = {
            "word_wrap": True,
            "tab_size": 4,
            "use_spaces": True
        }
        
        if not os.path.exists(self.config_path):
            return default_config

        try:
            with open(self.config_path, "r") as f:
                # Merge loaded config with defaults (in case new keys were added)
                loaded = json.load(f)
                default_config.update(loaded)
                return default_config
        except (json.JSONDecodeError, IOError):
            return default_config

    def save_config(self):
        try:
            with open(self.config_path, "w") as f:
                json.dump(self.config, f, indent=4)
        except IOError as e:
            print(f"Error saving config: {e}")

    def apply_settings(self):
        """Applies all current config values to the editor."""
        # Word Wrap
        if self.config["word_wrap"]:
            self.editor.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        else:
            self.editor.setLineWrapMode(QPlainTextEdit.NoWrap)
            
        # Tab Settings
        self.editor.set_tab_settings(self.config["tab_size"], self.config["use_spaces"])

    def apply_word_wrap(self, enabled):
        """Helper to actually apply the setting to the editor widget"""
        if enabled:
            self.editor.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        else:
            self.editor.setLineWrapMode(QPlainTextEdit.NoWrap)

    def toggle_word_wrap(self):
        self.config["word_wrap"] = self.wrap_action.isChecked()
        self.save_config()
        self.apply_settings()

    def toggle_tabs_vs_spaces(self):
        self.config["use_spaces"] = self.space_action.isChecked()
        self.save_config()
        self.apply_settings()

    def change_tab_size(self):
        # QInputDialog.getInt(parent, title, label, value, min, max, step)
        num, ok = QInputDialog.getInt(
            self, 
            "Tab Size", 
            "Enter tab width:", 
            self.config["tab_size"], 
            1, 
            16, 
            1
        )
        if ok:
            self.config["tab_size"] = num
            # Update menu text to reflect new size
            self.tab_size_action.setText(f"Set Tab Size ({num})")
            
            # Update editor
            self.editor.set_tab_settings(self.config["tab_size"], self.config["use_spaces"])
            
            self.save_config()

    def setup_font(self, size=12):
        font = QFont("Consolas") 
        if not font.exactMatch():
            font = QFont("Menlo") 
        if not font.exactMatch():
            font = QFont("Monospace")
            
        font.setStyleHint(QFont.Monospace)
        font.setPointSize(size)
        self.editor.setFont(font)

        # NEW: Set the visual tab stop distance to 4 spaces
        # This ensures existing tabs in files look correct
        metrics = self.editor.fontMetrics()
        self.editor.setTabStopDistance(4 * metrics.horizontalAdvance(' '))

    def keyPressEvent(self, event):
        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_QuoteLeft:
            self.context_menu.exec(self.cursor().pos())
        else:
            super().keyPressEvent(event)

def set_dark_theme(app):
    app.setStyle("Fusion")
    dark_palette = QPalette()
    dark_bg = QColor(45, 45, 45)
    editor_bg = QColor(30, 30, 30)
    text_color = QColor(230, 230, 230)
    highlight_color = QColor(42, 130, 218)

    dark_palette.setColor(QPalette.Window, dark_bg)
    dark_palette.setColor(QPalette.WindowText, text_color)
    dark_palette.setColor(QPalette.Base, editor_bg)
    dark_palette.setColor(QPalette.AlternateBase, dark_bg)
    dark_palette.setColor(QPalette.ToolTipBase, text_color)
    dark_palette.setColor(QPalette.ToolTipText, text_color)
    dark_palette.setColor(QPalette.Text, text_color)
    dark_palette.setColor(QPalette.Button, dark_bg)
    dark_palette.setColor(QPalette.ButtonText, text_color)
    dark_palette.setColor(QPalette.Link, highlight_color)
    dark_palette.setColor(QPalette.Highlight, highlight_color)
    dark_palette.setColor(QPalette.HighlightedText, Qt.white)
    app.setPalette(dark_palette)

    app.setStyleSheet(f"""
        QMenu {{ background-color: {dark_bg.name()}; color: {text_color.name()}; border: 1px solid #555555; }}
        QMenu::item {{ padding: 5px 20px; }}
        QMenu::item:selected {{ background-color: {highlight_color.name()}; color: white; }}
    """)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    set_dark_theme(app)
    window = PlanckEdit()
    window.show()
    sys.exit(app.exec())