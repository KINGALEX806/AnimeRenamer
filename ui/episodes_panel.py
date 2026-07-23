"""剧集元数据搜索面板 — FileBot 风格多数据源查询 + 番剧详情浏览
完全重写：修复封面残留、列拖动、筛选功能、主题适配、简介显示、剧集API、搜索按钮、联想词库、搜索源定义
"""

import re as _re_mod
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QScrollArea, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QSizePolicy, QSplitter, QStackedWidget,
    QCompleter, QDialog, QMenu
)
from PySide6.QtCore import Qt, Signal, QThread, QUrl, QSize, QTimer, QStringListModel, QEvent
from PySide6.QtGui import QColor, QFont, QPixmap, QKeySequence, QAction
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from ui.theme import theme_manager
from utils.config import load_config, set_config


# ── 数据源定义 ──
DB_INFO = {
    "bangumi":   {"label": "Bangumi",    "icon": "📚", "color": "#ff6b6b"},
    "themoviedb":{"label": "TheMovieDB", "icon": "🎬", "color": "#51cf66"},
    "thetvdb":   {"label": "TheTVDB",    "icon": "📺", "color": "#6cb2eb"},
    "tvmaze":    {"label": "TVMaze",     "icon": "📡", "color": "#ffd43b"},
    "imdb":      {"label": "IMDb",       "icon": "⭐", "color": "#f5c518"},
}

SOURCE_OPTIONS = [
    ("all",        "🌐  全部数据源"),
    ("bangumi",    "📚  Bangumi"),
    ("themoviedb", "🎬  TheMovieDB"),
    ("thetvdb",    "📺  TheTVDB"),
    ("tvmaze",     "📡  TVMaze"),
    ("imdb",       "⭐  IMDb"),
]

LANG_OPTIONS = [
    ("cn", "🇨🇳  中文"), ("jp", "🇯🇵  日语"),
    ("en", "🇺🇸  英语"), ("ro", "🏷   罗马音"),
]

SORT_OPTIONS = [
    ("airdate", "播出日期"), ("name", "名称"), ("eps", "集数"),
]

SEASON_OPTIONS = [
    ("all", "全部季"), ("s1", "第一季"), ("s2", "第二季"),
    ("s3", "第三季"), ("s4", "第四季"), ("s5", "第五季"), ("s6", "第六季"),
]

# ── 联想词库（扩充至 100+ 常见番剧名） ──
AUTOCOMPLETE_TERMS = [
    # 中文名
    "进击的巨人", "鬼灭之刃", "咒术回战", "间谍过家家", "葬送的芙莉莲",
    "刀剑神域", "某科学的超电磁炮", "Re:从零开始的异世界生活", "无职转生",
    "命运石之门", "紫罗兰永恒花园", "吹响吧！上低音号", "冰菓",
    "CLANNAD", "Angel Beats!", "Fate/stay night", "Fate/Zero",
    "Fate/Grand Order", "Fate/Apocrypha", "Fate/Extra", "Fate/strange Fake",
    "Fate/kaleid liner", "卫宫家今天的饭", "魔法少女伊莉雅",
    "魔法少女小圆", "化物语", "凉宫春日的忧郁", "轻音少女",
    "日常", "龙与虎", "未闻花名", "四月是你的谎言",
    "你的名字", "天气之子", "铃芽之旅", "千与千寻",
    "哈尔的移动城堡", "幽灵公主", "风之谷", "天空之城", "龙猫",
    "辉夜大小姐想让我告白", "青春猪头少年不会梦到兔女郎学姐",
    "我的青春恋爱物语果然有问题", "欢迎来到实力至上主义教室",
    "路人女主的养成方法", "樱花庄的宠物女孩", "中二病也要谈恋爱",
    "小林家的龙女仆", "干物妹小埋", "月刊少女野崎君",
    "齐木楠雄的灾难", "男子高中生的日常", "银魂", "海贼王", "火影忍者",
    "死神", "龙珠", "全职猎人", "钢之炼金术师", "JOJO的奇妙冒险",
    "东京喰种", "寄生兽", "一拳超人", "灵能百分百",
    "关于我转生变成史莱姆这档事", "为美好的世界献上祝福",
    "86-不存在的战区", "Lycoris Recoil", "孤独摇滚",
    "我推的孩子", "电锯人", "赛博朋克边缘行者",
    "药屋少女的呢喃", "我心里危险的东西", "迷宫饭",
    "夏日重现", "更衣人偶坠入爱河", "古见同学有交流障碍症",
    "总之就是非常可爱", "堀与宫村", "五等分的新娘",
    "想要成为影之实力者", "盾之勇者成名录", "声之形",
    "我想吃掉你的胰脏", "朝花夕誓", "玉子爱情故事",
    "无敌少侠", "Invincible", "无敌小子",
    # 日文/英文/罗马音
    "Steins;Gate", "Violet Evergarden", "Attack on Titan", "Demon Slayer",
    "Jujutsu Kaisen", "Spy x Family", "Sousou no Frieren",
    "Sword Art Online", "Mushoku Tensei", "Hibike! Euphonium",
    "One Piece", "Naruto", "Bleach", "Dragon Ball",
    "Kono Subarashii", "Overlord", "Youjo Senki", "Re:Zero",
    "86 Eighty Six", "Bocchi the Rock!", "Oshi no Ko",
    "Chainsaw Man", "Cyberpunk Edgerunners", "Fullmetal Alchemist",
    "Death Note", "Code Geass", "Neon Genesis Evangelion",
    "Cowboy Bebop", "Samurai Champloo", "Your Name",
    "Weathering with You", "Suzume", "Spirited Away",
    "Howl's Moving Castle", "Princess Mononoke", "My Neighbor Totoro",
    "Madoka Magica", "Bakemonogatari", "Haruhi Suzumiya",
    "K-On!", "Nichijou", "Toradora", "Anohana", "Your Lie in April",
    "Kaguya-sama", "Bunny Girl Senpai", "Oregairu",
    "Classroom of the Elite", "Made in Abyss", "Vinland Saga",
    "Mob Psycho 100", "Psycho-Pass", "Erased", "Tokyo Ghoul",
    "Parasyte", "One Punch Man", "Tensei Slime", "Konosuba",
    "Hunter x Hunter", "Gintama", "A Silent Voice",
    "I Want to Eat Your Pancreas", "Maquia",
    "Josee the Tiger and the Fish", "Summer Wars", "Wolf Children",
    "The Girl Who Leapt Through Time", "March Comes in Like a Lion",
    "Mushishi", "Natsume's Book of Friends", "Ping Pong the Animation",
    "The Tatami Galaxy", "Durarara!!", "Baccano!", "Monogatari Series",
    "Frieren: Beyond Journey's End", "The Apothecary Diaries",
    "Dandadan", "Kaiju No. 8", "Solo Leveling", "Wind Breaker",
    "The Dangers in My Heart", "Delicious in Dungeon",
    "Shangri-La Frontier", "The Eminence in Shadow",
    "Fate/Stay Night: Unlimited Blade Works", "Fate/Stay Night: Heaven's Feel",
    "Fate/Prototype", "Fate/Type Redline", "Lord El-Melloi II",
]


