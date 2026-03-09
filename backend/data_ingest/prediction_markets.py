"""Fetch geopolitical prediction market data from Polymarket and Kalshi."""
from __future__ import annotations
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx

ET = ZoneInfo("America/New_York")

GEOPOLITICAL_TAGS = {"geopolitics", "politics", "economics", "trade", "war", "military", "china", "iran", "russia"}


async def fetch_polymarket(limit: int = 30) -> list[dict]:
    """Fetch active geopolitical markets from Polymarket's public API."""
    markets = []
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(
                "https://gamma-api.polymarket.com/markets",
                params={"limit": 100, "active": True, "closed": False, "order": "volume", "ascending": False},
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            for mkt in data:
                tags = set((mkt.get("tags") or "").lower().split(","))
                question = (mkt.get("question") or "").lower()
                # Filter for geopolitical topics
                is_geopolitical = bool(tags & GEOPOLITICAL_TAGS) or any(
                    kw in question for kw in ["war", "iran", "china", "tariff", "sanction", "nato", "military", "russia", "ukraine", "trump", "election"]
                )
                if not is_geopolitical:
                    continue
                markets.append({
                    "source": "Polymarket",
                    "id": mkt.get("conditionId", ""),
                    "question": mkt.get("question", ""),
                    "probability": round(float(mkt.get("outcomePrices", "[0.5]").strip("[]").split(",")[0]), 3) if mkt.get("outcomePrices") else 0.5,
                    "volume": float(mkt.get("volume", 0) or 0),
                    "liquidity": float(mkt.get("liquidity", 0) or 0),
                    "end_date": mkt.get("endDate", ""),
                    "url": f"https://polymarket.com/event/{mkt.get('slug', '')}",
                    "fetched_at": datetime.now(ET).isoformat(),
                })
                if len(markets) >= limit:
                    break
        except Exception:
            pass
    return markets


async def fetch_kalshi(limit: int = 30) -> list[dict]:
    """Fetch active geopolitical markets from Kalshi's public API."""
    markets = []
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(
                "https://trading-api.kalshi.com/trade-api/v2/markets",
                params={"limit": 100, "status": "open"},
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            for mkt in data.get("markets", []):
                title = (mkt.get("title") or "").lower()
                category = (mkt.get("category") or "").lower()
                is_geopolitical = category in {"politics", "geopolitics", "economics", "world"} or any(
                    kw in title for kw in ["war", "iran", "china", "tariff", "sanction", "nato", "military", "russia", "ukraine", "trump"]
                )
                if not is_geopolitical:
                    continue
                markets.append({
                    "source": "Kalshi",
                    "id": mkt.get("ticker", ""),
                    "question": mkt.get("title", ""),
                    "probability": round(float(mkt.get("yes_ask", 0.5) or 0.5), 3),
                    "volume": int(mkt.get("volume", 0) or 0),
                    "liquidity": 0,
                    "end_date": mkt.get("close_time", ""),
                    "url": f"https://kalshi.com/markets/{mkt.get('ticker', '')}",
                    "fetched_at": datetime.now(ET).isoformat(),
                })
                if len(markets) >= limit:
                    break
        except Exception:
            pass
    return markets


async def fetch_all_prediction_markets() -> list[dict]:
    """Fetch from all prediction market sources."""
    poly = await fetch_polymarket()
    kalshi = await fetch_kalshi()
    combined = poly + kalshi
    combined.sort(key=lambda m: m.get("volume", 0), reverse=True)
    return combined
