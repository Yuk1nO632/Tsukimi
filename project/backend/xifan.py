"""Xifan public Next API adapter. Video bytes go directly to the browser."""

import os
import time
from threading import Lock
from urllib.parse import urlparse
from matching import discovery_queries, exact_source
from source_errors import SourceError

import httpx

API_ROOT = "https://api.xifanacg.com"
# Cloud-download redirects can be blocked by browser ORB checks.
MEDIA_HOSTS = {"play.xfvod.pro", "dl.playxf.top"}
# Public, anonymous client key published in KazumiRules/xfdmnext.json, not a user credential.
PUBLIC_KEY = "sb_publishable_OBIVAWACIX6lPXrO98_z24_HcsmalkA"


class XifanSource:
    name = "xifan"

    def __init__(self, transport=None):
        self.transport = transport
        self._details = {}
        self._searches = {}
        self._client = None
        self._lock = Lock()

    def close(self):
        with self._lock:
            if self._client is not None:
                self._client.close()
                self._client = None

    def http_client(self):
        with self._lock:
            if self._client is None:
                self._client = httpx.Client(timeout=12, transport=self.transport)
            return self._client

    def _post(self, path, body):
        key = os.getenv("TSUKIMI_XIFAN_PUBLIC_KEY", PUBLIC_KEY)
        try:
            response = self.http_client().post(API_ROOT + path, json=body, headers={
                "apikey": key, "Authorization": f"Bearer {key}",
                "User-Agent": "Tsukimi/0.3 (personal fullstack study project)",
            })
            if response.status_code == 404:
                raise SourceError("来源作品或资源已不存在，请重新匹配。", 404)
            if response.status_code == 429:
                raise SourceError("来源请求较多，请稍后重试。", 503)
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException as error:
            raise SourceError("稀饭动漫响应超时，请稍后重试。", 504) from error
        except (httpx.HTTPError, ValueError) as error:
            raise SourceError("暂时无法读取稀饭动漫，请稍后重试。") from error

    def search(self, query):
        with self._lock:
            cached = self._searches.get(query)
        if cached and time.monotonic() - cached[0] < 600:
            return cached[1]
        data = self._post("/rest/v1/rpc/search_animes", {
            "search_term": query, "page_number": 1, "items_per_page": 12,
        })
        if not isinstance(data, list):
            raise SourceError("来源搜索返回了无法识别的资料。")
        items = [{"id": item["id"], "title": str(item.get("title", "")),
                 "year": str(item.get("release_year") or ""),
                 "episodes": item.get("total_episodes") or 0}
                for item in data[:12] if isinstance(item, dict) and isinstance(item.get("id"), int) and item["id"] > 0]
        with self._lock:
            if len(self._searches) >= 64:
                self._searches.pop(next(iter(self._searches)))
            self._searches[query] = (time.monotonic(), items)
        return items

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

    def discover(self, anime):
        candidates = {}
        for query in discovery_queries(anime):
            for item in self.search(query):
                candidates[item["id"]] = item
            selected = exact_source(anime, list(candidates.values()))
            if selected:
                return selected, list(candidates.values())
        return None, list(candidates.values())

    def validate_binding(self, anime, source_anime_id):
        record = self.detail(source_anime_id)["anime"]
        candidate = {
            "id": source_anime_id, "title": record.get("title", ""),
            "year": str(record.get("release_year") or ""),
            "episodes": record.get("total_episodes") or 0,
        }
        if exact_source(anime, [candidate]) is None:
            raise SourceError("这条稀饭记录与作品名称、季数或年份不符，请重新选择。", 409)

    def resolve(self, source_anime_id, episode_number, line_id=None):
        detail = self.detail(source_anime_id)
        lines = [line for line in detail["sources"] if isinstance(line, dict)
                 and isinstance(line.get("id"), int) and line["id"] > 0 and isinstance(line.get("episodes"), list)]
        if line_id is None:
            line = next((line for line in lines if any(isinstance(item, dict) and item.get("kind") == "main"
                and item.get("episode_number") == episode_number for item in line["episodes"])), lines[0] if lines else None)
        else:
            line = next((line for line in lines if line["id"] == line_id), None)
        if line is None:
            raise SourceError("所选线路暂时不可用。", 404)
        # Match the episode's number, not its position; specials must not shift the main episodes.
        episode = next((item for item in line["episodes"] if isinstance(item, dict) and item.get("kind") == "main"
                        and item.get("episode_number") == episode_number), None)
        episode_numbers = [
            int(item["episode_number"]) for item in line["episodes"]
            if isinstance(item, dict) and item.get("kind") == "main"
            and type(item.get("episode_number")) in (int, float)
            and item["episode_number"] > 0 and float(item["episode_number"]).is_integer()
        ]
        common = {"provider": "xifan", "source_anime_id": source_anime_id,
                  "source_title": detail["anime"].get("title", ""),
                  "line_id": line["id"], "line_name": line.get("name", "稀饭动漫"),
                  "lines": [{"id": item["id"], "name": item.get("name", "播放线路")} for item in lines],
                  "episode_count": max(episode_numbers, default=0)}
        if episode is None:
            return {**common, "status": "unavailable", "message": "这条线路暂未提供这一集，可以切换线路或重新匹配来源。"}
        data = self._post("/functions/v1/issue-web-playback", {
            "action": "fallback", "episode_id": episode["id"], "source_id": line["id"],
        })
        if not isinstance(data, dict) or data.get("ok") is not True:
            raise SourceError("来源暂未提供可播放地址，请稍后重试或在来源站查看。")
        candidates = data.get("candidates") if isinstance(data.get("candidates"), list) else []
        urls = [data.get("url")] + [item.get("url") for item in candidates if isinstance(item, dict)]
        for url in urls:
            if not isinstance(url, str):
                continue
            try:
                parsed = urlparse(url)
                supported = (
                    parsed.scheme == "https" and parsed.hostname in MEDIA_HOSTS
                    and not parsed.username and not parsed.password
                    and (parsed.port is None or 1 <= parsed.port <= 65535)
                )
            except ValueError:
                continue
            if supported:
                break
        else:
            if line_id is None:
                alternatives = [item for item in lines if item["id"] != line["id"] and any(
                    isinstance(entry, dict) and entry.get("kind") == "main"
                    and entry.get("episode_number") == episode_number for entry in item["episodes"]
                )]
                for alternative in alternatives[:3]:
                    try:
                        return self.resolve(source_anime_id, episode_number, alternative["id"])
                    except SourceError:
                        continue
            raise SourceError("来源返回的视频地址暂不受支持，请切换线路或在来源站查看。")
        selected_line = next(item for item in common["lines"] if item["id"] == line["id"])
        selected_line["url"] = url
        return {**common, "status": "ready", "format": "hls" if parsed.path.lower().endswith(".m3u8") else "mp4", "url": url,
                "expires_at": data.get("expires_at"), "episode_title": episode.get("title", ""),
                "source_episode_id": episode["id"],
                "source_page": f"https://next.xifanacg.com/anime/{source_anime_id}/play/{episode['id']}"}
