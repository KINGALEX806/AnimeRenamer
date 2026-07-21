"""本地缓存系统 - 将番剧数据库查询结果缓存到 JSON 文件"""
import hashlib
import json
import os
import time
from pathlib import Path


DEFAULT_CACHE_DIR = Path(os.path.expanduser("~")) / ".anime_cache"
DEFAULT_EXPIRY_DAYS = 7


class AnimeCache:
    """番剧查询缓存管理器

    缓存查询结果到 JSON 文件，存储在用户主目录下的 .anime_cache 文件夹中。
    缓存条目在 7 天后自动过期。

    用法:
        cache = AnimeCache()
        data = cache.get("search_bangumi_攻壳机动队")
        if data is None:
            data = api_search("攻壳机动队")
            cache.set("search_bangumi_攻壳机动队", data)
    """

    def __init__(self, cache_dir=None, expiry_days=None):
        """
        Args:
            cache_dir: 缓存目录路径，默认为 ~/.anime_cache
            expiry_days: 缓存过期天数，默认为 7 天
        """
        if cache_dir is None:
            cache_dir = DEFAULT_CACHE_DIR
        if expiry_days is None:
            expiry_days = DEFAULT_EXPIRY_DAYS

        self.cache_dir = Path(cache_dir)
        self.expiry_seconds = expiry_days * 24 * 60 * 60

        # 确保缓存目录存在
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _sanitize_key(self, key):
        """将缓存键转换为安全的文件名

        使用 MD5 哈希确保文件名仅包含安全字符，同时保证一致性。

        Args:
            key: 原始缓存键

        Returns:
            安全的 MD5 哈希字符串
        """
        return hashlib.md5(key.encode("utf-8")).hexdigest()

    def _get_file_path(self, key):
        """获取缓存键对应的文件路径

        Args:
            key: 缓存键

        Returns:
            Path 对象
        """
        safe_name = self._sanitize_key(key)
        return self.cache_dir / f"{safe_name}.json"

    def get(self, key):
        """读取缓存

        如果缓存文件不存在、已过期或损坏，返回 None。

        Args:
            key: 缓存键

        Returns:
            缓存的数据，或 None
        """
        file_path = self._get_file_path(key)

        if not file_path.exists():
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                entry = json.load(f)
        except (json.JSONDecodeError, IOError, OSError):
            # 文件损坏或无法读取，视为缓存未命中
            return None

        # 检查是否过期
        timestamp = entry.get("timestamp", 0)
        if time.time() - timestamp > self.expiry_seconds:
            # 删除过期文件
            try:
                file_path.unlink(missing_ok=True)
            except OSError:
                pass
            return None

        return entry.get("data")

    def set(self, key, data):
        """写入缓存

        Args:
            key: 缓存键
            data: 要缓存的数据（必须可 JSON 序列化）
        """
        file_path = self._get_file_path(key)

        entry = {
            "key": key,
            "data": data,
            "timestamp": time.time(),
        }

        # 先写入临时文件，再原子替换，避免写入中断导致文件损坏
        tmp_path = file_path.with_suffix(".tmp")
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(entry, f, ensure_ascii=False, indent=2)
            tmp_path.replace(file_path)
        except Exception:
            # 清理临时文件
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise

    def clear(self):
        """清空所有缓存

        删除缓存目录中的所有 JSON 文件。
        """
        if not self.cache_dir.exists():
            return

        for file_path in self.cache_dir.glob("*.json"):
            try:
                file_path.unlink()
            except OSError:
                pass

        # 同时清理临时文件
        for file_path in self.cache_dir.glob("*.tmp"):
            try:
                file_path.unlink()
            except OSError:
                pass

    def get_stats(self):
        """获取缓存统计信息

        Returns:
            dict: {"count": 缓存文件数量, "size_bytes": 总字节数}
        """
        if not self.cache_dir.exists():
            return {"count": 0, "size_bytes": 0}

        files = list(self.cache_dir.glob("*.json"))
        count = len(files)
        total_size = sum(
            f.stat().st_size for f in files
            if f.exists()
        )

        return {"count": count, "size_bytes": total_size}