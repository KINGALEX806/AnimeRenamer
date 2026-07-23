"""重命名引擎 - 生成新文件名并执行重命名/移动/复制/硬链接/符号链接"""
import os
import re
import shutil
from pathlib import Path
from core.parser import ParsedInfo, get_season_episode_str
from utils.config import load_config


class RenameItem:
    """重命名项目"""
    def __init__(self, **kwargs):
        self.media_file = kwargs.get("media_file")       # MediaFile 对象
        self.parsed_info = kwargs.get("parsed_info")     # ParsedInfo 对象
        self.anime_info = kwargs.get("anime_info")       # AnimeInfo 对象
        self.old_path = kwargs.get("old_path") or kwargs.get("file_path")  # 原文件路径
        self.new_path = kwargs.get("new_path")            # 新文件路径
        self.old_name = kwargs.get("old_name", "")        # 原文件名
        self.new_name = kwargs.get("new_name", "")        # 新文件名
        self.status = kwargs.get("status", "pending")     # pending, ready, done, failed, conflict
        self.error_msg = kwargs.get("error_msg", "")      # 错误信息
        self.is_subtitle_match = kwargs.get("is_subtitle_match", False)  # 是否字幕匹配

    def __repr__(self):
        return f"RenameItem({self.old_name} -> {self.new_name})"


