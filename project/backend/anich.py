"""AniCh aggregate adapter. Metadata/choices cached, signed video URLs never cached."""
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
import hashlib
import ipaddress
import json
import os
import re
import time
from threading import Lock
from urllib.parse import urlsplit

import httpx

from anich_protocol import LIMIT, fields, decode_url
from matching import (
    anime_titles, exact_source, title_key, season_number, strip_season,
    fallback_search_title, discovery_queries, part_number, special_search_title, search_keyword,
)
from source_errors import SourceError

SHANGHAI = timezone(timedelta(hours=8))


def messages(payload):
    return [dict(fields(value)) for number, value in fields(payload) if number == 1 and isinstance(value, bytes)]


def text(item, number):
    return item.get(number, b'').decode('utf-8')


def public_media_url(url):
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None, 443):
        return False
    host = parsed.hostname.lower().rstrip('.')
    if host == 'localhost' or host.endswith(('.localhost', '.local', '.internal')) or '.' not in host:
        return False
    try:
        return ipaddress.ip_address(host).is_global
    except ValueError:
        return True


class AniChSource:
    name = 'anich'

    def __init__(self, transport=None):
        self.transport = transport
        self.base = os.getenv('TSUKIMI_ANICH_API', 'https://anich.sends.eu.org').rstrip('/')
        self._client = None
        self._lock = Lock()
        self._cache = {}

    def close(self):
        with self._lock:
            if self._client:
                self._client.close()
                self._client = None

    def _get(self, path, params=None, json_result=False):
        try:
            with self._lock:
                if self._client is None:
                    self._client = httpx.Client(timeout=12, transport=self.transport,
                        headers={'User-Agent': 'Tsukimi/0.5 (personal fullstack study project)'})
                client = self._client
            with client.stream('GET', self.base + path, params=params) as response:
                if response.status_code == 404:
                    raise SourceError('AniCh 中的作品或剧集已不可用，请重新匹配。', 404)
                if response.status_code == 401:
                    raise SourceError('AniCh 接口返回未授权，暂时无法读取来源。', 503, reason='unauthorized')
                if response.status_code == 403:
                    raise SourceError('AniCh 暂时拒绝请求，请稍后重试。', 503)
                if response.status_code == 429:
                    raise SourceError('AniCh 请求较多，请稍后重试。', 503)
                chunks, size = [], 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > LIMIT:
                        raise ValueError('oversized response')
                    chunks.append(chunk)
                raw = b''.join(chunks)
                is_json = 'application/json' in response.headers.get('content-type', '').lower()
                result = json.loads(raw) if json_result or is_json else raw
                if isinstance(result, dict) and str(result.get('message', '')).casefold() in {'unauthorized', 'unauthenticated'}:
                    raise SourceError('AniCh 接口返回未授权，暂时无法读取来源。', 503, reason='unauthorized')
                response.raise_for_status()
            if isinstance(result, dict) and result.get('error'):
                raise SourceError('AniCh 服务暂时拒绝了请求，请稍后重试。', 503)
            return result if json_result else raw
        except httpx.TimeoutException as error:
            raise SourceError('AniCh 响应超时，请稍后重试。', 504) from error
        except (httpx.HTTPError, ValueError, TypeError) as error:
            raise SourceError('暂时无法读取 AniCh 播放来源，请稍后重试。') from error

    def _cached(self, key, load, ttl=300):
        with self._lock:
            entry = self._cache.get(key)
        if entry and time.monotonic() - entry[0] < ttl:
            return entry[1]
        value = load()
        with self._lock:
            if len(self._cache) >= 96:
                self._cache.pop(next(iter(self._cache)))
            self._cache[key] = (time.monotonic(), value)
        return value

    def search(self, query, *, allow_fallback=True):
        # AniCh rejects some terminal title punctuation (e.g. 孤独摇滚！) with HTTP 500.
        # Only simplify the lookup keyword; returned titles and identity checks stay intact.
        keyword = search_keyword(query)
        if not keyword:
            raise SourceError('请输入有效的番名关键词。', 400)
        def load():
            try:
                rows = messages(self._get('/bangumi/search', {'keyword': keyword, 'skip': 0}))
                items = []
                for row in rows[:24]:
                    if not isinstance(row.get(1), int) or row[1] <= 0:
                        continue
                    # Search field 6 is not a reliable premiere date on this service.
                    year = ''
                    items.append({'id': row[1], 'title': text(row, 2), 'year': year, 'episodes': row.get(4, 0)})
                return items
            except SourceError as error:
                fallback = fallback_search_title(keyword)
                if allow_fallback and (error.status_code == 502 or error.reason == 'unauthorized') and fallback and fallback != keyword:
                    return self.search(fallback)
                raise
            except (ValueError, TypeError, KeyError, OverflowError, OSError) as error:
                raise SourceError('AniCh 搜索资料格式暂不受支持。') from error
        return self._cached(('search', keyword), load, 600)

    def detail(self, source_id):
        def load():
            data = self._get(f'/bangumi/detail/{source_id}', json_result=True)
            if not isinstance(data, dict) or data.get('id') != source_id or not isinstance(data.get('title'), str):
                raise SourceError('AniCh 作品资料格式暂不受支持。')
            return data
        return self._cached(('detail', source_id), load)

    @staticmethod
    def mapped_ids(detail):
        return {str(item.get('id')) for item in detail.get('sites', [])
                if isinstance(item, dict) and item.get('site') == 'bangumi'}

    def validate_binding(self, anime, source_id):
        linked = self.mapped_ids(self.detail(source_id))
        if linked and anime['id'].removeprefix('bgm-') not in linked:
            raise SourceError('这条 AniCh 记录对应另一部作品，请核对本篇、季数与年份。', 409)

    def discover(self, anime):
        candidates = {}
        queries = discovery_queries(anime)
        names = {title_key(value) for value in anime_titles(anime)}
        target_season = season_number(anime.get('title', '')) or season_number(anime.get('originalTitle', ''))
        target_part = part_number(anime.get('title', '')) or part_number(anime.get('originalTitle', ''))
        target_year = str(anime.get('year') or '')[:4]
        target_special = anime.get('platform') in {'OVA', 'OAD', 'SP'} or any(
            title_key(special_search_title(value)) != title_key(value)
            for value in (anime.get('title', ''), anime.get('originalTitle', ''))
        )
        def relevance(item):
            name = title_key(item['title'])
            same_season = season_number(item['title']) == target_season
            similarity = max((SequenceMatcher(None, name, known).ratio() for known in names), default=0)
            return (name in names, same_season, similarity)
        checked, verified, fallback = set(), [], []
        search_succeeded = False
        last_error = None
        for query in queries:
            try:
                for item in self.search(query, allow_fallback=False):
                    candidates[item['id']] = item
                search_succeeded = True
            except SourceError as error:
                if error.status_code in (503, 504) and error.reason != 'unauthorized':
                    raise
                last_error = error
                continue
            # Names rank the bounded detail probes. They must not block a valid official ID.
            plausible = sorted(candidates.values(), key=relevance, reverse=True)
            unchecked = [item for item in plausible if item['id'] not in checked]
            # Reserve capacity for later aliases when an earlier query returns unrelated hits.
            for item in unchecked[:min(8, 12 - len(checked))]:
                checked.add(item['id'])
                try:
                    detail = self.detail(item['id'])
                except SourceError as error:
                    if error.status_code in (503, 504) and error.reason != 'unauthorized':
                        raise
                    continue
                stamp = detail.get('airdate')
                if isinstance(stamp, (int, float)) and stamp > 0:
                    item = {**item, 'year': str(datetime.fromtimestamp(stamp / 1000, SHANGHAI).year)}
                    candidates[item['id']] = item
                linked = self.mapped_ids(detail)
                if anime['id'].removeprefix('bgm-') in linked:
                    source_season = season_number(detail['title'])
                    source_part = part_number(detail['title'])
                    source_special = title_key(special_search_title(detail['title'])) != title_key(detail['title'])
                    conflict = ((target_season and source_season and target_season != source_season) or
                                (target_part and source_part and target_part != source_part) or
                                (target_year and item['year'] and target_year != item['year']) or
                                (source_special and not target_special))
                    if not conflict:
                        verified.append(item['id'])
                elif not linked:
                    fallback.append(item)
            if len(verified) == 1:
                return verified[0], list(candidates.values())
            if len(verified) > 1:
                return None, list(candidates.values())
            selected = exact_source(anime, fallback)
            if selected:
                return selected, list(candidates.values())
        if not search_succeeded and last_error:
            raise last_error
        return None, list(candidates.values())

    def episodes(self, source_id):
        def load():
            try:
                return messages(self._get(f'/bangumi/episodes/{source_id}'))
            except (ValueError, TypeError) as error:
                raise SourceError('AniCh 剧集资料格式暂不受支持。') from error
        return self._cached(('episodes', source_id), load)

    @staticmethod
    def _episode_mapping(episodes, detail, anime, episode_number, target_season):
        """Map 1-based season episode numbers onto cumulative AniCh sort numbers when sequels continue prior seasons."""
        # The public client uses sort for VOD; standalone OAD/OVA records use type 0.
        # Keep specials separate when a record also contains main-series episodes.
        episode_type = 1 if any(row.get(1) == 1 for row in episodes) else 0
        available = sorted({
            row.get(2) for row in episodes
            if row.get(1, 0) == episode_type and type(row.get(2)) is int and row[2] > 0
        })
        available_set = set(available)
        first = available[0] if available else 0
        raw_total = (anime.get('episodes') if isinstance(anime, dict) else 0) or detail.get('episodes_total') or 0
        season_total = raw_total if type(raw_total) is int and raw_total > 0 else 0
        is_sequel = (target_season or 0) > 1
        cumulative_offset = (
            first - 1
            if first > 1 and (
                (season_total > 0 and first > season_total) or
                ((season_total == 0 or is_sequel) and first >= 12 and first > len(available))
            )
            else 0
        )
        target_sort = episode_number + cumulative_offset
        episode_count = max((ep - cumulative_offset for ep in available), default=0) if cumulative_offset else max(available_set, default=0)
        return available_set, target_sort, episode_count

    @staticmethod
    def _allowed_vod_titles(detail, anime, target_season):
        """Allow verified AniCh names and matching Bangumi aliases without relaxing season boundaries."""
        detail_titles = [detail['title'], *detail.get('titles', [])]
        extra_titles = anime_titles(anime) if isinstance(anime, dict) else []
        names = {title_key(value) for value in detail_titles if isinstance(value, str) and value}
        for value in extra_titles:
            season = season_number(value)
            if not target_season or target_season == 1:
                if season in (None, 1):
                    names.add(title_key(value))
            elif season == target_season:
                names.add(title_key(value))
        names.discard('')
        season_bases = set()
        if target_season and target_season > 1:
            for value in (*detail_titles, *extra_titles):
                if isinstance(value, str) and value and season_number(value) in (None, target_season):
                    base = title_key(strip_season(value))
                    if base:
                        season_bases.add(base)
        return names, season_bases

    def resolve(self, source_id, episode_number, line_id=None, anime=None):
        detail = self.detail(source_id)
        episodes = self.episodes(source_id)
        target_season = next((s for s in (season_number(v) for v in (detail['title'], *detail.get('titles', []))) if s), None)
        available_set, target_sort, episode_count = self._episode_mapping(episodes, detail, anime, episode_number, target_season)
        common = {'provider': self.name, 'source_anime_id': source_id, 'source_title': detail['title'],
                  'episode_count': episode_count, 'lines': [], 'line_id': None}
        if target_sort not in available_set:
            return {**common, 'status': 'unavailable', 'reason': 'episode_missing', 'message': f'已匹配《{detail["title"]}》，但来源目录暂未列出第 {episode_number} 集。'}
        raw = self._get(f'/vod/{source_id}/{target_sort}', json_result=True)
        try:
            if not isinstance(raw, list) or len(raw) > LIMIT or any(type(n) is not int or not 0 <= n <= 255 for n in raw):
                raise ValueError('not a byte array')
            rows = messages(bytes(raw))
            names, season_bases = self._allowed_vod_titles(detail, anime, target_season)
            accepted_episodes = {episode_number, target_sort}
            single_feature = len(available_set) == 1 and target_sort in available_set and detail.get('episodes_total') == 1 and episode_number == 1
            lines = {}
            rejected = 0
            for row in rows:
                candidate_episode = row.get(2, 0)
                feature_label = text(row, 4).split('·', 1)[0].strip()
                zero_feature = single_feature and candidate_episode == 0 and (
                    title_key(feature_label) in {'正片', '全集', '全片', '完整版', '全1集'} or
                    title_key(feature_label) in names
                )
                if candidate_episode not in accepted_episodes and not zero_feature:
                    rejected += 1
                    continue
                description = text(row, 6)
                title = description.split('·', 1)[0].strip()
                candidate_season = season_number(title)
                title_ok = title_key(title) in names or (
                    bool(target_season and target_season > 1 and candidate_season == target_season)
                    and title_key(strip_season(title)) in season_bases
                )
                if (candidate_season and candidate_season > 1 and candidate_season != target_season) or ((title or zero_feature) and not title_ok):
                    rejected += 1
                    continue
                try:
                    url = decode_url(text(row, 1))
                    valid_url = public_media_url(url)
                except (ValueError, TypeError):
                    valid_url = False
                if not valid_url:
                    rejected += 1
                    continue
                label = text(row, 5)
                if not label:
                    rejected += 1
                    continue
                codec = 'HEVC' if re.search(r'H\.?265|HEVC', description, re.I) else ('H.264' if re.search(r'H\.?264|AVC', description, re.I) else '')
                resolution = re.search(r'(\d{3,4})[x×](\d{3,4})', description)
                quality = f'{resolution[2]}P' if resolution else ''
                kind = 'hls' if urlsplit(url).path.lower().endswith('.m3u8') or text(row, 3).lower() == 'hls' else 'mp4'
                key = f'{label}|{quality}|{codec}|{kind}'
                stable_id = int(hashlib.sha256(key.encode()).hexdigest()[:12], 16) + 1
                lines.setdefault(stable_id, {'id': stable_id, 'name': ' · '.join(part for part in (label, quality, codec, 'HLS' if kind == 'hls' else '') if part),
                                             'url': url, 'format': kind, 'codec': codec, 'height': int(resolution[2]) if resolution else 0})
            def rank(item):
                # Prefer the H.264 MP4 CDN family verified in the Web player.
                host = urlsplit(item['url']).hostname
                known_cdn = host in {'v1.adkwai.com', 's1.kwai.net'}
                return ({'H.264': 0, '': 1, 'HEVC': 2}[item['codec']], not known_cdn, item['format'] != 'mp4', -item['height'], item['name'])
            choices = sorted(lines.values(), key=rank)
        except (ValueError, TypeError, KeyError, AttributeError) as error:
            raise SourceError('AniCh 视频资料格式暂不受支持，请稍后重试。') from error
        common.update(lines=[{'id': item['id'], 'name': item['name'], 'url': item['url'], 'format': item['format']} for item in choices], filtered_candidates=rejected)
        selected = next((item for item in choices if item['id'] == line_id), None) if line_id else (choices[0] if choices else None)
        if not selected:
            return {**common, 'status': 'unavailable',
                    'reason': 'line_missing' if choices else 'unverified_resources' if rows else 'no_resources',
                    'message': '所选线路本集暂不可用，请切换线路。' if choices else
                        '已有视频候选，但作品或剧集信息未核对通过，请确认来源。' if rows else
                        f'已匹配《{detail["title"]}》，但 AniCh 没有返回第 {episode_number} 集的视频线路。'}
        return {**common, 'status': 'ready', 'line_id': selected['id'], 'line_name': selected['name'],
                'url': selected['url'], 'format': selected['format'], 'episode_title': f'第 {episode_number} 集'}
