"""主题管理器 - 堤丰双形态清透配色 + 自定义点缀色 + 内置默认头像"""
import os
from PySide6.QtCore import QObject, Signal
from utils.config import load_config, set_config


# ── 内置默认头像路径 ────────────────────────────────────────
_ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
AVATAR_DEFAULT_DARK = os.path.join(_ASSETS_DIR, "avatar_dark.png")
AVATAR_DEFAULT_LIGHT = os.path.join(_ASSETS_DIR, "avatar_light.png")

# ── 默认点缀色 ──────────────────────────────────────────────
DEFAULT_ACCENT_DARK = "#ff4d5a"
DEFAULT_ACCENT_LIGHT = "#6cb2eb"


def _derive_accent_colors(hex_color):
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)

    def brighten(v): return min(255, int(v + (255 - v) * 0.18))
    rh, gh, bh = brighten(r), brighten(g), brighten(b)

    return {
        "accent": hex_color,
        "accent_hover": f"#{rh:02x}{gh:02x}{bh:02x}",
        "accent_glow": f"rgba({r}, {g}, {b}, 0.25)",
        "accent_text": "#ffffff",
        "border_focus": hex_color,
        "sidebar_active_indicator": hex_color,
        "nav_indicator": hex_color,
        "btn_shadow": f"rgba({r}, {g}, {b}, 0.35)",
        "avatar_glow": f"rgba({r}, {g}, {b}, 0.35)",
        "drop_glow": f"rgba({r}, {g}, {b}, 0.15)",
        "bg_hover": f"rgba({r}, {g}, {b}, 0.08)",
        "bg_table_hover": f"rgba({r}, {g}, {b}, 0.12)",
        "progress_chunk": hex_color,
    }


DARK_BASE = {
    "name": "dark",
    "bg_deepest": "#16171c",
    "bg_primary": "#1e2025",
    "bg_secondary": "#22242a",
    "bg_card": "rgba(42, 45, 52, 0.55)",
    "bg_card_solid": "#2a2d34",
    "bg_input": "rgba(30, 32, 37, 0.8)",
    "bg_sidebar": "rgba(22, 23, 28, 0.8)",
    "bg_table": "rgba(42, 45, 52, 0.3)",
    "bg_table_alt": "rgba(42, 45, 52, 0.15)",
    "bg_table_header": "rgba(30, 32, 37, 0.9)",
    "text_primary": "#e8e8ed",
    "text_secondary": "#a8a8b8",
    "text_muted": "#6a6a7a",
    "text_placeholder": "#505060",
    "accent_text": "#ffffff",
    "success": "#4ade80",
    "success_bg": "rgba(74, 222, 128, 0.15)",
    "error": "#f87171",
    "error_bg": "rgba(248, 113, 113, 0.15)",
    "warning": "#fbbf24",
    "warning_bg": "rgba(251, 191, 36, 0.15)",
    "info": "#60cdff",
    "info_bg": "rgba(96, 205, 255, 0.15)",
    "border": "rgba(255, 255, 255, 0.06)",
    "border_glow": "rgba(255, 255, 255, 0.1)",
    "grid": "rgba(255, 255, 255, 0.08)",
    "scrollbar_bg": "transparent",
    "scrollbar_handle": "rgba(255, 255, 255, 0.15)",
    "sidebar_hover_bg": "rgba(255, 255, 255, 0.05)",
    "status_bg": "rgba(22, 23, 28, 0.7)",
    "log_bg": "rgba(22, 23, 28, 0.7)",
    "btn_disabled_bg": "rgba(255, 255, 255, 0.06)",
    "btn_disabled_text": "#6a6a7a",
    "danger_hover_text": "#ffffff",
    "progress_chunk": "#ff4d5a",
}

LIGHT_BASE = {
    "name": "light",
    "bg_deepest": "#e8ecf2",
    "bg_primary": "#f6f8fc",
    "bg_secondary": "#eef0f6",
    "bg_card": "rgba(255, 255, 255, 0.75)",
    "bg_card_solid": "#ffffff",
    "bg_input": "rgba(255, 255, 255, 0.9)",
    "bg_sidebar": "rgba(240, 242, 248, 0.8)",
    "bg_table": "rgba(255, 255, 255, 0.4)",
    "bg_table_alt": "rgba(108, 178, 235, 0.05)",
    "bg_table_header": "rgba(255, 255, 255, 0.9)",
    "text_primary": "#1a1a2e",
    "text_secondary": "#4a4a5e",
    "text_muted": "#8a8a9e",
    "text_placeholder": "#b0b0c0",
    "accent_text": "#ffffff",
    "success": "#16a34a",
    "success_bg": "rgba(22, 163, 74, 0.12)",
    "error": "#dc2626",
    "error_bg": "rgba(220, 38, 38, 0.1)",
    "warning": "#d97706",
    "warning_bg": "rgba(217, 119, 6, 0.12)",
    "info": "#0284c7",
    "info_bg": "rgba(2, 132, 199, 0.1)",
    "border": "rgba(0, 0, 0, 0.06)",
    "border_glow": "rgba(0, 0, 0, 0.08)",
    "grid": "rgba(0, 0, 0, 0.08)",
    "scrollbar_bg": "transparent",
    "scrollbar_handle": "rgba(0, 0, 0, 0.12)",
    "sidebar_hover_bg": "rgba(0, 0, 0, 0.04)",
    "status_bg": "rgba(240, 242, 248, 0.7)",
    "log_bg": "rgba(240, 242, 248, 0.7)",
    "btn_disabled_bg": "rgba(0, 0, 0, 0.06)",
    "btn_disabled_text": "#b0b0c0",
    "danger_hover_text": "#ffffff",
    "progress_chunk": "#6cb2eb",
}


