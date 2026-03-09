"""Multi-source geopolitical news aggregation: NewsAPI + RSS feeds + GDELT."""
from __future__ import annotations
import hashlib
import re
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from zoneinfo import ZoneInfo

import feedparser
import httpx

from models.events import GeopoliticalEvent, Region, now_et

ET = ZoneInfo("America/New_York")

# ── Relevance Keywords (weighted) ──────────────────────────────────────
HIGH_WEIGHT_KEYWORDS = {
    "tariff", "sanction", "sanctions", "embargo", "trade war", "military",
    "invasion", "war", "conflict", "nuclear", "missile", "escalation",
    "ceasefire", "treaty", "summit", "nato", "brics", "opec", "semiconductor",
    "rare earth", "oil embargo", "blockade", "coup", "regime change",
    "currency war", "dollar hegemony", "reserve currency", "debt crisis",
    "default", "swift", "export controls", "arms deal",
}
MEDIUM_WEIGHT_KEYWORDS = {
    "diplomacy", "bilateral", "alliance", "geopolitical", "strategic",
    "defense", "intelligence", "espionage", "cyber attack", "election",
    "referendum", "succession", "pipeline", "energy security", "food security",
    "supply chain", "decoupling", "deglobalization", "proxy war",
}

# ── Region Detection ───────────────────────────────────────────────────
REGION_PATTERNS = {
    Region.US_CHINA: ["us-china", "china trade", "taiwan", "south china sea", "beijing", "washington"],
    Region.MIDDLE_EAST: ["iran", "israel", "saudi", "iraq", "syria", "gaza", "houthi", "hezbollah", "middle east"],
    Region.EUROPE: ["ukraine", "russia", "nato", "eu ", "european union", "brexit", "nord stream"],
    Region.INDO_PACIFIC: ["india", "japan", "korea", "asean", "pacific", "quad", "aukus", "australia"],
    Region.AMERICAS: ["latin america", "brazil", "mexico", "canada", "caribbean", "venezuela"],
    Region.AFRICA: ["africa", "sahel", "ethiopia", "libya", "sudan", "niger"],
}

