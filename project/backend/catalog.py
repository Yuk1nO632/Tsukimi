"""Fixed Bangumi endpoints; normalized metadata shared by search, detail and playback."""
from datetime import datetime, timedelta, timezone
import json
import re
from threading import Lock
import time
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Query, Request
from typing import Literal

GENRES = ("奇幻", "科幻", "日常", "恋爱", "悬疑", "治愈", "音乐", "战斗", "搞笑", "运动", "冒险")
SHANGHAI = timezone(timedelta(hours=8))


class CatalogError(Exception):
    def __init__(self, message, status_code=502):
        super().__init__(message)
        self.status_code = status_code


def image_url(value):
    if isinstance(value, str):
        parsed = urlparse(value)
        if parsed.scheme in {"http", "https"} and parsed.hostname == "lain.bgm.tv" and not parsed.username and not parsed.password:
            return value.replace("http://", "https://", 1)
    return "/covers/placeholder.svg"


def info_value(value):
    if isinstance(value, str):
        return value[:1000]
    if isinstance(value, list):
        return " / ".join(str(item.get("v", "")) for item in value[:10] if isinstance(item, dict))[:1000]
    return ""


def normalize(subject):
    if not isinstance(subject, dict) or subject.get("type") != 2 or subject.get("nsfw"):
        raise CatalogError("未找到可展示的动画条目。", 404)
    identifier = subject.get("id")
    if not isinstance(identifier, int) or identifier < 1:
        raise CatalogError("番剧资料格式暂时不可用。")
    date = str(subject.get("date") or subject.get("air_date") or "")
    tags = [str(item["name"])[:40] for item in subject.get("tags", []) if isinstance(item, dict) and item.get("name")]
    genres = [tag for tag in GENRES if tag in tags]
    summary = str(subject.get("summary") or "").strip()[:30000]
    infobox = {item["key"]: info_value(item.get("value")) for item in subject.get("infobox", []) if isinstance(item, dict) and isinstance(item.get("key"), str)}
    episodes = subject.get("eps") or 0
    if not isinstance(episodes, int) or episodes < 0:
        episodes = 0
    if not episodes and re.fullmatch(r"\d{1,4}", infobox.get("话数", "")):
        episodes = int(infobox["话数"])
    images = subject.get("images") or {}
    rating = subject.get("rating") or {}
    return {
        "id": f"bgm-{identifier}", "bangumiId": identifier,
        "title": subject.get("name_cn") or subject.get("name") or "未命名动画",
        "originalTitle": subject.get("name") or "", "cover": image_url(images.get("common") or images.get("large") or subject.get("image")),
        "tags": tags[:12], "category": " / ".join(genres[:3]) or str(subject.get("platform") or "动画"),
        "episodes": min(episodes, 10000), "synopsis": summary, "description": summary.splitlines()[0][:180] if summary else "暂无简介",
        "year": date[:4] if re.match(r"\d{4}-\d{2}-\d{2}", date) else "",
        "releaseDate": date, "releaseWeekday": subject.get("air_weekday") or 0,
        "score": rating.get("score") or 0, "ratingCount": rating.get("total") or 0,
        "rank": rating.get("rank") or subject.get("rank") or 0, "ratingDistribution": rating.get("count") or {},
        "platform": subject.get("platform") or "动画", "aliases": infobox.get("别名", ""),
        "staff": [{"label": key, "value": infobox[key]} for key in ("导演", "动画制作", "原作", "系列构成", "人物设定", "音乐", "放送星期", "播放结束") if infobox.get(key)],
        "sourceUrl": f"https://bgm.tv/subject/{identifier}", "sourceName": "Bangumi",
        "detailComplete": bool(subject.get("infobox")),
    }


class BangumiClient:
    def __init__(self, transport=None):
        self.transport = transport
        self.cache = {}
        self.lock = Lock()
        self._client = None

    def close(self):
        with self.lock:
            if self._client is not None:
                self._client.close()
                self._client = None

    def http_client(self):
        with self.lock:
            if self._client is None:
                self._client = httpx.Client(timeout=15, transport=self.transport)
            return self._client

    def request(self, method, path, body=None):
        key = (method, path, json.dumps(body, sort_keys=True))
        with self.lock:
            cached = self.cache.get(key)
        if cached and time.monotonic() - cached[0] < 600:
            return cached[1]
        try:
            response = self.http_client().request(method, "https://api.bgm.tv" + path, json=body,
                headers={"User-Agent": "Tsukimi/0.4 (personal fullstack study project)", "Accept": "application/json"})
            if response.status_code == 404:
                raise CatalogError("未找到这部番剧。", 404)
            if response.status_code == 429:
                raise CatalogError("资料服务请求较多，请稍后重试。", 503)
            response.raise_for_status()
            data = json.loads(response.content)
        except httpx.TimeoutException as error:
            raise CatalogError("番剧资料查询超时，请重试。", 504) from error
        except (httpx.HTTPError, ValueError) as error:
            raise CatalogError("暂时无法读取番剧资料，请稍后重试。") from error
        with self.lock:
            if len(self.cache) >= 128:
                self.cache.pop(next(iter(self.cache)))
            self.cache[key] = (time.monotonic(), data)
        return data


