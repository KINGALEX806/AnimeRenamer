# -*- coding: utf-8 -*-
"""AnimeRenamer - 无控制台静默启动入口 (.pyw)

双击此文件即可无窗口启动 AnimeRenamer。
Windows 会自动使用 pythonw.exe 执行 .pyw 文件。
"""
import sys
import os

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from ui.main_window import MainWindow
from ui.theme import theme_manager
from utils.config import load_config


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("AnimeRenamer")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("AnimeRenamer")

    config = load_config()
    theme = config.get("theme", "dark")
    theme_manager.set_theme(theme)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()