class EpisodesSearchWorker(QThread):
    """多数据源并发搜索"""

    result_ready = Signal(str, object)
    log = Signal(str)
    finished = Signal()

    def __init__(self, title, db_keys, config):
        super().__init__()
        self.title = title
        self.db_keys = db_keys
        self.config = config

    def run(self):
        from core.recognizer import AnimeRecognizer
        import time
        recognizer = AnimeRecognizer(config=self.config, log_callback=lambda m: self.log.emit(m))
        for db_key in self.db_keys:
            try:
                start = time.time()
                result = self._search_db(recognizer, db_key, self.title)
                elapsed = int((time.time() - start) * 1000)
                result["response_time_ms"] = elapsed
                result["db_key"] = db_key
                self.log.emit(f"[{DB_INFO.get(db_key, {}).get('label', db_key)}] 搜索完成，耗时 {elapsed}ms")
                self.result_ready.emit(db_key, result)
            except Exception as e:
                self.log.emit(f"[{DB_INFO.get(db_key, {}).get('label', db_key)}] 搜索出错: {e}")
                self.result_ready.emit(db_key, {
                    "db_key": db_key, "error": str(e), "response_time_ms": 0, "candidates": [],
                })
        self.finished.emit()

    def _search_db(self, r, db_key, title):
        if db_key == "bangumi":
            return self._process_bangumi(r._bgm_api_search(title))
        elif db_key == "themoviedb":
            return self._process_tmdb_list(r._tmdb_api_search(title))
        elif db_key == "thetvdb":
            return self._process_tvdb(r._thetvdb_api_search(title))
        elif db_key == "tvmaze":
            return self._process_tvmaze(r._tvmaze_api_search(title))
        elif db_key == "imdb":
            return self._process_imdb(r._imdb_api_search(title))
        elif db_key == "anilist":
            return self._process_generic(r._anilist_api_search(title), "AniList")
        elif db_key == "jikan":
            return self._process_generic(r._jikan_api_search(title), "Jikan")
        elif db_key == "anidb":
            return self._process_generic(r._anidb_api_search(title), "AniDB")
        return {"candidates": []}

    def _process_generic(self, items, source):
        """通用处理：将 recognizer 返回的列表转为 candidates 格式"""
        candidates = []
        for item in (items or []):
            candidates.append({
                "id": item.get("id"),
                "name_cn": item.get("name_cn", item.get("name", "")),
                "name": item.get("name", ""),
                "eps": item.get("eps", 0),
                "date": item.get("date", ""),
                "source": source, "type": item.get("type", ""),
                "summary": item.get("summary", ""),
                "cover": item.get("cover", ""),
                "score": item.get("score", 0), "rank": item.get("rank", 0),
            })
        return {"candidates": candidates}

    def _process_bangumi(self, items):
        candidates = []
        for item in (items or []):
            images = item.get("images") or {}
            rating = item.get("rating") or {}
            candidates.append({
                "id": item.get("id"), "name_cn": (item.get("name_cn") or "").strip(),
                "name": (item.get("name") or "").strip(),
                "eps": item.get("eps_count", 0) or item.get("eps", 0) or 0,
                "date": (item.get("air_date") or item.get("date") or ""),
                "source": "Bangumi", "type": (item.get("type") or ""),
                "summary": (item.get("summary") or "").strip(),
                "cover": (images.get("common") or images.get("medium") or images.get("large") or ""),
                "score": rating.get("score", 0) or 0,
                "rank": rating.get("rank", 0) or 0,
            })
        return {"candidates": candidates}

    def _process_tmdb_list(self, items):
        candidates = []
        for item in (items or []):
            poster = item.get("poster_path", "")
            cover = f"https://image.tmdb.org/t/p/w300{poster}" if poster else ""
            candidates.append({
                "id": item.get("id"), "name_cn": item.get("name", ""),
                "name": item.get("original_name", ""),
                "eps": item.get("number_of_episodes", 0) or 0,
                "date": (item.get("first_air_date") or "")[:4],
                "source": "TheMovieDB", "type": "TV",
                "summary": (item.get("overview", "") or "").strip(),
                "cover": cover, "score": (item.get("vote_average", 0) or 0), "rank": 0,
            })
        return {"candidates": candidates}

    def _process_tvdb(self, items):
        candidates = []
        for item in (items or []):
            candidates.append({
                "id": item.get("id"), "name_cn": item.get("name_cn", item.get("name", "")),
                "name": item.get("name", ""),
                "eps": item.get("eps", 0),
                "date": item.get("date", ""),
                "source": "TheTVDB", "type": "TV",
                "summary": item.get("summary", ""),
                "cover": item.get("cover", ""),
                "score": item.get("score", 0), "rank": 0,
            })
        return {"candidates": candidates}

    def _process_tvmaze(self, items):
        candidates = []
        for item in (items or []):
            candidates.append({
                "id": item.get("id"), "name_cn": item.get("name_cn", item.get("name", "")),
                "name": item.get("name", ""),
                "eps": item.get("eps", 0),
                "date": item.get("date", ""),
                "source": "TVMaze", "type": "TV",
                "summary": item.get("summary", ""),
                "cover": item.get("cover", ""),
                "score": item.get("score", 0), "rank": 0,
            })
        return {"candidates": candidates}

    def _process_imdb(self, items):
        candidates = []
        for item in (items or []):
            imdb_id = item.get("id", "")
            poster = item.get("poster", "")
            cover = item.get("cover", "") or poster
            eps = item.get("eps", 0)
            summary = item.get("summary", "")
            score = item.get("score", 0)
            candidates.append({
                "id": imdb_id,
                "name_cn": item.get("name", ""),
                "name": item.get("name", ""),
                "eps": eps,
                "date": item.get("date", ""),
                "source": "IMDb", "type": item.get("type", ""),
                "summary": summary,
                "cover": cover,
                "score": score, "rank": 0,
            })
        return {"candidates": candidates}

    def _try_imdb_scrape(self, imdb_id):
        """从 IMDb 页面抓取集数、评分、简介（JSON-LD 结构化数据）"""
        try:
            import requests as _req
            import re as _re
            import json as _json
            url = f"https://www.imdb.com/title/{imdb_id}/"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                       "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"}
            resp = _req.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                return None
            html = resp.text
            info = {}

            # JSON-LD 结构化数据
            m = _re.search(r'<script type="application/ld\+json">(.*?)</script>', html, _re.DOTALL)
            if m:
                try:
                    ld = _json.loads(m.group(1))
                    if isinstance(ld, dict):
                        if "aggregateRating" in ld and "ratingValue" in ld["aggregateRating"]:
                            info["score"] = float(ld["aggregateRating"]["ratingValue"])
                        if "numberOfEpisodes" in ld:
                            info["eps"] = int(ld["numberOfEpisodes"])
                        if "description" in ld:
                            info["summary"] = ld["description"]
                except (ValueError, _json.JSONDecodeError, KeyError):
                    pass

            # 备用正则
            if "score" not in info:
                m = _re.search(r'"ratingValue":\s*"?([\d.]+)"?', html)
                if m:
                    try:
                        info["score"] = float(m.group(1))
                    except ValueError:
                        pass
            if "eps" not in info:
                m = _re.search(r'"numberOfEpisodes":\s*(\d+)', html)
                if m:
                    info["eps"] = int(m.group(1))
            if "summary" not in info:
                m = _re.search(r'"description":\s*"([^"]+)"', html)
                if m:
                    info["summary"] = m.group(1).replace('\\"', '"').replace('\\n', '\n')

            return info if info else None
        except Exception:
            return None


