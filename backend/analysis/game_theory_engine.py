"""Core Game Theory Analysis Engine using Claude API.

Implements Professor Jiang Xueqin's "Predictive History" framework:
1. Identify players and their self-interest
2. Map constraints (debt, military, political, economic)
3. Find dominant strategies / Nash equilibria
4. Detect incentive convergence
5. Generate scenarios with probabilities
6. Map to tradeable assets and options structures
"""
from __future__ import annotations
import hashlib
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import anthropic

from models.events import (
    Convergence, Conviction, GameTheoryAnalysis, GeopoliticalEvent,
    OptionsStructure, Player, Scenario, TradeIdea, now_et,
)
from analysis.player_registry import format_players_for_prompt, get_players_for_actors

ET = ZoneInfo("America/New_York")

SYSTEM_PROMPT = """You are a geopolitical game theory analyst applying Professor Jiang Xueqin's "Predictive History" framework. You combine civilizational history, game theory, and financial analysis to forecast geopolitical outcomes and their market impact.

## YOUR METHOD (follow strictly):

### 1. IDENTIFY PLAYERS
List all key actors (nation-states, institutions, lobbies, individuals) with material influence on the outcome. Focus on self-interest, NOT ideology.

### 2. MAP SELF-INTEREST
For each player identify:
- Primary objective (what they want most)
- Secondary objectives
- Red lines (what they absolutely won't accept)
- Domestic political constraints & timeline pressures
- Economic constraints (debt, trade dependence, reserves)
- Military constraints & capabilities

### 3. FIND DOMINANT STRATEGIES
For each player: what action maximizes their self-interest REGARDLESS of what others do?
- Strictly dominant strategy = always best → high predictability
- Mixed strategy = depends on opponents → moderate predictability
- No dominant strategy = chaotic → low predictability

### 4. NASH EQUILIBRIUM
Where does the system settle when all players act in self-interest simultaneously?
- Is it stable (self-reinforcing) or unstable (vulnerable to shocks)?
- Can any player profitably deviate?

### 5. INCENTIVE CONVERGENCE (the Jiang Xueqin key insight)
When all major players' incentives point in the SAME direction, that outcome becomes near-certain.
When incentives diverge, expect deadlock, escalation, or black swan events.
Rate convergence:
- STRONG (>80%): All major players benefit from same outcome
- MODERATE (50-80%): Most players align but 1-2 key holdouts
- WEAK (<50%): Divergent interests, unpredictable outcome

### 6. SCENARIOS
Generate 2-4 scenarios with probability estimates (must sum to ~100%).
For each: timeline (days/weeks/months), trigger events, and invalidation signals.

### 7. MARKET IMPACT & TRADE IDEAS
For each scenario, identify:
- Equities: specific sectors and tickers with direction
- Commodities: oil, gold, rare earths, agricultural with direction
- Currencies: DXY, specific pairs with direction
- Bonds: yields, credit spreads direction
- Volatility: VIX direction and magnitude estimate

Map to concrete options structures based on conviction:
- HIGH conviction + clear direction → Debit Spread or Outright Call/Put
- HIGH conviction + unclear direction → Straddle
- MEDIUM conviction → Credit Spread or Iron Condor
- LOW conviction → Protective Put, Collar, or Calendar Spread
- Long timeline → LEAPS or Calendar Spread

ALWAYS be specific about direction, magnitude estimate, and timeline.
Acknowledge uncertainty explicitly. Never fabricate facts about current events."""

ANALYSIS_PROMPT_TEMPLATE = """## CURRENT EVENT
**{title}**
{summary}

Sources: {sources}

## RECENT CONTEXT (last 7 days)
{context}

## PREDICTION MARKET DATA
{prediction_markets}

## KNOWN PLAYER PROFILES
{player_profiles}

---

Analyze this event using the Predictive History framework. Return your analysis as JSON matching this EXACT schema (no markdown, just raw JSON):

{{
  "topic": "Brief topic label (3-5 words)",
  "players": [
    {{
      "name": "Actor name",
      "type": "nation_state|institution|lobby|individual",
      "primary_objective": "What they want most",
      "secondary_objectives": ["..."],
      "red_lines": ["..."],
      "constraints": {{"key": "constraint description"}},
      "dominant_strategy": "What they will likely do",
      "tools_available": ["..."]
    }}
  ],
  "nash_equilibrium": "Description of equilibrium outcome",
  "equilibrium_stability": "stable|unstable|shifting",
  "incentive_convergence": "STRONG|MODERATE|WEAK",
  "convergence_direction": "What direction all/most players point toward",
  "scenarios": [
    {{
      "title": "Scenario name",
      "description": "What happens",
      "probability": 45,
      "timeline_days": 30,
      "triggers": ["Event that would confirm this scenario"],
      "invalidators": ["Event that would kill this scenario"],
      "market_impact": {{
        "equities": "XLE +5-8%, LMT +10%, SPY -3-5%",
        "commodities": "Oil +15-20%, Gold +5%",
        "currencies": "DXY +2%, EUR/USD -2%",
        "bonds": "10Y yield -20bps (flight to safety)",
        "volatility": "VIX spike to 25-30"
      }}
    }}
  ],
  "trade_ideas": [
    {{
      "scenario_title": "Matching scenario name",
      "conviction": "HIGH|MEDIUM|LOW",
      "direction": "long|short|vol_long|vol_short",
      "assets": ["XLE", "USO", "GLD"],
      "structure": "Debit Spread|Credit Spread|Straddle|Strangle|Iron Condor|Butterfly|Outright Call|Outright Put|Protective Put|Collar|Calendar Spread|LEAPS",
      "suggested_dte": 30,
      "rationale": "Why this trade captures the scenario",
      "entry_notes": "When/how to enter",
      "risk_notes": "Max loss, key risks"
    }}
  ],
  "confidence": 72,
  "key_uncertainties": ["What we don't know"],
  "watch_for": ["Upcoming catalyst events to monitor"]
}}"""


