"""字幕 - 视频匹配模块
三阶段匹配:
  1. 精确名称匹配（剥离语言标签后）
  2. Diff 算法提取公共前缀/后缀匹配
  3. Episode 编号匹配（最稳健的兜底方案）
"""
from pathlib import Path
from core.parser import parse_filename


def _strip_subtitle_lang_tag(stem: str) -> str:
    """剥离字幕语言标签，如 .sc, .chs, .cht, .tc, .en, .ja 等"""
    import re
    # 匹配末尾的 .语言标签(可能带数字或连字符)
    return re.sub(r'[._-](sc|chs|cht|tc|en|ja|ko|fr|de|es|pt|ru|ar|hi|th|vi|id|ms|default|forced|sdh|hi|cc|简|繁|简体|繁體|chs_en|cht_en|jp_sc|jp_tc|sc_en|tc_en)$', '', stem, flags=re.IGNORECASE)


def match_subtitles_to_videos(video_files: list, subtitle_files: list):
    """将字幕文件匹配到对应的视频文件
    
    返回: list of (video_path, subtitle_path) 已匹配对
    """
    if not subtitle_files or not video_files:
        return []

    # 预处理：提取所有 stems
    video_stems = [vf.stem for vf in video_files]
    sub_stems = [sf.stem for sf in subtitle_files]
    sub_stems_clean = [_strip_subtitle_lang_tag(s) for s in sub_stems]

    # 构建视频 stem 查找表（小写）
    video_stems_lower = {}
    for vf, stem in zip(video_files, video_stems):
        video_stems_lower[stem.lower()] = vf

    matched_pairs = []
    used_videos = set()
    used_subs = set()

    # =============================================
    # 阶段 1: 精确名称匹配
    # =============================================
    for i, (sf, clean_stem) in enumerate(zip(subtitle_files, sub_stems_clean)):
        if clean_stem.lower() in video_stems_lower:
            matched_vf = video_stems_lower[clean_stem.lower()]
            matched_pairs.append((matched_vf, sf))
            used_videos.add(matched_vf)
            used_subs.add(i)

    # 收集剩余文件
    remaining_videos = [(vf, stem) for vf, stem in zip(video_files, video_stems) if vf not in used_videos]
    remaining_subs = [(i, sf, clean_stem) for i, (sf, clean_stem) in enumerate(zip(subtitle_files, sub_stems_clean)) if i not in used_subs]

    # =============================================
    # 阶段 2: Diff 算法匹配
    # =============================================
    if remaining_videos and remaining_subs:
        # 计算视频公共前缀/后缀
        rv_stems = [s for _, s in remaining_videos]
        common_prefix = _common_prefix(rv_stems)
        common_suffix = _common_suffix(rv_stems)

        # 视频的有效键
        video_keys = []
        for vf, s in remaining_videos:
            key = s[len(common_prefix):len(s) - len(common_suffix)].strip()
            video_keys.append((vf, key))

        # 字幕公共前缀/后缀
        rs_stems = [s for _, _, s in remaining_subs]
        sub_prefix = _common_prefix(rs_stems)
        sub_suffix = _common_suffix(rs_stems)

        sub_keys = []
        for i, sf, s in remaining_subs:
            key = s[len(sub_prefix):len(s) - len(sub_suffix)].strip()
            sub_keys.append((i, sf, key))

        # 匹配键
        for vf, vk in video_keys:
            if vf in used_videos:
                continue
            vk_lower = vk.lower()
            for (i, sf, sk) in sub_keys:
                if i in used_subs:
                    continue
                if sk.lower() == vk_lower:
                    matched_pairs.append((vf, sf))
                    used_videos.add(vf)
                    used_subs.add(i)
                    break

    # =============================================
    # 阶段 3: Episode 编号匹配（兜底）
    # =============================================
    remaining_videos_2 = [(vf, stem) for vf, stem in zip(video_files, video_stems) if vf not in used_videos]
    remaining_subs_2 = [(i, sf, stem) for i, (sf, stem) in enumerate(zip(subtitle_files, sub_stems)) if i not in used_subs]

    if remaining_videos_2 and remaining_subs_2:
        # 解析所有剩余文件的 episode 信息
        video_episodes = {}
        for vf, stem in remaining_videos_2:
            info = parse_filename(stem)
            if info:
                ep_key = (info.season, info.episode, info.episode_end)
                if ep_key and ep_key[1] is not None:
                    video_episodes[ep_key] = vf

        sub_episodes = []
        for i, sf, stem in remaining_subs_2:
            info = parse_filename(stem)
            if info:
                ep_key = (info.season, info.episode, info.episode_end)
                if ep_key and ep_key[1] is not None:
                    sub_episodes.append((i, sf, ep_key))

        # 匹配
        for i, sf, ep_key in sub_episodes:
            if ep_key in video_episodes:
                vf = video_episodes[ep_key]
                matched_pairs.append((vf, sf))
                used_videos.add(vf)
                used_subs.add(i)

    return matched_pairs


def _common_prefix(strings: list) -> str:
    """计算字符串列表的公共前缀"""
    if not strings:
        return ""
    result = strings[0]
    for s in strings[1:]:
        while not s.lower().startswith(result.lower()) and result:
            result = result[:-1]
    return result


def _common_suffix(strings: list) -> str:
    """计算字符串列表的公共后缀"""
    if not strings:
        return ""
    result = strings[0]
    for s in strings[1:]:
        while not s.lower().endswith(result.lower()) and result:
            result = result[1:]
    return result