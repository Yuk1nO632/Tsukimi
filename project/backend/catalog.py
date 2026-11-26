"""Fixed Bangumi endpoints; normalized metadata shared by search, detail and playback."""
from datetime import date, datetime, timedelta, timezone
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
SERIES_SEQUENCE = {"前传", "续集"}
SERIES_EXTRAS = {"番外篇", "总集篇", "全集", "衍生", "主线故事", "不同演绎"}
SERIES_LIMIT = 8
SERIES_BUDGET = 8.0


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


def episode_date(value):
    if not isinstance(value, str):
        return None
    value = value.replace("年", "-").replace("月", "-").removesuffix("日")
    if re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}", value) is None:
        return None
    try:
        return date(*map(int, value.split("-")))
    except ValueError:
        return None


def airing_info(anime, episodes, today=None):
    today = today or datetime.now(SHANGHAI).date()
    dates = {}
    for episode in episodes:
        if not isinstance(episode, dict) or episode.get("type") != 0:
            continue
        # Bangumi ep is relative to this subject. sort may continue a previous season.
        number = episode.get("ep", episode.get("sort"))
        if type(number) not in (int, float) or not 1 <= number <= 10000 or int(number) != number:
            continue
        number = int(number)
        airdate = episode_date(episode.get("airdate"))
        if number in dates and dates[number] != airdate:
            airdate = None
        dates[number] = airdate
    aired = [number for number, airdate in dates.items() if airdate and airdate <= today]
    future = [number for number, airdate in dates.items() if airdate and airdate > today]
    total = anime.get("episodes") or 0
    complete = total > 0 and set(dates) == set(aired) == set(range(1, total + 1))
    end = episode_date(next(
        (item.get("value") for item in anime.get("staff", []) if item.get("label") == "播放结束"),
        "",
    ))
    # The subject's planned count can include a separately classified OVA.
    complete = complete or bool(end and end <= today and aired and not future)
    release = episode_date(anime.get("releaseDate"))
    status = "unknown"
    if complete:
        status = "completed"
    elif aired and future:
        status = "airing"
    elif not aired and (
        (release and release > today)
        or (dates.get(1) and dates[1] > today and len(future) == len(dates))
    ):
        status = "upcoming"
    return {
        "status": status,
        "airedCount": len(aired),
        "latestEpisode": max(aired, default=0),
        "episodes": [
            {
                "number": number,
                "airdate": airdate.isoformat() if airdate else "",
                "status": "unknown" if airdate is None else "aired" if airdate <= today else "upcoming",
            }
            for number, airdate in sorted(dates.items())
        ],
        "asOf": today.isoformat(),
    }


def series_links(raw, current_id):
    if not isinstance(raw, list):
        raise CatalogError("系列关联资料暂时无法读取。")
    links = {}
    for item in raw:
        if not isinstance(item, dict) or item.get("type") != 2 or item.get("nsfw"):
            continue
        identifier, relation = item.get("id"), item.get("relation")
        if (type(identifier) is not int or not 1 <= identifier <= 999_999_999
                or not isinstance(relation, str) or relation not in SERIES_SEQUENCE | SERIES_EXTRAS):
            continue
        anime_id = f"bgm-{identifier}"
        if anime_id != current_id:
            links.setdefault(anime_id, set()).add(relation)
    return links


def ordered_series(anime_ids, edges):
    remaining = set(anime_ids)
    order = []
    while remaining:
        incoming = {after for before, after in edges if before in remaining and after in remaining}
        first = remaining - incoming
        if len(first) != 1:
            return []
        item = first.pop()
        remaining.remove(item)
        order.append(item)
    return order