# ── RSS Feeds ──────────────────────────────────────────────────────────
RSS_FEEDS = [
    ("Reuters World", "https://www.reutersagency.com/feed/?best-topics=political-general&post_type=best"),
    ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
    ("SCMP", "https://www.scmp.com/rss/91/feed"),
    ("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("NPR World", "https://feeds.npr.org/1004/rss.xml"),
]


def _make_id(title: str, date: str) -> str:
    return hashlib.md5(f"{title}:{date}".encode()).hexdigest()[:12]


def _score_relevance(title: str, summary: str) -> tuple[float, list[str]]:
    """Score relevance 0-100 and extract matched keywords."""
    text = f"{title} {summary}".lower()
    matched = []
    score = 0.0
    for kw in HIGH_WEIGHT_KEYWORDS:
        if kw in text:
            score += 15
            matched.append(kw)
    for kw in MEDIUM_WEIGHT_KEYWORDS:
        if kw in text:
            score += 8
            matched.append(kw)
    return min(score, 100.0), matched


def _detect_region(text: str) -> Region:
    text_lower = text.lower()
    best_region = Region.GLOBAL
    best_count = 0
    for region, patterns in REGION_PATTERNS.items():
        count = sum(1 for p in patterns if p in text_lower)
        if count > best_count:
            best_count = count
            best_region = region
    return best_region


def _detect_actors(text: str) -> list[str]:
    """Simple actor detection from text."""
    actor_patterns = {
        "United States": r"\b(US|U\.S\.|United States|America|Washington|White House|Pentagon|Trump|Biden)\b",
        "China": r"\b(China|Beijing|Xi Jinping|CCP|PLA)\b",
        "Russia": r"\b(Russia|Moscow|Putin|Kremlin)\b",
        "Iran": r"\b(Iran|Tehran|Khamenei|IRGC)\b",
        "Israel": r"\b(Israel|Netanyahu|IDF|Tel Aviv)\b",
        "EU": r"\b(EU|European Union|Brussels|Macron|Scholz)\b",
        "Japan": r"\b(Japan|Tokyo|Kishida)\b",
        "India": r"\b(India|Modi|New Delhi)\b",
        "Saudi Arabia": r"\b(Saudi|MBS|Riyadh|OPEC)\b",
        "North Korea": r"\b(North Korea|Pyongyang|Kim Jong)\b",
        "NATO": r"\b(NATO)\b",
        "Fed": r"\b(Federal Reserve|Fed |Powell)\b",
    }
    found = []
    for actor, pattern in actor_patterns.items():
        if re.search(pattern, text, re.IGNORECASE):
            found.append(actor)
    return found


def _is_duplicate(title: str, existing: list[GeopoliticalEvent], threshold: float = 0.75) -> bool:
    for evt in existing:
        if SequenceMatcher(None, title.lower(), evt.title.lower()).ratio() > threshold:
            return True
    return False


# ── Fetchers ───────────────────────────────────────────────────────────
async def fetch_newsapi(api_key: str, query: str = "geopolitics OR tariff OR sanctions OR war OR military") -> list[GeopoliticalEvent]:
    """Fetch from NewsAPI top headlines + everything."""
    events = []
    async with httpx.AsyncClient(timeout=15) as client:
        # Top headlines (geopolitics tends to be top news)
        resp = await client.get(
            "https://newsapi.org/v2/top-headlines",
            params={"category": "general", "language": "en", "pageSize": 30, "apiKey": api_key},
        )
        if resp.status_code == 200:
            articles = resp.json().get("articles", [])
            for art in articles:
                title = art.get("title") or ""
                summary = art.get("description") or ""
                score, keywords = _score_relevance(title, summary)
                if score < 10:
                    continue
                combined = f"{title} {summary}"
                events.append(GeopoliticalEvent(
                    id=_make_id(title, art.get("publishedAt", "")),
                    title=title,
                    summary=summary,
                    sources=[art.get("url", "")],
                    published_at=art.get("publishedAt", now_et().isoformat()),
                    relevance_score=score,
                    region=_detect_region(combined),
                    actors=_detect_actors(combined),
                    keywords=keywords,
                ))

        # Everything endpoint (broader search)
        from_date = (now_et() - timedelta(days=2)).strftime("%Y-%m-%d")
        resp2 = await client.get(
            "https://newsapi.org/v2/everything",
            params={"q": query, "language": "en", "sortBy": "relevancy", "pageSize": 20, "from": from_date, "apiKey": api_key},
        )
        if resp2.status_code == 200:
            articles2 = resp2.json().get("articles", [])
            for art in articles2:
                title = art.get("title") or ""
                summary = art.get("description") or ""
                score, keywords = _score_relevance(title, summary)
                if score < 15:
                    continue
                if _is_duplicate(title, events):
                    continue
                combined = f"{title} {summary}"
                events.append(GeopoliticalEvent(
                    id=_make_id(title, art.get("publishedAt", "")),
                    title=title,
                    summary=summary,
                    sources=[art.get("url", "")],
                    published_at=art.get("publishedAt", now_et().isoformat()),
                    relevance_score=score,
                    region=_detect_region(combined),
                    actors=_detect_actors(combined),
                    keywords=keywords,
                ))
    return events


async def fetch_rss_feeds() -> list[GeopoliticalEvent]:
    """Parse curated RSS feeds for geopolitical news."""
    events = []
    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
        for feed_name, url in RSS_FEEDS:
            try:
                resp = await client.get(url)
                if resp.status_code != 200:
                    continue
                feed = feedparser.parse(resp.text)
                for entry in feed.entries[:15]:
                    title = entry.get("title", "")
                    summary = entry.get("summary", entry.get("description", ""))
                    # Strip HTML tags from summary
                    summary = re.sub(r"<[^>]+>", "", summary)[:500]
                    score, keywords = _score_relevance(title, summary)
                    if score < 10:
                        continue
                    if _is_duplicate(title, events):
                        continue
                    published = entry.get("published", "")
                    combined = f"{title} {summary}"
                    events.append(GeopoliticalEvent(
                        id=_make_id(title, published),
                        title=title,
                        summary=summary,
                        sources=[entry.get("link", "")],
                        published_at=published or now_et().isoformat(),
                        relevance_score=score,
                        region=_detect_region(combined),
                        actors=_detect_actors(combined),
                        keywords=keywords,
                    ))
            except Exception:
                continue
    return events


async def fetch_gdelt(query: str = "sanctions OR tariff OR military conflict") -> list[GeopoliticalEvent]:
    """Fetch from GDELT 2.0 DOC API (free, no key)."""
    events = []
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(
                "https://api.gdeltproject.org/api/v2/doc/doc",
                params={
                    "query": query,
                    "mode": "ArtList",
                    "maxrecords": 20,
                    "format": "json",
                    "sourcelang": "english",
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                articles = data.get("articles", [])
                for art in articles:
                    title = art.get("title", "")
                    url = art.get("url", "")
                    seendate = art.get("seendate", "")
                    tone = art.get("tone", 0)
                    domain = art.get("domain", "")
                    score, keywords = _score_relevance(title, "")
                    if score < 10:
                        continue
                    if _is_duplicate(title, events):
                        continue
                    events.append(GeopoliticalEvent(
                        id=_make_id(title, seendate),
                        title=title,
                        summary=f"Source: {domain}",
                        sources=[url],
                        published_at=seendate or now_et().isoformat(),
                        relevance_score=score,
                        region=_detect_region(title),
                        actors=_detect_actors(title),
                        keywords=keywords,
                        sentiment=round(tone / 10, 2) if tone else 0.0,
                    ))
        except Exception:
            pass
    return events


async def fetch_all_events(newsapi_key: str | None = None) -> list[GeopoliticalEvent]:
    """Aggregate events from all sources, deduplicate, sort by relevance."""
    all_events: list[GeopoliticalEvent] = []

    # Fetch from all sources
    rss_events = await fetch_rss_feeds()
    all_events.extend(rss_events)

    gdelt_events = await fetch_gdelt()
    # Dedupe against existing
    for evt in gdelt_events:
        if not _is_duplicate(evt.title, all_events):
            all_events.append(evt)

    if newsapi_key:
        newsapi_events = await fetch_newsapi(newsapi_key)
        for evt in newsapi_events:
            if not _is_duplicate(evt.title, all_events):
                all_events.append(evt)

    # Sort by relevance score descending
    all_events.sort(key=lambda e: e.relevance_score, reverse=True)
    return all_events
