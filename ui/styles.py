"""样式表 - 堤丰双形态毛玻璃美学 QSS 定义"""
from ui.theme import theme_manager


def get_stylesheet():
    """获取完整的 QSS 样式表"""
    c = theme_manager.colors

    return f"""
    /* ============================================================
       全局基础
       ============================================================ */
    QWidget {{
        background-color: {c["bg_primary"]};
        color: {c["text_primary"]};
        font-family: "Microsoft YaHei", "Segoe UI", "PingFang SC", sans-serif;
        font-size: 13px;
    }}

    QMainWindow {{
        background-color: {c["bg_primary"]};
    }}

    /* ============================================================
       通用按钮
       ============================================================ */
    QPushButton {{
        background-color: {c["bg_card"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border"]};
        border-radius: 10px;
        padding: 8px 18px;
        font-size: 13px;
        min-height: 34px;
    }}

    QPushButton:hover {{
        background-color: {c["bg_hover"]};
        border-color: {c["border_glow"]};
    }}

    QPushButton:pressed {{
        background-color: {c["bg_card"]};
    }}

    QPushButton:disabled {{
        background-color: {c["btn_disabled_bg"]};
        color: {c["btn_disabled_text"]};
        border-color: {c["border"]};
    }}

    /* ── 主操作按钮 (胶囊发光) ── */
    QPushButton#primaryBtn {{
        background-color: {c["accent"]};
        color: {c["accent_text"]};
        border: none;
        border-radius: 10px;
        padding: 8px 28px;
        font-size: 14px;
        font-weight: bold;
        min-height: 36px;
        letter-spacing: 0.5px;
    }}

    QPushButton#primaryBtn:hover {{
        background-color: {c["accent_hover"]};
    }}

    QPushButton#primaryBtn:pressed {{
        background-color: {c["accent"]};
    }}

    QPushButton#primaryBtn:disabled {{
        background-color: {c["btn_disabled_bg"]};
        color: {c["btn_disabled_text"]};
    }}

    /* ── 图标按钮 ── */
    QPushButton#iconBtn {{
        background: transparent;
        border: none;
        border-radius: 10px;
        padding: 8px;
        min-width: 36px;
        min-height: 36px;
        font-size: 16px;
    }}

    QPushButton#iconBtn:hover {{
        background-color: {c["bg_hover"]};
    }}

    /* ── 胶囊按钮 (操作栏) ── */
    QPushButton#capsuleBtn {{
        background-color: {c["bg_card"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border_glow"]};
        border-radius: 28px;
        padding: 14px 36px;
        font-size: 15px;
        font-weight: 600;
        min-height: 48px;
        letter-spacing: 0.3px;
    }}

    QPushButton#capsuleBtn:hover {{
        background-color: {c["bg_hover"]};
        border-color: {c["accent"]};
        color: {c["accent"]};
    }}

    /* ── 危险操作按钮 ── */
    QPushButton#dangerBtn {{
        background-color: transparent;
        color: {c["error"]};
        border: 1px solid {c["error"]};
        border-radius: 10px;
        padding: 8px 18px;
    }}

    QPushButton#dangerBtn:hover {{
        background-color: {c["error"]};
        color: {c["danger_hover_text"]};
    }}

    /* ── 小按钮 ── */
    QPushButton#smallBtn {{
        padding: 5px 14px;
        font-size: 12px;
        min-height: 28px;
        border-radius: 8px;
    }}

    /* ============================================================
       侧边栏
       ============================================================ */
    #sidebar {{
        background-color: {c["bg_sidebar"]};
        border-right: 1px solid {c["border"]};
    }}

    #sidebarTitle {{
        font-size: 15px;
        font-weight: bold;
        color: {c["text_primary"]};
        background: transparent;
        padding: 0px;
    }}

    #sidebarSubtitle {{
        font-size: 10px;
        font-weight: 600;
        color: {c["text_muted"]};
        background: transparent;
        letter-spacing: 2px;
        padding: 0px;
    }}

    /* ── 看板娘头像容器 ── */
    #avatarContainer {{
        background: transparent;
        border: none;
    }}

    #avatarGlow {{
        background: transparent;
        border: none;
    }}

    /* ── 导航按钮 ── */
    QPushButton#navBtn {{
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

    QPushButton#navBtn:hover {{
        background-color: {c["sidebar_hover_bg"]};
        color: {c["text_primary"]};
    }}

    QPushButton#navBtnActive {{
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

    /* ── 主题切换按钮 ── */
    QPushButton#themeToggleBtn {{
        background: {c["bg_card"]};
        color: {c["text_secondary"]};
        border: 1px solid {c["border"]};
        border-radius: 20px;
        padding: 8px 16px;
        font-size: 12px;
        min-height: 32px;
    }}

    QPushButton#themeToggleBtn:hover {{
        background: {c["bg_hover"]};
        color: {c["text_primary"]};
    }}

    /* ============================================================
       标签
       ============================================================ */
    QLabel {{
        background: transparent;
        border: none;
    }}

    QLabel#sectionTitle {{
        font-size: 14px;
        font-weight: bold;
        color: {c["text_primary"]};
        padding: 4px 0px;
    }}

    QLabel#hintLabel {{
        font-size: 11px;
        color: {c["text_muted"]};
    }}

    QLabel#pathLabel {{
        font-size: 12px;
        color: {c["text_muted"]};
        background: transparent;
        font-family: "Consolas", "Cascadia Code", "Microsoft YaHei", monospace;
    }}

    QLabel#welcomeTitle {{
        font-size: 28px;
        font-weight: bold;
        color: {c["text_primary"]};
        background: transparent;
    }}

    QLabel#welcomeSubtitle {{
        font-size: 14px;
        color: {c["text_secondary"]};
        background: transparent;
    }}

    QLabel#aboutTitle {{
        font-size: 28px;
        font-weight: bold;
        color: {c["text_primary"]};
        background: transparent;
    }}

    QLabel#aboutVersion {{
        font-size: 14px;
        color: {c["accent"]};
        background: transparent;
    }}

    QLabel#aboutLine {{
        font-size: 15px;
        color: {c["text_secondary"]};
        background: transparent;
        line-height: 1.8;
        padding: 2px 0px;
    }}

    /* ============================================================
       输入框
       ============================================================ */
    QLineEdit#searchKeywordInput {{
        background-color: {c["bg_input"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border"]};
        border-radius: 10px;
        padding: 8px 12px;
        font-size: 12px;
        max-height: 32px;
        selection-background-color: {c["accent"]};
    }}

    QLineEdit#searchKeywordInput:focus {{
        border-color: {c["accent"]};
    }}

    /* ── 搜索结果下拉框 ── */
    QComboBox#searchResultCombo {{
        background-color: {c["bg_input"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border"]};
        border-radius: 10px;
        padding: 6px 10px;
        font-size: 12px;
        max-height: 32px;
    }}

    QComboBox#searchResultCombo:hover {{
        border-color: {c["border_glow"]};
    }}

    QComboBox#searchResultCombo QAbstractItemView {{
        background-color: {c["bg_card"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border"]};
        border-radius: 10px;
        padding: 4px;
        selection-background-color: {c["accent"]};
        selection-color: #ffffff;
        outline: none;
    }}

    QComboBox#searchResultCombo::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 24px;
        border: none;
        border-top-right-radius: 10px;
        border-bottom-right-radius: 10px;
    }}

    QLineEdit {{
        background-color: {c["bg_input"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border"]};
        border-radius: 10px;
        padding: 10px 14px;
        font-size: 13px;
        selection-background-color: {c["accent"]};
    }}

    QLineEdit:focus {{
        border-color: {c["border_focus"]};
    }}

    /* ============================================================
       复选框 & 单选框
       ============================================================ */
    QCheckBox {{
        background: transparent;
        spacing: 10px;
        color: {c["text_primary"]};
    }}

    QCheckBox::indicator {{
        width: 20px;
        height: 20px;
        border: 2px solid {c["border"]};
        border-radius: 6px;
        background: {c["bg_input"]};
    }}

    QCheckBox::indicator:checked {{
        background: {c["accent"]};
        border-color: {c["accent"]};
    }}

    QCheckBox::indicator:hover {{
        border-color: {c["accent"]};
    }}

    QRadioButton {{
        background: transparent;
        spacing: 10px;
        color: {c["text_primary"]};
    }}

    QRadioButton::indicator {{
        width: 20px;
        height: 20px;
        border: 2px solid {c["border"]};
        border-radius: 10px;
        background: {c["bg_input"]};
    }}

    QRadioButton::indicator:checked {{
        background: {c["accent"]};
        border-color: {c["accent"]};
    }}

    /* ============================================================
       滚动条
       ============================================================ */
    QScrollBar:vertical {{
        background: transparent;
        width: 6px;
        border-radius: 3px;
        margin: 4px 2px;
    }}

    QScrollBar::handle:vertical {{
        background: {c["scrollbar_handle"]};
        border-radius: 3px;
        min-height: 30px;
    }}

    QScrollBar::handle:vertical:hover {{
        background: {c["text_muted"]};
    }}

    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    QScrollBar:horizontal {{
        background: transparent;
        height: 6px;
        border-radius: 3px;
        margin: 2px 4px;
    }}

    QScrollBar::handle:horizontal {{
        background: {c["scrollbar_handle"]};
        border-radius: 3px;
        min-width: 30px;
    }}

    QScrollBar::add-line:horizontal,
    QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}

    /* ============================================================
       表格 (玻璃质感全屏)
       ============================================================ */
    QTableWidget {{
        background-color: transparent;
        border: none;
        gridline-color: transparent;
        selection-background-color: {c["bg_table_hover"]};
        selection-color: {c["text_primary"]};
        outline: none;
    }}

    QTableWidget::item {{
        padding: 10px 14px;
        border-bottom: 1px solid {c["border"]};
        background: transparent;
    }}

    QTableWidget::item:selected {{
        background-color: {c["bg_table_hover"]};
    }}

    QHeaderView::section {{
        background-color: {c["bg_table_header"]};
        color: {c["text_secondary"]};
        padding: 12px 14px;
        border: none;
        border-bottom: 1px solid {c["border_glow"]};
        font-weight: 600;
        font-size: 12px;
        letter-spacing: 0.3px;
    }}

    /* ============================================================
       分组框
       ============================================================ */
    QGroupBox {{
        background-color: {c["bg_card"]};
        border: 1px solid {c["border"]};
        border-radius: 14px;
        margin-top: 14px;
        padding: 18px;
        padding-top: 28px;
        font-weight: bold;
        color: {c["text_primary"]};
    }}

    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 18px;
        padding: 0 10px;
        color: {c["text_primary"]};
    }}

    /* ============================================================
       进度条
       ============================================================ */
    QProgressBar {{
        background-color: {c["bg_card"]};
        border: none;
        border-radius: 3px;
        text-align: center;
        height: 4px;
        font-size: 0px;
    }}

    QProgressBar::chunk {{
        background-color: {c["progress_chunk"]};
        border-radius: 3px;
    }}

    /* ============================================================
       下拉框
       ============================================================ */
    QComboBox {{
        background-color: {c["bg_input"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border"]};
        border-radius: 10px;
        padding: 10px 14px;
        min-height: 20px;
    }}

    QComboBox:hover {{
        border-color: {c["accent"]};
    }}

    QComboBox::drop-down {{
        border: none;
        width: 28px;
    }}

    QComboBox QAbstractItemView {{
        background-color: {c["bg_card_solid"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border"]};
        border-radius: 10px;
        selection-background-color: {c["bg_hover"]};
        padding: 6px;
    }}

    /* ============================================================
       分割线
       ============================================================ */
    #separator {{
        background-color: {c["border"]};
        max-height: 1px;
        min-height: 1px;
    }}

    /* ============================================================
       状态栏
       ============================================================ */
    #statusBar {{
        background-color: {c["status_bg"]};
        border-top: 1px solid {c["border"]};
    }}

    /* ============================================================
       提示框
       ============================================================ */
    QToolTip {{
        background-color: {c["bg_card_solid"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border_glow"]};
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 12px;
    }}

    /* ============================================================
       设置面板
       ============================================================ */
    #settingsPanel {{
        background-color: {c["bg_card"]};
        border: 1px solid {c["border"]};
        border-radius: 16px;
    }}

    #settingsScroll {{
        background: transparent;
        border: none;
    }}

    /* ── 颜色预览块 ── */
    #colorPreview {{
        border: 2px solid {c["border_glow"]};
        border-radius: 8px;
    }}

    /* ── 头像预览框 ── */
    #avatarPreview {{
        background-color: {c["bg_card"]};
        border: 2px dashed {c["border_glow"]};
        border-radius: 16px;
    }}

    /* ============================================================
       日志面板
       ============================================================ */
    #logPanel {{
        background-color: {c["log_bg"]};
        border: 1px solid {c["border"]};
        border-radius: 14px;
    }}

    #logText {{
        background-color: transparent;
        color: {c["text_secondary"]};
        font-family: "Consolas", "Cascadia Code", "Microsoft YaHei", monospace;
        font-size: 12px;
        border: none;
        padding: 10px;
    }}

    /* ============================================================
       卡片
       ============================================================ */
    #card {{
        background-color: {c["bg_card"]};
        border: 1px solid {c["border"]};
        border-radius: 16px;
    }}

    #glassCard {{
        background-color: {c["bg_card"]};
        border: 1px solid {c["border_glow"]};
        border-radius: 20px;
    }}

    /* ============================================================
       标签芯片
       ============================================================ */
    #chip {{
        background-color: {c["bg_table_hover"]};
        color: {c["accent"]};
        border: none;
        border-radius: 12px;
        padding: 4px 12px;
        font-size: 12px;
        font-weight: 600;
    }}

    /* ============================================================
       全域拖拽感应区
       ============================================================ */
    #mainDropArea {{
        background: transparent;
        border: 2px solid transparent;
        border-radius: 0px;
    }}

    #mainDropAreaActive {{
        background: transparent;
        border: 2px solid {c["accent"]};
    }}

    /* ============================================================
       操作栏
       ============================================================ */
    #actionBar {{
        background: transparent;
        border: none;
    }}

    /* ============================================================
       表格容器
       ============================================================ */
    #tableContainer {{
        background-color: {c["bg_table"]};
        border: 1px solid {c["border"]};
        border-radius: 16px;
    }}

    /* ============================================================
       侧边栏分隔线
       ============================================================ */
    #sidebarSep {{
        background-color: {c["border"]};
        max-height: 1px;
        min-height: 1px;
    }}

    /* ============================================================
       操作模式选择器（FileBot 风格）
       ============================================================ */
    QComboBox#operationModeCombo {{
        background-color: {c["bg_input"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border"]};
        border-radius: 8px;
        padding: 4px 10px;
        font-size: 12px;
        min-height: 26px;
        max-height: 28px;
        min-width: 80px;
    }}

    QComboBox#operationModeCombo:hover {{
        border-color: {c["accent"]};
    }}

    QComboBox#operationModeCombo QAbstractItemView {{
        background-color: {c["bg_card"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border"]};
        border-radius: 8px;
        padding: 4px;
        selection-background-color: {c["accent"]};
        selection-color: #ffffff;
        outline: none;
    }}

    /* ============================================================
       右键菜单
       ============================================================ */
    QMenu {{
        background-color: {c["bg_card_solid"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border_glow"]};
        border-radius: 10px;
        padding: 6px;
    }}

    QMenu::item {{
        padding: 8px 28px 8px 16px;
        border-radius: 6px;
        margin: 2px 4px;
    }}

    QMenu::item:selected {{
        background-color: {c["accent"]};
        color: #ffffff;
    }}

    QMenu::separator {{
        height: 1px;
        background: {c["border"]};
        margin: 4px 8px;
    }}

    /* ============================================================
       表格对照分隔线（FileBot 左右对照式）
       ============================================================ */
    #compareDivider {{
        background-color: {c["border_glow"]};
        min-width: 1px;
        max-width: 1px;
    }}

    /* ============================================================
       撤销按钮
       ============================================================ */
    QPushButton#undoBtn {{
        padding: 5px 14px;
        font-size: 12px;
        min-height: 28px;
        border-radius: 8px;
        background-color: transparent;
        color: {c["text_secondary"]};
        border: 1px solid {c["border"]};
    }}

    QPushButton#undoBtn:hover {{
        background-color: {c["bg_hover"]};
        color: {c["warning"]};
        border-color: {c["warning"]};
    }}

    QPushButton#undoBtn:disabled {{
        background-color: transparent;
        color: {c["btn_disabled_text"]};
        border-color: {c["border"]};
    }}
    """