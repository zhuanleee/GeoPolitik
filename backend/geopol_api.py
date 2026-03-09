"""GeoPolitik — Geopolitical Game Theory Analysis API.

Applies Professor Jiang Xueqin's "Predictive History" framework:
game theory + civilizational history + financial analysis → trading ideas.

Deploy: Railway (Docker)
"""
from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from models.events import DashboardData, GameTheoryAnalysis, GeopoliticalEvent
from data_ingest.news_fetcher import fetch_all_events
from data_ingest.prediction_markets import fetch_all_prediction_markets
from analysis.game_theory_engine import GameTheoryEngine
from analysis.player_registry import PLAYER_REGISTRY
from storage.journal import (
    load_analysis, load_events, load_latest_analyses,
    load_prediction_markets, load_recent_events,
    save_analysis, save_events, save_prediction_markets,
)

ET = ZoneInfo("America/New_York")
log = logging.getLogger("geopol")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

scheduler = AsyncIOScheduler(timezone=ET)


# ── Cron Jobs ──────────────────────────────────────────────────────────
async def ingest_events_job():
    """Fetch and store fresh geopolitical events."""
    try:
        newsapi_key = os.environ.get("NEWSAPI_KEY", "")
        events = await fetch_all_events(newsapi_key or None)
        if events:
            count = save_events(events)
            log.info(f"Ingested {count} new events (batch: {len(events)})")
    except Exception as e:
        log.error(f"Event ingestion failed: {e}")


async def refresh_markets_job():
    """Refresh prediction market data."""
    try:
        markets = await fetch_all_prediction_markets()
        if markets:
            save_prediction_markets(markets)
            log.info(f"Fetched {len(markets)} prediction markets")
    except Exception as e:
        log.error(f"Prediction market refresh failed: {e}")


# ── App Lifecycle ──────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: schedule crons and run initial ingestion
    scheduler.add_job(ingest_events_job, CronTrigger(minute="*/30", hour="6-23", timezone=ET), id="ingest_events")
    scheduler.add_job(refresh_markets_job, CronTrigger(minute="0", hour="*/4", timezone=ET), id="refresh_markets")
    scheduler.start()
    log.info("Scheduler started — events every 30m (6am-11pm ET), markets every 4h")

    # Run initial ingestion in background
    asyncio.create_task(ingest_events_job())
    asyncio.create_task(refresh_markets_job())

    yield

    # Shutdown
    scheduler.shutdown(wait=False)
    log.info("Scheduler stopped")


