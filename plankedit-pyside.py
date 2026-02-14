import sys
import json
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QPlainTextEdit, 
                               QWidget, QMenu, QTextEdit)
from PySide6.QtGui import (QPalette, QColor, QFont, QAction, QPainter, 
                           QTextFormat)
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

    def keyPressEvent(self, event):
        """
        Overrides the default key press to convert Tab to 4 spaces.
        """
        # Check if the key is Tab and no modifiers (like Ctrl or Alt) are pressed
        if event.key() == Qt.Key_Tab and event.modifiers() == Qt.NoModifier:
            self.insertPlainText("    ")
            # We return early to prevent the default behavior (inserting \t)
            return 
        
        # For all other keys, use the default behavior
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

        # 1. Determine Config Path (Same folder as this script)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_path = os.path.join(script_dir, "config.json")

        # 2. Setup Editor
        self.editor = CodeEditor()
        self.setCentralWidget(self.editor)
        
        self.setup_font(size=14)
        
        # 3. Load Config (Defaults if file missing)
        self.config = self.load_config()

        # 4. Setup Menu
        self.context_menu = QMenu(self)
        
        # Word Wrap Action
        self.wrap_action = QAction("Toggle Word Wrap", self)
        self.wrap_action.setCheckable(True)
        
        # Apply the loaded setting to the GUI
        is_wrapped = self.config.get("word_wrap", True) # Default True
        self.wrap_action.setChecked(is_wrapped)
        self.apply_word_wrap(is_wrapped)
        
        self.wrap_action.triggered.connect(self.toggle_word_wrap)
        self.context_menu.addAction(self.wrap_action)

        self.context_menu.addSeparator()

        close_action = QAction("Close", self)
        close_action.triggered.connect(self.close)
        self.context_menu.addAction(close_action)

    def load_config(self):
        """
        Loads settings from config.json. Returns default dict if file 
        doesn't exist or is corrupt.
        """
        default_config = {"word_wrap": True}
        
        if not os.path.exists(self.config_path):
            return default_config

        try:
            with open(self.config_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            print("Error loading config, using defaults.")
            return default_config

    def save_config(self):
        """Writes the current self.config dictionary to config.json"""
        try:
            with open(self.config_path, "w") as f:
                json.dump(self.config, f, indent=4)
        except IOError as e:
            print(f"Error saving config: {e}")

    def apply_word_wrap(self, enabled):
        """Helper to actually apply the setting to the editor widget"""
        if enabled:
            self.editor.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        else:
            self.editor.setLineWrapMode(QPlainTextEdit.NoWrap)

    def toggle_word_wrap(self):
        # 1. Get new state
        is_checked = self.wrap_action.isChecked()
        
        # 2. Apply it
        self.apply_word_wrap(is_checked)
        
        # 3. Update Config Object
        self.config["word_wrap"] = is_checked
        
        # 4. Save Immediately
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