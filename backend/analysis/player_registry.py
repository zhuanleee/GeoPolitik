"""Pre-populated registry of major geopolitical actors and their standing constraints.

This avoids Claude re-deriving common knowledge each call. Update periodically as facts shift.
"""
from __future__ import annotations

PLAYER_REGISTRY: dict[str, dict] = {
    "United States": {
        "type": "nation_state",
        "leader": "Donald Trump (R), term ends Jan 2029",
        "constraints": {
            "fiscal": "Debt/GDP ~124%, $36T+ national debt, rising interest costs",
            "political": "Republican trifecta but slim margins, 2026 midterm pressure",
            "military": "Global force projection, NATO commitment, overextension risk",
            "economic": "Consumer-driven services economy, dollar as reserve currency, trade deficit",
            "energy": "Net energy exporter (shale), LNG leverage over Europe/Asia",
        },
        "typical_tools": [
            "tariffs", "sanctions", "SWIFT exclusion", "military posture",
            "diplomatic pressure", "tech export controls (CHIPS Act)",
            "dollar weaponization", "secondary sanctions",
        ],
        "red_lines": ["direct great-power war", "nuclear escalation", "loss of dollar hegemony"],
        "key_interests": [
            "Maintain dollar reserve currency status",
            "Contain China's tech/military rise",
            "Secure energy supply chain dominance",
            "Domestic political survival (midterms)",
        ],
    },
    "China": {
        "type": "nation_state",
        "leader": "Xi Jinping, no term limit",
        "constraints": {
            "fiscal": "Local government debt crisis, property sector deflation",
            "political": "CCP legitimacy tied to economic growth, demographic decline",
            "military": "Regional power projection, PLA modernization ongoing, Taiwan contingency",
            "economic": "Export-dependent manufacturing, tech self-sufficiency drive, yuan internationalization",
            "energy": "Net energy importer, Strait of Malacca vulnerability",
        },
        "typical_tools": [
            "rare earth export controls", "industrial subsidies", "Belt and Road leverage",
            "currency management", "cyber operations", "economic coercion (Australia, Lithuania model)",
            "military posture (SCS, Taiwan Strait)", "BRICS coordination",
        ],
        "red_lines": ["Taiwan independence declaration", "regime change attempts", "complete tech decoupling"],
        "key_interests": [
            "Avoid economic slowdown that threatens CCP legitimacy",
            "Achieve semiconductor self-sufficiency",
            "Reunification with Taiwan (timeline flexible)",
            "Displace dollar with multipolar currency system",
        ],
    },
    "Russia": {
        "type": "nation_state",
        "leader": "Vladimir Putin, consolidated power",
        "constraints": {
            "fiscal": "Sanctions-battered, oil/gas revenue dependent",
            "political": "Authoritarian stability but succession uncertainty",
            "military": "Conventional forces degraded by Ukraine war, nuclear arsenal intact",
            "economic": "Commodity exporter, pivoting to China/India trade",
            "energy": "Major gas/oil supplier, leverage over EU diminished post-Ukraine",
        },
        "typical_tools": [
            "energy supply manipulation", "nuclear saber-rattling", "proxy conflicts",
            "information warfare", "Wagner/PMC operations", "BRICS coordination",
            "grain export leverage", "sanctions evasion via third countries",
        ],
        "red_lines": ["NATO membership for Ukraine", "existential regime threat"],
        "key_interests": [
            "End Ukraine conflict on favorable terms",
            "Maintain sphere of influence in post-Soviet space",
            "Break Western sanctions regime",
            "Prevent NATO further expansion",
        ],
    },
    "Iran": {
        "type": "nation_state",
        "leader": "Supreme Leader Khamenei + President Pezeshkian",
        "constraints": {
            "fiscal": "Sanctions-crippled economy, oil revenue via China/India workarounds",
            "political": "Domestic unrest risk, generational divide, reformist vs hardliner tension",
            "military": "Asymmetric warfare capability, proxy network (Hezbollah, Houthis, Iraqi militias), drone/missile tech",
            "nuclear": "Near-threshold enrichment capability, JCPOA dead",
        },
        "typical_tools": [
            "proxy warfare", "Strait of Hormuz leverage", "drone/missile strikes",
            "nuclear escalation ladder", "oil market disruption", "hostage diplomacy",
        ],
        "red_lines": ["regime change operation", "strikes on nuclear facilities"],
        "key_interests": [
            "Regime survival above all else",
            "Sanctions relief and economic normalization",
            "Regional influence maintenance (Iraq, Syria, Lebanon, Yemen)",
            "Nuclear deterrence capability (short of weapon)",
        ],
    },
    "Israel": {
        "type": "nation_state",
        "leader": "Netanyahu, coalition government",
        "constraints": {
            "political": "Coalition depends on far-right partners, domestic polarization",
            "military": "Advanced but small military, US dependency for resupply",
            "economic": "Tech-driven economy, vulnerable to prolonged conflict",
            "diplomatic": "Growing international isolation, ICJ/ICC proceedings",
        },
        "typical_tools": [
            "military strikes", "intelligence operations (Mossad)", "US lobby (AIPAC)",
            "settlement expansion", "economic pressure on PA", "normalization deals (Abraham Accords)",
        ],
        "red_lines": ["existential military threat", "nuclear Iran"],
        "key_interests": [
            "Neutralize Iran nuclear program",
            "Maintain US security guarantee",
            "Expand Abraham Accords normalization",
            "Domestic political survival (Netanyahu)",
        ],
    },
    "EU": {
        "type": "institution",
        "leader": "Commission President von der Leyen, rotating presidency",
        "constraints": {
            "political": "27-member consensus requirement, right-wing populism rising",
            "military": "Fragmented defense, NATO-dependent, rearmament nascent",
            "economic": "Slow growth, energy transition costs, competitiveness gap vs US/China",
            "energy": "Post-Russia energy restructuring, LNG/renewables dependence",
        },
        "typical_tools": [
            "regulatory power (GDPR, AI Act, CBAM)", "trade agreements",
            "sanctions alignment with US", "development aid", "enlargement carrot",
        ],
        "red_lines": ["EU breakup", "Russian military aggression against member state"],
        "key_interests": [
            "Strategic autonomy from US and China",
            "Energy security diversification",
            "Ukraine support without escalation",
            "Industrial competitiveness recovery",
        ],
    },
    "Saudi Arabia / OPEC+": {
        "type": "nation_state + cartel",
        "leader": "MBS (Crown Prince Mohammed bin Salman)",
        "constraints": {
            "fiscal": "Vision 2030 spending, breakeven oil price ~$80-85/bbl",
            "political": "Absolute monarchy, succession secured, social reforms ongoing",
            "energy": "Swing producer, spare capacity leverage",
        },
        "typical_tools": [
            "OPEC+ production cuts/increases", "oil pricing power",
            "sovereign wealth fund (PIF) investments", "diplomatic balancing (US/China/Russia)",
            "normalization deals (Israel)", "energy transition hedging",
        ],
        "red_lines": ["Iran nuclear weapon", "oil price collapse below $60"],
        "key_interests": [
            "Oil price stability at $80+",
            "Vision 2030 economic diversification",
            "Regional security (contain Iran)",
            "Strategic balancing between US and China",
        ],
    },
    "Japan": {
        "type": "nation_state",
        "leader": "PM Ishiba Shigeru",
        "constraints": {
            "fiscal": "Highest debt/GDP in developed world (~260%), BoJ rate normalization",
            "political": "LDP coalition, pacifist constitution under revision pressure",
            "military": "Rearmament accelerating, US alliance cornerstone",
            "economic": "Weak yen, export-driven, semiconductor supply chain focus",
        },
        "typical_tools": [
            "US alliance diplomacy", "ODA (development aid)", "tech export controls alignment",
            "yen intervention", "defense spending increase", "Quad participation",
        ],
        "red_lines": ["Chinese invasion of Taiwan", "North Korean nuclear strike"],
        "key_interests": [
            "Taiwan Strait stability",
            "Semiconductor supply chain security",
            "Defense normalization",
            "Manage China economic interdependence",
        ],
    },
    "Federal Reserve": {
        "type": "institution",
        "leader": "Chair Jerome Powell (term through 2026)",
        "constraints": {
            "mandate": "Dual mandate: maximum employment + 2% inflation",
            "independence": "Legally independent but political pressure from White House",
            "tools": "Fed funds rate, QE/QT, forward guidance, emergency facilities",
        },
        "typical_tools": [
            "interest rate adjustments", "quantitative easing/tightening",
            "forward guidance", "emergency lending facilities", "dollar swap lines",
        ],
        "red_lines": ["loss of independence", "hyperinflation"],
        "key_interests": [
            "Price stability (inflation at 2%)",
            "Financial system stability",
            "Institutional credibility and independence",
            "Full employment without overheating",
        ],
    },
    "India": {
        "type": "nation_state",
        "leader": "PM Narendra Modi (BJP)",
        "constraints": {
            "fiscal": "Growing but uneven economy, infrastructure investment needs",
            "political": "BJP dominance, Hindu nationalism, 2027 state elections",
            "military": "Regional power, border tensions with China, nuclear armed",
            "economic": "Fastest-growing large economy, demographic dividend, manufacturing push",
        },
        "typical_tools": [
            "multi-alignment diplomacy (US/Russia/China balancing)", "trade protectionism",
            "tech workforce leverage", "Quad participation", "Global South leadership",
            "energy buyer leverage (Russia oil discount)",
        ],
        "red_lines": ["Chinese border aggression (LAC)", "Pakistan-based terrorism"],
        "key_interests": [
            "Economic growth to $5T+ GDP",
            "Contain China on northern border",
            "Attract manufacturing from China (China+1)",
            "Strategic autonomy (no alliance binding)",
        ],
    },
}


