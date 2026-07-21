"""日志面板组件 - 毛玻璃终端风格"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTextEdit, QLabel, QHBoxLayout, QPushButton
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from datetime import datetime
from ui.theme import theme_manager


class LogPanel(QWidget):
    """日志面板 — 暗色终端风格"""

    def __init__(self):
        super().__init__()
        self._setup_ui()
        self._apply_theme()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.log_text = QTextEdit()
        self.log_text.setObjectName("logText")
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(120)
        self.log_text.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.log_text.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        layout.addWidget(self.log_text)

    def log(self, message):
        """添加日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"<span style='color:{theme_manager.colors.get('text_muted')};'>[{timestamp}]</span> {message}")
        # 自动滚动到底部
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear(self):
        self.log_text.clear()

    def _apply_theme(self):
        c = theme_manager.colors
        self.log_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {c["log_bg"]};
                color: {c["text_secondary"]};
                font-family: "Consolas", "Cascadia Code", "Microsoft YaHei", monospace;
                font-size: 12px;
                border: 1px solid {c["border"]};
                border-radius: 10px;
                padding: 10px;
            }}
        """)

    def refresh_theme(self):
        self._apply_theme()