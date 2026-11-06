"""AniCh aggregate adapter. Metadata/choices cached, signed video URLs never cached."""
from datetime import datetime, timezone
import hashlib
import ipaddress
import os
import re
import time
from threading import Lock
from urllib.parse import urlsplit

import httpx

from anich_protocol import LIMIT, fields, decode_url
from matching import exact_source, title_key, season_number
from source_errors import SourceError


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
                if response.status_code == 429:
                    raise SourceError('AniCh 请求较多，请稍后重试。', 503)
                response.raise_for_status()
                chunks, size = [], 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > LIMIT:
                        raise ValueError('oversized response')
                    chunks.append(chunk)
            import json
            raw = b''.join(chunks)
            result = json.loads(raw) if json_result else raw
            if isinstance(result, dict) and result.get('error'):
                raise SourceError('AniCh 服务暂时拒绝了请求，请稍后重试。', 503)
            return result
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

    def search(self, query):
        # AniCh rejects some terminal title punctuation (e.g. 孤独摇滚！) with HTTP 500.
        # Only simplify the lookup keyword; returned titles and identity checks stay intact.
        keyword = query.strip().rstrip('!！?？△ \t\r\n')
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
        queries = list(dict.fromkeys(value.strip()[:80] for value in
            (anime.get('title', ''), anime.get('originalTitle', '')) if value.strip()))
        names = {title_key(value) for value in (anime.get('title', ''), anime.get('originalTitle', ''),
            *re.split(r'\s+/\s+', anime.get('aliases', ''))) if value}
        for query in queries[:2]:
            for item in self.search(query):
                candidates[item['id']] = item
            verified, fallback = [], []
            # Bound detail fan-out; exact title before fetching any candidate detail.
            for item in [item for item in candidates.values() if title_key(item['title']) in names][:4]:
                detail = self.detail(item['id'])
                stamp = detail.get('airdate')
                if isinstance(stamp, (int, float)) and stamp > 0:
                    item = {**item, 'year': str(datetime.fromtimestamp(stamp / 1000, timezone.utc).year)}
                    candidates[item['id']] = item
                linked = self.mapped_ids(detail)
                if anime['id'].removeprefix('bgm-') in linked:
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
        return None, list(candidates.values())

    def episodes(self, source_id):
        def load():
            try:
                return messages(self._get(f'/bangumi/episodes/{source_id}'))
            except (ValueError, TypeError) as error:
                raise SourceError('AniCh 剧集资料格式暂不受支持。') from error
        return self._cached(('episodes', source_id), load)

    def resolve(self, source_id, episode_number, line_id=None):
        detail = self.detail(source_id)
        episodes = self.episodes(source_id)
        available = {row.get(2) for row in episodes if row.get(1) == 1 and isinstance(row.get(2), int)}
        common = {'provider': self.name, 'source_anime_id': source_id, 'source_title': detail['title'],
                  'episode_count': max(available, default=0), 'lines': [], 'line_id': None}
        if episode_number not in available:
            return {**common, 'status': 'unavailable', 'message': 'AniCh 暂未提供这一集，请稍后重试或重新匹配。'}
        raw = self._get(f'/vod/{source_id}/{episode_number}', json_result=True)
        try:
            if not isinstance(raw, list) or len(raw) > LIMIT or any(type(n) is not int or not 0 <= n <= 255 for n in raw):
                raise ValueError('not a byte array')
            rows = messages(bytes(raw))
            names = {title_key(value) for value in [detail['title'], *detail.get('titles', [])]}
            target_season = season_number(detail['title'])
            lines = {}
            rejected = 0
            for row in rows:
                if row.get(2) != episode_number:
                    rejected += 1
                    continue
                description = text(row, 6)
                title = description.split('·', 1)[0].strip()
                candidate_season = season_number(title)
                if (candidate_season and candidate_season > 1 and candidate_season != target_season) or (title and title_key(title) not in names):
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
            return {**common, 'status': 'unavailable', 'message': '所选线路本集暂不可用，请切换线路。' if choices else '尚无核对通过的线路，请稍后重试或重新匹配。'}
        return {**common, 'status': 'ready', 'line_id': selected['id'], 'line_name': selected['name'],
                'url': selected['url'], 'format': selected['format'], 'episode_title': f'第 {episode_number} 集'}