class EpisodesDetailWorker(QThread):
    """获取番剧剧集列表 — 改进版：详细日志 + TMDB 逐季获取"""

    episodes_ready = Signal(list)
    log = Signal(str)

    def __init__(self, subject_id, db_key, config):
        super().__init__()
        self.subject_id = subject_id
        self.db_key = db_key
        self.config = config

    def run(self):
        import requests as req
        episodes = []
        self.log.emit(f"开始获取剧集列表: db={self.db_key}, subject_id={self.subject_id}")
        if self.db_key == "bangumi":
            self._fetch_bangumi_episodes(episodes, req)
        elif self.db_key == "themoviedb":
            self._fetch_tmdb_season_episodes(episodes, req)
        elif self.db_key == "tvmaze":
            self._fetch_tvmaze_episodes(episodes, req)
        elif self.db_key == "imdb":
            self._fetch_imdb_episodes(episodes, req)
        else:
            self.log.emit(f"不支持的数据源: {self.db_key}")
        self.log.emit(f"剧集列表获取完成: 共 {len(episodes)} 集")
        self.episodes_ready.emit(episodes)

    def _fetch_bangumi_episodes(self, episodes, req):
        """Bangumi API: GET /v0/episodes?subject_id={id}&type=0&limit=200"""
        try:
            url = "https://api.bgm.tv/v0/episodes"
            params = {"subject_id": self.subject_id, "type": 0, "limit": 200}
            headers = {"User-Agent": "AnimeRenamer/1.0"}
            self.log.emit(f"Bangumi 请求: {url}?subject_id={self.subject_id}&type=0&limit=200")
            resp = req.get(url, params=params, headers=headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                eps_data = data.get("data", []) if isinstance(data, dict) else []
                for ep in eps_data:
                    episodes.append({
                        "ep": ep.get("ep", 0), "sort": ep.get("sort", 0),
                        "name": ep.get("name", "") or "",
                        "name_cn": ep.get("name_cn", "") or "",
                        "type": ep.get("type", 0),
                    })
                self.log.emit(f"Bangumi: 获取到 {len(episodes)} 集")
            else:
                self.log.emit(f"Bangumi API 返回状态码 {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            self.log.emit(f"Bangumi 获取剧集失败: {e}")

    def _fetch_tmdb_season_episodes(self, episodes, req):
        """TMDB API: 先获取剧集季信息，再逐季获取每集标题
        GET /tv/{id} 获取 seasons 列表
        GET /tv/{id}/season/{season_number} 获取每季剧集
        """
        try:
            api_key = self.config.get("tmdb_api_key", "") or "1f54bd990f1cdfb230adb312546d765d"
            headers = {"User-Agent": "AnimeRenamer/1.0"}

            # 第一步：获取剧集基本信息（含 seasons 列表）
            show_url = f"https://api.themoviedb.org/3/tv/{self.subject_id}"
            show_params = {"api_key": api_key, "language": "zh-CN"}
            self.log.emit(f"TMDB 请求剧集信息: {show_url}")
            resp = req.get(show_url, params=show_params, headers=headers, timeout=15)
            if resp.status_code != 200:
                self.log.emit(f"TMDB TV详情 API 返回 {resp.status_code}: {resp.text[:200]}")
                return

            show_data = resp.json()
            seasons = show_data.get("seasons", [])
            self.log.emit(f"TMDB: 发现 {len(seasons)} 个季")

            # 第二步：逐季获取每集标题
            total_episodes = 0
            for season in seasons:
                sn = season.get("season_number", 0)
                if sn is None or sn < 0:
                    continue
                season_url = f"https://api.themoviedb.org/3/tv/{self.subject_id}/season/{sn}"
                season_params = {"api_key": api_key, "language": "zh-CN"}
                self.log.emit(f"TMDB 请求 Season {sn}: {season_url}")
                try:
                    season_resp = req.get(season_url, params=season_params, headers=headers, timeout=15)
                except Exception as e:
                    self.log.emit(f"TMDB Season {sn} 请求失败: {e}")
                    continue

                if season_resp.status_code != 200:
                    self.log.emit(f"TMDB Season {sn} API 返回 {season_resp.status_code}")
                    continue

                season_data = season_resp.json()
                season_eps = season_data.get("episodes", [])
                for ep in season_eps:
                    ep_num = ep.get("episode_number", 0)
                    ep_name = ep.get("name", "") or ""
                    episodes.append({
                        "ep": ep_num,
                        "sort": ep_num,
                        "name": ep_name,
                        "name_cn": ep_name,
                        "type": 0,
                    })
                self.log.emit(f"TMDB Season {sn}: 获取到 {len(season_eps)} 集")
                total_episodes += len(season_eps)

            self.log.emit(f"TMDB: 总计获取到 {total_episodes} 集")
        except Exception as e:
            self.log.emit(f"TMDB 获取剧集失败: {e}")

    def _fetch_tvmaze_episodes(self, episodes, req):
        """TVMaze API: GET /shows/{id}/episodes"""
        try:
            url = f"https://api.tvmaze.com/shows/{self.subject_id}/episodes"
            self.log.emit(f"TVMaze 请求: {url}")
            resp = req.get(url, headers={"User-Agent": "AnimeRenamer/1.0"}, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                for ep in (data or []):
                    episodes.append({
                        "ep": ep.get("number", 0), "sort": ep.get("number", 0),
                        "name": ep.get("name", "") or "",
                        "name_cn": ep.get("name", "") or "",
                        "type": 0,
                    })
                self.log.emit(f"TVMaze: 获取到 {len(episodes)} 集")
            else:
                self.log.emit(f"TVMaze API 返回 {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            self.log.emit(f"TVMaze 获取剧集失败: {e}")

    def _fetch_imdb_episodes(self, episodes, req):
        """IMDb: 从 IMDb 自有页面抓取剧集列表（__NEXT_DATA__ JSON）"""
        try:
            import re as _re
            import json as _json
            url = f"https://www.imdb.com/title/{self.subject_id}/episodes"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                       "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"}
            self.log.emit(f"IMDb 请求剧集列表: {url}")
            resp = req.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                self.log.emit(f"IMDb 剧集页面返回 {resp.status_code}")
                return

            html = resp.text

            # 方法1：从 __NEXT_DATA__ 提取（最完整的结构化数据）
            m = _re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, _re.DOTALL)
            if m:
                try:
                    data = _json.loads(m.group(1))
                    # 遍历 props 找到剧集数据
                    props = data.get("props", {}).get("pageProps", {})
                    # 可能的路径：contentData -> section -> episodes
                    content_data = props.get("contentData", {}) or props
                    self._extract_imdb_eps_from_json(content_data, episodes)
                    if episodes:
                        self.log.emit(f"IMDb (__NEXT_DATA__): 获取到 {len(episodes)} 集")
                        return
                except (ValueError, _json.JSONDecodeError, Exception):
                    pass

            # 方法2：从页面内嵌的 JSON 数据提取（备用）
            ep_matches = _re.findall(r'"episode":\s*(\d+)[^}]*?"name":\s*"([^"]+)"', html)
            if not ep_matches:
                ep_matches = _re.findall(r'"episodeNumber":\s*(\d+)[^}]*?"name":\s*"([^"]+)"', html)

            for ep_num, ep_name in ep_matches:
                try:
                    num = int(ep_num)
                except ValueError:
                    continue
                episodes.append({
                    "ep": num, "sort": num,
                    "name": ep_name,
                    "name_cn": ep_name,
                    "type": 0,
                })
            self.log.emit(f"IMDb: 获取到 {len(episodes)} 集")
        except Exception as e:
            self.log.emit(f"IMDb 获取剧集失败: {e}")

    def _extract_imdb_eps_from_json(self, data, episodes):
        """递归从 IMDb __NEXT_DATA__ JSON 中提取剧集列表"""
        import json as _json
        if isinstance(data, dict):
            # 直接查找 episodes 键
            for key in ("episodes", "items", "episodeItems"):
                if key in data and isinstance(data[key], list):
                    for ep in data[key]:
                        if isinstance(ep, dict):
                            ep_num = ep.get("episode", ep.get("episodeNumber", 0))
                            ep_name = ep.get("name", ep.get("title", "")) or ""
                            if ep_num:
                                episodes.append({
                                    "ep": int(ep_num),
                                    "sort": int(ep_num),
                                    "name": str(ep_name),
                                    "name_cn": str(ep_name),
                                    "type": 0,
                                })
                    if episodes:
                        return
            # 递归搜索子节点
            for v in data.values():
                self._extract_imdb_eps_from_json(v, episodes)
                if episodes:
                    return
        elif isinstance(data, list):
            for item in data:
                self._extract_imdb_eps_from_json(item, episodes)
                if episodes:
                    return


class EpisodesPanel(QWidget):
    """剧集搜索面板 — FileBot 风格"""

    episode_selected = Signal(dict)

    # ── 列宽最小值（独立于两个表格） ──
    _RESULTS_COL_MINS = [200, 90, 70, 90]
    _EPISODES_COL_MINS = [80, 200]

    def __init__(self):
        super().__init__()
        self.setObjectName("episodesPanel")
        self._search_worker = None
        self._detail_worker = None
        self._search_history = []
        self._all_results = {}
        self._all_candidates = []
        self._filtered_candidates = []
        self._current_detail = None
        self._current_episodes = []
        self._net_manager = None
        self._cover_cache = {}
        self._current_cover_url = None  # 追踪当前封面 URL，防止残留
        self._summary_expanded = False
        self._preloaded_episodes = None  # 预加载的剧集缓存
        self._preloaded_for_id = None    # 预加载对应的 candidate id

        # 排序切换跟踪
        self._last_sort_key = None
        self._sort_ascending = False  # 播出日期默认从最新到最老（降序）

        # 两个表格各自独立的列拖动状态标志
        self._results_adjusting = False
        self._episodes_adjusting = False

        self._setup_ui()
        self._load_history()

    # ══════════════════════════════════════════════════════════
    #  UI 构建
    # ══════════════════════════════════════════════════════════

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        self._build_title(layout)
        self._build_search_bar(layout)
        self._build_filter_bar(layout)
        self._build_history_section(layout)

        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFixedHeight(1)
        layout.addWidget(sep)

        self._build_main_content(layout)
        layout.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll)

    def _build_title(self, layout):
        c = theme_manager.colors
        self.title_label = QLabel("剧集搜索")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet(
            f"font-size: 22px; font-weight: 700; color: {c['text_primary']}; background: transparent;")
        layout.addWidget(self.title_label)

    def _build_search_bar(self, layout):
        c = theme_manager.colors
        bar = QHBoxLayout()
        bar.setSpacing(8)

        self.source_combo = QComboBox()
        self.source_combo.setObjectName("sourceCombo")
        self.source_combo.setMinimumWidth(130)
        self.source_combo.setMinimumHeight(34)
        self.source_combo.setToolTip("选择搜索数据源")
        for key, label in SOURCE_OPTIONS:
            self.source_combo.addItem(label, key)
        self._apply_source_combo_style()
        bar.addWidget(self.source_combo)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入番剧名称搜索...")
        self.search_input.setObjectName("searchKeywordInput")
        self.search_input.setMinimumHeight(34)
        self.search_input.returnPressed.connect(self._start_search)
        self.search_input.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.search_input.customContextMenuRequested.connect(self._on_search_context_menu)
        self._setup_autocomplete()
        bar.addWidget(self.search_input, stretch=1)

        self.find_btn = QPushButton("🔍 搜索")
        self.find_btn.setObjectName("primaryBtn")
        self.find_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.find_btn.setFixedWidth(120)
        self.find_btn.setMinimumHeight(34)
        self.find_btn.setStyleSheet("""
            QPushButton#primaryBtn {
                padding: 4px 8px;
            }
        """)
        self.find_btn.clicked.connect(self._start_search)
        bar.addWidget(self.find_btn)

        layout.addLayout(bar)

    def _setup_autocomplete(self):
        model = QStringListModel()
        model.setStringList(AUTOCOMPLETE_TERMS)
        self._completer = QCompleter(self)
        self._completer.setModel(model)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self._completer.setMaxVisibleItems(20)
        self._completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.search_input.setCompleter(self._completer)

        # 存储所有联想词条（用于空格时的 token 匹配）
        self._all_ac_terms = list(AUTOCOMPLETE_TERMS)

        # 动态联想：用户输入时实时从 Bangumi API 搜索补充词条
        self._autocomplete_timer = QTimer(self)
        self._autocomplete_timer.setSingleShot(True)
        self._autocomplete_timer.setInterval(300)
        self._autocomplete_timer.timeout.connect(self._fetch_autocomplete_suggestions)
        self.search_input.textChanged.connect(self._on_autocomplete_text_changed)
        self._ac_thread = None

    def _on_autocomplete_text_changed(self, text):
        # 去除首尾空格后判断长度，1字符以上触发联想
        stripped = text.strip()
        if len(stripped) >= 1:
            # 如果包含空格，使用 token 模糊匹配更新 completer 模型
            if ' ' in stripped:
                self._update_completer_for_tokens(stripped)
            self._autocomplete_timer.start()
        else:
            self._autocomplete_timer.stop()
            # 恢复完整词条列表
            self._restore_full_ac_model()

    def _update_completer_for_tokens(self, text):
        """输入含空格时，用 token 模糊匹配过滤联想词条"""
        tokens = [t.lower() for t in text.split() if t]
        if not tokens:
            return
        filtered = [item for item in self._all_ac_terms
                    if all(token in item.lower() for token in tokens)]
        if filtered:
            model = QStringListModel()
            model.setStringList(filtered[:20])
            self._completer.setModel(model)
            # 强制弹出联想框：先设置 prefix 再 complete
            self._completer.setCompletionPrefix(text)
            self._completer.complete()

    def _restore_full_ac_model(self):
        """恢复完整的联想词条模型"""
        model = QStringListModel()
        model.setStringList(self._all_ac_terms)
        self._completer.setModel(model)

    def _fetch_autocomplete_suggestions(self):
        """从 Bangumi API 实时搜索补充联想词（在线程中执行）"""
        text = self.search_input.text().strip()
        if len(text) < 1:
            return

        class AcWorker(QThread):
            result_ready = Signal(list)
            def __init__(self, query):
                super().__init__()
                self.query = query
            def run(self):
                try:
                    import requests as _req
                    resp = _req.get("https://api.bgm.tv/search/subject/" + _req.utils.quote(self.query),
                                    params={"type": 2, "responseGroup": "small", "max_results": 10},
                                    headers={"User-Agent": "AnimeRenamer/1.0"}, timeout=4)
                    if resp.status_code == 200:
                        data = resp.json()
                        items = data.get("list", []) if isinstance(data, dict) else []
                        new_terms = []
                        for item in items:
                            cn = (item.get("name_cn") or "").strip()
                            name = (item.get("name") or "").strip()
                            if cn and cn not in AUTOCOMPLETE_TERMS:
                                new_terms.append(cn)
                            if name and name not in AUTOCOMPLETE_TERMS:
                                new_terms.append(name)
                        self.result_ready.emit(new_terms)
                except Exception:
                    pass

        if self._ac_thread and self._ac_thread.isRunning():
            self._ac_thread.terminate()
        self._ac_thread = AcWorker(text)
        self._ac_thread.result_ready.connect(self._on_ac_results)
        self._ac_thread.start()

    def _on_ac_results(self, new_terms):
        if new_terms:
            merged = list(dict.fromkeys(AUTOCOMPLETE_TERMS + new_terms))
            self._all_ac_terms = merged
            # 检查当前输入是否含空格，如果是则重新应用 token 过滤
            current_text = self.search_input.text().strip()
            if ' ' in current_text:
                self._update_completer_for_tokens(current_text)
            else:
                model = QStringListModel()
                model.setStringList(merged)
                self._completer.setModel(model)
                self._completer.complete()

    def _build_filter_bar(self, layout):
        c = theme_manager.colors
        bar = QHBoxLayout()
        bar.setSpacing(10)
        bar.setAlignment(Qt.AlignmentFlag.AlignCenter)

        bar.addWidget(QLabel("季"))
        self.season_combo = QComboBox()
        self.season_combo.setObjectName("operationModeCombo")
        for key, label in SEASON_OPTIONS:
            self.season_combo.addItem(label, key)
        self.season_combo.currentIndexChanged.connect(self._apply_filters)
        bar.addWidget(self.season_combo)

        bar.addSpacing(20)
        bar.addWidget(QLabel("排序"))
        self.sort_combo = QComboBox()
        self.sort_combo.setObjectName("operationModeCombo")
        for key, label in SORT_OPTIONS:
            self.sort_combo.addItem(label, key)
        self.sort_combo.currentIndexChanged.connect(self._apply_filters)
        bar.addWidget(self.sort_combo)

        self.sort_order_btn = QPushButton("▼")
        self.sort_order_btn.setFixedSize(28, 28)
        self.sort_order_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sort_order_btn.setToolTip("切换升序/降序（当前：降序）")
        self.sort_order_btn.setStyleSheet(f"""
            QPushButton {{ background-color: {c["bg_input"]}; color: {c["text_secondary"]};
                border: 1px solid {c["border"]}; border-radius: 6px; font-size: 12px;
                font-weight: bold; padding: 0px; margin: 0px; outline: none; }}
            QPushButton:hover {{ border-color: {c["accent"]}; color: {c["accent"]}; outline: none; }}
            QPushButton:focus {{ outline: none; }}
            QPushButton:pressed {{ outline: none; }}
        """)
        self.sort_order_btn.clicked.connect(self._toggle_sort_order)
        bar.addWidget(self.sort_order_btn, alignment=Qt.AlignmentFlag.AlignVCenter)

        bar.addSpacing(20)
        bar.addWidget(QLabel("语言"))
        self.lang_combo = QComboBox()
        self.lang_combo.setObjectName("operationModeCombo")
        for key, label in LANG_OPTIONS:
            self.lang_combo.addItem(label, key)
        self.lang_combo.currentIndexChanged.connect(self._apply_filters)
        bar.addWidget(self.lang_combo)

        layout.addLayout(bar)

    def _build_history_section(self, layout):
        c = theme_manager.colors
        hdr = QHBoxLayout()
        self.hist_title = QLabel("历史记录")
        self.hist_title.setStyleSheet(
            f"font-size: 13px; font-weight: 600; color: {c['text_secondary']}; background: transparent;")
        hdr.addWidget(self.hist_title)
        hdr.addStretch()
        layout.addLayout(hdr)

        self.history_widget = QWidget()
        self.history_layout = QHBoxLayout(self.history_widget)
        self.history_layout.setContentsMargins(0, 0, 0, 0)
        self.history_layout.setSpacing(8)
        self.history_layout.addStretch()
        layout.addWidget(self.history_widget)

    def _build_main_content(self, layout):
        self.content_stack = QStackedWidget()
        self.content_stack.setMinimumHeight(300)
        self._build_search_results_page()
        self._build_detail_page()
        self.content_stack.addWidget(self.results_page)
        self.content_stack.addWidget(self.detail_page)
        self.content_stack.setCurrentIndex(0)
        layout.addWidget(self.content_stack, stretch=1)

    def _build_search_results_page(self):
        c = theme_manager.colors
        self.results_page = QWidget()
        page_layout = QVBoxLayout(self.results_page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(10)

        self.status_label = QLabel("输入番剧名称并点击「搜索」开始搜索")
        self.status_label.setStyleSheet(
            f"color: {c['text_muted']}; font-size: 12px; background: transparent;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        page_layout.addWidget(self.status_label)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(["剧集名称", "播出年份", "集数", "数据源"])
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.results_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.results_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setShowGrid(True)
        self.results_table.setWordWrap(False)
        self.results_table.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        self.results_table.setMinimumHeight(200)
        self.results_table.setMouseTracking(True)
        self.results_table.cellDoubleClicked.connect(self._on_result_double_clicked)
        self.results_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.results_table.customContextMenuRequested.connect(self._on_results_context_menu)

        header = self.results_table.horizontalHeader()
        for col in range(4):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(False)

        for col, w in enumerate(self._RESULTS_COL_MINS):
            self.results_table.setColumnWidth(col, w)

        header.sectionResized.connect(self._on_results_section_resized)

        # 窗口 resize 时重新分配列
        self.results_table.installEventFilter(self)

        self._apply_results_table_style()
        page_layout.addWidget(self.results_table, stretch=1)

        # 首次显示时自动填满（照搬 file_list.py 模式）
        QTimer.singleShot(0, self._fill_results_column)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.view_detail_btn = QPushButton("查看详情")
        self.view_detail_btn.setObjectName("smallBtn")
        self.view_detail_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.view_detail_btn.setFixedWidth(120)
        self.view_detail_btn.setEnabled(False)
        self.view_detail_btn.clicked.connect(self._show_detail_for_selected)
        btn_row.addWidget(self.view_detail_btn)

        btn_row.addSpacing(10)
        self.use_btn = QPushButton("使用此数据")
        self.use_btn.setObjectName("primaryBtn")
        self.use_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.use_btn.setFixedWidth(140)
        self.use_btn.setEnabled(False)
        self.use_btn.clicked.connect(self._use_selected)
        btn_row.addWidget(self.use_btn)
        page_layout.addLayout(btn_row)

    def _build_detail_page(self):
        c = theme_manager.colors
        self.detail_page = QWidget()
        detail_outer = QVBoxLayout(self.detail_page)
        detail_outer.setContentsMargins(0, 0, 0, 0)
        detail_outer.setSpacing(0)

        # 返回按钮
        back_row = QHBoxLayout()
        self.back_btn = QPushButton("← 返回搜索结果")
        self.back_btn.setObjectName("smallBtn")
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.clicked.connect(self._back_to_results)
        back_row.addWidget(self.back_btn)
        back_row.addStretch()
        detail_outer.addLayout(back_row)
        detail_outer.addSpacing(12)

        # 整个详情页内容放在 QScrollArea 中，内容过多时可以滚动
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(14)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        self.detail_splitter = splitter  # 保存引用，用于海报缩放
        splitter.splitterMoved.connect(self._on_detail_splitter_moved)

        # ── 左侧：封面 + 信息 ──
        left_panel = QWidget()
        self.left_panel = left_panel  # 保存引用，用于海报缩放
        left_panel.installEventFilter(self)  # 监听 Resize 事件
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 16, 0)
        left_layout.setSpacing(12)

        self.cover_label = QLabel()
        self.cover_label.setObjectName("coverLabel")
        self.cover_label.setMinimumSize(160, 224)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_label.setStyleSheet(
            f"background-color: {c['bg_card']}; border: 1px solid {c['border']}; "
            f"border-radius: 12px; color: {c['text_muted']}; font-size: 48px;")
        self.cover_label.setText("🎬")
        self.cover_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cover_label.setToolTip("双击放大查看封面")
        self.cover_label.installEventFilter(self)
        left_layout.addWidget(self.cover_label, alignment=Qt.AlignmentFlag.AlignTop)

        self.score_label = QLabel("")
        self.score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.score_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.score_label.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.score_label.customContextMenuRequested.connect(self._on_text_context_menu)
        self.score_label.setStyleSheet("font-size: 28px; font-weight: 700; color: #ff4444; background: transparent;")
        left_layout.addWidget(self.score_label)

        self.meta_label = QLabel("")
        self.meta_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.meta_label.setWordWrap(True)
        self.meta_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.meta_label.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.meta_label.customContextMenuRequested.connect(self._on_text_context_menu)
        self.meta_label.setStyleSheet(
            f"font-size: 14px; color: {c['text_secondary']}; background: transparent; line-height: 1.6;")
        left_layout.addWidget(self.meta_label)
        left_layout.addStretch()

        # ── 右侧：简介 + 剧集列表 ──
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(16, 0, 0, 0)
        right_layout.setSpacing(12)

        self.detail_title = QLabel("")
        self.detail_title.setWordWrap(True)
        self.detail_title.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.detail_title.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.detail_title.customContextMenuRequested.connect(self._on_text_context_menu)
        self.detail_title.setStyleSheet(
            f"font-size: 22px; font-weight: 700; color: {c['text_primary']}; background: transparent;")
        right_layout.addWidget(self.detail_title)

        # 简介区域（含展开/收起按钮）
        summary_header = QHBoxLayout()
        summary_header.setSpacing(8)
        summary_lbl = QLabel("简介")
        summary_lbl.setStyleSheet(
            f"font-size: 13px; font-weight: 600; color: {c['text_secondary']}; background: transparent;")
        summary_header.addWidget(summary_lbl)
        summary_header.addStretch()
        self.summary_toggle_btn = QPushButton("▼ 展开全部")
        self.summary_toggle_btn.setObjectName("smallBtn")
        self.summary_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.summary_toggle_btn.setFixedWidth(100)
        self.summary_toggle_btn.setFixedHeight(22)
        self.summary_toggle_btn.clicked.connect(self._toggle_summary)
        self.summary_toggle_btn.setVisible(False)
        summary_header.addWidget(self.summary_toggle_btn)
        right_layout.addLayout(summary_header)

        self.summary_label = QLabel("")
        self.summary_label.setWordWrap(True)
        self.summary_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.summary_label.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.summary_label.customContextMenuRequested.connect(self._on_text_context_menu)
        self.summary_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        self.summary_label.setStyleSheet(
            f"font-size: 14px; color: {c['text_secondary']}; background: transparent; line-height: 1.7;")
        self.summary_label.setMinimumHeight(60)
        right_layout.addWidget(self.summary_label)

        ep_header = QLabel("剧集列表")
        ep_header.setStyleSheet(
            f"font-size: 13px; font-weight: 600; color: {c['text_secondary']}; background: transparent;")
        right_layout.addWidget(ep_header)

        self.episodes_status = QLabel("")
        self.episodes_status.setStyleSheet(
            f"font-size: 12px; color: {c['text_muted']}; background: transparent;")
        right_layout.addWidget(self.episodes_status)

        self.episodes_table = QTableWidget()
        self.episodes_table.setColumnCount(2)
        self.episodes_table.setHorizontalHeaderLabels(["序号", "标题"])
        self.episodes_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.episodes_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.episodes_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.episodes_table.setAlternatingRowColors(True)
        self.episodes_table.verticalHeader().setVisible(False)
        self.episodes_table.setShowGrid(True)
        self.episodes_table.setWordWrap(False)
        self.episodes_table.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.episodes_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.episodes_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.episodes_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        self.episodes_table.setMouseTracking(True)
        self.episodes_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.episodes_table.customContextMenuRequested.connect(self._on_episodes_context_menu)

        eh = self.episodes_table.horizontalHeader()
        for col in range(2):
            eh.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
        eh.setStretchLastSection(False)

        for col, w in enumerate(self._EPISODES_COL_MINS):
            self.episodes_table.setColumnWidth(col, w)

        eh.sectionResized.connect(self._on_episodes_section_resized)

        # 窗口 resize 时重新分配列
        self.episodes_table.installEventFilter(self)

        self._apply_episodes_table_style()
        right_layout.addWidget(self.episodes_table, stretch=1)

        # 首次显示时自动填满（照搬 file_list.py 模式）
        QTimer.singleShot(0, self._fill_episodes_column)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        scroll_layout.addWidget(splitter, stretch=1)

        scroll.setWidget(scroll_content)
        detail_outer.addWidget(scroll, stretch=1)

    # ══════════════════════════════════════════════════════════
    #  列宽控制 — 完全照搬 file_list.py 模式
    #  弹性列（results=0, episodes=1）始终填满剩余空间
    # ══════════════════════════════════════════════════════════

    def eventFilter(self, obj, event):
        """事件过滤器：封面双击放大 + 海报栏位 resize 跟随 + 表格列填充"""
        # 封面双击放大（cover_label 可能尚未创建，加 hasattr 保护）
        if hasattr(self, 'cover_label') and obj is self.cover_label:
            if event.type() == QEvent.Type.MouseButtonDblClick:
                self._on_cover_double_click(event)
                return True
            elif event.type() == QEvent.Type.Resize:
                # 海报跟随栏位宽度缩放
                QTimer.singleShot(0, self._resize_cover_to_fit)
        # 左侧面板 resize 时海报跟随缩放（拖动 splitter 时触发）
        if hasattr(self, 'left_panel') and obj is self.left_panel and event.type() == QEvent.Type.Resize:
            QTimer.singleShot(0, self._resize_cover_to_fit)
        # 窗口 resize 时重新分配列（完全照搬 file_list.py 模式，加 hasattr 防崩溃）
        if hasattr(self, 'results_table') and obj is self.results_table and event.type() == QEvent.Type.Resize:
            QTimer.singleShot(0, self._fill_results_column)
        if hasattr(self, 'episodes_table') and obj is self.episodes_table and event.type() == QEvent.Type.Resize:
            QTimer.singleShot(0, self._fill_episodes_column)
        # Ctrl+C 复制剧集列表选中文字
        if hasattr(self, 'episodes_table') and obj is self.episodes_table and event.type() == QEvent.Type.KeyPress:
            if event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_C:
                self._copy_episodes_selection()
                return True
        return super().eventFilter(obj, event)

    # ── 搜索结果表格（4 列：剧集名称 / 播出年份 / 集数 / 数据源） ──

    def _on_results_section_resized(self, col, old_size, new_size):
        """用户手动拖拽列宽后：保持列 3 填满。完全照搬 file_list.py 模式。"""
        self._fill_results_column()

    def _fill_results_column(self):
        """让列 3（数据源）填满剩余空间，确保每列不低于最小宽度。
        完全照搬 file_list.py 的 _fill_column_4 逻辑。"""
        if self._results_adjusting:
            return
        self._results_adjusting = True

        total = self.results_table.viewport().width()
        if total <= 0:
            self._results_adjusting = False
            return

        mins = self._RESULTS_COL_MINS

        # 第一步：确保列 0-2 不低于各自的最小宽度
        for col in range(3):
            if self.results_table.columnWidth(col) < mins[col]:
                self.results_table.setColumnWidth(col, mins[col])

        used = sum(self.results_table.columnWidth(c) for c in range(3))
        c3 = total - used

        if c3 >= mins[3]:
            self.results_table.setColumnWidth(3, c3)
        else:
            # 列 3 不够最小宽度，从列 2→1→0 依次压缩
            need = mins[3] - c3
            for col in (2, 1, 0):
                if need <= 0:
                    break
                cur = self.results_table.columnWidth(col)
                can_shrink = cur - mins[col]
                if can_shrink > 0:
                    shrink = min(can_shrink, need)
                    self.results_table.setColumnWidth(col, cur - shrink)
                    need -= shrink
            used = sum(self.results_table.columnWidth(c) for c in range(3))
            self.results_table.setColumnWidth(3, max(total - used, mins[3]))

        self._results_adjusting = False

    # ── 剧集列表表格（2 列：序号 / 标题） ──

    def _on_episodes_section_resized(self, col, old_size, new_size):
        """用户手动拖拽列宽后：保持列 1 填满。完全照搬 file_list.py 模式。"""
        self._fill_episodes_column()

    def _fill_episodes_column(self):
        """让列 1（标题）填满剩余空间，确保每列不低于最小宽度。
        完全照搬 file_list.py 的 _fill_column_4 逻辑。"""
        if self._episodes_adjusting:
            return
        self._episodes_adjusting = True

        total = self.episodes_table.viewport().width()
        if total <= 0:
            self._episodes_adjusting = False
            return

        mins = self._EPISODES_COL_MINS

        if self.episodes_table.columnWidth(0) < mins[0]:
            self.episodes_table.setColumnWidth(0, mins[0])

        used = self.episodes_table.columnWidth(0)
        c1 = total - used

        if c1 >= mins[1]:
            self.episodes_table.setColumnWidth(1, c1)
        else:
            # 列 1 不够最小宽度，从列 0 压缩
            need = mins[1] - c1
            cur = self.episodes_table.columnWidth(0)
            can_shrink = cur - mins[0]
            if can_shrink > 0:
                shrink = min(can_shrink, need)
                self.episodes_table.setColumnWidth(0, cur - shrink)
                need -= shrink
            used = self.episodes_table.columnWidth(0)
            self.episodes_table.setColumnWidth(1, max(total - used, mins[1]))

        self._episodes_adjusting = False

    # ══════════════════════════════════════════════════════════
    #  表格样式
    # ══════════════════════════════════════════════════════════

    def _apply_results_table_style(self):
        c = theme_manager.colors
        self.results_table.setStyleSheet(f"""
            QTableWidget {{ background-color: transparent; border: 1px solid {c["grid"]};
                gridline-color: {c["grid"]}; selection-background-color: {c["bg_table_hover"]};
                selection-color: {c["text_primary"]}; color: {c["text_primary"]}; outline: none;
                alternate-background-color: {c["bg_table_alt"]}; border-radius: 12px; }}
            QTableWidget::item {{ padding: 10px 14px; border-bottom: 1px solid {c["border"]}; background: transparent; }}
            QTableWidget::item:selected {{ background-color: {c["bg_table_hover"]}; color: {c["text_primary"]}; }}
            QHeaderView::section {{ background-color: {c["bg_table_header"]}; color: {c["text_secondary"]};
                padding: 12px 14px; border: none; border-right: 1px solid {c["grid"]};
                border-bottom: 1px solid {c["border_glow"]}; font-weight: 600; font-size: 12px; letter-spacing: 0.3px; }}
        """)

    def _apply_episodes_table_style(self):
        c = theme_manager.colors
        self.episodes_table.setStyleSheet(f"""
            QTableWidget {{ background-color: transparent; border: 1px solid {c["grid"]};
                gridline-color: {c["grid"]}; selection-background-color: {c["bg_table_hover"]};
                selection-color: {c["text_primary"]}; color: {c["text_primary"]}; outline: none;
                alternate-background-color: {c["bg_table_alt"]}; border-radius: 12px; }}
            QTableWidget::item {{ padding: 8px 12px; border-bottom: 1px solid {c["border"]}; background: transparent; }}
            QTableWidget::item:selected {{ background-color: {c["bg_table_hover"]}; color: {c["text_primary"]}; }}
            QHeaderView::section {{ background-color: {c["bg_table_header"]}; color: {c["text_secondary"]};
                padding: 10px 12px; border: none; border-right: 1px solid {c["grid"]};
                border-bottom: 1px solid {c["border_glow"]}; font-weight: 600; font-size: 12px; }}
        """)

    def _reapply_table_colors(self):
        """主题切换后重新设置表格项的前景色，确保暗色/亮色模式正确适配"""
        c = theme_manager.colors
        # 搜索结果表格
        for row in range(self.results_table.rowCount()):
            item0 = self.results_table.item(row, 0)
            if item0:
                item0.setForeground(QColor(c["text_primary"]))
            item1 = self.results_table.item(row, 1)
            if item1:
                item1.setForeground(QColor(c["text_secondary"]))
            # 第2列（数据源）保持其 db_color，不覆盖
        # 剧集列表表格
        for row in range(self.episodes_table.rowCount()):
            item0 = self.episodes_table.item(row, 0)
            if item0:
                item0.setForeground(QColor(c["text_secondary"]))
            item1 = self.episodes_table.item(row, 1)
            if item1:
                item1.setForeground(QColor(c["text_primary"]))

    def _apply_source_combo_style(self):
        c = theme_manager.colors
        self.source_combo.setStyleSheet(f"""
            QComboBox#sourceCombo {{ background-color: {c["bg_input"]}; color: {c["text_primary"]};
                border: 1px solid {c["border"]}; border-radius: 8px; padding: 4px 10px;
                font-size: 12px; min-height: 32px; }}
            QComboBox#sourceCombo:hover {{ border-color: {c["accent"]}; }}
            QComboBox#sourceCombo QAbstractItemView {{ background-color: {c["bg_card"]};
                color: {c["text_primary"]}; border: 1px solid {c["border"]}; border-radius: 8px;
                padding: 4px; selection-background-color: {c["accent"]}; selection-color: #ffffff; outline: none; }}
        """)

    # ══════════════════════════════════════════════════════════
    #  搜索逻辑
    # ══════════════════════════════════════════════════════════

    def _start_search(self):
        title = self.search_input.text().strip()
        if not title:
            return

        self._add_to_history(title)
        self.find_btn.setEnabled(False)
        self.status_label.setText(f"正在搜索 \"{title}\"...")
        self._all_results = {}
        self._all_candidates = []
        self._filtered_candidates = []
        self.results_table.setRowCount(0)
        self.view_detail_btn.setEnabled(False)
        self.use_btn.setEnabled(False)
        self.content_stack.setCurrentIndex(0)

        config = load_config()
        source_key = self.source_combo.currentData()
        if source_key and source_key != "all":
            db_keys = [source_key]
        else:
            # 使用全局配置中的搜索源顺序和启用状态
            db_order = config.get("db_order", ["bangumi", "themoviedb", "tvmaze", "thetvdb", "imdb"])
            db_enabled = config.get("db_enabled", {})
            db_keys = [k for k in db_order if db_enabled.get(k, True)]

        if self._search_worker and self._search_worker.isRunning():
            self._search_worker.terminate()

        self._search_worker = EpisodesSearchWorker(title, db_keys, config)
        self._search_worker.result_ready.connect(self._on_result_ready)
        self._search_worker.finished.connect(self._on_search_finished)
        self._search_worker.start()

    def _on_result_ready(self, db_key, result):
        self._all_results[db_key] = result
        self._refresh_table()

    def _on_search_finished(self):
        self.find_btn.setEnabled(True)
        total = sum(len(v.get("candidates", [])) for v in self._all_results.values())
        dbs = len(self._all_results)
        if total == 0:
            self.status_label.setText("未找到结果，请尝试其他关键词")
        else:
            self.status_label.setText(f"找到 {total} 个结果（来自 {dbs} 个数据源）")
            # 内部预加载第一项详情（不切换页面，只后台加载数据）
            if self._filtered_candidates:
                QTimer.singleShot(100, self._preload_first_detail)

    def _refresh_table(self):
        """从 _all_results 重新构建 _all_candidates 并应用筛选/排序/语言"""
        c = theme_manager.colors
        self._all_candidates = []

        for db_key, result in self._all_results.items():
            info = DB_INFO.get(db_key, {"label": db_key, "icon": "📄", "color": c["text_secondary"]})
            for cand in result.get("candidates", []):
                cand["_db_key"] = db_key
                cand["_db_label"] = info["label"]
                cand["_db_icon"] = info["icon"]
                cand["_db_color"] = info["color"]
                cand["_response_time"] = result.get("response_time_ms", 0)
                self._all_candidates.append(cand)

        self._apply_filters()

    def _render_table_rows(self, candidates):
        """将候选列表渲染到表格中"""
        c = theme_manager.colors
        lang = self.lang_combo.currentData()

        self.results_table.setRowCount(0)
        self.results_table.setRowCount(len(candidates))

        for i, cand in enumerate(candidates):
            # 根据语言选择显示名称
            if lang == "cn":
                name = cand.get("name_cn") or cand.get("name") or "Unknown"
            elif lang == "jp":
                name = cand.get("name") or cand.get("name_cn") or "Unknown"
            elif lang == "en":
                name = cand.get("name") or cand.get("name_cn") or "Unknown"
            else:  # ro - 罗马音
                name = cand.get("name") or cand.get("name_cn") or "Unknown"

            icon = cand["_db_icon"]
            name_item = QTableWidgetItem(f"  {icon}  {name}")
            name_item.setToolTip(f"{cand.get('name', '')}\n{cand.get('type', '')}")
            name_item.setForeground(QColor(c["text_primary"]))
            self.results_table.setItem(i, 0, name_item)

            # 播出年份
            year = (cand.get("date", "") or "")[:4]
            year_item = QTableWidgetItem(year)
            year_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            year_item.setForeground(QColor(c["text_secondary"]))
            self.results_table.setItem(i, 1, year_item)

            eps = cand.get("eps", 0)
            eps_text = f"{eps} 集" if eps else "?"
            eps_item = QTableWidgetItem(eps_text)
            eps_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            eps_item.setForeground(QColor(c["text_secondary"]))
            self.results_table.setItem(i, 2, eps_item)

            source = cand["_db_label"]
            source_item = QTableWidgetItem(source)
            source_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            source_item.setForeground(QColor(c["text_secondary"]))
            self.results_table.setItem(i, 3, source_item)

            self.results_table.setRowHeight(i, 42)

        # 断开旧连接避免重复绑定
        try:
            self.results_table.itemSelectionChanged.disconnect()
        except Exception:
            pass
        self.results_table.itemSelectionChanged.connect(lambda: self._on_selection_changed())

    def _on_selection_changed(self):
        has_sel = len(self.results_table.selectedItems()) > 0
        self.use_btn.setEnabled(has_sel)
        self.view_detail_btn.setEnabled(has_sel)

    def _on_result_double_clicked(self, row, col):
        filtered = self._filtered_candidates if self._filtered_candidates else self._all_candidates
        if row < 0 or row >= len(filtered):
            return
        self._show_detail(filtered[row])

    def _on_results_context_menu(self, pos):
        """搜索结果表格右键菜单（中文）"""
        row = self.results_table.rowAt(pos.y())
        filtered = self._filtered_candidates if self._filtered_candidates else self._all_candidates
        if row < 0 or row >= len(filtered):
            return

        self.results_table.selectRow(row)
        c = theme_manager.colors
        menu = QMenu(self.results_table)
        menu.setStyleSheet(f"""
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
        """)

        cand = filtered[row]
        name = cand.get("name_cn") or cand.get("name") or "Unknown"

        copy_name = menu.addAction(f"复制名称: {name}")
        copy_name.triggered.connect(lambda: self._copy_to_clipboard(name))

        menu.addSeparator()

        detail_action = menu.addAction("查看详情")
        detail_action.triggered.connect(lambda: self._show_detail(cand))

        menu.addSeparator()

        use_action = menu.addAction("使用此数据")
        use_action.triggered.connect(lambda: self.episode_selected.emit(cand))

        global_pos = self.results_table.viewport().mapToGlobal(pos)
        menu.exec(global_pos)

    def _copy_to_clipboard(self, text):
        """复制文本到剪贴板"""
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(text)

    def _copy_episodes_selection(self):
        """复制剧集列表选中单元格的文字"""
        from PySide6.QtWidgets import QApplication
        items = self.episodes_table.selectedItems()
        if items:
            text = items[0].text()
            QApplication.clipboard().setText(text)

    def _on_episodes_context_menu(self, pos):
        """剧集列表右键菜单（复制文字）"""
        row = self.episodes_table.rowAt(pos.y())
        col = self.episodes_table.columnAt(pos.x())
        if row < 0 or row >= len(self._current_episodes):
            return

        c = theme_manager.colors
        menu = QMenu(self.episodes_table)
        menu.setStyleSheet(f"""
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
        """)

        item = self.episodes_table.item(row, col)
        if item:
            text = item.text()
            if len(text) > 30:
                display_text = text[:30] + "..."
            else:
                display_text = text
            copy_action = menu.addAction(f"复制: {display_text}")
            copy_action.triggered.connect(lambda t=text: self._copy_to_clipboard(t))

        menu.exec(self.episodes_table.viewport().mapToGlobal(pos))

    def _on_search_context_menu(self, pos):
        """搜索框中文右键菜单"""
        c = theme_manager.colors
        menu = QMenu(self.search_input)
        menu.setStyleSheet(f"""
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
            QMenu::item:disabled {{
                color: {c["text_muted"]};
            }}
        """)

        has_selection = self.search_input.hasSelectedText()
        can_undo = self.search_input.isUndoAvailable()
        can_redo = self.search_input.isRedoAvailable()

        undo_action = QAction("撤销", menu)
        undo_action.setShortcut(QKeySequence("Ctrl+Z"))
        undo_action.setShortcutVisibleInContextMenu(True)
        undo_action.setEnabled(can_undo)
        undo_action.triggered.connect(self.search_input.undo)
        menu.addAction(undo_action)

        redo_action = QAction("重做", menu)
        redo_action.setShortcut(QKeySequence("Ctrl+Y"))
        redo_action.setShortcutVisibleInContextMenu(True)
        redo_action.setEnabled(can_redo)
        redo_action.triggered.connect(self.search_input.redo)
        menu.addAction(redo_action)

        menu.addSeparator()

        cut_action = QAction("剪切", menu)
        cut_action.setShortcut(QKeySequence("Ctrl+X"))
        cut_action.setShortcutVisibleInContextMenu(True)
        cut_action.setEnabled(has_selection)
        cut_action.triggered.connect(self.search_input.cut)
        menu.addAction(cut_action)

        copy_action = QAction("复制", menu)
        copy_action.setShortcut(QKeySequence("Ctrl+C"))
        copy_action.setShortcutVisibleInContextMenu(True)
        copy_action.setEnabled(has_selection)
        copy_action.triggered.connect(self.search_input.copy)
        menu.addAction(copy_action)

        paste_action = QAction("粘贴", menu)
        paste_action.setShortcut(QKeySequence("Ctrl+V"))
        paste_action.setShortcutVisibleInContextMenu(True)
        paste_action.triggered.connect(self.search_input.paste)
        menu.addAction(paste_action)

        delete_action = QAction("删除", menu)
        delete_action.setShortcut(QKeySequence("Del"))
        delete_action.setShortcutVisibleInContextMenu(True)
        delete_action.setEnabled(has_selection)
        delete_action.triggered.connect(lambda: self.search_input.del_())
        menu.addAction(delete_action)

        menu.addSeparator()

        select_all_action = QAction("全选", menu)
        select_all_action.setShortcut(QKeySequence("Ctrl+A"))
        select_all_action.setShortcutVisibleInContextMenu(True)
        select_all_action.triggered.connect(self.search_input.selectAll)
        menu.addAction(select_all_action)

        menu.exec(self.search_input.mapToGlobal(pos))

    def _on_text_context_menu(self, pos):
        """详情页可选中文字标签的中文右键菜单"""
        label = self.sender()
        if not isinstance(label, QLabel):
            return
        c = theme_manager.colors
        menu = QMenu(label)
        menu.setStyleSheet(f"""
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
            QMenu::item:disabled {{
                color: {c["text_muted"]};
            }}
        """)

        has_selection = label.hasSelectedText()

        copy_action = QAction("复制", menu)
        copy_action.setShortcut(QKeySequence("Ctrl+C"))
        copy_action.setShortcutVisibleInContextMenu(True)
        copy_action.setEnabled(has_selection)
        copy_action.triggered.connect(lambda: self._copy_label_text(label))
        menu.addAction(copy_action)

        menu.addSeparator()

        select_all_action = QAction("全选", menu)
        select_all_action.setShortcut(QKeySequence("Ctrl+A"))
        select_all_action.setShortcutVisibleInContextMenu(True)
        select_all_action.triggered.connect(lambda: self._select_all_label_text(label))
        menu.addAction(select_all_action)

        menu.exec(label.mapToGlobal(pos))

    def _copy_label_text(self, label):
        """复制 QLabel 选中的文字"""
        from PySide6.QtWidgets import QApplication
        if label.hasSelectedText():
            QApplication.clipboard().setText(label.selectedText())
        else:
            QApplication.clipboard().setText(label.text())

    def _select_all_label_text(self, label):
        """全选 QLabel 文字（通过模拟鼠标操作）"""
        # QLabel 不支持直接全选，通过设置 selection 来模拟
        from PySide6.QtGui import QTextCursor
        # 使用 QLabel 的 selectedText 无法设置，改用复制全文
        pass

    # ══════════════════════════════════════════════════════════
    #  筛选 / 排序 / 语言切换
    # ══════════════════════════════════════════════════════════

    def _apply_filters(self):
        """对 _all_candidates 应用季筛选、排序和语言切换，立即生效"""
        if not self._all_candidates:
            return

        candidates = list(self._all_candidates)

        # ── 季筛选 ──
        season = self.season_combo.currentData()
        if season and season != "all":
            candidates = self._filter_by_season(candidates, season)

        # ── 排序（切换按钮控制方向） ──
        sort_key = self.sort_combo.currentData()
        if sort_key == "airdate":
            candidates.sort(key=lambda c: c.get("date", "") or "", reverse=not self._sort_ascending)
        elif sort_key == "name":
            candidates.sort(key=lambda c: (c.get("name_cn") or c.get("name") or "").lower(),
                            reverse=not self._sort_ascending)
        elif sort_key == "eps":
            candidates.sort(key=lambda c: c.get("eps", 0), reverse=not self._sort_ascending)

        self._filtered_candidates = candidates
        self._render_table_rows(candidates)

    def _toggle_sort_order(self):
        """切换排序方向"""
        self._sort_ascending = not self._sort_ascending
        if self._sort_ascending:
            self.sort_order_btn.setText("▲")
            self.sort_order_btn.setToolTip("切换升序/降序（当前：升序）")
        else:
            self.sort_order_btn.setText("▼")
            self.sort_order_btn.setToolTip("切换升序/降序（当前：降序）")
        self._apply_filters()

    def _filter_by_season(self, candidates, season_key):
        """根据季号筛选候选列表。season_key 如 's1', 's2' 等"""
        try:
            season_num = int(season_key[1:])
        except (ValueError, IndexError):
            return candidates

        # 季号映射模式
        season_patterns = [
            (rf"第\s*{season_num}\s*季", 1.0),
            (rf"Season\s*{season_num}", 1.0),
            (rf"\bS{season_num}\b", 1.0),
            (rf"{season_num}(?:st|nd|rd|th)\s+Season", 1.0),
            (rf"第\s*{season_num}\s*期", 0.8),
            (rf"Part\s*{season_num}", 0.8),
            (rf"\b{season_num}\b", 0.5),
        ]

        filtered = []
        for cand in candidates:
            name = (cand.get("name_cn") or cand.get("name") or "")
            score = 0.0
            for pattern, weight in season_patterns:
                if _re_mod.search(pattern, name, _re_mod.IGNORECASE):
                    score = max(score, weight)

            if score >= 0.5:
                cand["_season_score"] = score
                filtered.append(cand)

        # 如果没匹配到任何结果，返回全部（不过滤）
        if not filtered:
            return candidates

        filtered.sort(key=lambda c: c.get("_season_score", 0), reverse=True)
        return filtered

    # ══════════════════════════════════════════════════════════
    #  详情页
    # ══════════════════════════════════════════════════════════

    def _preload_first_detail(self):
        """内部预加载第一项详情：后台加载封面和剧集，不切换页面"""
        if not self._filtered_candidates:
            return
        cand = self._filtered_candidates[0]
        preload_id = cand.get("id")
        # 预加载封面
        cover_url = cand.get("cover", "")
        if cover_url and cover_url not in self._cover_cache:
            self._load_cover(cover_url)
        # 预加载剧集列表
        db_key = cand.get("_db_key", cand.get("source", "").lower())
        if preload_id and db_key and not self._current_episodes:
            self._preloaded_for_id = preload_id  # 提前记录预加载的 ID
            self._fetch_episodes_internal(preload_id, db_key)
        # IMDb 数据源：预加载评分/简介/集数
        if db_key == "imdb" and preload_id:
            self._scrape_imdb_async(cand)

    def _fetch_episodes_internal(self, subject_id, db_key):
        """内部预加载剧集（不显示状态/不切换页面）"""
        if self._detail_worker and self._detail_worker.isRunning():
            return  # 已有任务在跑，不重复
        config = load_config()
        self._detail_worker = EpisodesDetailWorker(subject_id, db_key, config)
        self._detail_worker.episodes_ready.connect(self._on_preload_episodes_ready)
        self._detail_worker.log.connect(lambda msg: None)  # 静默
        self._detail_worker.start()

    def _on_preload_episodes_ready(self, episodes):
        """预加载的剧集数据就绪，缓存起来"""
        self._preloaded_episodes = episodes
        # _preloaded_for_id 已在 _preload_first_detail 中设置，不覆盖
        # 断开信号避免后续干扰
        if self._detail_worker:
            try:
                self._detail_worker.episodes_ready.disconnect(self._on_preload_episodes_ready)
            except Exception:
                pass

    def _show_detail_for_selected(self):
        row = self.results_table.currentRow()
        filtered = self._filtered_candidates if self._filtered_candidates else self._all_candidates
        if row < 0 or row >= len(filtered):
            return
        self._show_detail(filtered[row])

    def _show_detail(self, cand):
        c = theme_manager.colors
        self._current_detail = cand
        self._current_episodes = []

        # ── IMDb 数据源：从 IMDb 页面抓取评分/简介/集数（非阻塞，在线程中执行） ──
        db_key = cand.get("_db_key", "")
        if db_key == "imdb" and (not cand.get("score") or not cand.get("summary")):
            imdb_id = cand.get("id", "")
            if imdb_id:
                self._scrape_imdb_async(cand)

        # ── 调试：显示候选数据 ──
        keys = [k for k in cand.keys() if not k.startswith("_")]
        self.episodes_status.setText(f"数据: {', '.join(keys[:8])}")

        # ── 修复 1：封面残留 — 先清空再加载新封面 ──
        self.cover_label.setText("🎬")
        self.cover_label.setPixmap(QPixmap())
        self.cover_label.setStyleSheet(
            f"background-color: {c['bg_card']}; border: 1px solid {c['border']}; "
            f"border-radius: 12px; color: {c['text_muted']}; font-size: 48px;")

        name = cand.get("name_cn") or cand.get("name") or "Unknown"
        self.detail_title.setText(name)

        score = cand.get("score", 0)
        if score:
            self.score_label.setText(f"★ {score:.1f}")
        else:
            self.score_label.setText("")

        date_str = cand.get("date", "") or ""
        year = date_str[:4] if date_str else ""
        eps = cand.get("eps", 0)
        source = cand.get("_db_label", cand.get("source", ""))
        meta_parts = []
        if date_str:
            meta_parts.append(f"📅 {date_str}")
        if eps:
            meta_parts.append(f"📺 {eps} 集")
        if source:
            meta_parts.append(f"📡 {source}")
        self.meta_label.setText("\n".join(meta_parts))

        # ── 修复 5：简介显示 — 默认展开 ──
        summary = cand.get("summary", "")
        if summary:
            summary = _re_mod.sub(r'<[^>]+>', '', summary)
            self._full_summary = summary
            # 默认展开显示全部
            self.summary_label.setText(summary)
            self.summary_label.setMaximumHeight(16777215)
            self.summary_label.setMinimumHeight(0)
            self.summary_toggle_btn.setVisible(True)
            self.summary_toggle_btn.setText("▲ 收起")
            self._summary_expanded = True
        else:
            self._full_summary = ""
            self.summary_label.setText("暂无简介")
            self.summary_label.setMaximumHeight(16777215)
            self.summary_label.setMinimumHeight(0)
            self.summary_toggle_btn.setVisible(False)
            self._summary_expanded = True

        # 强制更新布局，确保简介在 QSplitter 中完整显示
        self.summary_label.adjustSize()
        self.summary_label.updateGeometry()
        if self.summary_label.parent():
            self.summary_label.parent().updateGeometry()
        self.detail_page.updateGeometry()

        # 加载封面
        cover_url = cand.get("cover", "")
        if cover_url:
            self._load_cover(cover_url)
        else:
            self.cover_label.setText("🎬")
            self.cover_label.setStyleSheet(
                f"background-color: {c['bg_card']}; border: 1px solid {c['border']}; "
                f"border-radius: 12px; color: {c['text_muted']}; font-size: 48px;")

        self.content_stack.setCurrentIndex(1)

        self.episodes_status.setText("")
        subject_id = cand.get("id")
        db_key = cand.get("_db_key", cand.get("source", "").lower())
        if subject_id and db_key:
            # 检查是否有预加载的剧集数据可用
            if (self._preloaded_episodes is not None and
                    self._preloaded_for_id == cand.get("id")):
                self._current_episodes = self._preloaded_episodes
                self._refresh_episodes_table()
                self.episodes_status.setText(f"已加载 {len(self._preloaded_episodes)} 集（预加载）")
                self._preloaded_episodes = None
                self._preloaded_for_id = None
            else:
                self._fetch_episodes(subject_id, db_key)
        else:
            self.episodes_status.setText(f"无法获取剧集：id={subject_id}, db={db_key}")

    def _toggle_summary(self):
        """展开/收起简介"""
        if self._summary_expanded:
            # 收起
            if len(self._full_summary) > 300:
                self.summary_label.setText(self._full_summary[:300] + "...")
            else:
                self.summary_label.setText(self._full_summary)
            self.summary_label.setMaximumHeight(120)
            self.summary_toggle_btn.setText("▼ 展开全部")
            self._summary_expanded = False
        else:
            # 展开
            self.summary_label.setText(self._full_summary)
            self.summary_label.setMaximumHeight(16777215)
            self.summary_label.setMinimumHeight(0)
            self.summary_toggle_btn.setText("▲ 收起")
            self._summary_expanded = True

    def _on_cover_double_click(self, event):
        """双击封面放大查看"""
        if not self._current_cover_url:
            return
        c = theme_manager.colors
        pixmap = self._cover_cache.get(self._current_cover_url)
        if not pixmap or pixmap.isNull():
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("封面预览")
        dialog.setStyleSheet(f"QDialog {{ background-color: {c['bg_primary']}; }}")
        dialog.setMinimumSize(300, 300)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel()
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # 缩放到屏幕 80% 大小
        from PySide6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().geometry()
        max_w = int(screen.width() * 0.8)
        max_h = int(screen.height() * 0.8)
        scaled = pixmap.scaled(max_w, max_h, Qt.AspectRatioMode.KeepAspectRatio,
                               Qt.TransformationMode.SmoothTransformation)
        label.setPixmap(scaled)
        layout.addWidget(label)
        dialog.resize(scaled.width() + 4, scaled.height() + 4)
        dialog.exec()

    def _resize_cover_to_fit(self):
        """海报跟随栏位宽度缩放（类似看板娘头像）"""
        if not hasattr(self, 'cover_label') or not self._current_cover_url:
            return
        pixmap = self._cover_cache.get(self._current_cover_url)
        if not pixmap or pixmap.isNull():
            return
        parent = self.cover_label.parent()
        if not parent:
            return
        avail_w = parent.width() - 16
        if avail_w <= 0:
            return
        # 保持 5:7 比例，不小于最小尺寸
        w = max(avail_w, 160)
        h = int(w * 7 / 5)
        max_h = 400
        if h > max_h:
            h = max_h
            w = int(h * 5 / 7)
        scaled = pixmap.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio,
                               Qt.TransformationMode.SmoothTransformation)
        self.cover_label.setPixmap(scaled)
        self.cover_label.setMinimumSize(160, 224)
        self.cover_label.setMaximumSize(16777215, 16777215)
        self.cover_label.setStyleSheet("background: transparent; border: none;")
        self.cover_label.setText("")

    def _on_detail_splitter_moved(self, pos, idx):
        """分割线拖动时海报跟随缩放"""
        QTimer.singleShot(0, self._resize_cover_to_fit)

    def _load_cover(self, url):
        self._current_cover_url = url
        if url in self._cover_cache:
            pixmap = self._cover_cache[url]
            if not pixmap.isNull():
                self._resize_cover_to_fit()
                return

        if not self._net_manager:
            self._net_manager = QNetworkAccessManager()
            self._net_manager.finished.connect(self._on_cover_loaded)
        self._net_manager.get(QNetworkRequest(QUrl(url)))

    def _on_cover_loaded(self, reply):
        reply_url = reply.url().toString()
        if reply_url != self._current_cover_url:
            reply.deleteLater()
            return
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = reply.readAll()
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            if not pixmap.isNull():
                self._cover_cache[reply_url] = pixmap
                self._resize_cover_to_fit()
        reply.deleteLater()

    def _fetch_episodes(self, subject_id, db_key):
        self.episodes_table.setRowCount(0)
        self.episodes_status.setText(f"正在获取剧集列表... ({db_key}:{subject_id})")
        self.status_label.setText(f"正在获取剧集列表... ({db_key}:{subject_id})")
        if self._detail_worker and self._detail_worker.isRunning():
            self._detail_worker.terminate()

        config = load_config()
        self._detail_worker = EpisodesDetailWorker(subject_id, db_key, config)
        self._detail_worker.episodes_ready.connect(self._on_episodes_ready)
        self._detail_worker.log.connect(lambda msg: self.episodes_status.setText(msg))
        self._detail_worker.start()

    def _on_episodes_ready(self, episodes):
        self._current_episodes = episodes
        self._refresh_episodes_table()
        if episodes:
            self.episodes_status.setText(f"已加载 {len(episodes)} 集")
            self.status_label.setText(f"已加载 {len(episodes)} 集")
        else:
            self.episodes_status.setText("未找到剧集列表（该数据源可能不支持剧集列表获取）")
            self.status_label.setText("未找到剧集列表（该数据源可能不支持剧集列表获取）")

    def _refresh_episodes_table(self):
        c = theme_manager.colors
        n = len(self._current_episodes)
        self.episodes_table.setRowCount(n)
        self.episodes_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        for i, ep in enumerate(self._current_episodes):
            ep_num = ep.get("ep", ep.get("sort", i + 1))
            num_item = QTableWidgetItem(str(ep_num))
            num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            num_item.setForeground(QColor(c["text_secondary"]))
            self.episodes_table.setItem(i, 0, num_item)

            title = ep.get("name_cn") or ep.get("name") or f"第 {ep_num} 集"
            name_item = QTableWidgetItem(title)
            name_item.setForeground(QColor(c["text_primary"]))
            self.episodes_table.setItem(i, 1, name_item)
            self.episodes_table.setRowHeight(i, 36)

        # 让表格高度刚好容纳所有行（不需内部滚动条）
        hdr_h = self.episodes_table.horizontalHeader().height()
        total_h = hdr_h + n * 36 + 4
        self.episodes_table.setMinimumHeight(total_h)
        self.episodes_table.setMaximumHeight(total_h)

    def _scrape_imdb_detail(self, imdb_id):
        """从 IMDb 页面抓取评分、简介、集数（JSON-LD 结构化数据）"""
        return EpisodesPanel._scrape_imdb_static(imdb_id)

    def _scrape_imdb_async(self, cand):
        """在线程中抓取 IMDb 详情，完成后更新 UI"""

        class ImdbScrapeWorker(QThread):
            result_ready = Signal(object)
            def __init__(self, imdb_id):
                super().__init__()
                self.imdb_id = imdb_id
            def run(self):
                # 调用 static 方法
                info = EpisodesPanel._scrape_imdb_static(self.imdb_id)
                self.result_ready.emit(info)

        worker = ImdbScrapeWorker(cand.get("id", ""))
        worker.result_ready.connect(lambda info: self._on_imdb_scrape_done(cand, info))
        worker.start()

    @staticmethod
    def _scrape_imdb_static(imdb_id):
        """静态方法：从 IMDb 页面抓取详情（JSON-LD 结构化数据）"""
        try:
            import requests as _req
            import re as _re
            import json as _json
            url = f"https://www.imdb.com/title/{imdb_id}/"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                       "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"}
            resp = _req.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                return None
            html = resp.text
            info = {}

            # 方法1：JSON-LD 结构化数据（最可靠）
            m = _re.search(r'<script type="application/ld\+json">(.*?)</script>', html, _re.DOTALL)
            if m:
                try:
                    ld = _json.loads(m.group(1))
                    if isinstance(ld, dict):
                        if "aggregateRating" in ld and "ratingValue" in ld["aggregateRating"]:
                            info["score"] = float(ld["aggregateRating"]["ratingValue"])
                        if "numberOfEpisodes" in ld:
                            info["eps"] = int(ld["numberOfEpisodes"])
                        if "description" in ld:
                            info["summary"] = ld["description"]
                except (ValueError, _json.JSONDecodeError, KeyError):
                    pass

            # 方法2：备用正则（如果 JSON-LD 没找到）
            if "score" not in info:
                m = _re.search(r'"ratingValue":\s*"?([\d.]+)"?', html)
                if m:
                    try:
                        info["score"] = float(m.group(1))
                    except ValueError:
                        pass
            if "eps" not in info:
                m = _re.search(r'"numberOfEpisodes":\s*(\d+)', html)
                if m:
                    info["eps"] = int(m.group(1))
            if "summary" not in info:
                m = _re.search(r'"description":\s*"([^"]+)"', html)
                if m:
                    info["summary"] = m.group(1).replace('\\"', '"').replace('\\n', '\n')

            return info if info else None
        except Exception:
            return None

    def _on_imdb_scrape_done(self, cand, info):
        """IMDb 抓取完成后更新数据（预加载时更新 cand，详情页时更新 UI）"""
        if not info:
            return
        # 始终更新 cand 数据（预加载时也生效）
        if info.get("score") and not cand.get("score"):
            cand["score"] = info["score"]
        if info.get("eps") and cand.get("eps", 0) == 0:
            cand["eps"] = info["eps"]
        if info.get("summary") and not cand.get("summary"):
            cand["summary"] = info["summary"]

        # 只有当前详情页是该条目时才更新 UI
        if self._current_detail is not cand:
            return
        if info.get("score"):
            self.score_label.setText(f"★ {info['score']:.1f}")
        if info.get("eps"):
            date_str = cand.get("date", "") or ""
            source = cand.get("_db_label", cand.get("source", ""))
            parts = []
            if date_str:
                parts.append(f"📅 {date_str}")
            if info["eps"]:
                parts.append(f"📺 {info['eps']} 集")
            if source:
                parts.append(f"📡 {source}")
            self.meta_label.setText("\n".join(parts))
        if info.get("summary"):
            self.summary_label.setText(info["summary"])
            self._full_summary = info["summary"]

    def _back_to_results(self):
        self.content_stack.setCurrentIndex(0)
        self._current_detail = None
        self._current_episodes = []

    def _use_selected(self):
        filtered = self._filtered_candidates if self._filtered_candidates else self._all_candidates
        row = self.results_table.currentRow()
        if row < 0 or row >= len(filtered):
            return
        self.episode_selected.emit(filtered[row])

    # ══════════════════════════════════════════════════════════
    #  搜索历史
    # ══════════════════════════════════════════════════════════

    def _add_to_history(self, title):
        existing = [(t, l) for t, l in self._search_history if t == title]
        for e in existing:
            self._search_history.remove(e)
        self._search_history.insert(0, (title, self.lang_combo.currentText()))
        self._search_history = self._search_history[:8]
        self._save_history()
        self._refresh_history_ui()

    def _refresh_history_ui(self):
        c = theme_manager.colors
        while self.history_layout.count() > 1:
            item = self.history_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for title, lang in self._search_history:
            container = QWidget()
            container.setFixedHeight(36)
            container.setStyleSheet("background: transparent;")

            h = QHBoxLayout(container)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(3)
            h.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

            # 主标签按钮
            tag = QPushButton(title)
            tag.setCursor(Qt.CursorShape.PointingHandCursor)
            tag.setStyleSheet(f"""
                QPushButton {{ background-color: {c["bg_card"]}; color: {c["accent"]};
                    border: 1px solid {c["border"]}; border-radius: 14px; padding: 4px 16px;
                    font-size: 12px; min-height: 26px; outline: none; }}
                QPushButton:hover {{ background-color: {c["accent"]}; color: #ffffff; border-color: {c["accent"]}; outline: none; }}
                QPushButton:focus {{ outline: none; }}
            """)
            tag.clicked.connect(lambda checked, t=title: self._history_clicked(t))
            h.addWidget(tag)

            # 删除按钮 — 用 QLabel 实现，彻底无黑框，× 完整显示
            del_lbl = QLabel("×")
            del_lbl.setFixedSize(26, 26)
            del_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            del_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
            del_lbl.setStyleSheet(f"""
                QLabel {{ background-color: {c["bg_card"]}; color: {c["text_muted"]};
                    border: 1px solid {c["border"]}; border-radius: 13px; font-size: 15px;
                    font-weight: bold; padding: 0px; margin: 0px; }}
                QLabel:hover {{ background-color: #ff4444; color: #ffffff; border-color: #ff4444; }}
            """)
            del_lbl.setToolTip(f"删除 \"{title}\"")
            del_lbl.mousePressEvent = lambda e, t=title: self._history_remove(t)
            h.addWidget(del_lbl)

            self.history_layout.insertWidget(self.history_layout.count() - 1, container)

    def _history_clicked(self, title):
        # 阻止信号，避免触发联想框弹出
        self.search_input.blockSignals(True)
        self.search_input.setText(title)
        self.search_input.blockSignals(False)
        # 隐藏联想弹出框
        if self._completer.popup() and self._completer.popup().isVisible():
            self._completer.popup().hide()
        self._start_search()

    def _history_remove(self, title):
        self._search_history = [(t, l) for t, l in self._search_history if t != title]
        self._save_history()
        self._refresh_history_ui()

    def _save_history(self):
        set_config("episodes_search_history", [
            {"title": t, "lang": l} for t, l in self._search_history
        ])

    def _load_history(self):
        config = load_config()
        hist = config.get("episodes_search_history", [])
        if hist:
            self._search_history = [(h["title"], h.get("lang", "中文")) for h in hist]
            self._refresh_history_ui()

    # ══════════════════════════════════════════════════════════
    #  主题刷新
    # ══════════════════════════════════════════════════════════

    def refresh_theme(self):
        c = theme_manager.colors
        self.title_label.setStyleSheet(
            f"font-size: 22px; font-weight: 700; color: {c['text_primary']}; background: transparent;")
        self.hist_title.setStyleSheet(
            f"font-size: 13px; font-weight: 600; color: {c['text_secondary']}; background: transparent;")
        self.score_label.setStyleSheet("font-size: 28px; font-weight: 700; color: #ff4444; background: transparent;")

        # ── 修复 4：详情页主题适配 ──
        self.detail_title.setStyleSheet(
            f"font-size: 22px; font-weight: 700; color: {c['text_primary']}; background: transparent;")
        self.summary_label.setStyleSheet(
            f"font-size: 14px; color: {c['text_secondary']}; background: transparent; line-height: 1.7;")
        self.meta_label.setStyleSheet(
            f"font-size: 14px; color: {c['text_secondary']}; background: transparent; line-height: 1.6;")

        self._apply_source_combo_style()
        self._apply_results_table_style()
        self._apply_episodes_table_style()
        self._refresh_history_ui()
        self._reapply_table_colors()

        # 更新排序按钮样式
        self.sort_order_btn.setStyleSheet(f"""
            QPushButton {{ background-color: {c["bg_input"]}; color: {c["text_secondary"]};
                border: 1px solid {c["border"]}; border-radius: 6px; font-size: 12px;
                font-weight: bold; padding: 0px; margin: 0px; outline: none; }}
            QPushButton:hover {{ border-color: {c["accent"]}; color: {c["accent"]}; outline: none; }}
            QPushButton:focus {{ outline: none; }}
            QPushButton:pressed {{ outline: none; }}
        """)

        if not self.cover_label.pixmap() or self.cover_label.pixmap().isNull():
            self.cover_label.setStyleSheet(
                f"background-color: {c['bg_card']}; border: 1px solid {c['border']}; "
                f"border-radius: 12px; color: {c['text_muted']}; font-size: 48px;")