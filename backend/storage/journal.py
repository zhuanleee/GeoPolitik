"""Persistent storage for events and analyses using local filesystem.

Uses DATA_ROOT env var for Railway persistent volume mount.
Default: /data/geopol
"""
from __future__ import annotations
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from models.events import GameTheoryAnalysis, GeopoliticalEvent

ET = ZoneInfo("America/New_York")


def _data_root() -> str:
    return os.environ.get("DATA_ROOT", "/data/geopol")


def _ensure_dirs():
    root = _data_root()
    os.makedirs(f"{root}/events", exist_ok=True)
    os.makedirs(f"{root}/analyses", exist_ok=True)
    os.makedirs(f"{root}/prediction_markets", exist_ok=True)


def _today_str() -> str:
    return datetime.now(ET).strftime("%Y-%m-%d")


# ── Events ─────────────────────────────────────────────────────────────
def save_events(events: list[GeopoliticalEvent]) -> int:
    _ensure_dirs()
    path = Path(f"{_data_root()}/events/{_today_str()}.json")
    existing = []
    if path.exists():
        existing = json.loads(path.read_text())
    existing_ids = {e["id"] for e in existing}
    new_events = [e.model_dump(mode="json") for e in events if e.id not in existing_ids]
    existing.extend(new_events)
    path.write_text(json.dumps(existing, indent=2, default=str))
    return len(new_events)


def load_events(date: str | None = None, limit: int = 50) -> list[GeopoliticalEvent]:
    _ensure_dirs()
    date = date or _today_str()
    path = Path(f"{_data_root()}/events/{date}.json")
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    events = [GeopoliticalEvent(**e) for e in data[-limit:]]
    events.sort(key=lambda e: e.relevance_score, reverse=True)
    return events


def load_recent_events(days: int = 3, limit: int = 50) -> list[GeopoliticalEvent]:
    """Load events from the last N days."""
    _ensure_dirs()
    all_events = []
    for i in range(days):
        dt = datetime.now(ET) - timedelta(days=i)
        date_str = dt.strftime("%Y-%m-%d")
        all_events.extend(load_events(date_str, limit=100))
    all_events.sort(key=lambda e: e.relevance_score, reverse=True)
    return all_events[:limit]


# ── Analyses ───────────────────────────────────────────────────────────
def save_analysis(analysis: GameTheoryAnalysis):
    _ensure_dirs()
    root = _data_root()
    path = Path(f"{root}/analyses/{analysis.id}.json")
    path.write_text(json.dumps(analysis.model_dump(mode="json"), indent=2, default=str))
    # Append to daily index
    index_path = Path(f"{root}/analyses/index_{_today_str()}.json")
    index = []
    if index_path.exists():
        index = json.loads(index_path.read_text())
    index.append({
        "id": analysis.id,
        "topic": analysis.topic,
        "event_id": analysis.event_id,
        "convergence": analysis.incentive_convergence.value,
        "confidence": analysis.confidence,
        "analyzed_at": analysis.analyzed_at.isoformat() if analysis.analyzed_at else "",
        "scenario_count": len(analysis.scenarios),
        "trade_idea_count": len(analysis.trade_ideas),
    })
    index_path.write_text(json.dumps(index, indent=2, default=str))


def load_analysis(analysis_id: str) -> GameTheoryAnalysis | None:
    path = Path(f"{_data_root()}/analyses/{analysis_id}.json")
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return GameTheoryAnalysis(**data)


def load_latest_analyses(limit: int = 10) -> list[dict]:
    """Load latest analysis summaries from index."""
    _ensure_dirs()
    root = _data_root()
    all_entries = []
    for i in range(7):
        dt = datetime.now(ET) - timedelta(days=i)
        date_str = dt.strftime("%Y-%m-%d")
        index_path = Path(f"{root}/analyses/index_{date_str}.json")
        if index_path.exists():
            entries = json.loads(index_path.read_text())
            all_entries.extend(entries)
    all_entries.sort(key=lambda e: e.get("analyzed_at", ""), reverse=True)
    return all_entries[:limit]


# ── Prediction Markets ─────────────────────────────────────────────────
def save_prediction_markets(markets: list[dict]):
    _ensure_dirs()
    path = Path(f"{_data_root()}/prediction_markets/{_today_str()}.json")
    path.write_text(json.dumps(markets, indent=2, default=str))


def load_prediction_markets() -> list[dict]:
    _ensure_dirs()
    path = Path(f"{_data_root()}/prediction_markets/{_today_str()}.json")
    if not path.exists():
        return []
    return json.loads(path.read_text())