def series_item(anime, relation):
    return {
        key: anime.get(key, "") for key in ("id", "title", "originalTitle", "cover", "releaseDate", "year", "platform")
    } | {"relation": relation}


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

    def request(self, method, path, body=None, *, timeout=None):
        key = (method, path, json.dumps(body, sort_keys=True))
        with self.lock:
            cached = self.cache.get(key)
        if cached and time.monotonic() - cached[0] < 600:
            return cached[1]
        try:
            client = self.http_client()
            response = client.request(method, "https://api.bgm.tv" + path, json=body,
                timeout=client.timeout if timeout is None else timeout, headers={"User-Agent": "Tsukimi/0.4 (personal fullstack study project)", "Accept": "application/json"})
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

    def detail(self, anime_id):
        anime = self.get(anime_id, enrich=True)
        episodes = []
        try:
            offset = 0
            while True:
                raw = self.provider.request("GET", f"/v0/episodes?subject_id={anime_id[4:]}&type=0&limit=200&offset={offset}")
                if (not isinstance(raw, dict) or not isinstance(raw.get("data"), list)
                        or type(raw.get("total")) is not int or not 0 <= raw["total"] <= 10000):
                    raise CatalogError("分集放送资料暂时不可用。")
                items = raw["data"]
                if len(items) > 200 or offset + len(items) > raw["total"]:
                    raise CatalogError("分集放送资料格式暂时不可用。")
                episodes.extend(items)
                offset += len(items)
                if offset >= raw["total"]:
                    break
                if not items:
                    raise CatalogError("分集放送资料尚未完整取得。")
            return {**anime, "airing": airing_info(anime, episodes)}
        except CatalogError:
            # A schedule failure must leave metadata and existing playback entry points usable.
            return {
                **anime,
                "airing": {
                    **airing_info(anime, []),
                    "warning": "放送进度暂时无法确认，请稍后刷新。",
                },
            }

    def series(self, anime_id):
        if re.fullmatch(r"bgm-[1-9]\d{0,8}", anime_id) is None:
            raise CatalogError("未找到这部番剧。", 404)

        deadline = time.monotonic() + SERIES_BUDGET

        def read(path):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise CatalogError("系列关联资料读取超时，请重试。", 504)
            return self.provider.request("GET", path, timeout=min(remaining, 4.0))

        def describe(subject_id):
            cached = self.store.cached_anime(subject_id)
            if cached:
                return cached[0]
            anime = normalize(read("/v0/subjects/" + subject_id[4:]))
            if anime["id"] != subject_id:
                raise CatalogError("资料服务返回了不一致的条目，请重试。")
            return self.remember(anime)

        # The relations response omits safety flags and release dates. Use verified
        # subject metadata for the cards and keep supplemental links out of the chain.
        def read_links(subject_id):
            return series_links(read(f"/v0/subjects/{subject_id[4:]}/subjects"), subject_id)

        current = describe(anime_id)
        direct = read_links(anime_id)
        main = {anime_id: current}
        edges = set()
        extras = {}
        observed = {anime_id}
        pending = [anime_id]
        partial = False

        for current_id in pending:
            try:
                links = direct if current_id == anime_id else read_links(current_id)
            except CatalogError:
                partial = True
                break

            for subject_id, relations in links.items():
                supplemental = relations & SERIES_EXTRAS
                if supplemental:
                    extras.setdefault(subject_id, sorted(supplemental)[0])
                    continue
                if subject_id not in observed:
                    if len(observed) >= SERIES_LIMIT:
                        partial = True
                        continue
                    observed.add(subject_id)
                    try:
                        main[subject_id] = describe(subject_id)
                    except CatalogError as error:
                        partial = partial or error.status_code != 404
                    else:
                        pending.append(subject_id)
                if subject_id in main:
                    if "前传" in relations:
                        edges.add((subject_id, current_id))
                    if "续集" in relations:
                        edges.add((current_id, subject_id))

        order = ordered_series(main, edges)
        direct_sequels = [
            subject_id for subject_id, relations in direct.items() if relations == {"续集"}
        ]
        sequel = None
        if order and len(direct_sequels) == 1:
            following = order.index(anime_id) + 1
            if following < len(order) and order[following] == direct_sequels[0]:
                sequel = series_item(main[order[following]], "续集")

        if order:
            current_index = order.index(anime_id)
            main_items = [
                series_item(main[subject_id], "当前" if index == current_index else
                            "前传" if index < current_index else "续集")
                for index, subject_id in enumerate(order)
            ]
        else:
            main_items = [series_item(current, "当前")]
            for subject_id, relations in direct.items():
                if subject_id in main:
                    relation = next(iter(relations)) if len(relations) == 1 else "关联作品"
                    main_items.append(series_item(main[subject_id], relation))

        extra_items = []
        candidates = [(subject_id, relation) for subject_id, relation in extras.items() if subject_id not in main]
        partial |= len(candidates) > SERIES_LIMIT
        for subject_id, relation in candidates[:SERIES_LIMIT]:
            try:
                extra_items.append(series_item(describe(subject_id), relation))
            except CatalogError as error:
                if error.status_code != 404:
                    partial = True
                    break

        return {"main": main_items, "extras": extra_items, "ordered": bool(order),
                "partial": partial, "sequel": sequel}

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

    @router.get("/{anime_id}/series")
    def series(anime_id: str, request: Request):
        return request.app.state.catalog.series(anime_id)

    @router.get("/{anime_id}")
    def detail(anime_id: str, request: Request, summary: bool = False):
        # Route rendering uses cached search/detail data; full enrichment is separate.
        catalog = request.app.state.catalog
        return catalog.get(anime_id) if summary else catalog.detail(anime_id)

    return router
