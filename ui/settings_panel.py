"""设置面板组件 - 毛玻璃卡片风格 + 色盘选择器 + 头像自定义"""
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QCheckBox, QLineEdit,
    QGroupBox, QScrollArea, QHBoxLayout, QPushButton, QRadioButton,
    QButtonGroup, QFrame, QSizePolicy, QGridLayout,
    QColorDialog, QComboBox
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont, QColor, QPixmap
from utils.config import load_config, save_config
from ui.theme import theme_manager


DB_INFO = {
    "bangumi": {
        "label": "Bangumi",
        "url": "bgm.tv",
        "key": "bangumi",
    },
    "anilist": {
        "label": "AniList",
        "url": "graphql.anilist.co",
        "key": "anilist",
    },
    "themoviedb": {
        "label": "TheMovieDB",
        "url": "themoviedb.org",
        "key": "themoviedb",
    },
    "jikan": {
        "label": "Jikan",
        "url": "jikan.moe",
        "key": "jikan",
    },
    "tvmaze": {
        "label": "TVMaze",
        "url": "tvmaze.com",
        "key": "tvmaze",
    },
    "anidb": {
        "label": "AniDB",
        "url": "anidb.net",
        "key": "anidb",
    },
    "thetvdb": {
        "label": "TheTVDB",
        "url": "thetvdb.com",
        "key": "thetvdb",
    },
    "imdb": {
        "label": "IMDb",
        "url": "imdb.com",
        "key": "imdb",
    },
}

SE_FORMAT_OPTIONS = [
    ("auto", "自动识别（保持原文件格式）"),
    ("sXXeYY", "S01E01（带季数）"),
    ("[##]", "[01] 方括号"),
    ("#01", "#01 井号"),
    ("EP01", "EP01 格式"),
    (" - 01", " - 01 破折号"),
    ("01", "01 纯数字"),
    ("第01话", "第01话 中文"),
]


class DbTestWorker(QThread):
    """数据库连接测试工作线程"""
    result = Signal(str, dict)

    def __init__(self, db_keys):
        super().__init__()
        self.db_keys = db_keys

    def run(self):
        from core.recognizer import AnimeRecognizer
        r = AnimeRecognizer()
        for key in self.db_keys:
            try:
                res = r.test_connection(key)
            except Exception as e:
                res = {"ok": False, "response_time_ms": 0, "message": str(e)}
            self.result.emit(key, res)


