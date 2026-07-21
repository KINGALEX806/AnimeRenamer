# -*- coding: utf-8 -*-
"""AnimeRenamer - 番剧视频智能重命名工具
主入口文件
"""
import sys
import os
import traceback
from pathlib import Path
from datetime import datetime

# 确保控制台输出编码为 UTF-8
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ====== 启动诊断日志 ======
_log_lines = []
def _diag(msg):
    _log_lines.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

_diag(f"Python: {sys.executable}")
_diag(f"version: {sys.version}")
_diag(f"cwd: {os.getcwd()}")
_diag(f"app_dir: {os.path.dirname(os.path.abspath(__file__))}")

try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
    import PySide6
    _diag(f"PySide6: {PySide6.__version__}")
except Exception as e:
    _diag(f"PySide6 import FAILED: {e}")

_diag(f"expanduser: {os.path.expanduser('~')}")

from ui.main_window import MainWindow
from ui.theme import theme_manager
from utils.config import load_config


def main():
    _diag("main() start")

    # 高 DPI 支持
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("AnimeRenamer")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("AnimeRenamer")

    # 应用主题
    config = load_config()
    _diag(f"config loaded: theme={config.get('theme')}, "
          f"title_source={config.get('title_source')}, "
          f"enabled_dbs={config.get('enabled_dbs')}")

    theme = config.get("theme", "dark")
    _diag(f"applying theme: {theme}")
    _diag(f"theme_manager._current_theme before set: {theme_manager._current_theme}")
    _diag(f"theme_manager.colors['bg_primary']: {theme_manager.colors.get('bg_primary')}")
    _diag(f"theme_manager.colors['name']: {theme_manager.colors.get('name')}")
    theme_manager.set_theme(theme)
    _diag(f"theme_manager._current_theme after set: {theme_manager._current_theme}")

    # 创建主窗口
    _diag("creating MainWindow")
    window = MainWindow()
    _diag("MainWindow created, showing")
    window.show()

    # 写日志文件
    try:
        log_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        log_file = log_dir / "startup.log"
        with open(log_file, "w", encoding="utf-8") as f:
            f.write("\n".join(_log_lines))
        _diag(f"log written to {log_file}")
    except Exception as e:
        _diag(f"FAILED to write log: {e}")

    try:
        sys.exit(app.exec())
    except Exception as e:
        _diag(f"app.exec() crashed: {e}\n{traceback.format_exc()}")
        try:
            log_dir = Path(os.path.dirname(os.path.abspath(__file__)))
            log_file = log_dir / "crash.log"
            with open(log_file, "w", encoding="utf-8") as f:
                f.write("\n".join(_log_lines))
                f.write(f"\nCRASH: {e}\n{traceback.format_exc()}")
        except:
            pass


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        _diag(f"FATAL: {e}\n{traceback.format_exc()}")
        try:
            log_dir = Path(os.path.dirname(os.path.abspath(__file__)))
            log_file = log_dir / "crash.log"
            with open(log_file, "w", encoding="utf-8") as f:
                f.write("\n".join(_log_lines))
                f.write(f"\nFATAL: {e}\n{traceback.format_exc()}")
        except:
            pass