"""Conservative source matching: exact normalized names plus independent year/episode evidence."""
import re
import unicodedata


def title_key(value):
    return "".join(char for char in unicodedata.normalize("NFKC", str(value)).casefold() if char.isalnum())


def special_search_title(value):
    """Broaden a special's search term while keeping its identity checks separate."""
    value = unicodedata.normalize("NFKC", str(value)).strip()
    return re.sub(
        r"(?:(?:\s+|(?<=[\u3040-\u30ff\u3400-\u9fff]))(?:OAD|OVA|SP)|特别篇|特別篇|特別編)\s*$",
        "", value, flags=re.I,
    ).strip()


def fallback_search_title(value):
    """Build a broad lookup term. Never use this term as proof of identity."""
    value = unicodedata.normalize("NFKC", str(value)).strip()
    result = special_search_title(value)
    result = re.sub(r"^(?:剧场版|劇場版|映画)\s*", "", result).strip()
    # Tilde-delimited subtitles, bracketed editions, seasons and parts vary by source.
    result = re.split(r"[~〜]", result, maxsplit=1)[0].strip()
    # Keep a title wrapped entirely in brackets; only discard an appended note.
    result = re.sub(r"(?<=\S)\s*[（(【\[].*?[）)】\]]\s*$", "", result).strip()
    result = re.sub(
        r"\s*(?:第\s*[一二三四五六七八九十0-9]+\s*(?:部分|季|期|部)|"
        r"(?:season|part)\s*\d+|第\s*\d+\s*クール)\s*$",
        "", result, flags=re.I,
    ).strip()
    result = re.sub(r"(?<=[\u3040-\u30ff\u3400-\u9fff])\s*(?:VIII|VII|III|VI|IV|II|IX|V|X)\s*$", "", result, flags=re.I).strip()
    if re.search(r"[\u3040-\u30ff\u3400-\u9fff]", result):
        result = result.translate(str.maketrans({char: " " for char in "【】[]（）()"})).strip()
        parts = re.split(r"[:：!！?？×・·]", result, maxsplit=1)
        if len(parts) == 2:
            # A short prefix such as Re: is less selective than the actual title.
            result = (parts[0] if len(title_key(parts[0])) >= 3 else parts[1]).strip()
        match = re.fullmatch(r"(.+[\u3040-\u30ff\u3400-\u9fff])\s+[A-Za-z][A-Za-z0-9\s!?'’.,:()_-]*", result)
        if match:
            result = match[1].strip()
    return result if len(title_key(result)) >= 2 else value


def search_keyword(value):
    """Normalize lookup punctuation without changing the stored work identity."""
    keyword = value.strip().rstrip("!！?？△ \t\r\n")
    wrappers = {"【": "】", "《": "》", "「": "」", "『": "』"}
    if len(keyword) > 1 and wrappers.get(keyword[0]) == keyword[-1]:
        keyword = keyword[1:-1].strip()
    return keyword


def discovery_queries(anime):
    names = [
        anime.get("title", ""), anime.get("originalTitle", ""),
        *re.split(r"\s+/\s+", anime.get("aliases", "")),
    ]
    queries = []
    for name in names:
        if not name:
            continue
        for query in (name.strip()[:80], fallback_search_title(name)[:80]):
            keyword = search_keyword(query)
            if keyword and keyword not in queries:
                queries.append(keyword)
    return queries[:6]


def season_number(value):
    text = unicodedata.normalize("NFKC", str(value)).casefold()
    match = re.search(r"第\s*([一二三四五六七八九十0-9]+)\s*(?:季|期|部(?!分))|season\s*(\d+)|(\d+)(?:st|nd|rd|th)\s*season", text)
    if match:
        number = next(value for value in match.groups() if value)
        return int(number) if number.isdigit() else {"一":1,"二":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9,"十":10}.get(number)
    roman = re.search(r"(?:^|\s|(?<=[\u3040-\u30ff\u3400-\u9fff]))(viii|vii|iii|vi|iv|ii|ix|v|x)(?=$|\s|[~〜:])", text)
    return {"ii":2,"iii":3,"iv":4,"v":5,"vi":6,"vii":7,"viii":8,"ix":9,"x":10}.get(roman[1]) if roman else None


def part_number(value):
    text = unicodedata.normalize("NFKC", str(value)).casefold()
    match = re.search(r"第\s*([一二三四0-9]+)\s*(?:部分|クール)|(?:part|cour)\.?\s*(\d+)", text)
    if not match:
        return None
    number = next(item for item in match.groups() if item)
    return int(number) if number.isdigit() else {"一":1,"二":2,"三":3,"四":4}.get(number)


def exact_source(anime, candidates):
    primary = {title_key(anime.get("title", "")), title_key(anime.get("originalTitle", ""))} - {""}
    aliases = re.split(r"\s+/\s+", anime.get("aliases", ""))
    names = primary | {title_key(alias) for alias in aliases if alias}
    year = str(anime.get("year") or "")[:4]
    episodes = anime.get("episodes") or 0
    target_season = season_number(anime.get("title", "")) or season_number(anime.get("originalTitle", ""))
    ranked = []
    for item in candidates:
        name = title_key(item.get("title", ""))
        if not name or name not in names:
            continue
        candidate_season = season_number(item.get("title", ""))
        if target_season and target_season > 1 and candidate_season != target_season:
            continue
        if candidate_season and candidate_season > 1 and candidate_season != target_season:
            continue
        source_year = str(item.get("year") or "")[:4]
        year_match = bool(year and source_year and year == source_year)
        if year and source_year and year != source_year:
            continue
        episode_match = bool(episodes and episodes == item.get("episodes"))
        # Ongoing sources may list only currently available episodes. A unique exact
        # name + matching year is sufficient; absent a year, require equal episodes.
        if not year_match and not (episode_match and name in primary):
            continue
        ranked.append(((int(year_match), int(name in primary), int(episode_match)), item))
    if not ranked:
        return None
    ranked.sort(key=lambda item: item[0], reverse=True)
    if len(ranked) > 1 and ranked[0][0] == ranked[1][0]:
        return None
    return ranked[0][1]["id"]
