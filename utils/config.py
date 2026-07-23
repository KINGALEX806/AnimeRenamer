"""配置管理模块"""
import json
import os
from pathlib import Path

CONFIG_DIR = Path(os.path.expanduser("~")) / ".anime_renamer"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "theme": "dark",
    "naming_template": "{title} - {season_episode} {episode_title}",
    "sync_subtitle": True,
    "remove_sc_tag": True,
    "keep_release_group": True,
    "keep_encoding_info": True,
    "keep_audio_info": True,
    "keep_language_tag": True,
    "custom_remove_keywords": [],
    "custom_keep_keywords": [],
    "tmdb_api_key": "1f54bd990f1cdfb230adb312546d765d",
    "language": "zh-CN",
    "db_primary": "bangumi",
    "db_auto_fallback": True,
    "db_order": ["bangumi", "anilist", "themoviedb", "jikan", "tvmaze", "anidb", "thetvdb", "imdb"],
    "db_enabled": {
        "bangumi": True,
        "anilist": True,
        "themoviedb": True,
        "jikan": True,
        "tvmaze": True,
        "thetvdb": False,
        "imdb": True,
        "anidb": True,
    },
    "episode_title_language": "cn",
    "title_source": "cn",
    "season_episode_format": "auto",
    "video_extensions": [".mkv", ".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".ts"],
    "subtitle_extensions": [".ass", ".ssa", ".srt", ".sub", ".idx", ".sup", ".vtt"],
    "custom_video_extensions": "",
    "custom_subtitle_extensions": "",
    "sidebar_width": 240,
    "column_widths": [70, 84, 84, 400, 300],
    "operation_mode": "rename",
    "undo_history": [],
    "use_absolute_episode": False,
    "absolute_episode_offset": 0,
}

def get_config_dir():
    """获取配置目录"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR

def load_config():
    """加载配置"""
    get_config_dir()
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
            # 合并默认配置
            merged = DEFAULT_CONFIG.copy()
            merged.update(config)
            return merged
        except Exception:
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()

def save_config(config):
    """保存配置"""
    get_config_dir()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def get_config(key, default=None):
    """获取单个配置项"""
    config = load_config()
    return config.get(key, default)

def set_config(key, value):
    """设置单个配置项"""
    config = load_config()
    config[key] = value
    save_config(config)