# ── FastAPI App ────────────────────────────────────────────────────────
app = FastAPI(title="GeoPolitik API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_engine() -> GameTheoryEngine:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    return GameTheoryEngine(api_key=api_key)


# ── Health ─────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    """Self-health check: API status, data freshness, pipeline health."""
    checks = {
        "api": "ok",
        "anthropic_key": "ok" if os.environ.get("ANTHROPIC_API_KEY") else "missing",
        "newsapi_key": "ok" if os.environ.get("NEWSAPI_KEY") else "missing",
        "scheduler": "running" if scheduler.running else "stopped",
    }

    data_root = os.environ.get("DATA_ROOT", "/data/geopol")
    events_dir = Path(f"{data_root}/events")
    if events_dir.exists():
        files = sorted(events_dir.glob("*.json"), reverse=True)
        if files:
            latest_file = files[0].stem
            checks["latest_events_date"] = latest_file
            try:
                file_dt = datetime.strptime(latest_file, "%Y-%m-%d").replace(tzinfo=ET)
                hours_old = (datetime.now(ET) - file_dt).total_seconds() / 3600
                checks["events_freshness"] = "fresh" if hours_old < 24 else f"stale ({hours_old:.0f}h old)"
            except Exception:
                checks["events_freshness"] = "unknown"
        else:
            checks["events_freshness"] = "no data"
    else:
        checks["events_freshness"] = "no data dir"

    analyses = load_latest_analyses(limit=1)
    if analyses:
        checks["latest_analysis"] = analyses[0].get("topic", "unknown")
        checks["latest_analysis_at"] = analyses[0].get("analyzed_at", "unknown")
    else:
        checks["latest_analysis"] = "none"

    overall = "healthy" if checks.get("anthropic_key") == "ok" and scheduler.running else "degraded"
    return {
        "status": overall,
        "service": "geopol-api",
        "timestamp": datetime.now(ET).isoformat(),
        "checks": checks,
    }


# ── Events ─────────────────────────────────────────────────────────────
@app.get("/events/latest")
async def get_latest_events(limit: int = Query(30, ge=1, le=100)):
    """Fetch fresh events from all sources and return them."""
    newsapi_key = os.environ.get("NEWSAPI_KEY", "")
    events = await fetch_all_events(newsapi_key or None)
    if events:
        save_events(events)
    return {"events": [e.model_dump(mode="json") for e in events[:limit]], "count": len(events)}


@app.get("/events/cached")
async def get_cached_events(days: int = Query(3, ge=1, le=14), limit: int = Query(50, ge=1, le=200)):
    """Return cached events from recent days."""
    events = load_recent_events(days=days, limit=limit)
    return {"events": [e.model_dump(mode="json") for e in events], "count": len(events)}


@app.get("/events/search")
async def search_events(q: str = Query(..., min_length=2), limit: int = Query(20, ge=1, le=100)):
    """Search cached events by keyword."""
    events = load_recent_events(days=7, limit=200)
    q_lower = q.lower()
    matches = [e for e in events if q_lower in e.title.lower() or q_lower in e.summary.lower()]
    return {"events": [e.model_dump(mode="json") for e in matches[:limit]], "count": len(matches)}


# ── Analysis ───────────────────────────────────────────────────────────
@app.post("/analysis/run")
async def run_analysis(
    event_id: str = Query(None),
    topic: str = Query(None),
    description: str = Query(""),
    actors: str = Query(""),
):
    """Run game theory analysis on an event or custom topic."""
    engine = _get_engine()
    context_events = load_recent_events(days=3, limit=20)
    prediction_markets = load_prediction_markets()

    if event_id:
        all_events = load_recent_events(days=7, limit=200)
        event = next((e for e in all_events if e.id == event_id), None)
        if not event:
            raise HTTPException(status_code=404, detail=f"Event {event_id} not found")
        analysis = await engine.analyze(event, context_events, prediction_markets)
    elif topic:
        actor_list = [a.strip() for a in actors.split(",") if a.strip()] if actors else []
        analysis = await engine.analyze_custom_topic(
            topic=topic,
            description=description,
            actors=actor_list,
            context_events=context_events,
            prediction_markets=prediction_markets,
        )
    else:
        raise HTTPException(status_code=400, detail="Provide event_id or topic")

    save_analysis(analysis)
    return analysis.model_dump(mode="json")


@app.get("/analysis/{analysis_id}")
async def get_analysis(analysis_id: str):
    """Get a previously run analysis by ID."""
    analysis = load_analysis(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail=f"Analysis {analysis_id} not found")
    return analysis.model_dump(mode="json")


@app.get("/analysis/latest/list")
async def get_latest_analyses(limit: int = Query(10, ge=1, le=50)):
    """Get latest analysis summaries."""
    entries = load_latest_analyses(limit=limit)
    return {"analyses": entries, "count": len(entries)}


# ── Prediction Markets ─────────────────────────────────────────────────
@app.get("/prediction-markets")
async def get_prediction_markets(refresh: bool = Query(False)):
    """Get geopolitical prediction market data."""
    if refresh:
        markets = await fetch_all_prediction_markets()
        if markets:
            save_prediction_markets(markets)
        return {"markets": markets, "count": len(markets)}
    else:
        markets = load_prediction_markets()
        if not markets:
            markets = await fetch_all_prediction_markets()
            if markets:
                save_prediction_markets(markets)
        return {"markets": markets, "count": len(markets)}


# ── Players ────────────────────────────────────────────────────────────
@app.get("/players")
async def get_players():
    """Get all players in the registry."""
    return {"players": PLAYER_REGISTRY}


@app.get("/players/{name}")
async def get_player(name: str):
    """Get a specific player's profile."""
    name_lower = name.lower()
    for key, val in PLAYER_REGISTRY.items():
        if name_lower in key.lower():
            return {"name": key, **val}
    raise HTTPException(status_code=404, detail=f"Player '{name}' not found")


# ── Dashboard ──────────────────────────────────────────────────────────
@app.get("/dashboard")
async def get_dashboard():
    """Aggregated dashboard data (single call for frontend)."""
    events = load_recent_events(days=2, limit=30)
    analyses = load_latest_analyses(limit=10)
    markets = load_prediction_markets()

    high_impact_today = sum(1 for e in events if e.relevance_score >= 50)
    active_scenarios = sum(a.get("scenario_count", 0) for a in analyses[:5])
    avg_convergence = 0.0
    if analyses:
        conv_map = {"STRONG": 90, "MODERATE": 65, "WEAK": 30}
        avg_convergence = sum(conv_map.get(a.get("convergence", "WEAK"), 30) for a in analyses) / len(analyses)
    open_trades = sum(a.get("trade_idea_count", 0) for a in analyses[:5])

    return {
        "metrics": {
            "active_scenarios": active_scenarios,
            "high_impact_events_today": high_impact_today,
            "avg_convergence": round(avg_convergence, 1),
            "open_trade_ideas": open_trades,
        },
        "latest_events": [e.model_dump(mode="json") for e in events[:20]],
        "latest_analyses": analyses,
        "prediction_markets": markets[:15],
        "timestamp": datetime.now(ET).isoformat(),
    }
