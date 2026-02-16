import sys
import json
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QPlainTextEdit, 
                               QWidget, QMenu, QTextEdit, QInputDialog, 
                               QFileDialog, QMessageBox)
from PySide6.QtGui import (QPalette, QColor, QFont, QAction, QPainter, 
                           QTextFormat, QCloseEvent, QKeySequence)
from PySide6.QtCore import Qt, QRect, QSize

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.codeEditor = editor

    def sizeHint(self):
        return QSize(self.codeEditor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.codeEditor.lineNumberAreaPaintEvent(event)

class CodeEditor(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        
        # --- CONFIGURATION ---
        self.tab_size = 4
        self.use_spaces = True
        self.font_size = 14
        self.font_family = "Courier New"
        # ---------------------

        self.line_number_area = LineNumberArea(self)

        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)

        self.setup_font()
        self.update_line_number_area_width(0)

    def setup_font(self):
        # Clean, consolidated font setup using the universal standard
        font = QFont(self.font_family)
        font.setStyleHint(QFont.Monospace)
        font.setPointSize(self.font_size)
        self.setFont(font)
        self.line_number_area.setFont(font)
        
        # Update tab stops based on the new font metrics
        metrics = self.fontMetrics()
        self.setTabStopDistance(self.tab_size * metrics.horizontalAdvance(' '))

    def line_number_area_width(self):
        digits = 1
        max_num = max(1, self.blockCount())
        while max_num >= 10:
            max_num //= 10
            digits += 1
        
        width = self.fontMetrics().horizontalAdvance('9')
        space = (width * digits) + width
        return space

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor(40, 40, 40))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                
                painter.setPen(QColor(150, 150, 150))
                painter.drawText(0, int(top), self.line_number_area.width() - 5, self.fontMetrics().height(),
                                 Qt.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1

    def set_tab_settings(self, size, use_spaces):
        self.tab_size = size
        self.use_spaces = use_spaces
        
        metrics = self.fontMetrics()
        self.setTabStopDistance(self.tab_size * metrics.horizontalAdvance(' '))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Tab and event.modifiers() == Qt.NoModifier:
            if self.use_spaces:
                self.insertPlainText(" " * self.tab_size)
            else:
                self.insertPlainText("\t")
            return 

        if event.key() == Qt.Key_Backtab:
            cursor = self.textCursor()
            position_in_block = cursor.positionInBlock()
            block_text = cursor.block().text()

            if self.use_spaces:
                text_before_cursor = block_text[:position_in_block]
                space_count = 0
                for char in reversed(text_before_cursor):
                    if char == ' ':
                        space_count += 1
                        if space_count == self.tab_size:
                            break
                    else:
                        break
                if space_count > 0:
                    for _ in range(space_count):
                        cursor.deletePreviousChar()
            else:
                if position_in_block > 0 and block_text[position_in_block - 1] == '\t':
                    cursor.deletePreviousChar()
            return

        if (event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter) and event.modifiers() == Qt.ShiftModifier:
            self.insertPlainText("\n")
            return

        super().keyPressEvent(event)

    def highlight_current_line(self):
        extra_selections = []
        
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            line_color = QColor(50, 50, 50) 
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)
        
        self.setExtraSelections(extra_selections)

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
        self.config = self.load_config()
        self.apply_settings()
        self.context_menu = QMenu(self)
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
        stash_action = QAction("Stash", self)
        stash_action.setShortcut(QKeySequence("Ctrl+Alt+S"))
        stash_action.triggered.connect(self.stash_file)
        self.context_menu.addAction(stash_action)
        self.addAction(stash_action)
        open_stash_action = QAction("Open Stash", self)
        open_stash_action.setShortcut(QKeySequence("Ctrl+Alt+O"))
        open_stash_action.triggered.connect(self.open_stash)
        self.context_menu.addAction(open_stash_action)
        self.addAction(open_stash_action)
        clear_stash_action = QAction("Clear Stash", self)
        clear_stash_action.setShortcut(QKeySequence("Ctrl+Alt+Backspace")) 
        clear_stash_action.triggered.connect(self.clear_stash)
        self.context_menu.addAction(clear_stash_action)
        self.addAction(clear_stash_action)
        self.context_menu.addSeparator()
        self.wrap_action = QAction("Toggle Word Wrap", self)
        self.wrap_action.setCheckable(True)
        self.wrap_action.setChecked(self.config["word_wrap"])
        self.wrap_action.triggered.connect(self.toggle_word_wrap)
        self.context_menu.addAction(self.wrap_action)
        self.context_menu.addSeparator()
        self.space_action = QAction("Indent with Spaces", self)
        self.space_action.setCheckable(True)
        self.space_action.setChecked(self.config["use_spaces"])
        self.space_action.triggered.connect(self.toggle_tabs_vs_spaces)
        self.context_menu.addAction(self.space_action)
        self.tab_size_action = QAction(f"Set Tab Size ({self.config['tab_size']})", self)
        self.tab_size_action.triggered.connect(self.change_tab_size)
        self.context_menu.addAction(self.tab_size_action)
        self.context_menu.addSeparator()
        close_action = QAction("Close", self)
        close_action.setShortcut(QKeySequence("Ctrl+W"))
        close_action.triggered.connect(self.close)
        self.context_menu.addAction(close_action)
        self.addAction(close_action)

        self.load_startup_stash()

    def new_file(self):
        if not self.maybe_save():
            return

        self.editor.clear()
        self.current_file = None 
        self.editor.document().setModified(False)
        self.update_title()

    def open_file(self):
        if not self.maybe_save():
            return

        path, _ = QFileDialog.getOpenFileName(self, "Open File", "", "All Files (*)")
        
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    text = f.read()
                
                self.editor.setPlainText(text)
                self.current_file = path
                self.editor.document().setModified(False)
                self.update_title()
            except Exception as e:
                print(f"Error opening file: {e}")

    def save_file(self):
        if self.current_file is None:
            return self.save_file_as()
        
        try:
            with open(self.current_file, 'w', encoding='utf-8') as f:
                f.write(self.editor.toPlainText())
            
            self.editor.document().setModified(False)
            self.update_title()
            print(f"Saved to {self.current_file}")
            return True
        except Exception as e:
            print(f"Error saving file: {e}")
            return False

    def save_file_as(self):
        was_stash_mode = (self.current_file is None)

        path, _ = QFileDialog.getSaveFileName(self, "Save File As", "", "All Files (*)")
        
        if path:
            self.current_file = path
            
            if self.save_file():
                if was_stash_mode:
                    self.clear_stash_file()
                return True
        
        return False
    
    def maybe_save(self):
        if not self.editor.document().isModified():
            return True

        if self.current_file is None:
            self.stash_file()
            return True 

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
        
        return True

    def stash_file(self):
        stash_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stash.txt")
        
        try:
            with open(stash_path, 'w', encoding='utf-8') as f:
                f.write(self.editor.toPlainText())
            
            print(f"Stashed to {stash_path}")
            
            self.setWindowTitle("planckedit - Stashed!")
            
        except Exception as e:
            print(f"Error stashing file: {e}")

    def open_stash(self):
        if self.current_file is not None:
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
            
            self.current_file = None 
            self.editor.document().setModified(False)
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
                
                self.editor.setPlainText(text)
                self.current_file = None
                self.editor.document().setModified(False)
                self.update_title()
            except Exception as e:
                print(f"Error loading stash on startup: {e}")

    def clear_stash_file(self):
        stash_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stash.txt")
        if os.path.exists(stash_path):
            try:
                os.remove(stash_path)
                print("Stash file cleared (content saved to new file).")
            except Exception as e:
                print(f"Error clearing stash: {e}")

    def clear_stash(self):
        stash_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stash.txt")
        if os.path.exists(stash_path):
            try:
                os.remove(stash_path)
                print("Stash file deleted.")
            except Exception as e:
                print(f"Error deleting stash file: {e}")

        self.editor.clear()
        self.current_file = None 
        self.editor.document().setModified(False)
        self.update_title()
    
    def update_title(self):
        title = "planckedit"
        
        if self.current_file:
            filename = os.path.basename(self.current_file)
            title = f"planckedit - {filename}"
        else:
            title = "planckedit - Untitled"

        if self.editor.document().isModified():
            title += "*"
            
        self.setWindowTitle(title)

    def closeEvent(self, event: QCloseEvent):
        if self.maybe_save():
            event.accept()
        else:
            event.ignore()

    def load_config(self):
        default_config = {
            "word_wrap": True,
            "tab_size": 4,
            "use_spaces": True
        }
        
        if not os.path.exists(self.config_path):
            return default_config

        try:
            with open(self.config_path, "r") as f:
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
        if self.config["word_wrap"]:
            self.editor.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        else:
            self.editor.setLineWrapMode(QPlainTextEdit.NoWrap)
            
        self.editor.set_tab_settings(self.config["tab_size"], self.config["use_spaces"])

    def apply_word_wrap(self, enabled):
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
            self.tab_size_action.setText(f"Set Tab Size ({num})")
            
            self.editor.set_tab_settings(self.config["tab_size"], self.config["use_spaces"])
            
            self.save_config()

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