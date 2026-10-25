"""One fixed provider: Xifan's public Next API. Video bytes go directly to the browser."""

import os
import time
from threading import Lock
from urllib.parse import urlparse

import httpx

API_ROOT = "https://api.xifanacg.com"
# Public, anonymous client key published in KazumiRules/xfdmnext.json, not a user credential.
PUBLIC_KEY = "sb_publishable_OBIVAWACIX6lPXrO98_z24_HcsmalkA"


class SourceError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


class XifanSource:
    def __init__(self, transport=None):
        self.transport = transport
        self._details = {}
        self._lock = Lock()

    def _post(self, path, body):
        key = os.getenv("TSUKIMI_XIFAN_PUBLIC_KEY", PUBLIC_KEY)
        try:
            with httpx.Client(timeout=12, transport=self.transport) as client:
                response = client.post(API_ROOT + path, json=body, headers={
                    "apikey": key, "Authorization": f"Bearer {key}",
                    "User-Agent": "Tsukimi/0.3 (personal fullstack study project)",
                })
                if response.status_code == 429:
                    raise SourceError("来源请求较多，请稍后重试。", 503)
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException as error:
            raise SourceError("稀饭动漫响应超时，请稍后重试。", 504) from error
        except (httpx.HTTPError, ValueError) as error:
            raise SourceError("暂时无法读取稀饭动漫，请稍后重试。") from error

    def search(self, query):
        data = self._post("/rest/v1/rpc/search_animes", {
            "search_term": query, "page_number": 1, "items_per_page": 12,
        })
        if not isinstance(data, list):
            raise SourceError("来源搜索返回了无法识别的资料。")
        return [{"id": item["id"], "title": str(item.get("title", "")),
                 "year": str(item.get("release_year") or ""),
                 "episodes": item.get("total_episodes") or 0}
                for item in data[:12] if isinstance(item, dict) and isinstance(item.get("id"), int) and item["id"] > 0]

    def detail(self, source_anime_id):
        with self._lock:
            cached = self._details.get(source_anime_id)
        if cached and time.monotonic() - cached[0] < 300:
            return cached[1]
        data = self._post("/rest/v1/rpc/get_anime_detail", {"p_id": source_anime_id})
        if not isinstance(data, dict) or not isinstance(data.get("anime"), dict):
            raise SourceError("该来源番剧暂时不可用。", 404)
        if not isinstance(data.get("sources"), list):
            raise SourceError("来源尚未提供可识别的播放线路。")
        with self._lock:
            if len(self._details) >= 32:
                self._details.pop(next(iter(self._details)))
            self._details[source_anime_id] = (time.monotonic(), data)
        return data

    def resolve(self, source_anime_id, episode_number, line_id=None):
        detail = self.detail(source_anime_id)
        lines = [line for line in detail["sources"] if isinstance(line, dict)
                 and isinstance(line.get("id"), int) and line["id"] > 0 and isinstance(line.get("episodes"), list)]
        line = next((line for line in lines if line_id is None or line["id"] == line_id), None)
        if line is None:
            raise SourceError("所选线路暂时不可用。", 404)
        # Match the episode's number, not its position; specials must not shift the main episodes.
        episode = next((item for item in line["episodes"] if isinstance(item, dict) and item.get("kind") == "main"
                        and item.get("episode_number") == episode_number), None)
        common = {"provider": "xifan", "source_anime_id": source_anime_id,
                  "source_title": detail["anime"].get("title", ""),
                  "line_id": line["id"], "line_name": line.get("name", "稀饭动漫"),
                  "lines": [{"id": item["id"], "name": item.get("name", "播放线路")} for item in lines]}
        if episode is None:
            return {**common, "status": "unavailable", "message": "这条线路暂未提供这一集，可以切换线路或重新匹配来源。"}
        data = self._post("/functions/v1/issue-web-playback", {
            "action": "fallback", "episode_id": episode["id"], "source_id": line["id"],
        })
        if not isinstance(data, dict) or data.get("ok") is not True:
            raise SourceError("来源暂未提供可播放地址，请稍后重试或在来源站查看。")
        candidates = data.get("candidates") if isinstance(data.get("candidates"), list) else []
        url = data.get("url") or (candidates[0].get("url") if candidates and isinstance(candidates[0], dict) else None)
        if not isinstance(url, str):
            raise SourceError("来源暂未提供有效的视频地址。")
        parsed = urlparse(url or "")
        # Never forward arbitrary URLs from a user or proxy video bytes through our backend.
        if parsed.scheme != "https" or parsed.hostname not in {"play.xfvod.pro", "dl.playxf.top"} or parsed.username or parsed.password:
            raise SourceError("来源返回的视频地址暂不受支持，请在来源站查看。")
        return {**common, "status": "ready", "format": "hls" if parsed.path.lower().endswith(".m3u8") else "mp4", "url": url,
                "expires_at": data.get("expires_at"), "episode_title": episode.get("title", ""),
                "source_episode_id": episode["id"],
                "source_page": f"https://next.xifanacg.com/anime/{source_anime_id}/play/{episode['id']}"}