def get_players_for_actors(actors: list[str]) -> dict[str, dict]:
    """Return registry entries for detected actors."""
    result = {}
    for actor in actors:
        # Normalize: "US" -> "United States", etc.
        normalized = {
            "US": "United States",
            "United States": "United States",
            "China": "China",
            "Russia": "Russia",
            "Iran": "Iran",
            "Israel": "Israel",
            "EU": "EU",
            "Saudi Arabia": "Saudi Arabia / OPEC+",
            "Japan": "Japan",
            "Fed": "Federal Reserve",
            "India": "India",
            "NATO": "EU",  # Closest proxy
            "North Korea": None,  # Not in registry yet
        }.get(actor, None)
        if normalized and normalized in PLAYER_REGISTRY:
            result[normalized] = PLAYER_REGISTRY[normalized]
    return result


def format_players_for_prompt(players: dict[str, dict]) -> str:
    """Format player registry data for Claude prompt injection."""
    lines = []
    for name, info in players.items():
        lines.append(f"\n## {name}")
        lines.append(f"Type: {info['type']} | Leader: {info['leader']}")
        lines.append("Constraints:")
        for k, v in info["constraints"].items():
            lines.append(f"  - {k}: {v}")
        lines.append(f"Tools: {', '.join(info['typical_tools'])}")
        lines.append(f"Red lines: {', '.join(info['red_lines'])}")
        lines.append(f"Key interests: {', '.join(info['key_interests'])}")
    return "\n".join(lines)
