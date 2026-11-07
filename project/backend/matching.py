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
    """Use a series keyword for title-specific search errors, preserving identity separately."""
    value = unicodedata.normalize("NFKC", str(value)).strip()
    special = special_search_title(value)
    if special != value:
        return special
    # Some AniCh searches reject a CJK title followed by a Latin subtitle such as Fine.
    match = re.fullmatch(r"(.+[\u3040-\u30ff\u3400-\u9fff])\s+[A-Za-z][A-Za-z0-9\s!?'’.,:()_-]*", value)
    return match[1].strip() if match else value


def season_number(value):
    text = unicodedata.normalize("NFKC", str(value)).casefold()
    match = re.search(r"第\s*([一二三四五六七八九十0-9]+)\s*[季期部]|season\s*(\d+)|(\d+)(?:st|nd|rd|th)\s*season", text)
    if not match:
        return None
    number = next(value for value in match.groups() if value)
    return int(number) if number.isdigit() else {"一":1,"二":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9,"十":10}.get(number)

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