class GameTheoryEngine:
    """Runs game theory analysis on geopolitical events using Claude API."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    async def analyze(
        self,
        event: GeopoliticalEvent,
        context_events: list[GeopoliticalEvent] | None = None,
        prediction_markets: list[dict] | None = None,
    ) -> GameTheoryAnalysis:
        """Run full game theory analysis on an event."""
        # Build context strings
        context_str = "No recent context available."
        if context_events:
            context_str = "\n".join(
                f"- [{e.region.value}] {e.title} (relevance: {e.relevance_score})"
                for e in context_events[:15]
            )

        pm_str = "No prediction market data available."
        if prediction_markets:
            pm_str = "\n".join(
                f"- [{m['source']}] {m['question']}: {m['probability']*100:.0f}% (vol: ${m.get('volume', 0):,.0f})"
                for m in prediction_markets[:10]
            )

        # Get player profiles from registry
        player_data = get_players_for_actors(event.actors)
        player_str = format_players_for_prompt(player_data) if player_data else "No pre-loaded profiles for detected actors."

        # Build prompt
        user_prompt = ANALYSIS_PROMPT_TEMPLATE.format(
            title=event.title,
            summary=event.summary,
            sources=", ".join(event.sources[:3]),
            context=context_str,
            prediction_markets=pm_str,
            player_profiles=player_str,
        )

        # Call Claude API
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw_text = response.content[0].text

        # Parse JSON response
        analysis = self._parse_response(raw_text, event)
        analysis.raw_reasoning = raw_text
        return analysis

    def _parse_response(self, raw_text: str, event: GeopoliticalEvent) -> GameTheoryAnalysis:
        """Parse Claude's JSON response into structured models."""
        # Extract JSON from response (handle potential markdown wrapping)
        json_str = raw_text.strip()
        if json_str.startswith("```"):
            lines = json_str.split("\n")
            json_str = "\n".join(lines[1:-1])

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            # Fallback: try to find JSON object in text
            start = raw_text.find("{")
            end = raw_text.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(raw_text[start:end])
            else:
                raise ValueError(f"Could not parse JSON from Claude response: {raw_text[:200]}")

        analysis_id = hashlib.md5(f"{event.id}:{now_et().isoformat()}".encode()).hexdigest()[:12]

        # Build Player models
        players = []
        for p in data.get("players", []):
            players.append(Player(
                name=p.get("name", ""),
                type=p.get("type", "nation_state"),
                primary_objective=p.get("primary_objective", ""),
                secondary_objectives=p.get("secondary_objectives", []),
                red_lines=p.get("red_lines", []),
                constraints=p.get("constraints", {}),
                dominant_strategy=p.get("dominant_strategy", ""),
                tools_available=p.get("tools_available", []),
            ))

        # Build Scenario models
        scenarios = []
        for s in data.get("scenarios", []):
            scenarios.append(Scenario(
                title=s.get("title", ""),
                description=s.get("description", ""),
                probability=float(s.get("probability", 25)),
                timeline_days=int(s.get("timeline_days", 30)),
                triggers=s.get("triggers", []),
                invalidators=s.get("invalidators", []),
                market_impact=s.get("market_impact", {}),
            ))

        # Build TradeIdea models
        trade_ideas = []
        for t in data.get("trade_ideas", []):
            try:
                structure = OptionsStructure(t.get("structure", "Debit Spread"))
            except ValueError:
                structure = OptionsStructure.DEBIT_SPREAD
            try:
                conviction = Conviction(t.get("conviction", "MEDIUM"))
            except ValueError:
                conviction = Conviction.MEDIUM

            trade_ideas.append(TradeIdea(
                scenario_title=t.get("scenario_title", ""),
                conviction=conviction,
                direction=t.get("direction", "long"),
                assets=t.get("assets", []),
                structure=structure,
                suggested_dte=int(t.get("suggested_dte", 30)),
                rationale=t.get("rationale", ""),
                entry_notes=t.get("entry_notes", ""),
                risk_notes=t.get("risk_notes", ""),
            ))

        # Map convergence
        convergence_str = data.get("incentive_convergence", "WEAK").upper()
        try:
            convergence = Convergence(convergence_str)
        except ValueError:
            convergence = Convergence.WEAK

        return GameTheoryAnalysis(
            id=analysis_id,
            event_id=event.id,
            topic=data.get("topic", event.title[:50]),
            players=players,
            nash_equilibrium=data.get("nash_equilibrium", ""),
            equilibrium_stability=data.get("equilibrium_stability", "unstable"),
            incentive_convergence=convergence,
            convergence_direction=data.get("convergence_direction", ""),
            scenarios=scenarios,
            trade_ideas=trade_ideas,
            confidence=float(data.get("confidence", 50)),
            key_uncertainties=data.get("key_uncertainties", []),
            watch_for=data.get("watch_for", []),
        )

    async def analyze_custom_topic(
        self,
        topic: str,
        description: str,
        actors: list[str],
        context_events: list[GeopoliticalEvent] | None = None,
        prediction_markets: list[dict] | None = None,
    ) -> GameTheoryAnalysis:
        """Analyze a custom topic (not from news feed)."""
        event = GeopoliticalEvent(
            id=hashlib.md5(topic.encode()).hexdigest()[:12],
            title=topic,
            summary=description,
            published_at=now_et(),
            actors=actors,
            relevance_score=100.0,
        )
        return await self.analyze(event, context_events, prediction_markets)
