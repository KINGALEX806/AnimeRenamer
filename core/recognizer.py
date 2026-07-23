"""番剧识别器 - 多数据库番剧识别，支持 Bangumi / AniList / TMDB / Jikan

优先级顺序（可配置）:
  1. Bangumi  - https://api.bgm.tv/
  2. AniList  - https://graphql.anilist.co
  3. TMDB     - https://api.themoviedb.org/3
  4. Jikan    - https://api.jikan.moe/v4 (MyAnimeList 非官方 API)

每个数据库的查询结果会缓存到本地 JSON 文件，避免重复请求。
"""
import re
import time
import json
import difflib
import requests

from core.cache import AnimeCache


# =============================================================================
# AnimeInfo - 番剧信息数据类
# =============================================================================

class AnimeInfo:
    """番剧信息

    Attributes:
        bangumi_id: Bangumi 条目 ID
        anilist_id: AniList 条目 ID
        tmdb_id:    TMDB 条目 ID
        mal_id:     MyAnimeList 条目 ID
        title:      主标题（优先中文，其次英文，最后原始标题）
        title_en:   英文标题
        title_zh:   中文标题
        title_jp:   日文标题
        title_romaji: 罗马字标题
        year:       播出年份
        season_number: 季号
        total_episodes: 总集数
        episode_titles: 集标题字典 {集号: 标题}  (兼容旧接口)
        episode_titles_cn: 中文集标题 {集号: 标题}
        episode_titles_jp: 日文集标题 {集号: 标题}
        episode_type: 类型: "TV" / "OVA" / "SP" / "Movie"
        overview:   简介
        source_db:  数据来源数据库名称
    """

    def __init__(self):
        self.bangumi_id = None
        self.anilist_id = None
        self.tmdb_id = None
        self.mal_id = None
        self.title = ""
        self.title_en = ""
        self.title_zh = ""
        self.title_jp = ""
        self.title_romaji = ""
        self.year = None
        self.season_number = 1
        self.total_episodes = 0
        self.episode_titles = {}      # {episode_number: title} (兼容)
        self.episode_titles_cn = {}   # {episode_number: 中文标题}
        self.episode_titles_jp = {}   # {episode_number: 日文标题}
        self.episode_type = "TV"
        self.overview = ""
        self.source_db = ""

    def get_best_title(self, lang="zh-CN"):
        """获取最佳标题"""
        if lang == "zh-CN" and self.title_zh:
            return self.title_zh
        if lang == "jp" and self.title_jp:
            return self.title_jp
        if self.title_en:
            return self.title_en
        if self.title_zh:
            return self.title_zh
        if self.title_romaji:
            return self.title_romaji
        return self.title

    def get_episode_title(self, episode_number, lang="cn"):
        """获取指定集数的标题

        Args:
            episode_number: 集号
            lang: "cn" 中文, "jp" 日文, "en" 英文

        Returns:
            集标题字符串，若不存在则返回空字符串
        """
        if lang == "jp" and self.episode_titles_jp:
            return self.episode_titles_jp.get(episode_number, "")
        if lang == "cn" and self.episode_titles_cn:
            return self.episode_titles_cn.get(episode_number, "")
        # 兼容旧 dict
        return self.episode_titles.get(episode_number, "") or \
               self.episode_titles_cn.get(episode_number, "") or \
               self.episode_titles_jp.get(episode_number, "")


# =============================================================================
# AnimeRecognizer - 多数据库番剧识别器
# =============================================================================

