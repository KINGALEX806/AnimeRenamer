"""文件名解析器 - 从文件名中提取番剧信息"""
import re


class ParsedInfo:
    """解析后的番剧信息"""
    def __init__(self):
        self.original_filename = ""
        self.show_title = ""          # 番剧标题
        self.season = 1               # 季数
        self.episode = 1              # 集数
        self.episode_end = None       # 多集结束编号
        self.episode_type = "TV"      # TV, OVA, SP, Movie
        self.episode_title = ""       # 本集标题（从网络获取）
        self.year = None              # 年份
        self.release_group = ""       # 发布组
        self.resolution = ""          # 分辨率：1080p, 720p, 4K, 2160p
        self.source_type = ""         # 片源：BDRip, WebRip, HDTV, DVDRip
        self.video_codec = ""         # 视频编码：x265, HEVC, AVC, x264
        self.audio_codec = ""         # 音频编码：FLAC, AAC, DTS, Opus
        self.video_info = ""          # 视频信息 (BD Remux 1080p AVC FLAC)
        self.audio_info = ""          # 音频信息 [Dual Audio]
        self.language_tag = ""        # 语言标识
        self.extra_tags = []          # 其他标签
        self.is_multi_episode = False # 是否多集文件
        self.confidence = 0.0         # 解析置信度
        self.se_pattern = "sXXeYY"    # 原始季集格式: sXXeYY, [##], EP##, - ##, ##, etc.

    def __repr__(self):
        return f"ParsedInfo({self.show_title} S{self.season:02d}E{self.episode:02d})"


# 视频/音频编码相关关键词
VIDEO_AUDIO_KW = [
    '1080p', '720p', '4k', '2160p', 'bd', 'bdrip', 'bdremux', 'remux',
    'web', 'web-dl', 'webrip', 'avc', 'hevc', 'x265', 'x264', 'h264',
    '10bit', '8bit', 'hdr', 'dv', 'hdr10', 'dolby vision',
    'flac', 'aac', 'dts', 'truehd', 'opus', 'ac3', 'eac3', 'dts-hd',
    'dual audio', 'multi audio', 'dual-audio', 'multi-audio',
]

# 发布组常见模式（全大写、短名称）
GROUP_PATTERN = re.compile(r'^[A-Z0-9][A-Za-z0-9&_-]{1,12}$')


def _is_video_audio_tag(tag):
    """判断是否是视频/音频标签"""
    tag_lower = tag.lower().replace('_', ' ').replace('-', ' ')
    for kw in VIDEO_AUDIO_KW:
        if kw in tag_lower:
            return True
    # 纯数字+字母组合，如 "1080p", "x265"
    if re.match(r'^\d{3,4}[pi]$', tag_lower):
        return True
    return False


def _is_likely_group(tag):
    """判断是否是发布组标签"""
    tag_stripped = tag.strip()
    # 短名称且全大写/首字母大写，如 "PMR", "VCB-Studio", "LoliHouse"
    if GROUP_PATTERN.match(tag_stripped):
        return True
    # 包含常见发布组特征
    if any(kw in tag_stripped.lower() for kw in ['subs', 'sub', 'encode', 'raws', 'fansub']):
        return True
    return False


def _is_episode_number(tag):
    """判断是否是纯集数标签"""
    # 纯数字 1-200
    if re.match(r'^\d{1,3}$', tag):
        n = int(tag)
        if 1 <= n <= 200:
            return True
    # 范围格式 01-02 或 01~02
    if re.match(r'^\d{1,3}[-~]\d{1,3}$', tag):
        return True
    return False


