"""Read-only AniCh compatibility probe. Not used by the running Tsukimi app.

Protocol reference: Sle2p/AniCh lib/protobuf/bangumi.pbjson.dart and
lib/src/pages/bangumi_vod/controller.dart (urlDecode). Uses existing httpx.
"""
import argparse
import base64
import json
import sys
from urllib.parse import urlsplit

import httpx

BASE = "https://anich.sends.eu.org"
LIMIT = 2 * 1024 * 1024


def fields(data):
    """Bounded Protobuf wire reader; retain unknown fields without interpreting them."""
    if len(data) > LIMIT:
        raise ValueError("Response exceeds probe limit")
    position = 0

    def varint():
        nonlocal position
        result = 0
        for shift in range(0, 70, 7):
            if position >= len(data):
                raise ValueError("Truncated varint")
            value = data[position]
            position += 1
            result |= (value & 127) << shift
            if value < 128:
                return result
        raise ValueError("Oversized varint")

    while position < len(data):
        tag = varint()
        number, wire = tag >> 3, tag & 7
        if number == 0:
            raise ValueError("Invalid field number")
        if wire == 0:
            value = varint()
        elif wire in (1, 2, 5):
            size = varint() if wire == 2 else (8 if wire == 1 else 4)
            if position + size > len(data):
                raise ValueError("Truncated field")
            value = data[position:position + size]
            position += size
        else:
            raise ValueError(f"Unsupported wire type {wire}")
        yield number, value


def text(data, number):
    return data.get(number, b"").decode("utf-8")


def response_bytes(client, path, params=None):
    with client.stream("GET", BASE + path, params=params) as response:
        response.raise_for_status()
        chunks, size = [], 0
        for chunk in response.iter_bytes():
            size += len(chunk)
            if size > LIMIT:
                raise ValueError("Response exceeds probe limit")
            chunks.append(chunk)
        return b"".join(chunks)


def messages(payload):
    return [dict(fields(value)) for number, value in fields(payload) if number == 1]


def decode_url(encoded):
    # Exactly the public client's urlDecode rule: remove character at index 3.
    value = encoded[:3] + encoded[4:]
    url = base64.b64decode(value + "=" * (-len(value) % 4), validate=True).decode("utf-8")
    if urlsplit(url).scheme not in ("http", "https"):
        raise ValueError("Not an HTTP media URL")
    return url


def probe_media(client, url):
    # Stream and close after 1 KB even if a CDN ignores Range. No full download.
    with client.stream("GET", url, headers={"Range": "bytes=0-1023", "Origin": "http://127.0.0.1:3000"}) as response:
        prefix = next(response.iter_bytes(chunk_size=1024), b"")
        return {"host": urlsplit(str(response.url)).hostname, "status": response.status_code,
                "content_type": response.headers.get("content-type"),
                "allow_origin": response.headers.get("access-control-allow-origin"),
                "content_range": response.headers.get("content-range"),
                "mp4_signature": prefix[4:8] == b"ftyp", "bytes_read": len(prefix)}


def run(args):
    with httpx.Client(timeout=15, follow_redirects=True,
                      headers={"User-Agent": "Tsukimi/0.4 (personal study; read-only compatibility probe)"}) as client:
        payload = response_bytes(client, "/bangumi/search", {"keyword": args.query, "skip": 0})
        results = [{"id": item[1], "title": text(item, 2), "episodes": item.get(4, 0)}
                   for item in messages(payload)]
        print(json.dumps({"search": results}, ensure_ascii=False, indent=2))
        if not args.id:
            print("Choose a verified search ID with --id; search IDs are not Bangumi IDs.")
            return
        detail = json.loads(response_bytes(client, f"/bangumi/detail/{args.id}"))
        episodes = messages(response_bytes(client, f"/bangumi/episodes/{args.id}"))
        print(json.dumps({"detail": {key: detail.get(key) for key in ("id", "title", "airdate", "episodes_total", "sites")},
                          "episode_count": len(episodes)}, ensure_ascii=False, indent=2))
        raw = json.loads(response_bytes(client, f"/vod/{args.id}/{args.episode}"))
        if not isinstance(raw, list) or len(raw) > LIMIT or any(type(n) is not int or not 0 <= n <= 255 for n in raw):
            raise ValueError("Unexpected VOD byte array")
        rows = messages(bytes(raw))
        urls, summary = [], []
        for item in rows:
            url = decode_url(text(item, 1))
            urls.append(url)
            summary.append({"host": urlsplit(url).hostname, "caption": text(item, 4),
                            "source_label_observed": text(item, 5), "description_observed": text(item, 6)})
        print(json.dumps({"vod_count": len(rows),
                          "distinct_source_labels": len({row['source_label_observed'] for row in summary}),
                          "lines": summary}, ensure_ascii=False, indent=2))
        if args.probe_media:
            # Check at most two different hosts; no automatic playback selection.
            seen = set()
            for url in urls:
                host = urlsplit(url).hostname
                if host in seen:
                    continue
                seen.add(host)
                try:
                    print(json.dumps({"media_probe": probe_media(client, url)}, ensure_ascii=False))
                except httpx.HTTPError as error:
                    print(json.dumps({"media_probe": {"host": host, "error": type(error).__name__}}))
                if len(seen) == 2:
                    break


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", default="葬送的芙莉莲")
    parser.add_argument("--id", type=int)
    parser.add_argument("--episode", type=int, default=1)
    parser.add_argument("--probe-media", action="store_true")
    options = parser.parse_args()
    if options.episode < 1 or (options.id is not None and options.id < 1):
        parser.error("ID and episode must be positive")
    try:
        run(options)
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as error:
        # Do not print temporary signed URLs contained in exception text.
        print(f"Probe failed: {type(error).__name__}", file=sys.stderr)
        sys.exit(1)