class Catalog:
    def __init__(self, store, provider):
        self.store = store
        self.provider = provider

    def remember(self, anime):
        self.store.cache_anime(anime, int(time.time()))
        return anime

    def get(self, anime_id, enrich=False):
        if re.fullmatch(r"bgm-[1-9]\d{0,8}", anime_id) is None:
            raise CatalogError("未找到这部番剧。", 404)
        cached = self.store.cached_anime(anime_id)
        if cached and (not enrich or (cached[0].get("detailComplete") and time.time() - cached[1] < 86400)):
            return cached[0]
        try:
            anime = normalize(self.provider.request("GET", "/v0/subjects/" + anime_id[4:]))
            if anime["id"] != anime_id:
                raise CatalogError("资料服务返回了不一致的条目，请重试。")
            return self.remember(anime)
        except CatalogError as error:
            if cached and error.status_code != 404:
                return {**cached[0], "detailWarning": "资料服务暂不可用，当前展示已缓存资料。"}
            raise

    def search(self, q, year, season, genre, sort, page, limit):
        filters = {"type": [2], "nsfw": False}
        if season and not year:
            year = datetime.now(SHANGHAI).year
        if year:
            start_month = (season - 1) * 3 + 1 if season else 1
            end_month = start_month + 3 if season else 13
            filters["air_date"] = [f">={year:04d}-{start_month:02d}-01", f"<{year + 1:04d}-01-01" if end_month > 12 else f"<{year:04d}-{end_month:02d}-01"]
        if genre:
            filters["tag"] = [genre]
        raw = self.provider.request("POST", f"/v0/search/subjects?limit={limit}&offset={(page - 1) * limit}",
                                    {"keyword": q.strip(), "sort": sort, "filter": filters})
        if not isinstance(raw, dict) or not isinstance(raw.get("data"), list):
            raise CatalogError("资料搜索返回了无法识别的结果。")
        items = []
        for subject in raw["data"]:
            try:
                items.append(normalize(subject))
            except CatalogError as error:
                if error.status_code != 404:
                    raise
        self.store.cache_animes(items, int(time.time()))
        return {"items": items, "total": int(raw.get("total") or 0), "page": page, "limit": limit, "provider": "Bangumi"}

    def calendar(self):
        raw = self.provider.request("GET", "/calendar")
        if not isinstance(raw, list):
            raise CatalogError("放送日历暂时无法读取。")
        days = []
        for day in raw:
            if not isinstance(day, dict) or not isinstance(day.get("weekday"), dict):
                continue
            identifier = day["weekday"].get("id")
            if identifier not in range(1, 8):
                continue
            items = []
            for subject in day.get("items", []):
                try:
                    anime = normalize(subject)
                    # Calendar summaries must not overwrite richer detail/search records.
                    self.store.cache_anime(anime, int(time.time()), seed=True)
                    items.append(anime)
                except CatalogError as error:
                    if error.status_code != 404:
                        raise
            days.append({"weekday": identifier, "items": items})
        return {"days": days, "fetchedAt": datetime.now(SHANGHAI).isoformat(), "provider": "Bangumi",
                "note": "按 Bangumi 当前放送星期展示，实际资源更新以播放来源为准。"}


def create_catalog_router():
    router = APIRouter(prefix="/api/catalog")

    @router.get("")
    def search(request: Request, q: str = Query(default="", max_length=100),
               year: int | None = Query(default=None, ge=1900, le=2100),
               season: int | None = Query(default=None, ge=1, le=4), genre: str = Query(default="", max_length=20),
               sort: Literal["match", "heat", "rank", "score"] = "heat",
               page: int = Query(default=1, ge=1, le=200), limit: int = Query(default=18, ge=1, le=24)):
        return request.app.state.catalog.search(q, year, season, genre, sort, page, limit)

    @router.get("/calendar")
    def calendar(request: Request):
        return request.app.state.catalog.calendar()

    @router.get("/{anime_id}")
    def detail(anime_id: str, request: Request):
        return request.app.state.catalog.get(anime_id, enrich=True)

    return router
