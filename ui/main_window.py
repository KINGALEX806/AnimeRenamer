"""主窗口 - AnimeRenamer 堤丰双形态毛玻璃美学界面"""
import os
import re as re_mod
import subprocess
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QStackedWidget, QSplitter,
    QStatusBar, QMessageBox, QProgressBar, QFrame, QSizePolicy,
    QDialog, QScrollArea, QLineEdit, QComboBox
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QSize
from PySide6.QtGui import QFont, QDragEnterEvent, QDropEvent, QColor, QPixmap, QIcon

from core.scanner import scan_folder, MediaFile
from core.parser import parse_filename, ParsedInfo, get_season_episode_str
from core.recognizer import AnimeRecognizer
from core.renamer import RenameEngine, RenameItem
from core.subtitle_matcher import match_subtitles_to_videos
from ui.file_list import FileListWidget
from ui.settings_panel import SettingsPanel
from ui.theme import theme_manager
from ui.styles import get_stylesheet
from utils.config import load_config, save_config


class RecognizeWorker(QThread):
    progress = Signal(int, int, str)
    log = Signal(str)
    finished = Signal(dict)

    def __init__(self, parsed_infos, config, manual_keyword=None, bangumi_id=None):
        super().__init__()
        self.parsed_infos = parsed_infos
        self.config = config
        self.manual_keyword = manual_keyword
        self.bangumi_id = bangumi_id

    def run(self):
        recognizer = AnimeRecognizer(
            config=self.config,
            progress_callback=lambda c, t, m: self.progress.emit(c, t, m),
            log_callback=lambda m: self.log.emit(m)
        )
        if self.bangumi_id:
            # 直接通过 ID 识别
            anime_info = recognizer.recognize_by_bangumi_id(self.bangumi_id, self.parsed_infos[0])
            if anime_info:
                results = {}
                for info in self.parsed_infos:
                    key = f"{info.show_title}_{info.year}"
                    results[key] = anime_info
            else:
                results = {}
            self.finished.emit(results)
        else:
            results = recognizer.batch_recognize(self.parsed_infos, manual_keyword=self.manual_keyword)
            self.finished.emit(results)


class SearchCandidatesWorker(QThread):
    """获取搜索候选列表（快速 API 调用）"""
    finished = Signal(list)
    log = Signal(str)

    def __init__(self, title, config):
        super().__init__()
        self.title = title
        self.config = config

    def run(self):
        recognizer = AnimeRecognizer(
            config=self.config,
            log_callback=lambda m: self.log.emit(m)
        )
        candidates = recognizer.get_search_candidates(self.title, limit=5)
        self.finished.emit(candidates)


