import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QPlainTextEdit, QMenu
from PySide6.QtGui import QPalette, QColor, QFont, QAction, QKeySequence, QCursor
from PySide6.QtCore import Qt

class PlanckEdit(QMainWindow):
    def __init__(self):
        super().__init__()

        # 1. Basic Setup
        self.setWindowTitle("planckedit")
        self.resize(1280, 720)

        # 2. Central Widget (The Editor)
        self.editor = QPlainTextEdit()
        self.setCentralWidget(self.editor)
        
        # 3. Font Setup
        self.setup_font(size=12)

        # 4. Custom Menu Setup
        self.context_menu = QMenu(self)
        
        # Add "Close" action
        close_action = QAction("Close", self)
        close_action.triggered.connect(self.close)
        self.context_menu.addAction(close_action)

    def setup_font(self, size=12):
        """Sets the editor to a common monospaced font."""
        # Try specific common monospace fonts, fall back to generic styling hint
        font = QFont("Consolas") 
        if not font.exactMatch():
            font = QFont("Menlo") 
        if not font.exactMatch():
            font = QFont("Courier New")
            
        font.setStyleHint(QFont.Monospace)
        font.setPointSize(size)
        self.editor.setFont(font)
        
    def set_font_size(self, size):
        """Public method to adjust font size dynamically."""
        font = self.editor.font()
        font.setPointSize(size)
        self.editor.setFont(font)

    def keyPressEvent(self, event):
        """Handle custom keyboard shortcuts."""
        # Check for Ctrl + Backtick (`)
        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_QuoteLeft:
            # Show menu at the current cursor position
            self.context_menu.exec(QCursor.pos())
        else:
            # Important: Pass other events to the base class so typing still works!
            super().keyPressEvent(event)

def set_dark_theme(app):
    """
    Applies a dark theme using Fusion style, QPalette, and QSS for specific widgets.
    """
    app.setStyle("Fusion")

    dark_palette = QPalette()
    
    # Define colors
    dark_bg = QColor(45, 45, 45)
    editor_bg = QColor(30, 30, 30)
    text_color = QColor(230, 230, 230)
    highlight_color = QColor(42, 130, 218) # The nice blue

    # General Palette
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

    # QSS for the Context Menu
    # QMenu sometimes resists QPalette for hover states, so we enforce it with CSS.
    app.setStyleSheet(f"""
        QMenu {{
            background-color: {dark_bg.name()};
            color: {text_color.name()};
            border: 1px solid #555555;
        }}
        QMenu::item {{
            padding: 5px 20px;
        }}
        QMenu::item:selected {{
            background-color: {highlight_color.name()};
            color: white;
        }}
    """)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    set_dark_theme(app)
    
    window = PlanckEdit()
    window.show()
    
    sys.exit(app.exec())