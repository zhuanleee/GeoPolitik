"""Pydantic models for geopolitical events, players, scenarios, and trade ideas."""
from __future__ import annotations
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")


def now_et() -> datetime:
    return datetime.now(ET)


# ── Enums ──────────────────────────────────────────────────────────────
class Region(str, Enum):
    US_CHINA = "US-China"
    MIDDLE_EAST = "Middle East"
    EUROPE = "Europe"
    INDO_PACIFIC = "Indo-Pacific"
    AMERICAS = "Americas"
    AFRICA = "Africa"
    GLOBAL = "Global"


class Convergence(str, Enum):
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"


class Conviction(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class OptionsStructure(str, Enum):
    DEBIT_SPREAD = "Debit Spread"
    CREDIT_SPREAD = "Credit Spread"
    STRADDLE = "Straddle"
    STRANGLE = "Strangle"
    IRON_CONDOR = "Iron Condor"
    BUTTERFLY = "Butterfly"
    OUTRIGHT_CALL = "Outright Call"
    OUTRIGHT_PUT = "Outright Put"
    PROTECTIVE_PUT = "Protective Put"
    COLLAR = "Collar"
    CALENDAR_SPREAD = "Calendar Spread"
    LEAPS = "LEAPS"


# ── Core Models ────────────────────────────────────────────────────────
class GeopoliticalEvent(BaseModel):
    id: str
    title: str
    summary: str
    sources: list[str] = []
    published_at: datetime
    ingested_at: datetime = Field(default_factory=now_et)
    relevance_score: float = 0.0
    region: Region = Region.GLOBAL
    actors: list[str] = []
    keywords: list[str] = []
    sentiment: float = 0.0
    prediction_market_odds: dict | None = None


class Player(BaseModel):
    name: str
    type: str  # nation_state, institution, lobby, individual
    primary_objective: str
    secondary_objectives: list[str] = []
    red_lines: list[str] = []
    constraints: dict[str, str] = {}
    dominant_strategy: str = ""
    tools_available: list[str] = []


class Scenario(BaseModel):
    title: str
    description: str
    probability: float  # 0-100
    timeline_days: int
    triggers: list[str] = []
    invalidators: list[str] = []
    market_impact: dict[str, str] = {}  # asset -> direction/magnitude


class TradeIdea(BaseModel):
    scenario_title: str
    conviction: Conviction
    direction: str  # "long", "short", "vol_long", "vol_short"
    assets: list[str]
    structure: OptionsStructure
    suggested_dte: int
    rationale: str
    entry_notes: str = ""
    risk_notes: str = ""


class GameTheoryAnalysis(BaseModel):
    id: str
    event_id: str
    analyzed_at: datetime = Field(default_factory=now_et)
    topic: str

    # Players
    players: list[Player] = []

    # Equilibrium
    nash_equilibrium: str = ""
    equilibrium_stability: str = ""  # stable, unstable, shifting
    incentive_convergence: Convergence = Convergence.WEAK
    convergence_direction: str = ""

    # Scenarios
    scenarios: list[Scenario] = []

    # Trade ideas
    trade_ideas: list[TradeIdea] = []

    # Meta
    confidence: float = 0.0
    key_uncertainties: list[str] = []
    watch_for: list[str] = []
    raw_reasoning: str = ""


class DashboardData(BaseModel):
    active_scenarios: int = 0
    high_impact_events_today: int = 0
    avg_convergence: float = 0.0
    open_trade_ideas: int = 0
    latest_events: list[GeopoliticalEvent] = []
    latest_analyses: list[GameTheoryAnalysis] = []
    prediction_markets: list[dict] = []