class MainWindow(QMainWindow):

    NAV_HOME = 0
    NAV_FILES = 1
    NAV_SETTINGS = 2
    NAV_ABOUT = 3

    _NAV_LABELS = [
        "\U0001F3E0  \u9996\u9875",
        "\U0001F4C2  \u6587\u4EF6",
        "\u2699  \u8BBE\u7F6E",
        "\u2139    \u5173\u4E8E",
    ]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AnimeRenamer — \u756A\u5267\u91CD\u547D\u540D\u5DE5\u5177")
        self.setMinimumSize(1100, 700)
        self.resize(1300, 820)

        self.rename_engine = RenameEngine(log_callback=self._log)
        self.rename_items = []
        self.video_files = []
        self.subtitle_files = []
        self.parsed_infos = []
        self.anime_infos = {}
        self.current_folder = None
        self._active_nav = self.NAV_HOME
        self._is_drag_over = False
        self._sidebar_width = 240
        self._ignore_combo_change = False   # 防止填充下拉框时触发重新识别
        self._search_candidates = []        # 当前搜索结果候选列表
        self._current_search_title = ""     # 当前搜索标题
        self._skip_candidates_fetch = False # 通过下拉框重选时跳过候选获取

        self.setAcceptDrops(True)

        self._setup_ui()
        self._apply_theme()
        self._connect_signals()
        self._update_button_states()

    # ══════════════════════════════════════════════════════════
    #  界面构建
    # ══════════════════════════════════════════════════════════

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(1)
        self.splitter.setStyleSheet("QSplitter::handle { background-color: rgba(255,255,255,0.06); }")

        self.sidebar = self._build_sidebar()
        self.splitter.addWidget(self.sidebar)

        self.right_widget = self._build_right_area()
        self.splitter.addWidget(self.right_widget)

        self.splitter.setSizes([self._sidebar_width, self.width() - self._sidebar_width])
        self.splitter.splitterMoved.connect(self._on_splitter_moved)

        root.addWidget(self.splitter)

        self.qt_status_bar = QStatusBar()
        self.setStatusBar(self.qt_status_bar)
        self.qt_status_bar.showMessage("\u5C31\u7EEA — \u6B22\u8FCE\u4F7F\u7528 AnimeRenamer")

    def _build_right_area(self):
        right = QWidget()
        right.setObjectName("mainDropArea")
        right.setAcceptDrops(True)
        right.dragEnterEvent = self._on_main_drag_enter
        right.dragLeaveEvent = self._on_main_drag_leave
        right.dropEvent = self._on_main_drop
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.page_stack = QStackedWidget()
        self.page_home = self._build_home_page()
        self.page_files = self._build_files_page()
        self.page_settings = self._build_settings_page()
        self.page_about = self._build_about_page()

        self.page_stack.addWidget(self.page_home)
        self.page_stack.addWidget(self.page_files)
        self.page_stack.addWidget(self.page_settings)
        self.page_stack.addWidget(self.page_about)

        right_layout.addWidget(self.page_stack, stretch=1)

        return right

    # ──────────────────────────────────────────────────────────
    #  侧边栏
    # ──────────────────────────────────────────────────────────

    def _build_sidebar(self):
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setMinimumWidth(180)
        sidebar.setMaximumWidth(400)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(8, 12, 8, 10)
        sidebar_layout.setSpacing(0)

        self._build_avatar_area(sidebar_layout)

        sidebar_layout.addSpacing(6)

        title = QLabel("AnimeRenamer")
        title.setObjectName("sidebarTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(title)

        subtitle = QLabel("ANIME ORGANIZER")
        subtitle.setObjectName("sidebarSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(subtitle)

        sidebar_layout.addStretch(1)

        self.nav_buttons = []
        for i, label in enumerate(self._NAV_LABELS):
            btn = QPushButton(label)
            btn.setObjectName("navBtnActive" if i == self.NAV_HOME else "navBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, idx=i: self._switch_nav(idx))
            sidebar_layout.addWidget(btn)
            sidebar_layout.addSpacing(2)
            self.nav_buttons.append(btn)

        sidebar_layout.addStretch(1)

        self.theme_btn = QPushButton("\U0001F319  \u6697\u8272\u6A21\u5F0F")
        self.theme_btn.setObjectName("themeToggleBtn")
        self.theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_btn.clicked.connect(self._toggle_theme)
        sidebar_layout.addWidget(self.theme_btn)

        sidebar_layout.addSpacing(6)

        version_label = QLabel("v1.0.0")
        version_label.setObjectName("hintLabel")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(version_label)

        return sidebar

    # ──────────────────────────────────────────────────────────
    #  看板娘头像（无边框、无背景、内置默认图）
    # ──────────────────────────────────────────────────────────

    def _build_avatar_area(self, layout):
        self.avatar_label = QLabel()
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.avatar_label.mousePressEvent = self._on_avatar_click
        self._refresh_avatar()

        avatar_container = QWidget()
        avatar_container.setObjectName("avatarContainer")
        avatar_layout = QHBoxLayout(avatar_container)
        avatar_layout.setContentsMargins(0, 0, 0, 0)
        avatar_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar_layout.addWidget(self.avatar_label)

        layout.addWidget(avatar_container)

    def _refresh_avatar(self):
        avatar_path = theme_manager.avatar_path
        size = self._avatar_size()

        if theme_manager.avatar_visible and avatar_path and os.path.exists(avatar_path):
            pixmap = QPixmap(avatar_path).scaled(
                size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            self.avatar_label.setPixmap(pixmap)
            self.avatar_label.setFixedSize(pixmap.width(), pixmap.height())
            self.avatar_label.setStyleSheet("background: transparent; border: none;")
            self.avatar_label.setText("")
        else:
            c = theme_manager.colors
            self.avatar_label.setPixmap(QPixmap())
            self.avatar_label.setFixedSize(size, size)
            self.avatar_label.setText("\U0001F3AD")
            font_size = int(size * 0.45)
            self.avatar_label.setStyleSheet(f"""
                QLabel {{
                    font-size: {font_size}px;
                    background: transparent;
                    border: none;
                    color: {c["accent"]};
                }}
            """)

    def _avatar_size(self):
        w = self._sidebar_width
        size = int(w * 0.95) - 4
        size = max(80, min(280, size))
        return size

    def _on_avatar_click(self, event):
        self._toggle_theme()

    # ──────────────────────────────────────────────────────────
    #  页面：首页
    # ──────────────────────────────────────────────────────────

    def _build_home_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(12)

        layout.addStretch()

        icon_label = QLabel("\U0001F3AC")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("font-size: 64px; background: transparent;")
        layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addSpacing(8)

        title = QLabel("\u6B22\u8FCE\u4F7F\u7528 AnimeRenamer")
        title.setObjectName("welcomeTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)

        sub = QLabel("\u667A\u80FD\u756A\u5267\u89C6\u9891\u6587\u4EF6\u91CD\u547D\u540D\u5DE5\u5177")
        sub.setObjectName("welcomeSubtitle")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(sub, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addSpacing(16)

        start_btn = QPushButton("\U0001F4C2  \u9009\u62E9\u6587\u4EF6\u5939")
        start_btn.setObjectName("capsuleBtn")
        start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        start_btn.setFixedWidth(220)
        start_btn.clicked.connect(self._select_folder)
        layout.addWidget(start_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addStretch()
        return page

    # ──────────────────────────────────────────────────────────
    #  页面：文件列表
    # ──────────────────────────────────────────────────────────

    def _build_files_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(0)

        # 顶部行：标题 + 搜索按钮
        header_row = QHBoxLayout()
        header_row.setContentsMargins(18, 4, 18, 8)

        table_title = QLabel("\u6587\u4EF6\u9884\u89C8")
        table_title.setObjectName("sectionTitle")
        header_row.addWidget(table_title)
        header_row.addStretch()

        # 🔍 搜索每集标题 按钮 — 右上角
        self.search_episodes_btn = QPushButton("🔍 搜索每集标题")
        self.search_episodes_btn.setObjectName("smallBtn")
        self.search_episodes_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.search_episodes_btn.clicked.connect(self._start_recognition)
        self.search_episodes_btn.setEnabled(False)
        self.search_episodes_btn.setVisible(False)
        header_row.addWidget(self.search_episodes_btn)

        # 手动搜索关键词输入框
        self.search_keyword_input = QLineEdit()
        self.search_keyword_input.setPlaceholderText("手动输入搜索关键词...")
        self.search_keyword_input.setObjectName("searchKeywordInput")
        self.search_keyword_input.setFixedWidth(180)
        self.search_keyword_input.setVisible(False)
        self.search_keyword_input.returnPressed.connect(self._start_recognition)
        header_row.addWidget(self.search_keyword_input)

        # 搜索结果选择下拉框
        self.search_result_combo = QComboBox()
        self.search_result_combo.setObjectName("searchResultCombo")
        self.search_result_combo.setFixedWidth(220)
        self.search_result_combo.setVisible(False)
        self.search_result_combo.setToolTip("选择搜索结果，点击重新识别")
        self.search_result_combo.currentIndexChanged.connect(self._on_search_result_selected)
        header_row.addWidget(self.search_result_combo)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setFixedWidth(160)
        header_row.addWidget(self.progress_bar)
        header_row.addSpacing(8)

        self.progress_label = QLabel("")
        self.progress_label.setObjectName("hintLabel")
        self.progress_label.setVisible(False)
        header_row.addWidget(self.progress_label)

        layout.addLayout(header_row)

        # 表格
        table_container = QWidget()
        table_container.setObjectName("tableContainer")
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(0)

        self.file_list = FileListWidget()
        table_layout.addWidget(self.file_list, stretch=1)

        layout.addWidget(table_container, stretch=1)

        # 底部操作栏
        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(18, 8, 18, 4)

        # 📂 选择文件夹 + 打开文件夹 — 左下角
        self.select_folder_btn = QPushButton("📂 选择文件夹")
        self.select_folder_btn.setObjectName("smallBtn")
        self.select_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.select_folder_btn.clicked.connect(self._select_folder)
        bottom_row.addWidget(self.select_folder_btn)

        bottom_row.addSpacing(6)

        self.open_folder_btn = QPushButton("📁 打开文件夹")
        self.open_folder_btn.setObjectName("smallBtn")
        self.open_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_folder_btn.clicked.connect(self._open_current_folder)
        self.open_folder_btn.setEnabled(False)
        bottom_row.addWidget(self.open_folder_btn)

        bottom_row.addStretch()

        self.file_count_label = QLabel("")
        self.file_count_label.setObjectName("hintLabel")
        bottom_row.addWidget(self.file_count_label)

        bottom_row.addStretch()

        # 🔍 预览 + 🎬 开始重命名 — 右下角
        self.preview_btn = QPushButton("📋 预览")
        self.preview_btn.setObjectName("smallBtn")
        self.preview_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.preview_btn.clicked.connect(self._show_rename_preview)
        self.preview_btn.setEnabled(False)
        bottom_row.addWidget(self.preview_btn)

        bottom_row.addSpacing(8)

        self.rename_btn = QPushButton("🎬 开始重命名")
        self.rename_btn.setObjectName("smallBtn")
        self.rename_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.rename_btn.clicked.connect(self._execute_rename)
        self.rename_btn.setEnabled(False)
        bottom_row.addWidget(self.rename_btn)

        layout.addLayout(bottom_row)

        # 路径栏
        self.path_bar = QWidget()
        self.path_bar.setObjectName("statusBar")
        self.path_bar.setFixedHeight(36)
        path_layout = QHBoxLayout(self.path_bar)
        path_layout.setContentsMargins(16, 4, 16, 4)
        path_layout.setSpacing(8)

        self.path_label = QLabel("\u5F53\u524D\u8DEF\u5F84: \u672A\u9009\u62E9")
        self.path_label.setObjectName("pathLabel")
        path_layout.addWidget(self.path_label)
        path_layout.addStretch()

        layout.addWidget(self.path_bar)

        return page

    def _build_settings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 0)
        layout.setSpacing(12)

        self.settings_panel = SettingsPanel()
        layout.addWidget(self.settings_panel, stretch=1)
        return page

    def _build_about_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 0, 40, 0)
        layout.setSpacing(0)

        layout.addStretch()

        title = QLabel("AnimeRenamer")
        title.setObjectName("aboutTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        layout.addSpacing(8)

        version = QLabel("v1.0.0")
        version.setObjectName("aboutVersion")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)

        layout.addSpacing(24)

        def _add_line(text, obj_name="aboutLine"):
            line = QLabel(text)
            line.setObjectName(obj_name)
            line.setAlignment(Qt.AlignmentFlag.AlignCenter)
            line.setWordWrap(True)
            line.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            layout.addWidget(line)
            layout.addSpacing(14)

        _add_line("智能番剧视频文件重命名工具")
        _add_line("支持多数据源识别")
        _add_line("支持每集标题获取、自定义命名模板")
        _add_line("作者：唯一の神")

        layout.addStretch()
        return page

    # ══════════════════════════════════════════════════════════
    #  信号 / 主题
    # ══════════════════════════════════════════════════════════

    def _connect_signals(self):
        theme_manager.theme_changed.connect(self._on_theme_changed)
        self.settings_panel.settings_changed.connect(self._on_settings_changed)
        # 防抖定时器：设置变更后 500ms 才重新生成名称
        self._settings_debounce = QTimer()
        self._settings_debounce.setSingleShot(True)
        self._settings_debounce.setInterval(500)
        self._settings_debounce.timeout.connect(self._on_settings_debounced)

    def _apply_theme(self):
        self.setStyleSheet(get_stylesheet())
        self._refresh_avatar()
        self._update_theme_btn_label()
        self._update_button_states()
        self._apply_nav_accent()

    def _on_theme_changed(self, theme_name):
        self._apply_theme()
        if hasattr(self, 'settings_panel') and self.settings_panel:
            self.settings_panel.refresh_theme()
        if hasattr(self, 'file_list') and self.file_list:
            self.file_list.refresh_theme()

    def _on_settings_changed(self):
        """设置变更时启动防抖定时器"""
        self._settings_debounce.start()

    def _on_settings_debounced(self):
        """防抖后重新生成所有名称"""
        if not self.rename_items:
            return
        self._log("设置已变更，重新生成命名方案...")
        self._generate_offline_names()
        self.file_list.populate(self.rename_items)
        self._update_button_states()

    def _toggle_theme(self):
        theme_manager.toggle()

    def _update_theme_btn_label(self):
        if theme_manager.current_theme == "dark":
            self.theme_btn.setText("\U0001F319  \u6697\u8272\u6A21\u5F0F")
        else:
            self.theme_btn.setText("\u2600  \u6D45\u8272\u6A21\u5F0F")

    def _apply_nav_accent(self):
        c = theme_manager.colors
        for i, btn in enumerate(self.nav_buttons):
            if i == self._active_nav:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {c["accent"]};
                        color: #ffffff;
                        border: none;
                        border-radius: 10px;
                        padding: 11px 18px;
                        text-align: center;
                        font-size: 13px;
                        font-weight: bold;
                        min-height: 38px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent;
                        color: {c["text_secondary"]};
                        border: none;
                        border-radius: 10px;
                        padding: 11px 18px;
                        text-align: center;
                        font-size: 13px;
                        font-weight: normal;
                        min-height: 38px;
                    }}
                    QPushButton:hover {{
                        background-color: {c["sidebar_hover_bg"]};
                        color: {c["text_primary"]};
                    }}
                """)

    def _update_button_states(self):
        if not hasattr(self, 'rename_btn'):
            return
        ready_count = sum(1 for i in self.rename_items if i.status == "ready")
        has_ready = ready_count > 0
        self.rename_btn.setEnabled(has_ready)
        if has_ready:
            self.rename_btn.setText(f"🎬 开始重命名 ({ready_count})")
        else:
            self.rename_btn.setText("🎬 开始重命名")

        # 预览按钮状态
        has_any = len(self.rename_items) > 0
        self.preview_btn.setEnabled(has_any)

        # 搜索按钮状态
        has_parsed = len(self.parsed_infos) > 0
        self.search_episodes_btn.setVisible(has_parsed)
        self.search_episodes_btn.setEnabled(has_parsed)
        self.search_keyword_input.setVisible(has_parsed)

        # 打开文件夹按钮
        self.open_folder_btn.setEnabled(self.current_folder is not None)

    # ══════════════════════════════════════════════════════════
    #  导航
    # ══════════════════════════════════════════════════════════

    def _switch_nav(self, index):
        if index == self._active_nav:
            return

        self._active_nav = index
        self.page_stack.setCurrentIndex(index)

        for i, btn in enumerate(self.nav_buttons):
            btn.setObjectName("navBtnActive" if i == index else "navBtn")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        self._apply_nav_accent()

    def _on_splitter_moved(self, pos, index):
        self._sidebar_width = self.sidebar.width()
        self._refresh_avatar()

    # ══════════════════════════════════════════════════════════
    #  全域拖拽
    # ══════════════════════════════════════════════════════════

    def _on_main_drag_enter(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            self._is_drag_over = True
            self._set_drop_glow(True)
            event.acceptProposedAction()

    def _on_main_drag_leave(self, event):
        self._is_drag_over = False
        self._set_drop_glow(False)

    def _on_main_drop(self, event: QDropEvent):
        self._is_drag_over = False
        self._set_drop_glow(False)
        urls = event.mimeData().urls()
        if urls:
            folder_path = urls[0].toLocalFile()
            if os.path.isdir(folder_path):
                self._process_folder(folder_path)
            elif os.path.isfile(folder_path):
                self._process_folder(os.path.dirname(folder_path))

    def _set_drop_glow(self, active):
        c = theme_manager.colors
        if active:
            self.right_widget.setStyleSheet(f"""
                #mainDropArea {{
                    background: transparent;
                    border: 2px solid {c["accent"]};
                }}
            """)
        else:
            self.right_widget.setStyleSheet("""
                #mainDropArea {
                    background: transparent;
                    border: 2px solid transparent;
                }
            """)

    # ══════════════════════════════════════════════════════════
    #  文件夹处理 — 第一步：只加载文件列表
    # ══════════════════════════════════════════════════════════

    def _select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "\u9009\u62E9\u756A\u5267\u6587\u4EF6\u5939")
        if folder:
            self._process_folder(folder)

    def _open_current_folder(self):
        """在文件资源管理器中打开当前文件夹"""
        if self.current_folder and os.path.exists(self.current_folder):
            subprocess.Popen(['explorer', self.current_folder])

    def _process_folder(self, folder_path):
        """扫描文件夹，加载文件列表（不触发识别）"""
        self.current_folder = folder_path
        self.path_label.setText(f"\u5F53\u524D\u8DEF\u5F84: {folder_path}")
        self.path_bar.setVisible(True)
        self.qt_status_bar.showMessage(f"\u6B63\u5728\u626B\u63CF: {folder_path}")

        result = scan_folder(folder_path)
        self.video_files = result.videos
        self.subtitle_files = result.subtitles

        if not self.video_files:
            QMessageBox.information(self, "\u63D0\u793A",
                "\u672A\u627E\u5230\u89C6\u9891\u6587\u4EF6\u3002\n\n"
                "\u8BF7\u786E\u8BA4\uFF1A\n"
                "1. \u6587\u4EF6\u5939\u4E2D\u662F\u5426\u6709\u89C6\u9891\u6587\u4EF6\n"
                "2. \u8BBE\u7F6E\u9875\u4E2D\u7684\u81EA\u5B9A\u4E49\u683C\u5F0F\u662F\u5426\u5305\u542B\u60A8\u7684\u6587\u4EF6\u7C7B\u578B")
            self.qt_status_bar.showMessage("\u672A\u627E\u5230\u89C6\u9891\u6587\u4EF6")
            return

        # 解析所有文件名
        self.parsed_infos = []
        for vf in self.video_files:
            info = parse_filename(vf.filename)
            self.parsed_infos.append(info)

        # 创建 RenameItem 列表
        self.rename_items = []
        for i, vf in enumerate(self.video_files):
            item = RenameItem(
                file_path=str(vf.path),
                old_name=vf.filename,
                parsed_info=self.parsed_infos[i],
                status="pending"
            )
            self.rename_items.append(item)

        # SubRenamer 风格字幕匹配
        if self.subtitle_files:
            try:
                sub_matches = match_subtitles_to_videos(self.video_files, self.subtitle_files)
                for vf, sf in sub_matches:
                    v_idx = None
                    for idx, item in enumerate(self.rename_items):
                        if item.old_name == vf.filename:
                            v_idx = idx
                            break
                    if v_idx is not None:
                        sub_item = RenameItem(
                            file_path=str(sf.path),
                            old_name=sf.filename,
                            parsed_info=self.parsed_infos[v_idx],
                            status="pending",
                            is_subtitle_match=True
                        )
                        self.rename_items.append(sub_item)
                self._log(f"\u5B57\u5E55\u5339\u914D: {len(sub_matches)} \u5BF9")
            except Exception as e:
                self._log(f"\u5B57\u5E55\u5339\u914D\u5931\u8D25: {e}")

        # 离线生成新名称（不依赖联网搜索）
        self._generate_offline_names()

        # 刷新文件列表
        self.file_list.populate(self.rename_items)
        self.file_count_label.setText(f"\u5171 {len(self.rename_items)} \u4E2A\u6587\u4EF6")

        # 自动切换到文件页
        self._switch_nav(self.NAV_FILES)

        # 更新按钮状态
        self._update_button_states()

        self.qt_status_bar.showMessage(
            f"\u2705 \u5DF2\u52A0\u8F7D {len(self.video_files)} \u4E2A\u89C6\u9891"
            + (f", {len(self.subtitle_files)} \u4E2A\u5B57\u5E55" if self.subtitle_files else "")
            + " — \u70B9\u51FB\u300C\u641C\u7D22\u6BCF\u96C6\u6807\u9898\u300D\u5F00\u59CB\u8BC6\u522B"
        )

    # ══════════════════════════════════════════════════════════
    #  第二步：搜索每集标题（按钮触发）
    # ══════════════════════════════════════════════════════════

    def _start_recognition(self):
        """开始联网搜索每集标题"""
        if not self.parsed_infos:
            QMessageBox.information(self, "\u63D0\u793A", "\u8BF7\u5148\u9009\u62E9\u6587\u4EF6\u5939\u52A0\u8F7D\u6587\u4EF6\u5217\u8868\u3002")
            return

        # 防止重复点击
        if hasattr(self, '_recognition_running') and self._recognition_running:
            self._log("搜索正在进行中，请等待完成...")
            return
        self._recognition_running = True

        config = load_config()
        manual_keyword = self.search_keyword_input.text().strip() or None
        search_title = manual_keyword or self.parsed_infos[0].show_title
        self._current_search_title = search_title

        self.worker = RecognizeWorker(self.parsed_infos, config, manual_keyword=manual_keyword)
        self.worker.progress.connect(self._on_recognition_progress)
        self.worker.log.connect(self._log)
        self.worker.finished.connect(self._on_recognition_finished)
        self.worker.start()

        self.search_result_combo.setVisible(False)
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)
        self.search_episodes_btn.setEnabled(False)
        self.qt_status_bar.showMessage("\u6B63\u5728\u8054\u7F51\u8BC6\u522B\u756A\u5267\u4FE1\u606F...")

    def _on_recognition_progress(self, current, total, message):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.progress_label.setText(message)
        self.qt_status_bar.showMessage(f"\u8BC6\u522B\u4E2D: {current}/{total} — {message}")

    def _on_recognition_finished(self, results):
        self._recognition_running = False
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.search_episodes_btn.setEnabled(True)
        self.anime_infos = results

        self._apply_recognition_results(results)

        status_msg = "识别完成"
        ready_count = sum(1 for i in self.rename_items if i.status == "ready")
        fail_count = sum(1 for i in self.rename_items if i.status == "failed")
        if fail_count:
            status_msg += f" | {fail_count} 失败"
        self.qt_status_bar.showMessage(status_msg)

        # 获取搜索候选列表，填充下拉框
        if self._current_search_title and not self._skip_candidates_fetch:
            config = load_config()
            self.candidates_worker = SearchCandidatesWorker(self._current_search_title, config)
            self.candidates_worker.log.connect(self._log)
            self.candidates_worker.finished.connect(self._on_candidates_fetched)
            self.candidates_worker.start()
        self._skip_candidates_fetch = False

    def _apply_recognition_results(self, results):
        """将识别结果应用到 rename_items"""
        config = load_config()
        template = config.get("naming_template", "{title} - {season_episode} {episode_title}")
        ep_lang = config.get("episode_title_language", "cn")
        title_source = config.get("title_source", "cn")

        for item in self.rename_items:
            if item.parsed_info:
                key = f"{item.parsed_info.show_title}_{item.parsed_info.year}"
                anime_info = results.get(key)
                if anime_info:
                    if title_source == "original":
                        show_title = item.parsed_info.show_title
                    else:
                        show_title = anime_info.get_best_title("zh-CN" if title_source == "cn" else "en-US") or anime_info.title or item.parsed_info.show_title
                    episode_title = anime_info.get_episode_title(item.parsed_info.episode, ep_lang)
                    new_name = self._generate_new_name(item, show_title, episode_title, template)
                    if new_name:
                        item.new_name = new_name
                        item.anime_info = anime_info
                        item.status = "ready"
                    else:
                        item.status = "failed"
                else:
                    item.status = "failed"

        # 冲突检测
        existing_names = set()
        for item in self.rename_items:
            if item.status == "ready":
                if item.new_name in existing_names:
                    item.status = "conflict"
                else:
                    existing_names.add(item.new_name)

        self.file_list.populate(self.rename_items)
        ready_count = sum(1 for i in self.rename_items if i.status == "ready")
        fail_count = sum(1 for i in self.rename_items if i.status == "failed")
        conflict_count = sum(1 for i in self.rename_items if i.status == "conflict")
        self.file_count_label.setText(
            f"共 {len(self.rename_items)} 个 | ✔ {ready_count} 待修改"
            + (f" | ⚠ {conflict_count} 冲突" if conflict_count else "")
            + (f" | ✗ {fail_count} 失败" if fail_count else "")
        )
        self._update_button_states()

    def _on_candidates_fetched(self, candidates):
        """填充搜索结果下拉框"""
        self._search_candidates = candidates
        self._ignore_combo_change = True
        self.search_result_combo.clear()
        if candidates:
            self.search_result_combo.addItem("— 选择搜索结果（点击切换）—", None)
            for c in candidates:
                cn = c["name_cn"] or c["name"]
                eps = c["eps"]
                date = c["date"][:4] if c["date"] else ""
                label = f"{cn}"
                if eps:
                    label += f" ({eps}集)"
                if date:
                    label += f" [{date}]"
                self.search_result_combo.addItem(label, c["id"])
            self.search_result_combo.setCurrentIndex(0)  # 显示提示项
            self.search_result_combo.setVisible(True)
        else:
            self.search_result_combo.setVisible(False)
        self._ignore_combo_change = False

    def _on_search_result_selected(self, index):
        """用户在下拉框中选择了不同的搜索结果，重新识别"""
        if self._ignore_combo_change or index <= 0:
            return
        bangumi_id = self.search_result_combo.currentData()
        if not bangumi_id:
            return

        # 防止重复点击
        if hasattr(self, '_recognition_running') and self._recognition_running:
            self._log("搜索正在进行中，请等待完成...")
            return
        self._recognition_running = True

        self._log(f"用户选择 Bangumi ID: {bangumi_id}，重新识别...")
        self._skip_candidates_fetch = True  # 不重复获取候选
        config = load_config()
        self.worker = RecognizeWorker(self.parsed_infos, config, bangumi_id=bangumi_id)
        self.worker.progress.connect(self._on_recognition_progress)
        self.worker.log.connect(self._log)
        self.worker.finished.connect(self._on_recognition_finished)
        self.worker.start()

        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)
        self.search_episodes_btn.setEnabled(False)
        self.qt_status_bar.showMessage("正在重新识别番剧信息...")

    def _generate_new_name(self, item, show_title, episode_title, template):
        pi = item.parsed_info
        config = load_config()
        se_format = config.get("season_episode_format", "sXXeYY")
        se_str = get_season_episode_str(pi, fmt=se_format)

        base_name = template.replace("{title}", show_title)
        base_name = base_name.replace("{season_episode}", se_str)
        base_name = base_name.replace("{episode_title}", episode_title)
        base_name = base_name.replace("{group}", pi.release_group or "")
        base_name = base_name.replace("{resolution}", pi.resolution or "")
        base_name = base_name.replace("{source}", pi.source_type or "")
        base_name = base_name.replace("{video_codec}", pi.video_codec or "")
        base_name = base_name.replace("{audio_codec}", pi.audio_codec or "")
        base_name = base_name.replace("{year}", str(pi.year) if pi.year else "")
        base_name = base_name.replace("{video_info}", pi.video_info or "")
        base_name = base_name.replace("{audio_info}", pi.audio_info or "")
        base_name = re_mod.sub(r"\s+", " ", base_name).strip()
        base_name = re_mod.sub(r"\s*-\s*$", "", base_name)
        base_name = re_mod.sub(r'\[\s*\]', '', base_name)
        base_name = re_mod.sub(r'\(\s*\)', '', base_name)
        base_name = re_mod.sub(r"\s+", " ", base_name).strip()

        # 处理附加信息（保留选项）
        parts = []
        if config.get("keep_encoding_info", True) and pi.video_info:
            parts.append(pi.video_info)
        if config.get("keep_audio_info", True) and pi.audio_info:
            parts.append(pi.audio_info)
        if config.get("keep_release_group", True) and pi.release_group:
            parts.append(pi.release_group)
        if config.get("keep_language_tag", True) and pi.language_tag:
            parts.append(pi.language_tag)
        for tag in pi.extra_tags:
            if config.get("keep_encoding_info", True) and any(
                kw in tag.lower() for kw in ['1080p', '720p', '4k', '2160p', 'bd', 'web', 'remux', 'avc', 'hevc', 'x265', 'x264', '10bit', '8bit', 'flac', 'aac']):
                parts.append(tag)
        if parts:
            base_name = f"{base_name} {' '.join(parts)}"
        base_name = re_mod.sub(r"\s+", " ", base_name).strip()

        ext = Path(item.old_name).suffix
        new_name = f"{base_name}{ext}"

        name, ext_part = os.path.splitext(new_name)
        name = name.replace("/", " ").replace("\\", " ")
        name = re_mod.sub(r'[<>:"|?*]', "", name)
        name = re_mod.sub(r"\s+", " ", name).strip()
        return f"{name}{ext_part}"

    def _generate_offline_names(self):
        """离线生成新名称（不依赖联网搜索，基于解析的标题和集数）"""
        config = load_config()
        template = config.get("naming_template", "{title} - {season_episode} {episode_title}")
        title_source = config.get("title_source", "cn")

        for item in self.rename_items:
            if item.status == "ready" or item.status == "done":
                continue

            pi = item.parsed_info
            if not pi:
                continue

            # 使用解析出的原标题
            show_title = pi.show_title if pi.show_title else Path(item.old_name).stem

            # 离线没有每集标题
            episode_title = ""

            new_name = self._generate_new_name(item, show_title, episode_title, template)
            item.new_name = new_name
            item.new_path = Path(item.old_path).parent / new_name if item.old_path else None
            item.status = "ready"

            # 检查冲突
            if item.new_path and item.new_path.exists() and item.new_path != Path(item.old_path):
                item.status = "conflict"
                item.error_msg = "\u76EE\u6807\u6587\u4EF6\u5DF2\u5B58\u5728"

    # ══════════════════════════════════════════════════════════
    #  重命名预览（弹窗）
    # ══════════════════════════════════════════════════════════

    def _show_rename_preview(self):
        if not self.rename_items:
            QMessageBox.information(self, "\u63D0\u793A", "\u8BF7\u5148\u52A0\u8F7D\u6587\u4EF6\u5939\u3002")
            return

        ready = [i for i in self.rename_items if i.status == "ready"]
        done = [i for i in self.rename_items if i.status == "done"]
        conflict = [i for i in self.rename_items if i.status == "conflict"]
        fail = [i for i in self.rename_items if i.status == "failed"]

        c = theme_manager.colors

        dialog = QDialog(self)
        dialog.setWindowTitle("\u91CD\u547D\u540D\u9884\u89C8")
        dialog.setMinimumSize(620, 420)
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {c["bg_primary"]};
                border: 1px solid {c["border_glow"]};
                border-radius: 16px;
            }}
        """)

        dlg_layout = QVBoxLayout(dialog)
        dlg_layout.setContentsMargins(24, 20, 24, 20)
        dlg_layout.setSpacing(14)

        # 标题
        title = QLabel(f"\u91CD\u547D\u540D\u9884\u89C8 \u2014 \u5171 {len(self.rename_items)} \u4E2A\u6587\u4EF6")
        title.setObjectName("sectionTitle")
        dlg_layout.addWidget(title)

        # 统计摘要
        summary = QLabel(
            f"\u2705 \u5F85\u4FEE\u6539: {len(ready)} | "
            f"\u2713 \u5DF2\u5B8C\u6210: {len(done)} | "
            f"\u26A0 \u51B2\u7A81: {len(conflict)} | "
            f"\u2717 \u5931\u8D25: {len(fail)}"
        )
        summary.setStyleSheet(f"font-size: 13px; color: {c['text_secondary']}; background: transparent;")
        dlg_layout.addWidget(summary)

        # 分隔线
        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFixedHeight(1)
        dlg_layout.addWidget(sep)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ background: transparent; border: none; }} QScrollArea > QWidget > QWidget {{ background: transparent; }}")

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(6)

        # 待重命名
        if ready:
            sec = QLabel("\u2705 \u5F85\u91CD\u547D\u540D\u7684\u6587\u4EF6:")
            sec.setStyleSheet(f"font-weight: bold; color: {c['success']}; background: transparent;")
            scroll_layout.addWidget(sec)
            for item in ready:
                row = QLabel(f"  {item.old_name}  \u2192  {item.new_name}")
                row.setStyleSheet(f"font-size: 12px; color: {c['text_primary']}; background: transparent; padding: 3px 0;")
                row.setWordWrap(True)
                scroll_layout.addWidget(row)
            scroll_layout.addSpacing(8)

        # 冲突
        if conflict:
            sec = QLabel(f"\u26A0\uFE0F \u51B2\u7A81\u7684\u6587\u4EF6 ({len(conflict)}):")
            sec.setStyleSheet(f"font-weight: bold; color: {c['error']}; background: transparent;")
            scroll_layout.addWidget(sec)
            for item in conflict:
                row = QLabel(f"  {item.old_name}")
                row.setStyleSheet(f"font-size: 12px; color: {c['error']}; background: transparent; padding: 3px 0;")
                row.setWordWrap(True)
                scroll_layout.addWidget(row)
            scroll_layout.addSpacing(8)

        # 失败
        if fail:
            sec = QLabel(f"\u274C \u8BC6\u522B\u5931\u8D25\u7684\u6587\u4EF6 ({len(fail)}):")
            sec.setStyleSheet(f"font-weight: bold; color: {c['text_muted']}; background: transparent;")
            scroll_layout.addWidget(sec)
            for item in fail:
                row = QLabel(f"  {item.old_name}")
                row.setStyleSheet(f"font-size: 12px; color: {c['text_muted']}; background: transparent; padding: 3px 0;")
                row.setWordWrap(True)
                scroll_layout.addWidget(row)

        if not ready and not conflict and not fail:
            empty = QLabel("\u6682\u65E0\u6570\u636E\uFF0C\u8BF7\u5148\u52A0\u8F7D\u6587\u4EF6\u5939\u5E76\u641C\u7D22\u6BCF\u96C6\u6807\u9898\u3002")
            empty.setStyleSheet(f"color: {c['text_muted']}; background: transparent;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            scroll_layout.addWidget(empty)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        dlg_layout.addWidget(scroll, stretch=1)

        # 关闭按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("\u5173\u95ED")
        close_btn.setObjectName("smallBtn")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(dialog.accept)
        close_btn.setFixedWidth(100)
        btn_row.addWidget(close_btn)
        dlg_layout.addLayout(btn_row)

        dialog.exec()

    # ══════════════════════════════════════════════════════════
    #  执行重命名
    # ══════════════════════════════════════════════════════════

    def _execute_rename(self):
        ready_items = [i for i in self.rename_items if i.status == "ready"]
        if not ready_items:
            QMessageBox.information(self, "\u63D0\u793A", "\u6CA1\u6709\u53EF\u91CD\u547D\u540D\u7684\u6587\u4EF6\u3002")
            return

        reply = QMessageBox.question(
            self, "\u786E\u8BA4\u91CD\u547D\u540D",
            f"\u5C06\u91CD\u547D\u540D {len(ready_items)} \u4E2A\u6587\u4EF6\uFF0C\u786E\u5B9A\u7EE7\u7EED\u5417\uFF1F",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        for item in ready_items:
            if not item.old_path:
                item.old_path = str(Path(self.current_folder) / item.old_name)
            item.new_path = str(Path(self.current_folder) / item.new_name)

        success, failed = self.rename_engine.execute_rename(ready_items)
        self.file_list.populate(self.rename_items)
        self._update_button_states()

        if failed:
            QMessageBox.warning(
                self, "\u91CD\u547D\u540D\u5B8C\u6210",
                f"\u6210\u529F: {success} \u4E2A\n\u5931\u8D25: {failed} \u4E2A"
            )
        else:
            self.qt_status_bar.showMessage(f"\u2705 \u6210\u529F\u91CD\u547D\u540D {success} \u4E2A\u6587\u4EF6")

    def _undo_rename(self):
        done_items = [i for i in self.rename_items if i.status == "done"]
        if not done_items:
            QMessageBox.information(self, "\u63D0\u793A", "\u6CA1\u6709\u53EF\u64A4\u9500\u7684\u64CD\u4F5C\u3002")
            return

        reply = QMessageBox.question(
            self, "\u786E\u8BA4\u64A4\u9500",
            f"\u5C06\u64A4\u9500 {len(done_items)} \u4E2A\u6587\u4EF6\u7684\u91CD\u547D\u540D\uFF0C\u786E\u5B9A\u7EE7\u7EED\u5417\uFF1F",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        success, failed = self.rename_engine.undo_rename(done_items)
        self.file_list.populate(self.rename_items)
        self._update_button_states()
        self.qt_status_bar.showMessage(f"\u64A4\u9500\u5B8C\u6210: {success} \u6210\u529F, {failed} \u5931\u8D25")

    # ══════════════════════════════════════════════════════════
    #  日志
    # ══════════════════════════════════════════════════════════

    def _log(self, message):
        if hasattr(self, 'qt_status_bar'):
            self.qt_status_bar.showMessage(message)

    # ══════════════════════════════════════════════════════════
    #  响应式缩放
    # ══════════════════════════════════════════════════════════

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'avatar_label'):
            self._refresh_avatar()