def parse_filename(filename):
    """解析文件名，提取番剧信息"""
    info = ParsedInfo()
    info.original_filename = filename

    original_name = filename

    # 去掉扩展名
    name = filename
    # 处理 .sc.ass / .tc.ass / .chs.ass / .cht.ass / .jp.ass / .en.ass 等字幕标签
    # 也处理 .CHS&JP.ass / .CHS.ass / .CHT.ass 等复杂格式
    name = re.sub(r'\.(sc|tc|chs|cht|ch|en|jp|jap|eng|chi|zh)(\s*[&+]\s*(jp|jap|en|eng|cht|chs|tc|sc))*\.(ass|ssa|srt|sub|vtt)$',
                  r'.\4', name, flags=re.IGNORECASE)

    for ext in ['.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.ts',
                '.ass', '.ssa', '.srt', '.sub', '.idx', '.sup', '.vtt']:
        if name.lower().endswith(ext):
            name = name[:-len(ext)]
            break

    # ====== 提取所有标签 ======
    # 提取所有方括号内容
    bracket_matches = list(re.finditer(r'\[([^\]]*)\]', name))
    bracket_tags = [(m.group(1), m.start(), m.end()) for m in bracket_matches]

    # 提取所有圆括号内容
    paren_matches = list(re.finditer(r'\(([^)]*)\)', name))
    paren_tags = [(m.group(1), m.start(), m.end()) for m in paren_matches]

    # 分类方括号标签
    for tag_text, start, end in bracket_tags:
        if _is_episode_number(tag_text):
            # 集数标签 - 后面处理
            pass
        elif _is_video_audio_tag(tag_text):
            tag_lower = tag_text.lower()
            if any(kw in tag_lower for kw in ['dual audio', 'multi audio', 'dual-audio', 'multi-audio']):
                info.audio_info = f"[{tag_text}]"
            else:
                info.extra_tags.append(f"[{tag_text}]")
        elif _is_likely_group(tag_text):
            if not info.release_group:
                info.release_group = f"[{tag_text}]"
            else:
                info.extra_tags.append(f"[{tag_text}]")
        else:
            # 可能是标题 - 暂存，后面处理
            pass

    # 分类圆括号标签
    for tag_text, start, end in paren_tags:
        if _is_video_audio_tag(tag_text):
            if not info.video_info:
                info.video_info = f"({tag_text})"
            else:
                info.extra_tags.append(f"({tag_text})")
        else:
            info.extra_tags.append(f"({tag_text})")

    # ====== 提取分辨率、片源、编码、音频 ======
    all_tags_text = " ".join([t for t, _, _ in bracket_tags + paren_tags]).lower()

    # 分辨率
    res_match = re.search(r'(?<!\d)(\d{3,4}[pi])\b', all_tags_text, re.IGNORECASE)
    if res_match:
        info.resolution = res_match.group(1)
    # 也检查 WxH 格式 (如 3840x2160, 1920x1080)
    if not info.resolution:
        res_match = re.search(r'(?<!\d)(\d{3,4})x(\d{3,4})\b', all_tags_text, re.IGNORECASE)
        if res_match:
            info.resolution = f"{res_match.group(2)}p"
    # 也检查 4K 等文字形式
    if not info.resolution:
        if re.search(r'\b4k\b', all_tags_text, re.IGNORECASE):
            info.resolution = "4K"

    # 片源
    source_order = ["bdremux", "bdrip", "bluray", "bd", "webrip", "web-dl", "webdl", "web", "hdtv", "hdrip", "dvdrip", "dvd"]
    source_display = {"bdremux": "BDRemux", "bdrip": "BDRip", "bluray": "BluRay", "bd": "BD",
                      "webrip": "WebRip", "web-dl": "WEB-DL", "webdl": "WEB-DL", "web": "WEB",
                      "hdtv": "HDTV", "hdrip": "HDRip", "dvdrip": "DVDRip", "dvd": "DVD"}
    for src in source_order:
        if src in all_tags_text:
            info.source_type = source_display.get(src, src.upper())
            break

    # 视频编码
    codec_order = ["x265", "hevc", "x264", "avc", "h265", "h264", "xvid"]
    for codec in codec_order:
        if codec in all_tags_text:
            info.video_codec = codec.upper() if codec in ["hevc", "avc", "xvid"] else codec
            break
    # 10bit 附加
    if "10bit" in all_tags_text or "10-bit" in all_tags_text:
        if info.video_codec:
            info.video_codec += " 10bit"

    # 音频编码
    audio_order = ["flac", "truehd", "dts-hd", "dts", "aac", "opus", "ac3", "eac3", "mp3"]
    for ac in audio_order:
        if ac in all_tags_text:
            info.audio_codec = ac.upper() if ac in ["flac", "aac", "dts", "dts-hd"] else ac
            break

    # ====== 提取季数集数 ======
    # 去掉所有标签后的文本
    clean_name = name
    for tag_text, start, end in bracket_tags:
        clean_name = clean_name.replace(f"[{tag_text}]", " ")
    for tag_text, start, end in paren_tags:
        clean_name = clean_name.replace(f"({tag_text})", " ")

    # 清理多余空白
    clean_name = re.sub(r'\s+', ' ', clean_name).strip()
    # 去除 .sc/.tc/.chs 等残留
    clean_name = re.sub(r'\.(sc|tc|chs|cht|ch|en|jp|jap|eng|chi|zh)(\s*[&+]\s*(jp|jap|en|eng|cht|chs|tc|sc))*$', '', clean_name, flags=re.IGNORECASE)

    season_found = False
    ep_found = False

    # 1. 尝试 S01E01 格式
    m = re.search(r'[Ss](\d{1,2})\s*[Ee](\d{1,3})(?:\s*[-~]\s*[Ee]?(\d{1,3}))?', clean_name)
    if m:
        info.season = int(m.group(1))
        info.episode = int(m.group(2))
        if m.group(3):
            info.episode_end = int(m.group(3))
            info.is_multi_episode = True
        info.confidence = 0.9
        season_found = True
        ep_found = True
        clean_name = clean_name[:m.start()].strip() + " " + clean_name[m.end():].strip()

    # 2. 尝试 EP01 格式
    if not ep_found:
        m = re.search(r'[Ee][Pp](\d{1,3})', clean_name)
        if m:
            info.episode = int(m.group(1))
            info.confidence = 0.7
            ep_found = True
            clean_name = clean_name[:m.start()].strip() + " " + clean_name[m.end():].strip()

    # 3. 尝试 S2 格式（不带 E）- 用于识别季数
    if not season_found:
        m = re.search(r'(?:^|\s)[Ss](\d{1,2})(?:\s|$)', clean_name)
        if m:
            info.season = int(m.group(1))
            info.confidence = 0.8
            season_found = True
            clean_name = clean_name[:m.start()].strip() + " " + clean_name[m.end():].strip()

    # 4. 尝试纯数字集数（在剩余文本中）
    if not ep_found:
        # 优先匹配 " - 01" 格式
        m = re.search(r'[\s_-](\d{1,3})(?:\s*[-~]\s*(\d{1,3}))?(?:\s|$)', clean_name)
        if m:
            ep_num = int(m.group(1))
            if 1 <= ep_num <= 200 and ep_num not in [720, 1080, 480, 360, 2160]:
                info.episode = ep_num
                if m.group(2):
                    info.episode_end = int(m.group(2))
                    info.is_multi_episode = True
                info.confidence = 0.7
                ep_found = True
                clean_name = clean_name[:m.start()].strip() + " " + clean_name[m.end():].strip()

    # 5. 尝试从方括号标签中提取集数
    if not ep_found:
        for tag_text, start, end in bracket_tags:
            if _is_episode_number(tag_text):
                m = re.match(r'^(\d{1,3})(?:[-~](\d{1,3}))?$', tag_text)
                if m:
                    ep_num = int(m.group(1))
                    if 1 <= ep_num <= 200:
                        info.episode = ep_num
                        if m.group(2):
                            info.episode_end = int(m.group(2))
                            info.is_multi_episode = True
                        info.confidence = 0.6
                        ep_found = True
                        break

    # ====== 提取标题 ======
    # 从剩余文本中提取标题
    clean_name = re.sub(r'\s+', ' ', clean_name).strip()
    clean_name = re.sub(r'^[\s\-_\.]+', '', clean_name)
    clean_name = re.sub(r'[\s\-_\.]+$', '', clean_name)

    if clean_name and len(clean_name) > 1:
        info.show_title = clean_name
    else:
        # 如果 clean_name 为空，从方括号标签中提取标题
        release_group_name = info.release_group.strip("[]") if info.release_group else ""
        for tag_text, start, end in bracket_tags:
            if _is_episode_number(tag_text):
                continue
            if _is_video_audio_tag(tag_text):
                continue
            # 跳过已识别的发布组
            if release_group_name and tag_text == release_group_name:
                continue
            if len(tag_text) > 2:
                info.show_title = tag_text
                break

    # 如果还是没找到标题，使用文件名中的主要部分
    if not info.show_title:
        # 取第一个非标签、非集数的括号内容
        fallback = name
        for tag_text, _, _ in bracket_tags + paren_tags:
            if not _is_episode_number(tag_text) and not _is_video_audio_tag(tag_text):
                fallback = tag_text
                break
        info.show_title = _clean_title(fallback)

    # ====== 检测 OVA/SP/剧场版 ======
    name_lower = original_name.lower()
    if any(kw in name_lower for kw in ['ova', 'oad']):
        info.episode_type = "OVA"
    elif any(kw in name_lower for kw in ['special', ' sp ', '.sp.', '_sp_']):
        info.episode_type = "SP"
    elif any(kw in name_lower for kw in ['movie', '剧场版', '劇場版', 'gekijouban']):
        info.episode_type = "Movie"

    # ====== 提取年份 ======
    year_match = re.search(r'(?:^|\D)(\d{4})(?:\D|$)', name)
    if year_match:
        year = int(year_match.group(1))
        if 1960 <= year <= 2030:
            info.year = year

    # ====== 提取语言标识 ======
    lang_match = re.search(
        r'\[([^\]]*(?:Dual Audio|Multi Audio|ENG|JAP|CHI|CHS|CHT|JP|EN|SC|TC)[^\]]*)\]',
        original_name, re.IGNORECASE
    )
    if lang_match and not info.audio_info:
        info.language_tag = f"[{lang_match.group(1)}]"

    # 检测原始季集格式
    info.se_pattern = _detect_se_pattern(original_name, info)

    return info