class ThemeManager(QObject):
    theme_changed = Signal(str)

    def __init__(self):
        super().__init__()
        config = load_config()
        self._current_theme = config.get("theme", "dark")
        self._custom_accent_dark = config.get("custom_accent_dark", "")
        self._custom_accent_light = config.get("custom_accent_light", "")
        self._avatar_dark = config.get("avatar_dark", "")
        self._avatar_light = config.get("avatar_light", "")
        self._avatar_visible = config.get("avatar_visible", True)
        self._colors = self._build_colors(self._current_theme)

    def _build_colors(self, theme_name):
        base = dict(DARK_BASE if theme_name == "dark" else LIGHT_BASE)
        custom = self._custom_accent_dark if theme_name == "dark" else self._custom_accent_light
        hex_color = custom if custom else (DEFAULT_ACCENT_DARK if theme_name == "dark" else DEFAULT_ACCENT_LIGHT)
        accent = _derive_accent_colors(hex_color)
        base.update(accent)
        return base

    @property
    def current_theme(self):
        return self._current_theme

    @property
    def colors(self):
        return self._colors

    @property
    def avatar_visible(self):
        return self._avatar_visible

    @property
    def avatar_path(self):
        """获取当前主题的头像路径（优先用户自定义，其次内置默认）"""
        if self._current_theme == "dark":
            if self._avatar_dark and os.path.exists(self._avatar_dark):
                return self._avatar_dark
            if os.path.exists(AVATAR_DEFAULT_DARK):
                return AVATAR_DEFAULT_DARK
        else:
            if self._avatar_light and os.path.exists(self._avatar_light):
                return self._avatar_light
            if os.path.exists(AVATAR_DEFAULT_LIGHT):
                return AVATAR_DEFAULT_LIGHT
        return ""

    def get(self, key):
        return self._colors.get(key, "")

    def toggle(self):
        self._current_theme = "light" if self._current_theme == "dark" else "dark"
        self._colors = self._build_colors(self._current_theme)
        set_config("theme", self._current_theme)
        self.theme_changed.emit(self._current_theme)

    def set_theme(self, theme_name):
        if theme_name in ("dark", "light") and theme_name != self._current_theme:
            self._current_theme = theme_name
            self._colors = self._build_colors(theme_name)
            set_config("theme", theme_name)
            self.theme_changed.emit(theme_name)

    def set_custom_accent(self, hex_color, theme_name=None):
        if theme_name is None:
            theme_name = self._current_theme
        if theme_name == "dark":
            self._custom_accent_dark = hex_color
            set_config("custom_accent_dark", hex_color)
        else:
            self._custom_accent_light = hex_color
            set_config("custom_accent_light", hex_color)
        if theme_name == self._current_theme:
            self._colors = self._build_colors(self._current_theme)
            self.theme_changed.emit(self._current_theme)

    def reset_accent(self, theme_name=None):
        if theme_name is None:
            theme_name = self._current_theme
        if theme_name == "dark":
            self._custom_accent_dark = ""
            set_config("custom_accent_dark", "")
        else:
            self._custom_accent_light = ""
            set_config("custom_accent_light", "")
        if theme_name == self._current_theme:
            self._colors = self._build_colors(self._current_theme)
            self.theme_changed.emit(self._current_theme)

    @property
    def custom_accent_dark(self):
        return self._custom_accent_dark or DEFAULT_ACCENT_DARK

    @property
    def custom_accent_light(self):
        return self._custom_accent_light or DEFAULT_ACCENT_LIGHT

    def set_avatar(self, path, theme_name=None):
        if theme_name is None:
            theme_name = self._current_theme
        if theme_name == "dark":
            self._avatar_dark = path
            set_config("avatar_dark", path)
        else:
            self._avatar_light = path
            set_config("avatar_light", path)

    def set_avatar_visible(self, visible):
        self._avatar_visible = visible
        set_config("avatar_visible", visible)

    def get_avatar_for_theme(self, theme_name):
        return self._avatar_dark if theme_name == "dark" else self._avatar_light


theme_manager = ThemeManager()