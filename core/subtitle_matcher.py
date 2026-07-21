"""SubRenamer 风格字幕-视频匹配算法

参考 https://github.com/qwqcode/SubRenamer 的核心算法实现：
1. 自动 Diff 算法：提取公共前缀/后缀，计算集数 Key
2. 同名优先：完全相同的文件名（去扩展名）直接匹配
3. 一对多映射：同一 Key 下，一个视频可匹配多个字幕
4. 自然排序：数字部分按数值排序
"""
import re
import unicodedata
from pathlib import Path


def normalize_filename(name):
    """Unicode NFKC 规范化"""
    return unicodedata.normalize("NFKC", name)


def _strip_subtitle_lang_tag(stem):
    """去除字幕语言标签后缀，如 .sc / .tc / .chs&jp / .CHS 等"""
    return re.sub(
        r'\.(sc|tc|chs|cht|ch|en|jp|jap|eng|chi|zh)(\s*[&+]\s*(jp|jap|en|eng|cht|chs|tc|sc))*$',
        '', stem, flags=re.IGNORECASE
    )


def match_subtitles_to_videos(video_files, subtitle_files):
    """将字幕文件匹配到视频文件

    Args:
        video_files: MediaFile 列表 (type='video')
        subtitle_files: MediaFile 列表 (type='subtitle')

    Returns:
        list of (video_mediafile, subtitle_mediafile) 匹配对
    """
    if not video_files or not subtitle_files:
        return []

    # 1对1快速路径
    if len(video_files) == 1 and len(subtitle_files) == 1:
        return [(video_files[0], subtitle_files[0])]

    # 提取文件名（去扩展名、规范化）
    video_stems = [normalize_filename(vf.stem) for vf in video_files]
    sub_stems = [normalize_filename(sf.stem) for sf in subtitle_files]

    # 去除字幕语言标签后缀，用于匹配
    sub_stems_clean = [_strip_subtitle_lang_tag(s) for s in sub_stems]

    # 分离已精确匹配的
    matched_pairs = []
    remaining_videos = []
    remaining_subs = []

    # 同名优先匹配（使用 clean stem）
    video_stems_lower = {s.lower(): vf for s, vf in zip(video_stems, video_files)}
    for sf, stem, clean_stem in zip(subtitle_files, sub_stems, sub_stems_clean):
        if clean_stem.lower() in video_stems_lower:
            matched_vf = video_stems_lower[clean_stem.lower()]
            matched_pairs.append((matched_vf, sf))
        else:
            remaining_subs.append((sf, clean_stem))

    for vf, stem in zip(video_files, video_stems):
        if stem.lower() not in {s.lower() for _, s in remaining_subs}:
            if vf not in [p[0] for p in matched_pairs]:
                remaining_videos.append((vf, stem))

    # 如果剩余的都匹配完了，直接返回
    if not remaining_videos or not remaining_subs:
        return matched_pairs

    # 计算 Key（Diff 算法）
    video_keys = _calculate_keys([stem for _, stem in remaining_videos])
    sub_keys = _calculate_keys([stem for _, stem in remaining_subs])

    # 按 Key 匹配
    for (vf, v_stem), v_key in zip(remaining_videos, video_keys):
        for (sf, s_stem), s_key in zip(remaining_subs, sub_keys):
            if v_key and s_key and v_key == s_key:
                matched_pairs.append((vf, sf))
                break

    return matched_pairs


def _calculate_keys(stems):
    """计算文件名 Key（集数标识符）

    使用 SubRenamer 的 Diff 算法提取每个文件的集数标识符。
    """
    n = len(stems)
    if n < 2:
        return [_fallback_key(stems[0])] if stems else []

    # 计算公共前缀和后缀
    prefix, suffix = _get_diff(stems)

    # 构建正则并提取 Key
    keys = []
    for stem in stems:
        key = _extract_key(stem, prefix, suffix)
        keys.append(_patch_key(key))

    return keys


def _get_diff(stems):
    """计算公共前缀和后缀

    从列表两端取文件名进行 Diff，选择差异最大的文件对。
    """
    n = len(stems)
    if n < 2:
        return "", ""

    # 从两端取：第一个和最后一个
    first = stems[0].lower()
    last = stems[-1].lower()

    # 找公共前缀（去掉末尾数字）
    prefix = _find_common_prefix(first, last)
    if prefix:
        prefix = re.sub(r"\d+$", "", prefix)

    # 找公共后缀
    suffix = ""
    if prefix:
        # 从前缀之后开始找
        start = len(prefix)
        suffix = _find_common_suffix(first[start:], last[start:])

    return prefix, suffix


def _find_common_prefix(a, b):
    """找最长公共前缀（大小写不敏感）"""
    min_len = min(len(a), len(b))
    i = 0
    while i < min_len and a[i].lower() == b[i].lower():
        i += 1
    return a[:i]


def _find_common_suffix(a, b):
    """找公共后缀

    白名单：只有非 ASCII 字母数字的字符才能作为后缀。
    跳过 ASCII 字母和数字，因为它们可能是集数 Key 的一部分。
    """
    a_len = len(a)
    b_len = len(b)
    result = []
    a_idx = a_len - 1
    b_idx = b_len - 1

    while a_idx >= 0 and b_idx >= 0:
        if a[a_idx].lower() == b[b_idx].lower():
            ch = a[a_idx]
            # 白名单：非 ASCII 字母数字，或空格
            if not ch.isascii() or not ch.isalnum() or ch == ' ':
                result.insert(0, ch)
                a_idx -= 1
                b_idx -= 1
            else:
                break
        else:
            break

    return ''.join(result)


def _extract_key(stem, prefix, suffix):
    """根据 Diff 结果提取 Key"""
    if not prefix:
        return _fallback_key(stem)

    # 构建正则
    escaped_prefix = re.escape(prefix)
    if suffix:
        escaped_suffix = re.escape(suffix)
        pattern = f"{escaped_prefix}(.+?){escaped_suffix}"
    else:
        pattern = f"{escaped_prefix}(\\d+)"

    m = re.search(pattern, stem, re.IGNORECASE)
    if m:
        return m.group(1)
    return _fallback_key(stem)


def _fallback_key(stem):
    """回退：匹配最后一个数字"""
    m = re.search(r"(\d+)(?!.*\d)", stem)
    if m:
        return m.group(1)
    return ""


def _patch_key(key):
    """Key 规范化：纯数字去前导零"""
    if key and key.isdigit():
        return str(int(key))
    return key


def _natural_sort_key(s):
    """自然排序 key"""
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', s)]