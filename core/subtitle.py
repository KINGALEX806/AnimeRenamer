"""字幕匹配模块 - 将字幕文件与视频文件匹配"""
import re
from pathlib import Path
from utils.config import load_config


class SubtitleMatcher:
    """字幕匹配器"""

    def __init__(self, log_callback=None):
        self.log_callback = log_callback
        self.matches = []  # [(video_item, subtitle_item)]

    def _log(self, msg):
        if self.log_callback:
            self.log_callback(msg)

    def match(self, video_rename_items, subtitle_files):
        """将字幕文件匹配到视频重命名项"""
        self.matches = []

        # 按集数建立视频索引
        video_index = {}
        for item in video_rename_items:
            parsed = item.parsed_info
            if parsed and parsed.episode:
                key = (parsed.episode, parsed.season)
                if key not in video_index:
                    video_index[key] = []
                video_index[key].append(item)

        # 匹配字幕
        for sub in subtitle_files:
            sub_ep = self._extract_episode_from_filename(sub.filename)
            if sub_ep is None:
                self._log(f"无法识别字幕集数: {sub.filename}")
                continue

            # 尝试匹配
            matched = None
            for (ep, season), videos in video_index.items():
                if ep == sub_ep:
                    # 优先匹配集数相同的第一个未匹配视频
                    for v in videos:
                        already_matched = any(
                            m[1] == v for m in self.matches
                        )
                        if not already_matched:
                            matched = v
                            break
                    if matched:
                        break

            if matched:
                self.matches.append((matched, sub))
                self._log(f"字幕匹配: {sub.filename} -> {matched.old_name}")
            else:
                self._log(f"字幕未匹配: {sub.filename}")

        return self.matches

    def _extract_episode_from_filename(self, filename):
        """从字幕文件名提取集数"""
        name = filename

        # 去掉扩展名
        for ext in ['.ass', '.ssa', '.srt', '.sub', '.idx', '.sup', '.vtt']:
            if name.lower().endswith(ext):
                name = name[:-len(ext)]
                break

        # 尝试 S01E01 格式
        m = re.search(r'[Ss]\d{1,2}\s*[Ee](\d{1,3})', name)
        if m:
            return int(m.group(1))

        # 尝试 [01] 格式
        m = re.search(r'\[(\d{1,3})\]', name)
        if m:
            ep = int(m.group(1))
            if ep <= 200:
                return ep

        # 尝试纯数字
        m = re.search(r'[\s_-](\d{1,2})(?:\s|$|\.)', name)
        if m:
            ep = int(m.group(1))
            if ep <= 200:
                return ep

        # 尝试 EP01
        m = re.search(r'[Ee][Pp](\d{1,3})', name)
        if m:
            return int(m.group(1))

        return None

    def generate_subtitle_new_name(self, sub_file, matched_video, config=None):
        """为字幕生成新文件名"""
        if config is None:
            config = load_config()

        if not config.get("sync_subtitle", True):
            return sub_file.filename

        # 基于匹配到的视频的新文件名
        video_new_name = matched_video.new_name
        video_new_stem = Path(video_new_name).stem

        # 处理字幕扩展名
        sub_ext = sub_file.extension

        # 去除 .sc 标签
        if config.get("remove_sc_tag", True):
            sub_ext = re.sub(r'\.sc\.', '.', sub_ext)
            # 处理文件名中的 .sc
            if '.sc.' in sub_file.stem:
                video_new_stem = video_new_stem.replace('.sc', '')

        new_name = f"{video_new_stem}{sub_ext}"

        return new_name

    def process_subtitles(self, video_rename_items, subtitle_files, rename_engine):
        """处理字幕：匹配并生成重命名项"""
        self.match(video_rename_items, subtitle_files)

        config = load_config()
        subtitle_items = []

        for video_item, sub_file in self.matches:
            item = type('RenameItem', (), {})()
            item.media_file = sub_file
            item.parsed_info = video_item.parsed_info
            item.anime_info = video_item.anime_info
            item.old_path = sub_file.path
            item.old_name = sub_file.filename
            item.new_name = self.generate_subtitle_new_name(sub_file, video_item, config)
            item.new_path = sub_file.path.parent / item.new_name
            item.status = "ready"
            item.error_msg = ""
            item.is_subtitle_match = True

            # 检查冲突
            if item.new_path.exists() and item.new_path != item.old_path:
                item.status = "conflict"
                item.error_msg = "目标文件已存在"

            subtitle_items.append(item)

        rename_engine.rename_items.extend(subtitle_items)
        self._log(f"字幕处理完成: {len(subtitle_items)} 个字幕匹配")
        return subtitle_items