def _detect_se_pattern(filename, info):
    """从原始文件名中检测季集格式"""
    # 去掉扩展名
    name = filename
    for ext in ['.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.ts',
                '.ass', '.ssa', '.srt', '.sub', '.idx', '.sup', '.vtt']:
        if name.lower().endswith(ext):
            name = name[:-len(ext)]
            break
    # 去掉字幕语言标签
    name = re.sub(r'\.(sc|tc|chs|cht|ch|en|jp|jap|eng|chi|zh)(\s*[&+]\s*(jp|jap|en|eng|cht|chs|tc|sc))*$',
                  '', name, flags=re.IGNORECASE)

    # 1. S01E01 格式
    if re.search(r'[Ss]\d{1,2}\s*[Ee]\d{1,3}', name):
        return "sXXeYY"

    # 2. [01] 方括号格式
    if re.search(r'\[\d{1,3}\]', name):
        return "[##]"

    # 3. #01 井号格式
    if re.search(r'#\d{1,3}', name):
        return "#01"

    # 4. EP01 格式
    if re.search(r'[Ee][Pp]\d{1,3}', name):
        return "EP01"

    # 5. 第01话 / 第01集 格式
    if re.search(r'第\d{1,3}[话話集]', name):
        return "第01话"

    # 6.  - 01 破折号格式
    if re.search(r'\s-\s\d{1,3}', name):
        return " - 01"

    # 7. 纯数字 01 格式
    if re.search(r'(?:^|\s)\d{1,3}(?:\s|$)', name):
        return "01"

    # 默认
    return "sXXeYY"


