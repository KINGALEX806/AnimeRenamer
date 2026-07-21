"""设置面板组件 - 毛玻璃卡片风格 + 色盘选择器 + 头像自定义"""
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QCheckBox, QLineEdit,
    QGroupBox, QScrollArea, QHBoxLayout, QPushButton, QRadioButton,
    QButtonGroup, QFrame, QSizePolicy, QGridLayout,
    QColorDialog
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
    "tmdb": {
        "label": "TMDB",
        "url": "themoviedb.org",
        "key": "tmdb",
    },
    "jikan": {
        "label": "Jikan",
        "url": "jikan.moe",
        "key": "jikan",
    },
}


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

        # ========== 4. 标题语言 ==========
        self._build_language_section(layout)

        # ========== 5. 番剧数据源 ==========
        self._build_database_section(layout)

        # ========== 6. API 设置 ==========
        self._build_api_section(layout)

        # ========== 7. 主题点缀色自定义 ==========
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
                      "{year}年份, {video_info}完整视频信息, {audio_info}完整音频信息")
        hint.setObjectName("hintLabel")
        hint.setWordWrap(True)
        naming_layout.addWidget(hint)

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

        # 视频格式
        fmt_layout.addWidget(QLabel("\u89C6\u9891\u6269\u5C55\u540D (\u5DF2\u5185\u7F6E: .mkv .mp4 .avi .mov .wmv .flv .webm .m4v .ts):"))
        self.custom_video_input = QLineEdit()
        self.custom_video_input.setPlaceholderText("\u4F8B\u5982: .rmvb .ogm .divx .m2ts .vob")
        fmt_layout.addWidget(self.custom_video_input)

        # 字幕格式
        fmt_layout.addWidget(QLabel("\u5B57\u5E55\u6269\u5C55\u540D (\u5DF2\u5185\u7F6E: .ass .ssa .srt .sub .idx .sup .vtt):"))
        self.custom_sub_input = QLineEdit()
        self.custom_sub_input.setPlaceholderText("\u4F8B\u5982: .txt .pgs .usf .xssf")
        fmt_layout.addWidget(self.custom_sub_input)

        layout.addWidget(fmt_group)

    def _build_language_section(self, layout):
        lang_group = QGroupBox("\u756A\u5267\u540D")
        lang_group.setStyleSheet(self._group_style())
        lang_layout = QVBoxLayout(lang_group)
        lang_layout.setSpacing(10)
        lang_layout.setContentsMargins(16, 24, 16, 16)

        # 番剧名来源
        lang_layout.addWidget(QLabel("\u756A\u5267\u540D\u6765\u6E90:"))
        self.title_cn = QRadioButton("\u4E2D\u6587\u6807\u9898")
        self.title_en = QRadioButton("\u82F1\u6587/\u7F57\u9A6C\u5B57\u6807\u9898")
        self.title_original = QRadioButton("\u4FDD\u7559\u539F\u6587\u4EF6\u6807\u9898\uFF08\u4E0D\u641C\u7D22\uFF09")
        self.title_cn.setChecked(True)

        self.title_group = QButtonGroup()
        self.title_group.addButton(self.title_cn, 0)
        self.title_group.addButton(self.title_en, 1)
        self.title_group.addButton(self.title_original, 2)

        lang_layout.addWidget(self.title_cn)
        lang_layout.addWidget(self.title_en)
        lang_layout.addWidget(self.title_original)

        # 分隔线
        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFixedHeight(1)
        lang_layout.addWidget(sep)

        # 每集标题语言
        lang_layout.addWidget(QLabel("\u6BCF\u96C6\u6807\u9898\u8BED\u8A00:"))
        self.ep_title_cn = QRadioButton("\u4E2D\u6587\u6807\u9898")
        self.ep_title_jp = QRadioButton("\u65E5\u6587\u6807\u9898")
        self.ep_title_cn.setChecked(True)

        self.ep_title_group = QButtonGroup()
        self.ep_title_group.addButton(self.ep_title_cn, 0)
        self.ep_title_group.addButton(self.ep_title_jp, 1)

        lang_layout.addWidget(self.ep_title_cn)
        lang_layout.addWidget(self.ep_title_jp)
        layout.addWidget(lang_group)

        # ── 季集格式 ──
        se_group = QGroupBox("\u5B63\u96C6\u683C\u5F0F")
        se_group.setStyleSheet(self._group_style())
        se_layout = QVBoxLayout(se_group)
        se_layout.setSpacing(10)
        se_layout.setContentsMargins(16, 24, 16, 16)

        se_layout.addWidget(QLabel("\u5B63\u96C6\u6570\u663E\u793A\u683C\u5F0F:"))
        self.se_sXXeYY = QRadioButton("S01E01 \u683C\u5F0F\uFF08\u5E26\u5B63\u6570\uFF09")
        self.se_number = QRadioButton("01 \u7EAF\u6570\u5B57\u683C\u5F0F\uFF08\u65E0\u5B63\u6570\uFF09")
        self.se_sXXeYY.setChecked(True)

        self.se_format_group = QButtonGroup()
        self.se_format_group.addButton(self.se_sXXeYY, 0)
        self.se_format_group.addButton(self.se_number, 1)

        se_layout.addWidget(self.se_sXXeYY)
        se_layout.addWidget(self.se_number)
        layout.addWidget(se_group)

    def _build_database_section(self, layout):
        """构建番剧数据源管理区域"""
        db_group = QGroupBox("番剧数据源")
        db_group.setStyleSheet(self._group_style())
        db_layout = QVBoxLayout(db_group)
        db_layout.setSpacing(12)
        db_layout.setContentsMargins(16, 24, 16, 16)

        # ---- 主数据源选择 ----
        db_layout.addWidget(QLabel("当前主数据源:"))

        self.db_primary_group = QButtonGroup()
        db_primary_layout = QVBoxLayout()
        db_primary_layout.setSpacing(8)

        db_choices = [
            ("bangumi", "Bangumi"),
            ("anilist", "AniList"),
            ("tmdb", "TMDB"),
            ("jikan", "Jikan"),
        ]
        self.db_primary_radios = {}
        for key, label in db_choices:
            radio = QRadioButton(label)
            db_primary_layout.addWidget(radio)
            self.db_primary_group.addButton(radio)
            self.db_primary_radios[key] = radio

        self.db_primary_radios["bangumi"].setChecked(True)
        db_layout.addLayout(db_primary_layout)

        # ---- 自动切换 ----
        self.db_auto_fallback_cb = QCheckBox("启用自动切换（失败时自动尝试下一数据源）")
        self.db_auto_fallback_cb.setChecked(True)
        db_layout.addWidget(self.db_auto_fallback_cb)

        # ---- 分隔线 ----
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("separator")
        db_layout.addWidget(sep)

        # ---- 查询顺序 + 一键测试 ----
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

        for db_key in ("bangumi", "anilist", "tmdb", "jikan"):
            info = DB_INFO[db_key]
            row = self._build_db_row(info)
            db_layout.addLayout(row)

        layout.addWidget(db_group)

    def _build_db_row(self, info):
        """构建单个数据源的行"""
        c = theme_manager.colors
        row = QVBoxLayout()
        row.setSpacing(4)

        # 第一行: 复选框 + 名称 + 状态
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        cb = QCheckBox(info["label"])
        cb.setChecked(True)
        top_row.addWidget(cb)
        self.db_enabled[info["key"]] = cb

        # URL 标签
        url_label = QLabel(f"({info['url']})")
        url_label.setObjectName("hintLabel")
        top_row.addWidget(url_label)

        # 状态标签
        status_label = QLabel("就绪")
        status_label.setObjectName("hintLabel")
        status_label.setStyleSheet(f"color: {c['success']}; font-size: 11px;")
        top_row.addWidget(status_label)
        self.db_status_labels[info["key"]] = status_label

        top_row.addStretch()

        # 测试连接按钮
        test_btn = QPushButton("测试连接")
        test_btn.setObjectName("smallBtn")
        test_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        test_btn.clicked.connect(lambda checked, k=info["key"]: self._test_db_connection(k))
        top_row.addWidget(test_btn)
        self.db_test_buttons[info["key"]] = test_btn

        row.addLayout(top_row)

        # TMDB 额外: API Key 输入框
        if info["key"] == "tmdb":
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
            self.db_api_key_inputs["tmdb"] = api_input

            row.addLayout(api_row)

        return row

    def _build_api_section(self, layout):
        api_group = QGroupBox("API 设置")
        api_group.setStyleSheet(self._group_style())
        api_layout = QVBoxLayout(api_group)
        api_layout.setSpacing(10)
        api_layout.setContentsMargins(16, 24, 16, 16)

        api_layout.addWidget(QLabel("TMDB API Key (可选):"))
        api_hint = QLabel("用于获取番剧信息和每集标题\n留空使用默认 Key")
        api_hint.setObjectName("hintLabel")
        api_hint.setWordWrap(True)
        api_layout.addWidget(api_hint)

        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("输入你的 TMDB API Key")
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        api_layout.addWidget(self.api_key_input)

        api_btn_layout = QHBoxLayout()
        get_key_btn = QPushButton("获取免费 Key")
        get_key_btn.setObjectName("smallBtn")
        get_key_btn.setToolTip("前往 TMDB 官网免费注册获取 API Key")
        get_key_btn.clicked.connect(self._open_tmdb_site)
        api_btn_layout.addWidget(get_key_btn)
        api_btn_layout.addStretch()
        api_layout.addLayout(api_btn_layout)

        layout.addWidget(api_group)

    # ================================================================
    #  信号连接
    # ================================================================

    def _build_color_section(self, layout):
        """🎨 主题点缀色自定义"""
        color_group = QGroupBox("🎨 主题点缀色自定义")
        color_group.setStyleSheet(self._group_style())
        color_layout = QVBoxLayout(color_group)
        color_layout.setSpacing(12)
        color_layout.setContentsMargins(16, 24, 16, 16)

        # ── 暗色模式点缀色 ──
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

        # ── 浅色模式点缀色 ──
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
        # 命名规则
        self.template_input.textChanged.connect(self._on_setting_changed)

        # 字幕选项
        self.sync_subtitle_cb.toggled.connect(self._on_setting_changed)
        self.remove_sc_cb.toggled.connect(self._on_setting_changed)

        # 标签处理
        self.keep_group_cb.toggled.connect(self._on_setting_changed)
        self.keep_encoding_cb.toggled.connect(self._on_setting_changed)
        self.keep_audio_cb.toggled.connect(self._on_setting_changed)
        self.keep_language_cb.toggled.connect(self._on_setting_changed)

        # 语言
        self.title_cn.toggled.connect(self._on_setting_changed)
        self.title_en.toggled.connect(self._on_setting_changed)
        self.title_original.toggled.connect(self._on_setting_changed)
        self.ep_title_cn.toggled.connect(self._on_setting_changed)
        self.ep_title_jp.toggled.connect(self._on_setting_changed)

        # 季集格式
        self.se_sXXeYY.toggled.connect(self._on_setting_changed)
        self.se_number.toggled.connect(self._on_setting_changed)

        # 数据源
        for radio in self.db_primary_radios.values():
            radio.toggled.connect(self._on_setting_changed)
        self.db_auto_fallback_cb.toggled.connect(self._on_setting_changed)
        for cb in self.db_enabled.values():
            cb.toggled.connect(self._on_setting_changed)

        # API
        self.api_key_input.textChanged.connect(self._on_setting_changed)
        # 同步 TMDB API Key 到数据库区域
        self.api_key_input.textChanged.connect(self._sync_tmdb_api_key)
        # 同步数据库区域 TMDB API Key 到主输入框
        if "tmdb" in self.db_api_key_inputs:
            self.db_api_key_inputs["tmdb"].textChanged.connect(self._sync_tmdb_api_key)
            self.db_api_key_inputs["tmdb"].textChanged.connect(self._on_setting_changed)

        # 自定义格式
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
        self.save_settings()
        self.settings_changed.emit()

    def _load_settings(self):
        config = load_config()

        # 命名规则
        template = config.get("naming_template", "{title} - {season_episode} {episode_title}")
        self.template_input.setText(template)

        # 字幕
        self.sync_subtitle_cb.setChecked(config.get("sync_subtitle", True))
        self.remove_sc_cb.setChecked(config.get("remove_sc_tag", True))

        # 标签处理
        self.keep_group_cb.setChecked(config.get("keep_release_group", True))
        self.keep_encoding_cb.setChecked(config.get("keep_encoding_info", True))
        self.keep_audio_cb.setChecked(config.get("keep_audio_info", True))
        self.keep_language_cb.setChecked(config.get("keep_language_tag", True))

        # 语言
        lang = config.get("language", "zh-CN")
        title_source = config.get("title_source", "cn")
        if title_source == "original":
            self.title_original.setChecked(True)
        elif title_source == "en":
            self.title_en.setChecked(True)
        else:
            self.title_cn.setChecked(True)

        # 每集标题语言
        ep_lang = config.get("episode_title_language", "cn")
        self.ep_title_cn.setChecked(ep_lang == "cn")
        self.ep_title_jp.setChecked(ep_lang == "jp")

        # 季集格式
        se_format = config.get("season_episode_format", "sXXeYY")
        self.se_sXXeYY.setChecked(se_format == "sXXeYY")
        self.se_number.setChecked(se_format == "number")

        # 自定义格式
        self.custom_video_input.setText(config.get("custom_video_extensions", ""))
        self.custom_sub_input.setText(config.get("custom_subtitle_extensions", ""))

        # 数据源 - 主数据源
        db_primary = config.get("db_primary", "bangumi")
        if db_primary in self.db_primary_radios:
            self.db_primary_radios[db_primary].setChecked(True)

        # 数据源 - 自动切换
        self.db_auto_fallback_cb.setChecked(config.get("db_auto_fallback", True))

        # 数据源 - 启用状态
        db_enabled = config.get("db_enabled", {})
        for key, cb in self.db_enabled.items():
            cb.setChecked(db_enabled.get(key, True))

        # API Key
        api_key = config.get("tmdb_api_key", "")
        self.api_key_input.setText(api_key)
        if "tmdb" in self.db_api_key_inputs:
            self.db_api_key_inputs["tmdb"].setText(api_key)

        # 点缀色
        custom_dark = config.get("custom_accent_dark", "")
        custom_light = config.get("custom_accent_light", "")
        self.color_hex_dark.setText(custom_dark)
        self.color_hex_light.setText(custom_light)
        self._update_color_preview("dark", custom_dark or "#ff4d5a")
        self._update_color_preview("light", custom_light or "#6cb2eb")



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
        config["season_episode_format"] = "sXXeYY" if self.se_sXXeYY.isChecked() else "number"

        # 自定义格式
        config["custom_video_extensions"] = self.custom_video_input.text().strip()
        config["custom_subtitle_extensions"] = self.custom_sub_input.text().strip()

        # 数据源
        for key, radio in self.db_primary_radios.items():
            if radio.isChecked():
                config["db_primary"] = key
                break

        config["db_auto_fallback"] = self.db_auto_fallback_cb.isChecked()

        db_enabled = {}
        for key, cb in self.db_enabled.items():
            db_enabled[key] = cb.isChecked()
        config["db_enabled"] = db_enabled

        config["tmdb_api_key"] = self.api_key_input.text().strip()

        config["custom_accent_dark"] = self.color_hex_dark.text().strip()
        config["custom_accent_light"] = self.color_hex_light.text().strip()

        save_config(config)

    def get_settings(self):
        """获取当前设置字典"""
        db_primary = "bangumi"
        for key, radio in self.db_primary_radios.items():
            if radio.isChecked():
                db_primary = key
                break

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
            "tmdb_api_key": self.api_key_input.text().strip(),
        }

    # ================================================================
    #  辅助方法
    # ================================================================

    def _sync_tmdb_api_key(self, text):
        """同步 TMDB API Key 到数据源区域的输入框"""
        # 如果是从主输入框触发，同步到数据库区域
        if self.sender() == self.api_key_input:
            if "tmdb" in self.db_api_key_inputs:
                self.db_api_key_inputs["tmdb"].setText(text)
        # 如果是从数据库区域输入框触发，同步到主输入框
        elif self.sender() == self.db_api_key_inputs.get("tmdb"):
            self.api_key_input.setText(text)

    def _open_tmdb_site(self):
        import webbrowser
        webbrowser.open("https://www.themoviedb.org/settings/api")

    def _test_db_connection(self, db_key):
        """测试单个数据源连接（不弹窗）"""
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
        """一键测试所有启用的数据源连接"""
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
        """单个数据库测试完成"""
        self._update_db_status(db_key, result)

    def _on_all_tests_finished(self):
        """全部测试完成"""
        self.test_all_btn.setEnabled(True)
        self.test_all_btn.setText("\U0001F50D  \u4E00\u952E\u6D4B\u8BD5\u5168\u90E8")

    def _update_db_status(self, db_key, result):
        """更新数据库状态标签"""
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

    # ================================================================
    #  点缀色 & 头像方法
    # ================================================================

    def _pick_color(self, theme_name):
        """打开色盘选择器"""
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
        """HEX 输入框变化时实时更新"""
        if len(text) == 7 and text.startswith("#"):
            try:
                QColor(text)
                self._update_color_preview(theme_name, text)
                theme_manager.set_custom_accent(text, theme_name)
            except Exception:
                pass

    def _update_color_preview(self, theme_name, hex_color):
        """更新颜色预览按钮"""
        preview = self.color_preview_dark if theme_name == "dark" else self.color_preview_light
        preview.setStyleSheet(f"""
            #colorPreview {{
                background-color: {hex_color};
                border: 2px solid {hex_color};
                border-radius: 8px;
            }}
        """)

    def _reset_accent(self, theme_name):
        """重置为默认点缀色"""
        if theme_name == "dark":
            self.color_hex_dark.setText("")
            self._update_color_preview("dark", "#ff4d5a")
        else:
            self.color_hex_light.setText("")
            self._update_color_preview("light", "#6cb2eb")
        theme_manager.reset_accent(theme_name)

    # ================================================================
    #  主题刷新
    # ================================================================

    def refresh_theme(self):
        """刷新所有 GroupBox 样式"""
        for child in self.findChildren(QGroupBox):
            child.setStyleSheet(self._group_style())

        # 刷新状态标签颜色
        c = theme_manager.colors
        for label in self.db_status_labels.values():
            label.setStyleSheet(f"color: {c['success']}; font-size: 11px;")

    def _apply_theme(self):
        pass