class RenameEngine:
    """重命名引擎"""

    def __init__(self, log_callback=None):
        self.log_callback = log_callback
        self.rename_items = []

    def _log(self, msg):
        if self.log_callback:
            self.log_callback(msg)

    def generate_new_names(self, parsed_infos, anime_infos, media_files):
        """根据解析结果和番剧信息生成新文件名"""
        self.rename_items = []
        config = load_rename_config()

        for mf, parsed in zip(media_files, parsed_infos):
            item = RenameItem()
            item.media_file = mf
            item.parsed_info = parsed
            item.old_path = mf.path
            item.old_name = mf.filename

            # 获取番剧信息
            cache_key = f"{parsed.show_title}_{parsed.year}"
            anime_info = anime_infos.get(cache_key)
            item.anime_info = anime_info

            # 获取最佳标题
            if anime_info and anime_info.title:
                show_title = anime_info.get_best_title(config.get("language", "zh-CN"))
            else:
                show_title = parsed.show_title

            # 获取集标题（按用户选择的语言）
            ep_lang = config.get("episode_title_language", "cn")
            episode_title = ""
            if anime_info:
                episode_title = anime_info.get_episode_title(parsed.episode, ep_lang)

            parsed.episode_title = episode_title

            # 生成新文件名
            new_name = self._build_filename(parsed, show_title, episode_title, config, mf)
            item.new_name = new_name
            item.new_path = mf.path.parent / new_name
            item.status = "ready"

            # 检查冲突
            if item.new_path.exists() and item.new_path != item.old_path:
                item.status = "conflict"
                item.error_msg = "目标文件已存在"

            self.rename_items.append(item)

        self._log(f"已生成 {len(self.rename_items)} 个重命名方案")
        return self.rename_items

    def _build_filename(self, parsed, show_title, episode_title, config, mf):
        """构建新文件名"""
        se_format = config.get("season_episode_format", "sXXeYY")
        se_str = get_season_episode_str(parsed, fmt=se_format)

        # 基础命名模板
        template = config.get("naming_template", "{title} - {season_episode} {episode_title}")

        base_name = template.replace("{title}", show_title)
        base_name = base_name.replace("{season_episode}", se_str)
        base_name = base_name.replace("{episode_title}", episode_title)
        base_name = base_name.replace("{group}", parsed.release_group or "")
        base_name = base_name.replace("{resolution}", parsed.resolution or "")
        base_name = base_name.replace("{source}", parsed.source_type or "")
        base_name = base_name.replace("{video_codec}", parsed.video_codec or "")
        base_name = base_name.replace("{audio_codec}", parsed.audio_codec or "")
        base_name = base_name.replace("{year}", str(parsed.year) if parsed.year else "")
        base_name = base_name.replace("{video_info}", parsed.video_info or "")
        base_name = base_name.replace("{audio_info}", parsed.audio_info or "")
        base_name = re.sub(r'\s+', ' ', base_name).strip()
        base_name = re.sub(r'\s*-\s*$', '', base_name)
        # 清理空的方括号/圆括号
        base_name = re.sub(r'\[\s*\]', '', base_name)
        base_name = re.sub(r'\(\s*\)', '', base_name)
        base_name = re.sub(r'\s+', ' ', base_name).strip()

        # 处理附加信息
        parts = []

        # 视频信息
        if config.get("keep_encoding_info", True) and parsed.video_info:
            parts.append(parsed.video_info)

        # 音频信息
        if config.get("keep_audio_info", True) and parsed.audio_info:
            parts.append(parsed.audio_info)

        # 发布组
        if config.get("keep_release_group", True) and parsed.release_group:
            parts.append(parsed.release_group)

        # 语言标识
        if config.get("keep_language_tag", True) and parsed.language_tag:
            parts.append(parsed.language_tag)

        # 额外标签（未分类的）
        for tag in parsed.extra_tags:
            if config.get("keep_encoding_info", True) and any(
                kw in tag.lower() for kw in ['1080p', '720p', '4k', '2160p', 'bd', 'web', 'remux', 'avc', 'hevc', 'x265', 'x264', '10bit', '8bit', 'flac', 'aac']):
                parts.append(tag)

        if parts:
            base_name = f"{base_name} {' '.join(parts)}"

        # 添加扩展名
        new_name = f"{base_name}{mf.extension}"

        # 清理文件名中的非法字符
        new_name = self._sanitize_filename(new_name)

        return new_name

    def _sanitize_filename(self, filename):
        """清理文件名中的非法字符"""
        name, ext = os.path.splitext(filename)
        # 替换斜杠为空格（常见于 Fate/strange 这类标题）
        name = name.replace('/', ' ')
        name = name.replace('\\', ' ')
        # 移除 Windows 文件名非法字符
        name = re.sub(r'[<>:"|?*]', '', name)
        name = re.sub(r'\s+', ' ', name).strip()
        return f"{name}{ext}"

    def execute_rename(self, items, dry_run=False, mode="rename"):
        """执行操作（重命名/移动/复制/硬链接/符号链接）
        
        Args:
            items: RenameItem 列表
            dry_run: 预览模式
            mode: "rename" | "move" | "copy" | "hardlink" | "symlink"
        """
        results = {"success": 0, "failed": 0, "skipped": 0, "conflicts": 0}
        mode_labels = {
            "rename": "重命名",
            "move": "移动",
            "copy": "复制",
            "hardlink": "硬链接",
            "symlink": "符号链接",
        }
        mode_label = mode_labels.get(mode, "操作")

        for item in items:
            # 如果 new_path 未设置，从 old_path 和 new_name 构建
            if item.new_path is None and item.old_path and item.new_name:
                item.new_path = Path(item.old_path).parent / item.new_name

            if item.status == "conflict":
                results["conflicts"] += 1
                self._log(f"冲突: {item.old_name} -> {item.new_name}")
                continue

            if item.status == "done":
                results["skipped"] += 1
                continue

            if dry_run:
                item.status = "ready"
                results["success"] += 1
                self._log(f"[预览] {item.old_name} -> {item.new_name}")
                continue

            try:
                old_path = Path(item.old_path) if not isinstance(item.old_path, Path) else item.old_path
                new_path = Path(item.new_path) if not isinstance(item.new_path, Path) else item.new_path

                # 如果目标已存在且不是同一个文件
                if new_path.exists() and new_path != old_path:
                    item.status = "conflict"
                    item.error_msg = "目标文件已存在"
                    results["conflicts"] += 1
                    self._log(f"冲突: {item.old_name} -> {item.new_name}")
                    continue

                if mode == "rename":
                    if new_path.parent != old_path.parent:
                        item.status = "failed"
                        item.error_msg = "不支持跨目录重命名"
                        results["failed"] += 1
                        continue
                    old_path.rename(new_path)
                    # 保存旧路径用于撤销
                    item._undo_old_path = str(old_path)
                    item._undo_new_path = str(new_path)

                elif mode == "move":
                    shutil.move(str(old_path), str(new_path))
                    item._undo_old_path = str(old_path)
                    item._undo_new_path = str(new_path)

                elif mode == "copy":
                    shutil.copy2(str(old_path), str(new_path))
                    # 复制模式不改变原文件，无需撤销

                elif mode == "hardlink":
                    if new_path.exists():
                        new_path.unlink()
                    os.link(str(old_path), str(new_path))
                    item._undo_old_path = str(old_path)
                    item._undo_new_path = str(new_path)

                elif mode == "symlink":
                    if new_path.exists():
                        new_path.unlink()
                    os.symlink(str(old_path), str(new_path))
                    item._undo_old_path = str(old_path)
                    item._undo_new_path = str(new_path)

                item.status = "done"
                results["success"] += 1
                self._log(f"{mode_label}: {item.old_name} -> {item.new_name}")

            except Exception as e:
                item.status = "failed"
                item.error_msg = str(e)
                results["failed"] += 1
                self._log(f"失败: {item.old_name} - {e}")

        self._log(f"完成: 成功 {results['success']}, 失败 {results['failed']}, "
                  f"跳过 {results['skipped']}, 冲突 {results['conflicts']}")
        return results

    def undo_rename(self, items):
        """撤销最近操作（支持 rename/move/hardlink/symlink，copy 不支持撤销）"""
        results = {"success": 0, "failed": 0}

        for item in items:
            if item.status != "done":
                continue

            try:
                undo_old = getattr(item, '_undo_old_path', None)
                undo_new = getattr(item, '_undo_new_path', None)

                if undo_old and undo_new:
                    old_path = Path(undo_old)
                    new_path = Path(undo_new)
                    if new_path.exists():
                        new_path.rename(old_path)
                        self._log(f"撤销: {Path(new_path).name} -> {Path(old_path).name}")
                    elif old_path.exists():
                        # 文件可能已经被移回，跳过
                        self._log(f"撤销跳过: {old_path} 已存在")
                    else:
                        results["failed"] += 1
                        self._log(f"撤销失败: 源文件和目标文件都不存在")
                        continue
                    item.status = "ready"
                    item.new_name = item.old_name
                    results["success"] += 1
                elif item.new_path and item.old_path:
                    # 旧版回退：将 new_path 重命名为 old_path
                    new_p = Path(item.new_path) if isinstance(item.new_path, str) else item.new_path
                    old_p = Path(item.old_path) if isinstance(item.old_path, str) else item.old_path
                    if new_p.exists():
                        new_p.rename(old_p)
                        item.status = "ready"
                        item.new_name = item.old_name
                        results["success"] += 1
                        self._log(f"撤销: {new_p.name} -> {old_p.name}")
                    else:
                        results["failed"] += 1
                        self._log(f"撤销失败: {new_p} 不存在")
                else:
                    results["failed"] += 1
                    self._log(f"撤销失败: 缺少路径信息")

            except Exception as e:
                results["failed"] += 1
                self._log(f"撤销失败: {item.new_name} - {e}")

        return results

    def get_rename_preview(self):
        """获取重命名预览列表"""
        return [
            {
                "old_name": item.old_name,
                "new_name": item.new_name,
                "status": item.status,
                "error": item.error_msg,
            }
            for item in self.rename_items
        ]


def load_rename_config():
    """加载重命名配置"""
    config = load_config()
    return {
        "naming_template": config.get("naming_template", "{title} - {season_episode} {episode_title}"),
        "keep_release_group": config.get("keep_release_group", True),
        "keep_encoding_info": config.get("keep_encoding_info", True),
        "keep_audio_info": config.get("keep_audio_info", True),
        "keep_language_tag": config.get("keep_language_tag", True),
        "language": config.get("language", "zh-CN"),
        "season_episode_format": config.get("season_episode_format", "sXXeYY"),
        "title_source": config.get("title_source", "cn"),
    }