def _clean_title(title):
    """清理番剧标题"""
    if not title:
        return ""
    title = re.sub(r'^[\s\-_\.\[\]【】]+', '', title)
    title = re.sub(r'[\s\-_\.\[\]【】]+$', '', title)
    title = re.sub(r'\s+', ' ', title).strip()
    return title


def get_season_episode_str(info, fmt="sXXeYY"):
    """获取季数集数字符串
    fmt: "sXXeYY" (S01E01), "number" (01), "auto" (根据原始文件格式)
    """
    if info.episode_type == "Movie":
        return f"({info.year})" if info.year else "(Movie)"
    elif info.episode_type in ("OVA", "SP"):
        if fmt == "number":
            return f"{info.episode_type}{info.episode:02d}"
        if fmt == "auto":
            fmt = info.se_pattern if hasattr(info, 'se_pattern') else "sXXeYY"
        return f"{info.episode_type}{info.episode:02d}"
    else:
        # 自动模式：使用原始文件检测到的格式
        if fmt == "auto":
            fmt = info.se_pattern if hasattr(info, 'se_pattern') else "sXXeYY"

        if fmt == "number" or fmt == "01":
            if info.is_multi_episode and info.episode_end:
                return f"{info.episode:02d}-{info.episode_end:02d}"
            return f"{info.episode:02d}"
        elif fmt == "[##]":
            if info.is_multi_episode and info.episode_end:
                return f"[{info.episode:02d}-{info.episode_end:02d}]"
            return f"[{info.episode:02d}]"
        elif fmt == "#01":
            if info.is_multi_episode and info.episode_end:
                return f"#{info.episode:02d}-{info.episode_end:02d}"
            return f"#{info.episode:02d}"
        elif fmt == "EP01":
            if info.is_multi_episode and info.episode_end:
                return f"EP{info.episode:02d}-{info.episode_end:02d}"
            return f"EP{info.episode:02d}"
        elif fmt == " - 01":
            if info.is_multi_episode and info.episode_end:
                return f" - {info.episode:02d}-{info.episode_end:02d}"
            return f" - {info.episode:02d}"
        elif fmt == "第01话":
            if info.is_multi_episode and info.episode_end:
                return f"第{info.episode:02d}-{info.episode_end:02d}话"
            return f"第{info.episode:02d}话"
        else:
            # sXXeYY 默认
            if info.is_multi_episode and info.episode_end:
                return f"S{info.season:02d}E{info.episode:02d}-E{info.episode_end:02d}"
            return f"S{info.season:02d}E{info.episode:02d}"