class SettingsPanel(QWidget):
    """设置面板"""

    settings_changed = Signal()

    def __init__(self):
        super().__init__()
        self.setObjectName("settingsPanel")
        self._loading = False  # 加载中标志，防止 textChanged 误触发保存
        self._setup_ui()
        self._load_settings()

    # ================================================================
    #  UI 构建
    # ================================================================

    def _setup_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setObjectName("settingsScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        # ========== 1. 命名规则 ==========
        self._build_naming_section(layout)

        # ========== 2. 字幕选项 ==========
        self._build_subtitle_section(layout)

        # ========== 3. 标签处理 ==========
        self._build_tag_section(layout)

        # ========== 3.5 自定义格式扩展 ==========
        self._build_format_section(layout)

        # ========== 4. 番剧数据源 ==========
        self._build_database_section(layout)

        # ========== 6. 主题点缀色自定义 ==========
        self._build_color_section(layout)

        layout.addStretch()

        scroll.setWidget(content)
        outer_layout.addWidget(scroll)

        # 连接信号
        self._connect_signals()

    def _build_naming_section(self, layout):
        naming_group = QGroupBox("命名规则")
        naming_group.setStyleSheet(self._group_style())
        naming_layout = QVBoxLayout(naming_group)
        naming_layout.setSpacing(10)
        naming_layout.setContentsMargins(16, 24, 16, 16)

        naming_layout.addWidget(QLabel("命名模板:"))
        self.template_input = QLineEdit()
        self.template_input.setPlaceholderText("{title} - {season_episode} {episode_title}")
        naming_layout.addWidget(self.template_input)

        hint = QLabel("可用变量: {title}作品名, {season_episode}季集数, {episode_title}每集标题\n"
                      "{group}发布组, {resolution}分辨率, {source}片源, {video_codec}视频编码, {audio_codec}音频编码\n"
                      "{year}年份, {absolute}绝对集数(动漫), {video_info}完整视频信息, {audio_info}完整音频信息")
        hint.setObjectName("hintLabel")
        hint.setWordWrap(True)
        naming_layout.addWidget(hint)

        # ── 番剧名来源 & 每集标题语言 ──
        title_row = QHBoxLayout()
        title_row.setSpacing(20)

        # 番剧名来源
        title_src_layout = QVBoxLayout()
        title_src_layout.addWidget(QLabel("番剧名来源:"))
        self.title_cn = QRadioButton("中文标题")
        self.title_en = QRadioButton("英文/罗马字标题")
        self.title_original = QRadioButton("保留原文件名（不搜索）")
        self.title_cn.setChecked(True)
        self.title_group = QButtonGroup()
        self.title_group.addButton(self.title_cn, 0)
        self.title_group.addButton(self.title_en, 1)
        self.title_group.addButton(self.title_original, 2)
        title_src_layout.addWidget(self.title_cn)
        title_src_layout.addWidget(self.title_en)
        title_src_layout.addWidget(self.title_original)
        title_row.addLayout(title_src_layout)

        # 每集标题语言
        ep_lang_layout = QVBoxLayout()
        ep_lang_layout.addWidget(QLabel("每集标题语言:"))
        self.ep_title_cn = QRadioButton("中文标题")
        self.ep_title_jp = QRadioButton("日文标题")
        self.ep_title_cn.setChecked(True)
        self.ep_title_group = QButtonGroup()
        self.ep_title_group.addButton(self.ep_title_cn, 0)
        self.ep_title_group.addButton(self.ep_title_jp, 1)
        ep_lang_layout.addWidget(self.ep_title_cn)
        ep_lang_layout.addWidget(self.ep_title_jp)
        title_row.addLayout(ep_lang_layout)

        naming_layout.addLayout(title_row)

        # ── 季集格式 ──
        se_row = QHBoxLayout()
        se_row.setSpacing(10)
        se_row.addWidget(QLabel("季集格式:"))
        self.se_format_combo = QComboBox()
        for key, label in SE_FORMAT_OPTIONS:
            self.se_format_combo.addItem(label, key)
        se_row.addWidget(self.se_format_combo)
        se_row.addStretch()
        naming_layout.addLayout(se_row)

        layout.addWidget(naming_group)

    def _build_subtitle_section(self, layout):
        sub_group = QGroupBox("\u5B57\u5E55\u9009\u9879")
        sub_group.setStyleSheet(self._group_style())
        sub_layout = QVBoxLayout(sub_group)
        sub_layout.setSpacing(10)
        sub_layout.setContentsMargins(16, 24, 16, 16)

        self.sync_subtitle_cb = QCheckBox("\u540C\u6B65\u4FEE\u6539\u5B57\u5E55\u540D\u79F0")
        self.sync_subtitle_cb.setChecked(True)
        sub_layout.addWidget(self.sync_subtitle_cb)

        self.remove_sc_cb = QCheckBox("\u53BB\u9664\u5B57\u5E55\u8BED\u8A00\u6807\u7B7E .sc/.tc/.chs/.cht/.jp/.en \u7B49")
        self.remove_sc_cb.setChecked(True)
        sub_layout.addWidget(self.remove_sc_cb)

        layout.addWidget(sub_group)

    def _build_tag_section(self, layout):
        tag_group = QGroupBox("标签处理")
        tag_group.setStyleSheet(self._group_style())
        tag_layout = QVBoxLayout(tag_group)
        tag_layout.setSpacing(10)
        tag_layout.setContentsMargins(16, 24, 16, 16)

        self.keep_group_cb = QCheckBox("保留发布组标签 [Group]")
        self.keep_group_cb.setChecked(True)
        tag_layout.addWidget(self.keep_group_cb)

        self.keep_encoding_cb = QCheckBox("保留编码信息 (1080p, AVC, FLAC等)")
        self.keep_encoding_cb.setChecked(True)
        tag_layout.addWidget(self.keep_encoding_cb)

        self.keep_audio_cb = QCheckBox("保留音频信息 [Dual Audio]")
        self.keep_audio_cb.setChecked(True)
        tag_layout.addWidget(self.keep_audio_cb)

        self.keep_language_cb = QCheckBox("保留语言标识")
        self.keep_language_cb.setChecked(True)
        tag_layout.addWidget(self.keep_language_cb)

        layout.addWidget(tag_group)

    def _build_format_section(self, layout):
        """自定义视频/字幕格式扩展"""
        fmt_group = QGroupBox("\U0001F4E6 \u81EA\u5B9A\u4E49\u6587\u4EF6\u683C\u5F0F\u6269\u5C55")
        fmt_group.setStyleSheet(self._group_style())
        fmt_layout = QVBoxLayout(fmt_group)
        fmt_layout.setSpacing(10)
        fmt_layout.setContentsMargins(16, 24, 16, 16)

        hint = QLabel("\u5728\u6B64\u6DFB\u52A0\u60A8\u60F3\u8BC6\u522B\u7684\u989D\u5916\u6587\u4EF6\u683C\u5F0F\uFF0C\u7528\u7A7A\u683C\u3001\u9017\u53F7\u6216\u5206\u53F7\u5206\u9694\u3002\u5185\u7F6E\u683C\u5F0F\u5DF2\u5305\u542B\u5E38\u89C1\u89C6\u9891\u548C\u5B57\u5E55\u6269\u5C55\u540D\u3002")
        hint.setWordWrap(True)
        hint.setObjectName("hintLabel")
        fmt_layout.addWidget(hint)

        fmt_layout.addWidget(QLabel("\u89C6\u9891\u6269\u5C55\u540D (\u5DF2\u5185\u7F6E: .mkv .mp4 .avi .mov .wmv .flv .webm .m4v .ts):"))
        self.custom_video_input = QLineEdit()
        self.custom_video_input.setPlaceholderText("\u4F8B\u5982: .rmvb .ogm .divx .m2ts .vob")
        fmt_layout.addWidget(self.custom_video_input)

        fmt_layout.addWidget(QLabel("\u5B57\u5E55\u6269\u5C55\u540D (\u5DF2\u5185\u7F6E: .ass .ssa .srt .sub .idx .sup .vtt):"))
        self.custom_sub_input = QLineEdit()
        self.custom_sub_input.setPlaceholderText("\u4F8B\u5982: .txt .pgs .usf .xssf")
        fmt_layout.addWidget(self.custom_sub_input)

        layout.addWidget(fmt_group)

    def _build_database_section(self, layout):
        """构建番剧数据源管理区域"""
        db_group = QGroupBox("番剧数据源")
        db_group.setStyleSheet(self._group_style())
        db_layout = QVBoxLayout(db_group)
        db_layout.setSpacing(10)
        db_layout.setContentsMargins(16, 24, 16, 16)

        # 当前主数据源 — 下拉框形式（节省空间）
        primary_row = QHBoxLayout()
        primary_row.setSpacing(10)
        primary_row.addWidget(QLabel("当前主数据源:"))
        self.db_primary_combo = QComboBox()
        self.db_primary_combo.setObjectName("sourceCombo")
        self.db_primary_combo.setMinimumWidth(140)
        self.db_primary_combo.setMinimumHeight(32)
        db_choices = [
            ("bangumi", "Bangumi"),
            ("anilist", "AniList"),
            ("themoviedb", "TheMovieDB"),
            ("jikan", "Jikan"),
            ("tvmaze", "TVMaze"),
            ("anidb", "AniDB"),
            ("thetvdb", "TheTVDB"),
            ("imdb", "IMDb"),
        ]
        for key, label in db_choices:
            self.db_primary_combo.addItem(label, key)
        primary_row.addWidget(self.db_primary_combo)
        primary_row.addStretch()
        db_layout.addLayout(primary_row)

        self.db_auto_fallback_cb = QCheckBox("启用自动切换（失败时自动尝试下一数据源）")
        self.db_auto_fallback_cb.setChecked(True)
        db_layout.addWidget(self.db_auto_fallback_cb)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("separator")
        db_layout.addWidget(sep)

        query_header = QHBoxLayout()
        query_header.setSpacing(10)
        query_label = QLabel("查询顺序:")
        query_header.addWidget(query_label)
        query_header.addStretch()

        self.test_all_btn = QPushButton("\U0001F50D  \u4E00\u952E\u6D4B\u8BD5\u5168\u90E8")
        self.test_all_btn.setObjectName("smallBtn")
        self.test_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.test_all_btn.clicked.connect(self._test_all_db_connections)
        query_header.addWidget(self.test_all_btn)
        db_layout.addLayout(query_header)

        self.db_enabled = {}
        self.db_status_labels = {}
        self.db_test_buttons = {}
        self.db_api_key_inputs = {}
        self.db_api_key_buttons = {}

        for db_key in ("bangumi", "anilist", "themoviedb", "jikan", "tvmaze", "anidb", "thetvdb", "imdb"):
            info = DB_INFO[db_key]
            row = self._build_db_row(info)
            db_layout.addLayout(row)

        layout.addWidget(db_group)

    def _build_db_row(self, info):
        """构建单个数据源的行"""
        c = theme_manager.colors
        row = QVBoxLayout()
        row.setSpacing(4)

        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        cb = QCheckBox(info["label"])
        cb.setChecked(True)
        top_row.addWidget(cb)
        self.db_enabled[info["key"]] = cb

        url_label = QLabel(f"({info['url']})")
        url_label.setObjectName("hintLabel")
        top_row.addWidget(url_label)

        status_label = QLabel("就绪")
        status_label.setObjectName("hintLabel")
        status_label.setStyleSheet(f"color: {c['success']}; font-size: 11px;")
        top_row.addWidget(status_label)
        self.db_status_labels[info["key"]] = status_label

        top_row.addStretch()

        test_btn = QPushButton("测试连接")
        test_btn.setObjectName("smallBtn")
        test_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        test_btn.clicked.connect(lambda checked, k=info["key"]: self._test_db_connection(k))
        top_row.addWidget(test_btn)
        self.db_test_buttons[info["key"]] = test_btn

        row.addLayout(top_row)

        if info["key"] == "themoviedb":
            api_row = QHBoxLayout()
            api_row.setSpacing(8)
            api_row.setContentsMargins(30, 4, 0, 4)

            api_label = QLabel("API Key:")
            api_label.setObjectName("hintLabel")
            api_row.addWidget(api_label)

            api_input = QLineEdit()
            api_input.setPlaceholderText("输入 TMDB API Key")
            api_input.setEchoMode(QLineEdit.EchoMode.Password)
            api_row.addWidget(api_input)
            self.db_api_key_inputs["themoviedb"] = api_input

            save_btn = QPushButton("保存")
            save_btn.setObjectName("smallBtn")
            save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            save_btn.clicked.connect(lambda: self._save_tmdb_key())
            api_row.addWidget(save_btn)
            self.db_api_key_buttons["themoviedb"] = save_btn

            row.addLayout(api_row)

        return row

    def _build_color_section(self, layout):
        """🎨 主题点缀色自定义"""
        color_group = QGroupBox("🎨 主题点缀色自定义")
        color_group.setStyleSheet(self._group_style())
        color_layout = QVBoxLayout(color_group)
        color_layout.setSpacing(12)
        color_layout.setContentsMargins(16, 24, 16, 16)

        dark_label = QLabel("暗色模式点缀色:")
        dark_label.setStyleSheet("font-weight: bold; background: transparent;")
        color_layout.addWidget(dark_label)

        dark_row = QHBoxLayout()
        dark_row.setSpacing(10)

        self.color_preview_dark = QPushButton()
        self.color_preview_dark.setObjectName("colorPreview")
        self.color_preview_dark.setFixedSize(36, 36)
        self.color_preview_dark.setCursor(Qt.CursorShape.PointingHandCursor)
        self.color_preview_dark.clicked.connect(lambda: self._pick_color("dark"))
        dark_row.addWidget(self.color_preview_dark)

        self.color_hex_dark = QLineEdit()
        self.color_hex_dark.setPlaceholderText("#ff4d5a")
        self.color_hex_dark.setFixedWidth(100)
        self.color_hex_dark.textChanged.connect(lambda t: self._on_hex_changed("dark", t))
        dark_row.addWidget(self.color_hex_dark)

        reset_dark_btn = QPushButton("重置默认")
        reset_dark_btn.setObjectName("smallBtn")
        reset_dark_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_dark_btn.clicked.connect(lambda: self._reset_accent("dark"))
        dark_row.addWidget(reset_dark_btn)

        dark_row.addStretch()
        color_layout.addLayout(dark_row)

        light_label = QLabel("浅色模式点缀色:")
        light_label.setStyleSheet("font-weight: bold; background: transparent;")
        color_layout.addWidget(light_label)

        light_row = QHBoxLayout()
        light_row.setSpacing(10)

        self.color_preview_light = QPushButton()
        self.color_preview_light.setObjectName("colorPreview")
        self.color_preview_light.setFixedSize(36, 36)
        self.color_preview_light.setCursor(Qt.CursorShape.PointingHandCursor)
        self.color_preview_light.clicked.connect(lambda: self._pick_color("light"))
        light_row.addWidget(self.color_preview_light)

        self.color_hex_light = QLineEdit()
        self.color_hex_light.setPlaceholderText("#6cb2eb")
        self.color_hex_light.setFixedWidth(100)
        self.color_hex_light.textChanged.connect(lambda t: self._on_hex_changed("light", t))
        light_row.addWidget(self.color_hex_light)

        reset_light_btn = QPushButton("重置默认")
        reset_light_btn.setObjectName("smallBtn")
        reset_light_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_light_btn.clicked.connect(lambda: self._reset_accent("light"))
        light_row.addWidget(reset_light_btn)

        light_row.addStretch()
        color_layout.addLayout(light_row)

        layout.addWidget(color_group)

    # ================================================================
    #  信号连接
    # ================================================================

    def _connect_signals(self):
        self.template_input.textChanged.connect(self._on_setting_changed)

        self.sync_subtitle_cb.toggled.connect(self._on_setting_changed)
        self.remove_sc_cb.toggled.connect(self._on_setting_changed)

        self.keep_group_cb.toggled.connect(self._on_setting_changed)
        self.keep_encoding_cb.toggled.connect(self._on_setting_changed)
        self.keep_audio_cb.toggled.connect(self._on_setting_changed)
        self.keep_language_cb.toggled.connect(self._on_setting_changed)

        self.title_cn.toggled.connect(self._on_setting_changed)
        self.title_en.toggled.connect(self._on_setting_changed)
        self.title_original.toggled.connect(self._on_setting_changed)
        self.ep_title_cn.toggled.connect(self._on_setting_changed)
        self.ep_title_jp.toggled.connect(self._on_setting_changed)

        self.se_format_combo.currentIndexChanged.connect(self._on_setting_changed)

        self.db_primary_combo.currentIndexChanged.connect(self._on_setting_changed)
        self.db_auto_fallback_cb.toggled.connect(self._on_setting_changed)
        for cb in self.db_enabled.values():
            cb.toggled.connect(self._on_setting_changed)

        if "themoviedb" in self.db_api_key_inputs:
            # TMDB Key 通过旁边的保存按钮手动保存，不自动保存
            pass

        self.custom_video_input.textChanged.connect(self._on_setting_changed)
        self.custom_sub_input.textChanged.connect(self._on_setting_changed)

    # ================================================================
    #  样式
    # ================================================================

    def _group_style(self):
        c = theme_manager.colors
        return f"""
            QGroupBox {{
                background-color: {c["bg_card"]};
                border: 1px solid {c["border"]};
                border-radius: 14px;
                margin-top: 14px;
                padding-top: 28px;
                font-weight: bold;
                font-size: 13px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 10px;
                color: {c["text_primary"]};
            }}
        """

    # ================================================================
    #  加载 / 保存
    # ================================================================

    def _on_setting_changed(self, *args):
        if self._loading:
            return
        self.save_settings()
        self.settings_changed.emit()

    def _save_tmdb_key(self):
        """手动保存 TMDB API Key"""
        config = load_config()
        if "themoviedb" in self.db_api_key_inputs:
            config["tmdb_api_key"] = self.db_api_key_inputs["themoviedb"].text().strip()
        save_config(config)
        self.settings_changed.emit()

    def _load_settings(self):
        self._loading = True
        config = load_config()

        template = config.get("naming_template", "{title} - {season_episode} {episode_title}")
        self.template_input.setText(template)

        self.sync_subtitle_cb.setChecked(config.get("sync_subtitle", True))
        self.remove_sc_cb.setChecked(config.get("remove_sc_tag", True))

        self.keep_group_cb.setChecked(config.get("keep_release_group", True))
        self.keep_encoding_cb.setChecked(config.get("keep_encoding_info", True))
        self.keep_audio_cb.setChecked(config.get("keep_audio_info", True))
        self.keep_language_cb.setChecked(config.get("keep_language_tag", True))

        title_source = config.get("title_source", "cn")
        if title_source == "original":
            self.title_original.setChecked(True)
        elif title_source == "en":
            self.title_en.setChecked(True)
        else:
            self.title_cn.setChecked(True)

        ep_lang = config.get("episode_title_language", "cn")
        self.ep_title_cn.setChecked(ep_lang == "cn")
        self.ep_title_jp.setChecked(ep_lang == "jp")

        se_format = config.get("season_episode_format", "auto")
        idx = self.se_format_combo.findData(se_format)
        if idx >= 0:
            self.se_format_combo.setCurrentIndex(idx)

        self.custom_video_input.setText(config.get("custom_video_extensions", ""))
        self.custom_sub_input.setText(config.get("custom_subtitle_extensions", ""))

        db_primary = config.get("db_primary", "bangumi")
        idx = self.db_primary_combo.findData(db_primary)
        if idx >= 0:
            self.db_primary_combo.setCurrentIndex(idx)

        self.db_auto_fallback_cb.setChecked(config.get("db_auto_fallback", True))

        db_enabled = config.get("db_enabled", {})
        for key, cb in self.db_enabled.items():
            cb.setChecked(db_enabled.get(key, True))

        api_key = config.get("tmdb_api_key", "")
        if "themoviedb" in self.db_api_key_inputs:
            self.db_api_key_inputs["themoviedb"].setText(api_key)

        custom_dark = config.get("custom_accent_dark", "")
        custom_light = config.get("custom_accent_light", "")
        self.color_hex_dark.setText(custom_dark)
        self.color_hex_light.setText(custom_light)
        self._update_color_preview("dark", custom_dark or "#ff4d5a")
        self._update_color_preview("light", custom_light or "#6cb2eb")
        self._loading = False

    def save_settings(self):
        config = load_config()

        config["naming_template"] = self.template_input.text() or "{title} - {season_episode} {episode_title}"
        config["sync_subtitle"] = self.sync_subtitle_cb.isChecked()
        config["remove_sc_tag"] = self.remove_sc_cb.isChecked()
        config["keep_release_group"] = self.keep_group_cb.isChecked()
        config["keep_encoding_info"] = self.keep_encoding_cb.isChecked()
        config["keep_audio_info"] = self.keep_audio_cb.isChecked()
        config["keep_language_tag"] = self.keep_language_cb.isChecked()
        config["language"] = "zh-CN" if self.title_cn.isChecked() else "en-US"
        config["title_source"] = "cn" if self.title_cn.isChecked() else ("en" if self.title_en.isChecked() else "original")
        config["episode_title_language"] = "cn" if self.ep_title_cn.isChecked() else "jp"
        config["season_episode_format"] = self.se_format_combo.currentData()

        config["custom_video_extensions"] = self.custom_video_input.text().strip()
        config["custom_subtitle_extensions"] = self.custom_sub_input.text().strip()

        config["db_primary"] = self.db_primary_combo.currentData()

        config["db_auto_fallback"] = self.db_auto_fallback_cb.isChecked()

        db_enabled = {}
        for key, cb in self.db_enabled.items():
            db_enabled[key] = cb.isChecked()
        config["db_enabled"] = db_enabled

        if "themoviedb" in self.db_api_key_inputs:
            config["tmdb_api_key"] = self.db_api_key_inputs["themoviedb"].text().strip()
        else:
            config["tmdb_api_key"] = ""

        config["custom_accent_dark"] = self.color_hex_dark.text().strip()
        config["custom_accent_light"] = self.color_hex_light.text().strip()

        save_config(config)

    def get_settings(self):
        db_primary = self.db_primary_combo.currentData() or "bangumi"

        db_enabled = {}
        for key, cb in self.db_enabled.items():
            db_enabled[key] = cb.isChecked()

        return {
            "naming_template": self.template_input.text() or "{title} - {season_episode} {episode_title}",
            "sync_subtitle": self.sync_subtitle_cb.isChecked(),
            "remove_sc_tag": self.remove_sc_cb.isChecked(),
            "keep_release_group": self.keep_group_cb.isChecked(),
            "keep_encoding_info": self.keep_encoding_cb.isChecked(),
            "keep_audio_info": self.keep_audio_cb.isChecked(),
            "keep_language_tag": self.keep_language_cb.isChecked(),
            "language": "zh-CN" if self.lang_zh_radio.isChecked() else "en-US",
            "db_primary": db_primary,
            "db_auto_fallback": self.db_auto_fallback_cb.isChecked(),
            "db_enabled": db_enabled,
            "tmdb_api_key": self.db_api_key_inputs["themoviedb"].text().strip() if "themoviedb" in self.db_api_key_inputs else "",
        }

    def _test_db_connection(self, db_key):
        info = DB_INFO.get(db_key, {})
        status_label = self.db_status_labels.get(db_key)

        try:
            from core.recognizer import AnimeRecognizer
            c = theme_manager.colors
            if status_label:
                status_label.setText("测试中...")
                status_label.setStyleSheet(f"color: {c['warning']}; font-size: 11px;")

            r = AnimeRecognizer()
            result = r.test_connection(db_key)

            self._update_db_status(db_key, result)

        except Exception as e:
            if status_label:
                c = theme_manager.colors
                status_label.setText(f"错误: {e}")
                status_label.setStyleSheet(f"color: {c['error']}; font-size: 11px;")

    def _test_all_db_connections(self):
        enabled_keys = [k for k, cb in self.db_enabled.items() if cb.isChecked()]
        if not enabled_keys:
            return

        c = theme_manager.colors
        for key in enabled_keys:
            label = self.db_status_labels.get(key)
            if label:
                label.setText("测试中...")
                label.setStyleSheet(f"color: {c['warning']}; font-size: 11px;")

        self.test_all_btn.setEnabled(False)
        self.test_all_btn.setText("测试中...")

        self.test_worker = DbTestWorker(enabled_keys)
        self.test_worker.result.connect(self._on_db_test_result)
        self.test_worker.finished.connect(self._on_all_tests_finished)
        self.test_worker.start()

    def _on_db_test_result(self, db_key, result):
        self._update_db_status(db_key, result)

    def _on_all_tests_finished(self):
        self.test_all_btn.setEnabled(True)
        self.test_all_btn.setText("\U0001F50D  \u4E00\u952E\u6D4B\u8BD5\u5168\u90E8")

    def _update_db_status(self, db_key, result):
        c = theme_manager.colors
        status_label = self.db_status_labels.get(db_key)
        if not status_label:
            return

        if result.get("ok"):
            latency = result.get("response_time_ms", 0)
            status_label.setText(f"正常 ({latency}ms)")
            status_label.setStyleSheet(f"color: {c['success']}; font-size: 11px;")
        else:
            msg = result.get("message", "未知错误")
            status_label.setText(f"失败: {msg}")
            status_label.setStyleSheet(f"color: {c['error']}; font-size: 11px;")

    def _pick_color(self, theme_name):
        current = self.color_hex_dark.text() if theme_name == "dark" else self.color_hex_light.text()
        init_color = QColor(current) if current and len(current) == 7 else QColor("#ff4d5a" if theme_name == "dark" else "#6cb2eb")

        color = QColorDialog.getColor(init_color, self, f"选择{theme_name}模式点缀色")
        if color.isValid():
            hex_color = color.name()
            if theme_name == "dark":
                self.color_hex_dark.setText(hex_color)
            else:
                self.color_hex_light.setText(hex_color)
            self._update_color_preview(theme_name, hex_color)
            theme_manager.set_custom_accent(hex_color, theme_name)

    def _on_hex_changed(self, theme_name, text):
        if len(text) == 7 and text.startswith("#"):
            try:
                QColor(text)
                self._update_color_preview(theme_name, text)
                theme_manager.set_custom_accent(text, theme_name)
            except Exception:
                pass

    def _update_color_preview(self, theme_name, hex_color):
        preview = self.color_preview_dark if theme_name == "dark" else self.color_preview_light
        preview.setStyleSheet(f"""
            #colorPreview {{
                background-color: {hex_color};
                border: 2px solid {hex_color};
                border-radius: 8px;
            }}
        """)

    def _reset_accent(self, theme_name):
        if theme_name == "dark":
            self.color_hex_dark.setText("")
            self._update_color_preview("dark", "#ff4d5a")
        else:
            self.color_hex_light.setText("")
            self._update_color_preview("light", "#6cb2eb")
        theme_manager.reset_accent(theme_name)

    def refresh_theme(self):
        for child in self.findChildren(QGroupBox):
            child.setStyleSheet(self._group_style())

        c = theme_manager.colors
        for label in self.db_status_labels.values():
            label.setStyleSheet(f"color: {c['success']}; font-size: 11px;")

    def _apply_theme(self):
        pass