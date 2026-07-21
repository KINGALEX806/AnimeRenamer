"""文件扫描器 - 扫描文件夹中的视频和字幕文件"""
import os
from pathlib import Path
from utils.config import load_config


class MediaFile:
    """媒体文件信息"""
    def __init__(self, path: Path, file_type: str):
        self.path = path
        self.filename = path.name
        self.stem = path.stem
        self.extension = path.suffix.lower()
        self.file_type = file_type  # 'video' or 'subtitle'
        self.size = path.stat().st_size if path.exists() else 0

    def __repr__(self):
        return f"MediaFile({self.filename}, {self.file_type})"


class ScanResult:
    """扫描结果"""
    def __init__(self):
        self.videos = []
        self.subtitles = []
        self.folder_path = None
        self.total_files = 0

    @property
    def all_files(self):
        return self.videos + self.subtitles


def scan_folder(folder_path, progress_callback=None):
    """扫描文件夹，返回视频和字幕文件列表"""
    result = ScanResult()
    result.folder_path = Path(folder_path)

    if not result.folder_path.exists():
        return result

    config = load_config()
    video_exts = set(config.get("video_extensions", [".mkv", ".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".ts"]))
    subtitle_exts = set(config.get("subtitle_extensions", [".ass", ".ssa", ".srt", ".sub", ".idx", ".sup", ".vtt"]))

    # 合并用户自定义扩展名
    custom_video = config.get("custom_video_extensions", "")
    if custom_video:
        for ext in custom_video.replace(",", " ").replace(";", " ").split():
            ext = ext.strip().lower()
            if ext and not ext.startswith("."):
                ext = "." + ext
            if ext:
                video_exts.add(ext)

    custom_sub = config.get("custom_subtitle_extensions", "")
    if custom_sub:
        for ext in custom_sub.replace(",", " ").replace(";", " ").split():
            ext = ext.strip().lower()
            if ext and not ext.startswith("."):
                ext = "." + ext
            if ext:
                subtitle_exts.add(ext)

    all_files = list(result.folder_path.iterdir())
    result.total_files = len(all_files)

    for i, file_path in enumerate(all_files):
        if file_path.is_file():
            ext = file_path.suffix.lower()
            if ext in video_exts:
                result.videos.append(MediaFile(file_path, "video"))
            elif ext in subtitle_exts:
                result.subtitles.append(MediaFile(file_path, "subtitle"))

        if progress_callback:
            progress_callback(i + 1, result.total_files)

    # 按文件名排序
    result.videos.sort(key=lambda x: x.filename.lower())
    result.subtitles.sort(key=lambda x: x.filename.lower())

    return result


def scan_multiple_folders(folder_paths, progress_callback=None):
    """扫描多个文件夹"""
    all_results = []
    for folder in folder_paths:
        result = scan_folder(folder, progress_callback)
        all_results.append(result)
    return all_results