class AnimeRecognizer:
    """番剧识别器

    按优先级顺序查询多个数据库，获取番剧元数据和每集标题。
    查询结果通过 AnimeCache 缓存到本地，默认 7 天过期。

    用法:
        recognizer = AnimeRecognizer(
            config={"db_order": ["bangumi", "anilist", "tmdb", "jikan"]},
            progress_callback=lambda cur, total, msg: print(f"[{cur}/{total}] {msg}"),
            log_callback=lambda msg: print(msg),
        )
        anime_info = recognizer.recognize(parsed_info)
    """

    # ---- API 端点 ----
    BANGUMI_API = "https://api.bgm.tv"
    ANILIST_API = "https://graphql.anilist.co"
    TMDB_API = "https://api.themoviedb.org/3"
    JIKAN_API = "https://api.jikan.moe/v4"
    TVMAZE_API = "https://api.tvmaze.com"
    TVDB_API = "https://api4.thetvdb.com/v4"
    IMDB_API = "https://v2.sg.media-imdb.com"

    # ---- 默认 TMDB API Key（公开测试 Key，可能已失效，建议用户自行申请） ----
    DEFAULT_TMDB_KEY = "1f54bd990f1cdfb230adb312546d765d"

    # ---- 默认配置 ----
    DEFAULT_CONFIG = {
        "db_order": ["bangumi", "anilist", "tmdb", "themoviedb", "jikan", "tvmaze", "thetvdb", "anidb"],
        "db_enabled": {
            "bangumi": True,
            "anilist": True,
            "tmdb": True,
            "themoviedb": True,
            "jikan": True,
            "tvmaze": True,
            "thetvdb": True,
            "anidb": True,
        },
        "tmdb_api_key": DEFAULT_TMDB_KEY,
    }

    # ---- 数据库名称映射 ----
    DB_NAMES = {
        "bangumi": "Bangumi",
        "anilist": "AniList",
        "tmdb": "TMDB",
        "jikan": "Jikan (MyAnimeList)",
        "tvmaze": "TVMaze",
        "thetvdb": "TheTVDB",
        "anidb": "AniDB",
    }

    # ---- 罗马字 → 中文关键词映射（用于纯 ASCII 标题搜索不到时回退） ----
    ROMAJI_DICT = {
        "conan": "名侦探柯南",
        "detective conan": "名侦探柯南",
    }

    def __init__(self, config=None, progress_callback=None, log_callback=None):
        """初始化识别器

        Args:
            config: 配置字典，包含以下键:
                - db_order (list): 数据库查询优先级，如 ["bangumi","anilist","tmdb","jikan"]
                - db_enabled (dict): 各数据库启用状态，如 {"bangumi": True, ...}
                - tmdb_api_key (str): TMDB API 密钥
            progress_callback: 进度回调，签名 (current, total, message)
            log_callback: 日志回调，签名 (message)
        """
        self.progress_callback = progress_callback
        self.log_callback = log_callback

        # 合并配置
        merged = self.DEFAULT_CONFIG.copy()
        if config:
            merged["db_order"] = config.get("db_order", merged["db_order"])
            merged["db_enabled"] = config.get("db_enabled", merged["db_enabled"])
            merged["tmdb_api_key"] = config.get("tmdb_api_key", merged["tmdb_api_key"])
        self.config = merged

        # HTTP 会话
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "AnimeRenamer/1.0 (your@email.com)",
            "Accept": "application/json",
        })

        # 缓存（使用用户提供的 AnimeCache）
        self._cache = AnimeCache()

        # 上次 Jikan 请求时间（用于限速）
        self._jikan_last_request = 0

    # =========================================================================
    # 日志与进度
    # =========================================================================

    def _log(self, msg):
        """输出日志"""
        if self.log_callback:
            self.log_callback(msg)

    def _progress(self, current, total, msg=""):
        """更新进度"""
        if self.progress_callback:
            self.progress_callback(current, total, msg)

    # =========================================================================
    # 缓存辅助
    # =========================================================================

    def _cache_get(self, key):
        """读取缓存，记录命中/未命中日志"""
        data = self._cache.get(key)
        if data is not None:
            self._log(f"  [Cache] 命中: {key}")
        return data

    def _cache_set(self, key, data):
        """写入缓存"""
        self._cache.set(key, data)

    # =========================================================================
    # 主识别流程
    # =========================================================================

    def recognize(self, parsed_info, manual_keyword=None):
        """识别单个番剧信息

        按 db_order 指定的顺序依次尝试各数据库，首个成功匹配即返回。

        Args:
            parsed_info: ParsedInfo 对象，包含 show_title、season、year 等字段
            manual_keyword: 手动指定搜索关键词（覆盖自动提取的标题）

        Returns:
            AnimeInfo 对象，若所有数据库均未匹配则返回仅含解析标题的 AnimeInfo
        """
        title = manual_keyword or parsed_info.show_title
        year = parsed_info.year
        season = getattr(parsed_info, "season", 1)

        self._log(f"--- 开始识别: {title} (年份: {year or '未知'}, 季: {season}) ---")

        for db_name in self.config["db_order"]:
            if not self.config["db_enabled"].get(db_name, False):
                self._log(f"  {self.DB_NAMES.get(db_name, db_name)} 已禁用，跳过")
                continue

            self._log(f"  >>> 尝试 {self.DB_NAMES.get(db_name, db_name)} ...")

            result = None
            if db_name == "bangumi":
                result = self._search_bangumi(title, year)
            elif db_name == "anilist":
                result = self._search_anilist(title, year)
            elif db_name == "tmdb" or db_name == "themoviedb":
                result = self._search_tmdb(title, year)
            elif db_name == "jikan":
                result = self._search_jikan(title, year)
            elif db_name == "tvmaze":
                result = self._search_tvmaze(title, year)
            elif db_name == "thetvdb":
                result = self._search_thetvdb(title, year)
            elif db_name == "anidb":
                result = self._search_anidb(title, year)

            if result is None:
                self._log(f"  {self.DB_NAMES.get(db_name, db_name)} 未匹配")
                continue

            # 构建 AnimeInfo
            anime_info = self._build_anime_info(result, db_name)

            # 保留 parsed_info 中的季号
            anime_info.season_number = season

            # 获取每集标题
            self._log(f"  {self.DB_NAMES.get(db_name, db_name)} 匹配成功，获取剧集信息...")
            if db_name == "bangumi":
                self._fetch_bangumi_episodes(anime_info, season)
            elif db_name == "anilist":
                self._fetch_anilist_episodes(anime_info, season)
            elif db_name == "tmdb":
                self._fetch_tmdb_episodes(anime_info, season)
            elif db_name == "jikan":
                self._fetch_jikan_episodes(anime_info, season)

            self._log(f"--- 识别完成: {anime_info.title} (来源: {anime_info.source_db}) ---")
            return anime_info

        # 所有数据库均未匹配，使用原始标题
        self._log("  所有数据库均未匹配，使用原始标题")
        anime_info = AnimeInfo()
        anime_info.title = title
        anime_info.title_en = title
        anime_info.title_zh = title
        anime_info.season_number = season
        anime_info.source_db = "local"
        return anime_info

    def batch_recognize(self, parsed_infos, manual_keyword=None):
        """批量识别番剧

        按番剧标题分组，每组只调用一次 recognize，避免重复查询。

        Args:
            parsed_infos: ParsedInfo 对象列表
            manual_keyword: 手动指定搜索关键词（覆盖自动提取的标题）

        Returns:
            dict: {group_key: AnimeInfo}
        """
        results = {}

        if manual_keyword:
            # 手动关键词模式：所有文件使用同一个关键词
            self._log(f"--- 手动搜索关键词: {manual_keyword} ---")
            anime_info = self.recognize(parsed_infos[0], manual_keyword=manual_keyword)
            for info in parsed_infos:
                key = f"{info.show_title}_{info.year}"
                results[key] = anime_info
            return results

        # 按番剧标题分组
        groups = {}
        for info in parsed_infos:
            key = f"{info.show_title}_{info.year}"
            if key not in groups:
                groups[key] = []
            groups[key].append(info)

        total = len(groups)
        for i, (key, infos) in enumerate(groups.items()):
            self._progress(i + 1, total, f"识别番剧: {infos[0].show_title}")
            anime_info = self.recognize(infos[0])
            results[key] = anime_info

        return results

    def _build_anime_info(self, result, db_name):
        """从搜索结果字典构建 AnimeInfo 对象

        Args:
            result: _search_XXX 返回的字典
            db_name: 数据库名称

        Returns:
            AnimeInfo 对象
        """
        info = AnimeInfo()
        info.source_db = db_name

        info.bangumi_id = result.get("bangumi_id")
        info.anilist_id = result.get("anilist_id")
        info.tmdb_id = result.get("tmdb_id")
        info.mal_id = result.get("mal_id")

        info.title = result.get("title", "")
        info.title_en = result.get("title_en", "")
        info.title_zh = result.get("title_zh", "")
        info.title_jp = result.get("title_jp", "")
        info.title_romaji = result.get("title_romaji", "")

        info.year = result.get("year")
        info.total_episodes = result.get("total_episodes", 0)
        info.episode_type = result.get("episode_type", "TV")
        info.overview = result.get("overview", "")

        # 确保主标题不为空
        if not info.title:
            info.title = info.title_zh or info.title_en or info.title_romaji or info.title_jp or ""

        return info

    # =========================================================================
    # 1. Bangumi API — 多策略搜索
    # =========================================================================

    def _search_bangumi(self, title, year=None):
        """在 Bangumi 搜索番剧 — 多策略模糊匹配

        策略:
          1. 用原标题搜索 POST /v0/search/subjects (sort=match, 文本匹配优先)
          2. 清理后的标题搜索
          3. 罗马字→中文映射搜索
          4. sort=rank 搜索 (热门度优先，排除 TVCM 等冷门条目)
          5. 合并所有结果，选最佳匹配

        Args:
            title: 番剧标题
            year: 年份（可选）

        Returns:
            dict 或 None
        """
        cache_key = f"search_bangumi_{title}_{year}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        all_items = {}  # id → item，用于去重合并

        title_lower = title.lower().strip()
        use_romaji = title_lower in self.ROMAJI_DICT

        if use_romaji:
            # ROMAJI_DICT 命中 → 直接用映射的中文关键词搜索（跳过原标题）
            cn_keyword = self.ROMAJI_DICT[title_lower]
            items1 = self._bgm_api_search(cn_keyword, sort="match")
            for item in items1:
                item_id = item.get("id")
                if item_id:
                    all_items[item_id] = item
            self._log(f"    策略1 (罗马字映射 '{title}' → '{cn_keyword}'): {len(items1)} 条")
        else:
            # 策略1: 原标题 match 搜索
            items1 = self._bgm_api_search(title, sort="match")
            for item in items1:
                item_id = item.get("id")
                if item_id:
                    all_items[item_id] = item
            self._log(f"    策略1 (match): {len(items1)} 条")

            # 策略2: 清理后的标题搜索
            cleaned = self._clean_search_title(title)
            if cleaned and cleaned != title:
                items2 = self._bgm_api_search(cleaned, sort="match")
                for item in items2:
                    item_id = item.get("id")
                    if item_id and item_id not in all_items:
                        all_items[item_id] = item
                self._log(f"    策略2 (清理标题): {len(items2)} 条")

            # 策略3: rank 排序搜索 (热门度优先，排除冷门 TVCM/PV)
            items3 = self._bgm_api_search(title, sort="rank")
            for item in items3:
                item_id = item.get("id")
                if item_id and item_id not in all_items:
                    all_items[item_id] = item
            self._log(f"    策略3 (rank): {len(items3)} 条")

        if not all_items:
            self._cache_set(cache_key, None)
            return None

        items = list(all_items.values())
        best = self._pick_best_match(items, title, year, "bangumi")
        if best is None:
            self._cache_set(cache_key, None)
            return None

        result = self._build_bangumi_result(best)
        self._cache_set(cache_key, result)
        return result

    def _bgm_api_search(self, keyword, sort="match"):
        """Bangumi POST API 原始搜索

        POST /v0/search/subjects
        使用 meilisearch 引擎，sort=match 模糊匹配，sort=rank 按热门度排序。

        Args:
            keyword: 搜索关键词
            sort: 排序方式 — "match" (文本匹配) 或 "rank" (热门度)

        Returns:
            搜索结果列表
        """
        try:
            url = f"{self.BANGUMI_API}/v0/search/subjects"
            body = {
                "keyword": keyword,
                "sort": sort,
                "filter": {"type": [2]},  # 2 = 动画
            }
            headers = {
                "User-Agent": "AnimeRenamer/1.0",
                "Content-Type": "application/json",
            }
            resp = self.session.post(url, json=body, headers=headers, timeout=15)
            if resp.status_code != 200:
                self._log(f"    Bangumi API 返回 {resp.status_code}")
                return []
            data = resp.json()
            return data.get("data", []) if isinstance(data, dict) else []
        except requests.RequestException as e:
            self._log(f"    Bangumi 搜索异常: {e}")
            return []

    def _clean_search_title(self, title):
        """清理搜索标题，去除干扰项

        - 去除末尾季数标记 (S1, S2, Season 1 等)
        - 去除末尾破折号分隔的集标题（仅当末尾片段含 CJK 字符时）
        - 去除首尾特殊字符和空白
        """
        t = title.strip()
        # 去除末尾季数标记
        t = re.sub(r'\s+[Ss](?:eason\s*)?\d+\s*$', '', t)
        t = re.sub(r'\s+第[一二三四五六七八九十\d]+季\s*$', '', t)
        # 去除末尾破折号分隔的片段 — 仅当末尾片段含中日韩文字时剥离
        # （避免误删英文副标题如 "Sword Art Online - Alicization"）
        m = re.search(r'^(.+)\s+[-–—]+\s+([^-–—]+)$', t)
        if m:
            last_seg = m.group(2).strip()
            if re.search(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]', last_seg):
                t = m.group(1).strip()
        # 去除首尾特殊字符
        t = t.strip('[]()（）_-.!?;:,\'" ')
        return t

    def _build_bangumi_result(self, best):
        """从 Bangumi API 条目构建标准结果字典"""
        return {
            "bangumi_id": best.get("id"),
            "title": best.get("name_cn") or best.get("name", ""),
            "title_zh": best.get("name_cn", ""),
            "title_jp": best.get("name", ""),
            "title_en": best.get("name_cn") or best.get("name", ""),
            "title_romaji": "",
            "year": self._extract_year_from_date(best.get("air_date") or best.get("date")),
            "total_episodes": best.get("eps_count", 0) or best.get("eps", 0) or 0,
            "episode_type": self._map_bangumi_type(best.get("type")),
            "overview": best.get("summary", ""),
        }

    def get_search_candidates(self, title, limit=5):
        """获取搜索候选列表，供 UI 展示选择

        Args:
            title: 搜索关键词
            limit: 返回数量上限

        Returns:
            list[dict]: 候选列表，每项包含 id, name_cn, name, eps, date, score
        """
        items = self._bgm_api_search(title)
        if not items:
            return []

        # 对每个结果打分
        title_norm = self._norm_compare(title)
        title_tokens = self._tokenize(title_norm)
        is_short_ascii = len(title.strip()) <= 6 and all(c.isascii() for c in title.strip())

        scored = []
        for item in items:
            fields = [
                (item.get("name_cn") or "").strip(),
                (item.get("name") or "").strip(),
            ]
            item_eps = item.get("eps_count", 0) or item.get("eps", 0) or 0
            item_name_raw = (item.get("name") or "").lower()
            has_cn = bool(item.get("name_cn"))

            best_score = 0
            for field in fields:
                if not field:
                    continue
                field_norm = self._norm_compare(field)
                field_tokens = self._tokenize(field_norm)

                if title_norm == field_norm:
                    best_score = max(best_score, 100)
                    break
                if title_norm in field_norm:
                    if is_short_ascii and len(title_norm) <= 5 and len(field_norm) > 15:
                        best_score = max(best_score, 40)
                    else:
                        best_score = max(best_score, 75)
                    continue
                if field_norm in title_norm:
                    best_score = max(best_score, 60)
                    continue
                sim = difflib.SequenceMatcher(None, title_norm, field_norm).ratio()
                best_score = max(best_score, int(sim * 50))
                if title_tokens and field_tokens:
                    overlap = title_tokens & field_tokens
                    if overlap:
                        ratio = len(overlap) / max(len(title_tokens), 1)
                        best_score = max(best_score, int(ratio * 30))

            if has_cn:
                best_score += 10
            if item_eps == 1 and bool(re.search(r'\b(TVCM|PV|CM|Promotion|Trailer|预告)\b', item_name_raw, re.IGNORECASE)):
                best_score -= 40
            if item_eps > 12:
                best_score += 5
            elif item_eps > 1:
                best_score += 3

            scored.append((best_score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:limit]

        candidates = []
        for score, item in top:
            candidates.append({
                "id": item.get("id"),
                "name_cn": (item.get("name_cn") or "").strip(),
                "name": (item.get("name") or "").strip(),
                "eps": item.get("eps_count", 0) or item.get("eps", 0) or 0,
                "date": (item.get("air_date") or item.get("date") or ""),
                "score": score,
            })
        return candidates

    def recognize_by_bangumi_id(self, bangumi_id, parsed_info):
        """通过指定 Bangumi ID 直接识别（用于用户手动选择搜索结果后）

        Args:
            bangumi_id: Bangumi 条目 ID
            parsed_info: ParsedInfo 对象

        Returns:
            AnimeInfo 对象
        """
        self._log(f"--- 通过 ID 直接识别: {bangumi_id} ---")
        try:
            url = f"{self.BANGUMI_API}/v0/subjects/{bangumi_id}"
            headers = {"User-Agent": "AnimeRenamer/1.0"}
            resp = self.session.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                self._log(f"    Bangumi 获取条目失败: HTTP {resp.status_code}")
                return None
            item = resp.json()
            result = self._build_bangumi_result(item)
            anime_info = self._build_anime_info(result, "bangumi")
            anime_info.season_number = getattr(parsed_info, "season", 1)
            self._fetch_bangumi_episodes(anime_info, anime_info.season_number)
            self._log(f"--- 识别完成: {anime_info.title} (来源: bangumi) ---")
            return anime_info
        except requests.RequestException as e:
            self._log(f"    Bangumi 获取条目异常: {e}")
            return None

    def _fetch_bangumi_episodes(self, anime_info, season):
        """获取 Bangumi 剧集标题（中日文分别存储）

        GET https://api.bgm.tv/v0/episodes?subject_id={id}&type=0&limit=200
        """
        if anime_info.bangumi_id is None:
            return

        cache_key = f"episodes_bangumi_{anime_info.bangumi_id}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            # JSON 反序列化后 key 会变成字符串，需转回 int
            ep_cn = {int(k): v for k, v in cached.get("cn", {}).items()}
            ep_jp = {int(k): v for k, v in cached.get("jp", {}).items()}
            anime_info.episode_titles_cn = ep_cn
            anime_info.episode_titles_jp = ep_jp
            anime_info.episode_titles = ep_cn
            self._log(f"    获取到 {len(ep_cn)} 集标题 (缓存)")
            return

        try:
            url = f"{self.BANGUMI_API}/v0/episodes"
            params = {
                "subject_id": anime_info.bangumi_id,
                "type": 0,     # 0 = 本篇
                "limit": 200,
            }
            headers = {"User-Agent": "AnimeRenamer/1.0 (your@email.com)"}

            resp = self.session.get(url, params=params, headers=headers, timeout=15)
            if resp.status_code != 200:
                self._log(f"    Bangumi 剧集获取失败: HTTP {resp.status_code}")
                return

            data = resp.json()
            episodes = data.get("data", []) if isinstance(data, dict) else data

            ep_cn = {}
            ep_jp = {}
            for ep in episodes:
                ep_num = ep.get("ep", 0) or ep.get("sort", 0)
                if ep_num:
                    name_cn = ep.get("name_cn", "")
                    name_jp = ep.get("name", "")
                    if name_cn:
                        ep_cn[int(ep_num)] = name_cn
                    if name_jp:
                        ep_jp[int(ep_num)] = name_jp

            anime_info.episode_titles_cn = ep_cn
            anime_info.episode_titles_jp = ep_jp
            anime_info.episode_titles = ep_cn  # 兼容

            cached = {"cn": ep_cn, "jp": ep_jp}
            self._cache_set(cache_key, cached)
            self._log(f"    获取到 {len(ep_cn)} 集中文标题 / {len(ep_jp)} 集日文标题 (Bangumi)")

        except requests.RequestException as e:
            self._log(f"    Bangumi 剧集获取异常: {e}")

    def _map_bangumi_type(self, bangumi_type):
        """将 Bangumi 类型映射为标准类型"""
        if bangumi_type is None:
            return "TV"
        type_str = str(bangumi_type)
        if type_str == "2":
            return "TV"
        type_map = {
            1: "TV",
            2: "TV",
            3: "TV",
            4: "TV",
            6: "Movie",
        }
        return type_map.get(bangumi_type, "TV")

    # =========================================================================
    # 2. AniList API
    # =========================================================================

    def _search_anilist(self, title, year=None):
        """在 AniList 搜索番剧（GraphQL）

        Args:
            title: 番剧标题
            year: 年份（可选）

        Returns:
            dict 或 None
        """
        cache_key = f"search_anilist_{title}_{year}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        try:
            query = """
            query ($search: String) {
                Page(perPage: 5) {
                    media(search: $search, type: ANIME) {
                        id
                        idMal
                        title { romaji english native }
                        seasonYear
                        episodes
                        format
                        description
                    }
                }
            }
            """
            resp = self.session.post(
                self.ANILIST_API,
                json={"query": query, "variables": {"search": title}},
                timeout=15,
            )

            if resp.status_code != 200:
                self._log(f"    AniList 搜索失败: HTTP {resp.status_code}")
                return None

            data = resp.json()
            media_list = data.get("data", {}).get("Page", {}).get("media", [])
            if not media_list:
                return None

            # 找到最佳匹配
            best = self._pick_best_match(media_list, title, year, "anilist")
            if best is None:
                return None

            titles = best.get("title", {})
            fmt = best.get("format", "")

            result = {
                "anilist_id": best.get("id"),
                "mal_id": best.get("idMal"),
                "title": titles.get("english") or titles.get("romaji") or titles.get("native", ""),
                "title_en": titles.get("english", ""),
                "title_zh": titles.get("native", ""),  # native 通常是日文/中文
                "title_jp": titles.get("native", ""),
                "title_romaji": titles.get("romaji", ""),
                "year": best.get("seasonYear"),
                "total_episodes": best.get("episodes") or 0,
                "episode_type": self._map_anilist_format(fmt),
                "overview": (best.get("description") or "")[:500],
            }
            self._cache_set(cache_key, result)
            return result

        except requests.RequestException as e:
            self._log(f"    AniList 搜索异常: {e}")
            return None

    def _fetch_anilist_episodes(self, anime_info, season):
        """AniList 不直接提供每集标题，尝试通过 TMDB 补充

        Args:
            anime_info: AnimeInfo 对象
            season: 季号
        """
        # AniList 本身不提供 episode titles
        # 尝试用 TMDB 补充
        if anime_info.title_en and anime_info.tmdb_id is None:
            self._log("    AniList 无剧集标题，尝试通过 TMDB 补充...")
            tmdb_result = self._search_tmdb(anime_info.title_en, anime_info.year)
            if tmdb_result and tmdb_result.get("tmdb_id"):
                anime_info.tmdb_id = tmdb_result["tmdb_id"]
                self._fetch_tmdb_episodes(anime_info, season)

    def _map_anilist_format(self, fmt):
        """将 AniList format 映射为标准类型"""
        if not fmt:
            return "TV"
        mapping = {
            "TV": "TV",
            "TV_SHORT": "TV",
            "MOVIE": "Movie",
            "OVA": "OVA",
            "ONA": "TV",
            "SPECIAL": "SP",
            "MUSIC": "SP",
        }
        return mapping.get(fmt, "TV")

    # =========================================================================
    # 3. TMDB API
    # =========================================================================

    def _get_tmdb_key(self):
        """获取 TMDB API Key"""
        key = self.config.get("tmdb_api_key", "").strip()
        return key if key else self.DEFAULT_TMDB_KEY

    def _search_tmdb(self, title, year=None):
        """在 TMDB 搜索番剧

        GET https://api.themoviedb.org/3/search/tv

        Args:
            title: 番剧标题
            year: 年份（可选）

        Returns:
            dict 或 None
        """
        cache_key = f"search_tmdb_{title}_{year}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        api_key = self._get_tmdb_key()
        if not api_key:
            self._log("    TMDB API Key 未设置，跳过")
            return None

        try:
            params = {
                "api_key": api_key,
                "query": title,
                "language": "zh-CN",
            }
            if year:
                params["first_air_date_year"] = year

            resp = self.session.get(
                f"{self.TMDB_API}/search/tv",
                params=params,
                timeout=15,
            )

            if resp.status_code == 401:
                self._log("    TMDB API Key 无效")
                return None
            if resp.status_code == 429:
                self._log("    TMDB 请求过于频繁，等待 1 秒...")
                time.sleep(1)
                return None
            if resp.status_code != 200:
                self._log(f"    TMDB 搜索失败: HTTP {resp.status_code}")
                return None

            data = resp.json()
            results = data.get("results", [])
            if not results:
                self._log("    TMDB 搜索无结果")
                self._cache_set(cache_key, None)
                return None

            self._log(f"    TMDB 搜索返回 {len(results)} 条结果")
            best = self._pick_best_match(results, title, year, "tmdb")
            if best is None:
                self._log("    TMDB 匹配评分未通过")
                self._cache_set(cache_key, None)
                return None

            tv_id = best["id"]

            # 获取详细信息（含中文标题），失败时回退到搜索结果的 name
            detail = self._get_tmdb_detail(tv_id, api_key)
            fallback_name = best.get("name", "") or best.get("original_name", "")

            result = {
                "tmdb_id": tv_id,
                "title": (detail.get("title_zh") or detail.get("title_en") or fallback_name) if detail else fallback_name,
                "title_zh": detail.get("title_zh", "") if detail else "",
                "title_en": detail.get("title_en", best.get("original_name", "")) if detail else best.get("original_name", ""),
                "title_jp": detail.get("title_jp", "") if detail else "",
                "title_romaji": "",
                "year": (detail.get("year") if detail else None) or self._extract_year_from_date(best.get("first_air_date")),
                "total_episodes": (detail.get("total_episodes", 0) if detail else 0) or best.get("episode_count", 0) or 0,
                "episode_type": "TV",
                "overview": (detail.get("overview", "") if detail else "") or best.get("overview", ""),
            }
            self._cache_set(cache_key, result)
            return result

        except requests.RequestException as e:
            self._log(f"    TMDB 搜索异常: {e}")
            return None

    def _get_tmdb_detail(self, tv_id, api_key):
        """获取 TMDB 番剧详情（含中英文标题）

        Args:
            tv_id: TMDB 剧集 ID
            api_key: API Key

        Returns:
            dict 或 None
        """
        cache_key = f"detail_tmdb_{tv_id}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        try:
            # 中文详情
            resp_zh = self.session.get(
                f"{self.TMDB_API}/tv/{tv_id}",
                params={"api_key": api_key, "language": "zh-CN"},
                timeout=15,
            )
            # 英文详情
            resp_en = self.session.get(
                f"{self.TMDB_API}/tv/{tv_id}",
                params={"api_key": api_key, "language": "en-US"},
                timeout=15,
            )
            # 日文详情
            resp_jp = self.session.get(
                f"{self.TMDB_API}/tv/{tv_id}",
                params={"api_key": api_key, "language": "ja-JP"},
                timeout=15,
            )

            detail = {}
            if resp_zh.status_code == 200:
                d = resp_zh.json()
                detail["title_zh"] = d.get("name", "")
                detail["overview"] = d.get("overview", "")
                detail["total_episodes"] = d.get("number_of_episodes", 0)
                detail["year"] = self._extract_year_from_date(d.get("first_air_date"))
            if resp_en.status_code == 200:
                detail["title_en"] = resp_en.json().get("name", "")
            if resp_jp.status_code == 200:
                detail["title_jp"] = resp_jp.json().get("name", "")

            if not detail:
                return None

            self._cache_set(cache_key, detail)
            return detail

        except requests.RequestException as e:
            self._log(f"    TMDB 详情获取异常: {e}")
            return None

    def _fetch_tmdb_episodes(self, anime_info, season):
        """获取 TMDB 季的每集标题

        GET https://api.themoviedb.org/3/tv/{id}/season/{season}

        Args:
            anime_info: AnimeInfo 对象（会原地修改 episode_titles）
            season: 季号
        """
        if anime_info.tmdb_id is None:
            return

        cache_key = f"episodes_tmdb_{anime_info.tmdb_id}_{season}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            # JSON 反序列化后 key 会变成字符串，需转回 int
            anime_info.episode_titles = {int(k): v for k, v in cached.items()}
            self._log(f"    获取到 {len(anime_info.episode_titles)} 集标题 (缓存)")
            return

        api_key = self._get_tmdb_key()
        if not api_key:
            self._log("    TMDB API Key 未设置，跳过剧集获取")
            return

        try:
            resp = self.session.get(
                f"{self.TMDB_API}/tv/{anime_info.tmdb_id}/season/{season}",
                params={"api_key": api_key, "language": "zh-CN"},
                timeout=15,
            )

            if resp.status_code != 200:
                self._log(f"    TMDB 季信息获取失败: HTTP {resp.status_code}")
                return

            data = resp.json()
            episodes = data.get("episodes", [])
            episode_titles = {}
            for ep in episodes:
                ep_num = ep.get("episode_number", 0)
                ep_name = ep.get("name", "")
                if ep_num and ep_name:
                    episode_titles[int(ep_num)] = ep_name

            anime_info.episode_titles = episode_titles
            self._cache_set(cache_key, episode_titles)
            self._log(f"    获取到 {len(episode_titles)} 集标题 (TMDB)")

        except requests.RequestException as e:
            self._log(f"    TMDB 季信息获取异常: {e}")

    # =========================================================================
    # 4. Jikan API (MyAnimeList)
    # =========================================================================

    def _search_jikan(self, title, year=None):
        """在 Jikan (MyAnimeList) 搜索番剧

        GET https://api.jikan.moe/v4/anime?q={title}&limit=5

        限速: 每秒最多 3 次请求 (间隔 0.4 秒)

        Args:
            title: 番剧标题
            year: 年份（可选）

        Returns:
            dict 或 None
        """
        cache_key = f"search_jikan_{title}_{year}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        # Jikan 限速: 3 次/秒
        self._jikan_throttle()

        try:
            params = {
                "q": title,
                "limit": 8,  # 多获取一些结果便于匹配
            }
            # Jikan 504 重试逻辑（MAL 间歇性拒绝连接）
            retry_count = 0
            while retry_count < 3:
                resp = self.session.get(
                    f"{self.JIKAN_API}/anime",
                    params=params,
                    timeout=15,
                )

                if resp.status_code == 429:
                    self._log("    Jikan 限速，等待 3 秒...")
                    time.sleep(3)
                    retry_count += 1
                    continue
                if resp.status_code == 504:
                    retry_count += 1
                    if retry_count >= 3:
                        self._log("    Jikan 504 重试耗尽 (MAL 不可达)，跳过")
                        return None
                    self._log(f"    Jikan 504 (MAL 不可达)，第 {retry_count} 次重试 (等待 3 秒)...")
                    time.sleep(3)
                    continue
                if resp.status_code != 200:
                    self._log(f"    Jikan 搜索失败: HTTP {resp.status_code}")
                    return None
                break
            else:
                self._log("    Jikan 重试耗尽，跳过")
                return None

            data = resp.json()
            items = data.get("data", [])
            if not items:
                self._log("    Jikan 搜索无结果")
                self._cache_set(cache_key, None)
                return None

            self._log(f"    Jikan 搜索返回 {len(items)} 条结果")
            # 找到最佳匹配
            best = self._pick_best_match(items, title, year, "jikan")
            if best is None:
                self._log("    Jikan 匹配评分未通过")
                self._cache_set(cache_key, None)
                return None

            titles_list = best.get("titles", [])
            title_jp = best.get("title", "")
            title_en = ""
            title_zh = ""
            for t in titles_list:
                ttype = t.get("type", "")
                if ttype == "English":
                    title_en = t.get("title", "")
                elif ttype in ("Synonym", "Chinese"):
                    title_zh = t.get("title", "")

            result = {
                "mal_id": best.get("mal_id"),
                "title": title_zh or title_en or title_jp,
                "title_en": title_en,
                "title_zh": title_zh,
                "title_jp": title_jp,
                "title_romaji": "",
                "year": best.get("year"),
                "total_episodes": best.get("episodes") or 0,
                "episode_type": self._map_jikan_type(best.get("type", "")),
                "overview": best.get("synopsis", ""),
            }
            self._cache_set(cache_key, result)
            return result

        except requests.RequestException as e:
            self._log(f"    Jikan 搜索异常: {e}")
            return None

    def _fetch_jikan_episodes(self, anime_info, season):
        """获取 Jikan (MyAnimeList) 剧集标题

        GET https://api.jikan.moe/v4/anime/{id}/episodes?page=1

        Jikan v4 的 episodes 端点按顺序返回每集数据，不包含显式的集号字段，
        因此使用全局计数器（从 1 开始）分配集号。

        Args:
            anime_info: AnimeInfo 对象（会原地修改 episode_titles）
            season: 季号（Jikan 目前不支持分季，直接获取所有剧集）
        """
        if anime_info.mal_id is None:
            return

        cache_key = f"episodes_jikan_{anime_info.mal_id}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            # JSON 反序列化后 key 会变成字符串，需转回 int
            anime_info.episode_titles = {int(k): v for k, v in cached.items()}
            self._log(f"    获取到 {len(anime_info.episode_titles)} 集标题 (缓存)")
            return

        all_episodes = {}
        page = 1
        ep_counter = 1  # 集号计数器，Jikan 按顺序返回剧集
        retry_504 = 0    # 504 重试计数器

        try:
            while True:
                self._jikan_throttle()

                resp = self.session.get(
                    f"{self.JIKAN_API}/anime/{anime_info.mal_id}/episodes",
                    params={"page": page},
                    timeout=15,
                )

                if resp.status_code == 429:
                    self._log("    Jikan 限速，等待 3 秒...")
                    time.sleep(3)
                    retry_504 += 1
                    if retry_504 >= 5:
                        self._log("    Jikan 重试耗尽，跳过剧集获取")
                        break
                    continue
                if resp.status_code == 504:
                    retry_504 += 1
                    if retry_504 >= 5:
                        self._log("    Jikan 504 重试耗尽 (MAL 不可达)，跳过剧集获取")
                        break
                    self._log(f"    Jikan 504 (MAL 不可达)，第 {retry_504} 次重试 (等待 3 秒)...")
                    time.sleep(3)
                    continue
                if resp.status_code != 200:
                    self._log(f"    Jikan 剧集获取失败: HTTP {resp.status_code}")
                    break

                data = resp.json()
                episodes = data.get("data", [])
                if not episodes:
                    break

                for ep in episodes:
                    ep_name = ep.get("title", "")
                    ep_title_jp = ep.get("title_japanese", "")
                    best_name = ep_name or ep_title_jp
                    if best_name:
                        all_episodes[ep_counter] = best_name
                    ep_counter += 1

                pagination = data.get("pagination", {})
                has_next = pagination.get("has_next_page", False)
                if not has_next:
                    break
                page += 1

            anime_info.episode_titles = all_episodes
            self._cache_set(cache_key, all_episodes)
            self._log(f"    获取到 {len(all_episodes)} 集标题 (Jikan)")

        except requests.RequestException as e:
            self._log(f"    Jikan 剧集获取异常: {e}")

    def _jikan_throttle(self):
        """Jikan API 限速控制: 确保两次请求间隔 >= 0.4 秒"""
        now = time.time()
        elapsed = now - self._jikan_last_request
        if elapsed < 0.4:
            time.sleep(0.4 - elapsed)
        self._jikan_last_request = time.time()

    def _map_jikan_type(self, jikan_type):
        """将 Jikan 类型映射为标准类型"""
        if not jikan_type:
            return "TV"
        mapping = {
            "TV": "TV",
            "OVA": "OVA",
            "Movie": "Movie",
            "Special": "SP",
            "ONA": "TV",
            "Music": "SP",
        }
        return mapping.get(jikan_type, "TV")

    # =========================================================================
    # 通用匹配引擎 — 智能模糊匹配
    # =========================================================================

    def _pick_best_match(self, items, title, year, db_name):
        """从搜索结果中选择最佳匹配

        评分策略（按优先级）:
          1. 标准化精确匹配: 100 分
          2. 子串包含: 60-75 分（短标题惩罚）
          3. 编辑距离相似度: 0-50 分
          4. 分词命中: 0-30 分
          5. 年份匹配: +20 分
          6. 有中文标题: +10 分
          7. TVCM/PV/CM 惩罚: -40 分
          8. 集数偏好: 1集=0, 2-12集=+3, 13+集=+5

        Args:
            items: 搜索结果列表
            title: 原始搜索标题
            year: 年份
            db_name: 数据库名称

        Returns:
            最佳匹配条目或 None
        """
        if not items:
            return None
        if len(items) == 1:
            return items[0]

        title_norm = self._norm_compare(title)
        title_tokens = self._tokenize(title_norm)
        is_short_ascii = len(title.strip()) <= 6 and all(c.isascii() for c in title.strip())

        scored = []
        for item in items:
            # 提取标题字段
            if db_name == "bangumi":
                fields = [
                    (item.get("name_cn") or "").strip(),
                    (item.get("name") or "").strip(),
                ]
                item_year = self._extract_year_from_date(item.get("air_date") or item.get("date"))
                has_cn = bool(item.get("name_cn"))
                item_eps = item.get("eps_count", 0) or item.get("eps", 0) or 0
                item_name_raw = (item.get("name") or "").lower()
            elif db_name == "anilist":
                titles = item.get("title", {})
                fields = [
                    (titles.get("romaji") or "").strip(),
                    (titles.get("english") or "").strip(),
                    (titles.get("native") or "").strip(),
                ]
                item_year = item.get("seasonYear")
                has_cn = False
                item_eps = 0
                item_name_raw = ""
            elif db_name == "tmdb":
                fields = [
                    (item.get("name") or "").strip(),
                    (item.get("original_name") or "").strip(),
                ]
                item_year = self._extract_year_from_date(item.get("first_air_date"))
                has_cn = bool(item.get("name") and item.get("original_name") and item.get("name") != item.get("original_name"))
                item_eps = item.get("episode_count", 0) or 0
                item_name_raw = (item.get("original_name") or "").lower()
            elif db_name == "jikan":
                # 使用 title 和 titles 数组中的所有英文/同义词标题
                fields = [(item.get("title") or "").strip()]
                for t in (item.get("titles") or []):
                    ttype = t.get("type", "")
                    if ttype in ("English", "Synonym", "Default"):
                        title_val = (t.get("title") or "").strip()
                        if title_val and title_val not in fields:
                            fields.append(title_val)
                item_year = item.get("year")
                has_cn = any(
                    t.get("type") in ("Synonym", "Chinese") and
                    re.search(r'[\u4e00-\u9fff]', t.get("title", ""))
                    for t in (item.get("titles") or [])
                )
                item_eps = item.get("episodes") or 0
                item_name_raw = (item.get("title") or "").lower()
            elif db_name in ("tvmaze", "thetvdb", "anidb"):
                fields = [(item.get("name") or "").strip()]
                item_year = (self._extract_year_from_date(item.get("premiered") or item.get("first_air_time")) or item.get("year"))
                has_cn = False
                item_eps = 0
                item_name_raw = (item.get("name") or "").lower()
            else:
                return items[0]

            best_score = 0

            for field in fields:
                if not field:
                    continue
                field_norm = self._norm_compare(field)
                field_tokens = self._tokenize(field_norm)

                # 1. 精确匹配
                if title_norm == field_norm:
                    best_score = max(best_score, 100)
                    break

                # 2. 子串包含
                if title_norm in field_norm:
                    # 短 ASCII 标题在长名称中匹配 → 可能是假阳性，降低分数
                    if is_short_ascii and len(title_norm) <= 5 and len(field_norm) > 15:
                        best_score = max(best_score, 40)
                    else:
                        best_score = max(best_score, 75)
                    continue
                if field_norm in title_norm:
                    best_score = max(best_score, 60)
                    continue

                # 3. 编辑距离
                sim = difflib.SequenceMatcher(None, title_norm, field_norm).ratio()
                best_score = max(best_score, int(sim * 50))

                # 4. 分词命中
                if title_tokens and field_tokens:
                    overlap = title_tokens & field_tokens
                    if overlap:
                        ratio = len(overlap) / max(len(title_tokens), 1)
                        best_score = max(best_score, int(ratio * 30))

            # 5. 年份匹配
            if year and item_year and year == item_year:
                best_score += 20

            # 6. 中文标题加分
            if has_cn:
                best_score += 10

            # 7. TVCM/PV/CM 惩罚 — 名称中含 TVCM/PV/CM 且只有1集
            if item_eps == 1 and bool(re.search(r'\b(TVCM|PV|CM|Promotion|Trailer|预告)\b', item_name_raw, re.IGNORECASE)):
                best_score -= 40

            # 8. 集数偏好 — 多集条目加分
            if item_eps > 12:
                best_score += 5
            elif item_eps > 1:
                best_score += 3

            scored.append((best_score, item))

        scored.sort(key=lambda x: x[0], reverse=True)

        # 日志：输出前3个匹配结果
        if scored and len(scored) > 1:
            top = scored[:3]
            parts = []
            for rank, (s, it) in enumerate(top):
                if db_name == "tmdb":
                    label = (it.get("name") or it.get("original_name") or str(it.get("id", "?")))[:30]
                    eps = it.get("episode_count", 0) or 0
                elif db_name == "jikan":
                    label = (it.get("title") or str(it.get("mal_id", "?")))[:30]
                    eps = it.get("episodes") or 0
                else:
                    label = (it.get("name_cn") or it.get("name") or str(it.get("id", "?")))[:30]
                    eps = it.get("eps_count", 0) or it.get("eps", 0) or 0
                parts.append(f"#{rank + 1} {label} (eps={eps}, {s}分)")
            self._log(f"    匹配评分: {' | '.join(parts)}")

        return scored[0][1] if scored else None

    @staticmethod
    def _norm_compare(s):
        """标准化字符串用于比较：去特殊字符、去空格、小写"""
        s = re.sub(r'[^\w\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff]', '', s)
        return s.lower()

    @staticmethod
    def _tokenize(s):
        """分词：按空格、下划线、连字符、大小写边界切分"""
        tokens = set()
        # 按分隔符切
        for part in re.split(r'[\s\-_\.:!?/]+', s):
            part = part.strip().lower()
            if part and len(part) >= 2:
                tokens.add(part)
        # 大小写边界切分
        for part in list(tokens):
            sub = re.findall(r'[a-z]+|[A-Z][a-z]*|[0-9]+', part)
            for s2 in sub:
                if len(s2) >= 2:
                    tokens.add(s2.lower())
        return tokens

    def _extract_year_from_date(self, date_str):
        """从日期字符串中提取年份

        Args:
            date_str: 日期字符串，如 "2021-04-10" 或 "2021"

        Returns:
            年份整数或 None
        """
        if not date_str:
            return None
        match = re.search(r"(\d{4})", str(date_str))
        if match:
            return int(match.group(1))
        return None

    # =========================================================================
    # 连接测试
    # =========================================================================

    def test_connection(self, db_name):
        """测试指定数据库 API 的连接状态

        使用简单的查询测试 API 是否可用。

        Args:
            db_name: 数据库名称，可选: "bangumi", "anilist", "tmdb", "jikan"

        Returns:
            dict: {"ok": bool, "message": str, "response_time_ms": int}
        """
        db_name = db_name.lower()
        test_queries = {
            "bangumi": ("GET", f"{self.BANGUMI_API}/search/subject/Steins Gate", {"type": 2, "responseGroup": "small"}),
            "anilist": ("POST", self.ANILIST_API, None),
            "tmdb": ("GET", f"{self.TMDB_API}/search/tv", {"api_key": self._get_tmdb_key(), "query": "Steins Gate", "language": "zh-CN"}),
            "themoviedb": ("GET", f"{self.TMDB_API}/search/tv", {"api_key": self._get_tmdb_key(), "query": "Steins Gate", "language": "zh-CN"}),
            "jikan": ("GET", f"{self.JIKAN_API}/anime", {"q": "Steins Gate", "limit": 1}),
            "tvmaze": ("GET", "https://api.tvmaze.com/search/shows", {"q": "Steins Gate"}),
            "anidb": ("GET", "https://anidb.net/anime/", {}),
            "thetvdb": ("GET", "https://api4.thetvdb.com/v4/search", {"query": "Steins Gate", "type": "series"}),
            "imdb": ("GET", "https://v2.sg.media-imdb.com/suggestion/s/steins gate.json", {}),
        }

        if db_name not in test_queries:
            return {"ok": False, "message": f"未知数据库: {db_name}", "response_time_ms": 0}

        method, url, params = test_queries[db_name]
        headers = {}
        if db_name == "bangumi":
            headers = {"User-Agent": "AnimeRenamer/1.0 (your@email.com)"}

        try:
            start = time.time()
            if method == "GET":
                resp = self.session.get(url, params=params, headers=headers, timeout=10)
            else:
                # AniList GraphQL
                query = "query($search:String){Page(perPage:1){media(search:$search,type:ANIME){id}}}"
                resp = self.session.post(
                    url,
                    json={"query": query, "variables": {"search": "Steins Gate"}},
                    timeout=10,
                )

            elapsed_ms = int((time.time() - start) * 1000)

            if resp.status_code == 200:
                return {"ok": True, "message": f"{self.DB_NAMES.get(db_name, db_name)} 连接正常", "response_time_ms": elapsed_ms}
            elif resp.status_code == 401:
                return {"ok": False, "message": "API Key 无效", "response_time_ms": elapsed_ms}
            elif resp.status_code == 429:
                return {"ok": False, "message": "请求过于频繁，请稍后重试", "response_time_ms": elapsed_ms}
            elif resp.status_code == 504:
                return {"ok": False, "message": "MAL 暂时不可达 (504)", "response_time_ms": elapsed_ms}
            else:
                return {"ok": False, "message": f"HTTP {resp.status_code}", "response_time_ms": elapsed_ms}

        except requests.Timeout:
            return {"ok": False, "message": "连接超时", "response_time_ms": 0}
        except requests.ConnectionError:
            return {"ok": False, "message": "无法连接到服务器", "response_time_ms": 0}
        except requests.RequestException as e:
            return {"ok": False, "message": str(e), "response_time_ms": 0}

    # =========================================================================
    # 5. TVMaze API
    # =========================================================================

    def _search_tvmaze(self, title, year=None):
        """在 TVMaze 搜索番剧

        GET https://api.tvmaze.com/search/shows?q={title}

        Args:
            title: 番剧标题
            year: 年份（可选）

        Returns:
            dict 或 None
        """
        cache_key = f"search_tvmaze_{title}_{year}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        try:
            url = f"{self.TVMAZE_API}/search/shows"
            resp = self.session.get(url, params={"q": title}, timeout=15)
            if resp.status_code != 200:
                self._log(f"    TVMaze 搜索失败: HTTP {resp.status_code}")
                return None

            data = resp.json()
            if not data:
                self._log("    TVMaze 搜索无结果")
                self._cache_set(cache_key, None)
                return None

            # 找到最佳匹配
            items = []
            for item in data:
                show = item.get("show", {})
                items.append({
                    "name": show.get("name", ""),
                    "premiered": show.get("premiered", ""),
                    "summary": show.get("summary", ""),
                    "rating": show.get("rating", {}).get("average", 0),
                    "id": show.get("id"),
                })

            best = self._pick_best_match(items, title, year, "tvmaze")
            if best is None:
                self._cache_set(cache_key, None)
                return None

            result = {
                "title": best.get("name", ""),
                "title_zh": best.get("name", ""),
                "title_en": best.get("name", ""),
                "title_jp": "",
                "title_romaji": "",
                "year": self._extract_year_from_date(best.get("premiered")),
                "total_episodes": 0,
                "episode_type": "TV",
                "overview": (best.get("summary") or "")[:500],
            }
            self._cache_set(cache_key, result)
            return result

        except requests.RequestException as e:
            self._log(f"    TVMaze 搜索异常: {e}")
            return None

    # =========================================================================
    # 6. TheTVDB API
    # =========================================================================

    def _search_thetvdb(self, title, year=None):
        """在 TheTVDB 搜索番剧

        POST /login 获取 token，然后 GET /search?query={title}&type=series

        Args:
            title: 番剧标题
            year: 年份（可选）

        Returns:
            dict 或 None
        """
        cache_key = f"search_thetvdb_{title}_{year}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        try:
            # 获取 token
            login_url = f"{self.TVDB_API}/login"
            api_key = "0a0fe7e0-2b5e-4f7e-8b0e-0a0fe7e02b5e"
            login_resp = self.session.post(login_url, json={"apikey": api_key}, timeout=15)
            if login_resp.status_code != 200:
                self._log(f"    TheTVDB 登录失败: HTTP {login_resp.status_code}")
                return None
            token = login_resp.json().get("data", {}).get("token", "")
            if not token:
                self._log("    TheTVDB 获取 token 失败")
                return None

            # 搜索
            search_url = f"{self.TVDB_API}/search"
            headers = {"Authorization": f"Bearer {token}"}
            resp = self.session.get(
                search_url,
                params={"query": title, "type": "series", "limit": 10},
                headers=headers,
                timeout=15,
            )
            if resp.status_code != 200:
                self._log(f"    TheTVDB 搜索失败: HTTP {resp.status_code}")
                return None

            data = resp.json().get("data", []) or []
            if not data:
                self._log("    TheTVDB 搜索无结果")
                self._cache_set(cache_key, None)
                return None

            items = []
            for item in data:
                items.append({
                    "name": item.get("name", ""),
                    "first_air_time": item.get("first_air_time", ""),
                    "overview": item.get("overview", ""),
                    "id": item.get("tvdb_id", item.get("id")),
                })

            best = self._pick_best_match(items, title, year, "thetvdb")
            if best is None:
                self._cache_set(cache_key, None)
                return None

            result = {
                "title": best.get("name", ""),
                "title_zh": best.get("name", ""),
                "title_en": best.get("name", ""),
                "title_jp": "",
                "title_romaji": "",
                "year": self._extract_year_from_date(best.get("first_air_time")),
                "total_episodes": 0,
                "episode_type": "TV",
                "overview": (best.get("overview") or "")[:500],
            }
            self._cache_set(cache_key, result)
            return result

        except requests.RequestException as e:
            self._log(f"    TheTVDB 搜索异常: {e}")
            return None

    # =========================================================================
    # 7. AniDB API
    # =========================================================================

    def _search_anidb(self, title, year=None):
        """在 AniDB 搜索番剧（HTTP HTML 解析）

        Args:
            title: 番剧标题
            year: 年份（可选）

        Returns:
            dict 或 None
        """
        cache_key = f"search_anidb_{title}_{year}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        try:
            url = "https://anidb.net/anime/list/"
            params = {"adb.search": title, "do.search": "1"}
            headers = {
                "User-Agent": "AnimeRenamer/1.0 (your@email.com)",
                "Accept": "text/html,application/xhtml+xml",
            }
            resp = self.session.get(url, params=params, headers=headers, timeout=15)
            if resp.status_code != 200:
                self._log(f"    AniDB 搜索失败: HTTP {resp.status_code}")
                return None

            html = resp.text
            import re as _re
            rows = _re.findall(
                r'<tr\s+class="(?:even|odd)".*?<a\s+href="/anime/(\d+)"[^>]*>(.*?)</a>',
                html, _re.DOTALL | _re.IGNORECASE
            )
            if not rows:
                self._log("    AniDB 搜索无结果")
                self._cache_set(cache_key, None)
                return None

            # 取第一个结果
            aid, name = rows[0]
            name = _re.sub(r'<[^>]+>', '', name).strip()

            result = {
                "title": name,
                "title_zh": name,
                "title_en": name,
                "title_jp": "",
                "title_romaji": "",
                "year": year,
                "total_episodes": 0,
                "episode_type": "TV",
                "overview": "",
            }
            self._cache_set(cache_key, result)
            return result

        except requests.RequestException as e:
            self._log(f"    AniDB 搜索异常: {e}")
            return None

    # =========================================================================
    # 辅助搜索别名（供 episodes_panel 使用）
    # =========================================================================

    def _tvmaze_api_search(self, title):
        """TVMaze 搜索 — 免费无 API Key，含集数信息"""
        try:
            url = f"{self.TVMAZE_API}/search/shows"
            resp = self.session.get(url, params={"q": title}, timeout=10)
            if resp.status_code != 200:
                return []
            data = resp.json()
            results = []
            for item in (data or []):
                show = item.get("show", {})
                sid = show.get("id")
                # 获取剧集数量
                eps_count = 0
                try:
                    ep_resp = self.session.get(
                        f"{self.TVMAZE_API}/shows/{sid}/episodes",
                        timeout=8,
                    )
                    if ep_resp.status_code == 200:
                        eps_count = len(ep_resp.json() or [])
                except Exception:
                    pass

                image = show.get("image") or {}
                results.append({
                    "id": sid,
                    "name": show.get("name", ""),
                    "name_cn": show.get("name", ""),
                    "eps": eps_count,
                    "date": (show.get("premiered") or "")[:4],
                    "type": "TV",
                    "summary": (show.get("summary", "") or "").strip(),
                    "cover": image.get("medium", ""),
                    "score": show.get("rating", {}).get("average", 0) or 0,
                    "rank": 0,
                    "source": "TVMaze",
                })
            return results
        except Exception:
            return []

    # =========================================================================
    # TheTVDB API 搜索
    # =========================================================================

    def _thetvdb_api_search(self, title):
        """TheTVDB 搜索 — v4 API"""
        try:
            # 先获取 token
            login_url = f"{self.TVDB_API}/login"
            api_key = "0a0fe7e0-2b5e-4f7e-8b0e-0a0fe7e02b5e"  # 公开测试 key
            login_resp = self.session.post(login_url, json={"apikey": api_key}, timeout=10)
            if login_resp.status_code != 200:
                return []
            token = login_resp.json().get("data", {}).get("token", "")
            if not token:
                return []

            # 搜索
            search_url = f"{self.TVDB_API}/search"
            headers = {"Authorization": f"Bearer {token}"}
            resp = self.session.get(search_url, params={"query": title, "type": "series", "limit": 10},
                                    headers=headers, timeout=10)
            if resp.status_code != 200:
                return []
            data = resp.json().get("data", []) or []
            results = []
            for item in data:
                results.append({
                    "id": item.get("tvdb_id", item.get("id")),
                    "name": item.get("name", ""),
                    "name_cn": item.get("translations", {}).get("zho", "") if isinstance(item.get("translations"), dict) else "",
                    "eps": 0,
                    "date": (item.get("first_air_time") or item.get("year") or ""),
                    "type": "TV",
                    "summary": (item.get("overview", "") or "").strip(),
                    "cover": (item.get("image_url") or ""),
                    "score": 0,
                    "rank": 0,
                    "source": "TheTVDB",
                })
            return results
        except Exception:
            return []

    # =========================================================================
    # 通用搜索入口（供 episodes_panel 使用）
    # =========================================================================

    def _tmdb_api_search(self, title):
        """TMDB 搜索 — 返回含集数信息的增强结果（供 episodes_panel 使用）"""
        api_key = self._get_tmdb_key()
        try:
            params = {
                "api_key": api_key,
                "query": title,
                "language": "zh-CN",
            }
            resp = self.session.get(
                f"{self.TMDB_API}/search/tv",
                params=params,
                timeout=15,
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            results = data.get("results", [])[:10]

            # 批量获取 TV 详情以得到集数
            from concurrent.futures import ThreadPoolExecutor, as_completed
            def fetch_detail(item):
                tid = item.get("id")
                try:
                    d_resp = self.session.get(
                        f"{self.TMDB_API}/tv/{tid}",
                        params={"api_key": api_key, "language": "zh-CN"},
                        timeout=8,
                    )
                    if d_resp.status_code == 200:
                        d = d_resp.json()
                        item["number_of_episodes"] = d.get("number_of_episodes", 0) or 0
                        item["number_of_seasons"] = d.get("number_of_seasons", 0) or 0
                    else:
                        item["number_of_episodes"] = 0
                        item["number_of_seasons"] = 0
                except Exception:
                    item["number_of_episodes"] = 0
                    item["number_of_seasons"] = 0
                return item

            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {executor.submit(fetch_detail, item): item for item in results}
                enriched = []
                for f in as_completed(futures):
                    enriched.append(f.result())
            return enriched
        except Exception:
            return []

    def _imdb_api_search(self, title):
        """IMDb 搜索 — 使用官方建议 API（免费无 Key）"""
        import urllib.parse
        try:
            # IMDb suggestion API: 按首字母分桶
            q = title.strip()
            first = q[0].lower() if q else 'a'
            encoded = urllib.parse.quote(q)
            url = f"{self.IMDB_API}/suggestion/{first}/{encoded}.json"
            resp = self.session.get(url, headers={"User-Agent": "AnimeRenamer/1.0"}, timeout=10)
            if resp.status_code != 200:
                return []
            data = resp.json()
            items = data.get("d", []) or []
            results = []
            for item in items:
                # 只取 TV 类型
                qid = item.get("qid", "")
                if qid not in ("tvSeries", "tvMiniSeries", "tvShort"):
                    continue
                rid = item.get("id", "")
                # 提取 IMDb ID
                imdb_id = rid
                poster = item.get("i", {})
                cover = poster.get("imageUrl", "") if isinstance(poster, dict) else ""
                year = item.get("y", item.get("yr", "")) or ""
                results.append({
                    "id": imdb_id,
                    "name": item.get("l", ""),
                    "name_cn": item.get("l", ""),
                    "eps": 0,
                    "date": str(year) if year else "",
                    "type": qid,
                    "summary": "",
                    "cover": cover,
                    "score": 0,
                    "rank": 0,
                    "source": "IMDb",
                })
            return results[:10]
        except Exception:
            return []

    def _anilist_api_search(self, title):
        """AniList 搜索 — 别名"""
        return self._search_anilist(title)

    def _jikan_api_search(self, title):
        """Jikan 搜索 — 别名"""
        return self._search_jikan(title)

    def _anidb_api_search(self, title):
        """AniDB 搜索 — HTTP 搜索 (HTML 解析)"""
        try:
            url = "https://anidb.net/anime/list/"
            params = {"adb.search": title, "do.search": "1"}
            headers = {
                "User-Agent": "AnimeRenamer/1.0 (your@email.com)",
                "Accept": "text/html,application/xhtml+xml",
            }
            resp = self.session.get(url, params=params, headers=headers, timeout=15)
            if resp.status_code != 200:
                return []
            html = resp.text
            # 解析 HTML 表格提取标题和 ID
            results = []
            # 匹配多种可能的 HTML 结构
            import re as _re
            rows = _re.findall(
                r'<a\s+href="[^"]*?/anime/(\d+)"[^>]*>(.*?)</a>',
                html, _re.DOTALL | _re.IGNORECASE
            )
            if not rows:
                # 备用匹配：表格行中的链接
                rows = _re.findall(
                    r'<tr[^>]*>.*?<a\s+href="[^"]*?/anime/(\d+)"[^>]*>(.*?)</a>',
                    html, _re.DOTALL | _re.IGNORECASE
                )
            for aid, name in rows[:10]:
                name = _re.sub(r'<[^>]+>', '', name).strip()
                results.append({
                    "id": int(aid) if aid.isdigit() else aid,
                    "name": name,
                    "name_cn": name,
                    "eps": 0,
                    "date": "",
                    "type": "TV",
                    "summary": "",
                    "cover": "",
                    "score": 0,
                    "rank": 0,
                    "source": "AniDB",
                })
            return results
        except Exception:
            return []