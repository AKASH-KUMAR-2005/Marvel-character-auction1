import json
import logging
import math
from ..models import BattleAnalysis, TeamRoster, Team, Character, db
from .ai_provider import get_ai_provider, AIUnavailable

log = logging.getLogger(__name__)

ANALYSIS_SYSTEM = """You are a careful analyst of hypothetical battles using only each supplied character version's listed movie feats, powers, limitations, and scenario settings. Do not use comic-only feats unless the profile explicitly says they were demonstrated in the film version. Do not auto-award wins to villains, high bids, or a simple headcount. Evaluate counters, synergy, battlefield control, durability, mobility, magic, tactics, and conditions. This is an estimate, not an objective fact. Return one JSON object with keys: winner_team_id (string), team1_win_probability (number 0-100), team2_win_probability (number 0-100), overall_comparison (string), offense_defense_comparison (string), strongest_member_team1 (string), strongest_member_team2 (string), best_synergy (string), biggest_weakness_team1 (string), biggest_weakness_team2 (string), key_matchups (array of strings), likely_outcome (string), confidence (low|medium|high), assumptions (array of strings). Probabilities must sum to 100 (within rounding)."""


def _characters(team):
    roster = []
    for item in team.roster:
        c = item.character
        roster.append({
            "id": c.id, "display_name": c.display_name, "identity": c.identity, "universe": c.universe,
            "classification": c.classification, "powers": json.loads(c.powers_json),
            "weaknesses": json.loads(c.weaknesses_json), "combat_style": c.combat_style,
            "intelligence_tactics": c.intelligence_tactics, "feats": json.loads(c.feats_json),
            "movies": json.loads(c.movies_json), "stats": json.loads(c.stats_json),
            "purchase_price": item.purchase_price,
        })
    return roster


def _normalize_payload(payload, team1, team2):
    required = {
        "winner_team_id", "team1_win_probability", "team2_win_probability", "overall_comparison",
        "offense_defense_comparison", "strongest_member_team1", "strongest_member_team2", "best_synergy",
        "biggest_weakness_team1", "biggest_weakness_team2", "key_matchups", "likely_outcome", "confidence", "assumptions",
    }
    missing = required - set(payload.keys())
    if missing:
        raise ValueError(f"AI analysis omitted required keys: {', '.join(sorted(missing))}")
    allowed_keys = {team1.id, team2.id}
    winner_id = payload.get("winner_team_id")
    if winner_id not in allowed_keys:
        raise ValueError("AI analysis returned a winner_team_id outside this match.")
    p1 = float(payload["team1_win_probability"])
    p2 = float(payload["team2_win_probability"])
    if not math.isfinite(p1) or not math.isfinite(p2) or not (0 <= p1 <= 100) or not (0 <= p2 <= 100):
        raise ValueError("AI analysis returned invalid probability values.")
    if not isinstance(payload.get("key_matchups"), list) or not isinstance(payload.get("assumptions"), list):
        raise ValueError("AI analysis arrays were invalid.")
    if p1 + p2 <= 0:
        p1 = p2 = 50.0
    total = p1 + p2
    p1, p2 = round(p1 * 100 / total), round(p2 * 100 / total)
    p2 = 100 - p1
    confidence = payload.get("confidence")
    if confidence not in {"low", "medium", "high"}:
        raise ValueError("AI analysis returned an invalid confidence level.")
    def strval(key, fallback):
        value = payload.get(key, fallback)
        return str(value)[:3000] if value is not None else fallback
    matchups = payload.get("key_matchups", [])
    assumptions = payload.get("assumptions", [])
    if not isinstance(matchups, list): matchups = []
    if not isinstance(assumptions, list): assumptions = []
    return {
        "winner_team_id": winner_id,
        "team1_win_probability": p1,
        "team2_win_probability": p2,
        "overall_comparison": strval("overall_comparison", "The rosters have different strengths and no certain result."),
        "offense_defense_comparison": strval("offense_defense_comparison", "Compare ranged power, durability, control, and protection in the supplied rosters."),
        "strongest_member_team1": strval("strongest_member_team1", "Not established"),
        "strongest_member_team2": strval("strongest_member_team2", "Not established"),
        "best_synergy": strval("best_synergy", "No decisive combination identified."),
        "biggest_weakness_team1": strval("biggest_weakness_team1", "Roster-specific counters remain uncertain."),
        "biggest_weakness_team2": strval("biggest_weakness_team2", "Roster-specific counters remain uncertain."),
        "key_matchups": [str(x)[:700] for x in matchups[:8]],
        "likely_outcome": strval("likely_outcome", "A hypothetical outcome based on the listed movie feats and assumptions."),
        "confidence": confidence,
        "assumptions": [str(x)[:500] for x in assumptions[:8]],
    }


def _fallback(team1, team2, roster1, roster2, match):
    def score(roster):
        if not roster:
            return {"total": 0, "offense": 0, "defense": 0, "speed": 0, "magic": 0, "tactics": 0, "versatility": 0}
        dimensions = ["offense", "defense", "speed", "magic", "tactics", "versatility"]
        return {k: sum((r.get("stats") or {}).get(k, 5) for r in roster) / len(roster) for k in dimensions} | {"total": sum(sum((r.get("stats") or {}).get(k, 5) for k in dimensions) for r in roster) / len(roster)}
    s1, s2 = score(roster1), score(roster2)
    # Weighted stat comparison is explicitly a fallback estimate, not live AI reasoning.
    weights = {"offense": .24, "defense": .20, "speed": .13, "magic": .16, "tactics": .14, "versatility": .13}
    raw1 = sum(s1[k] * w for k, w in weights.items()) + min(len(roster1), 6) * .15
    raw2 = sum(s2[k] * w for k, w in weights.items()) + min(len(roster2), 6) * .15
    if not roster1 and not roster2:
        p1 = 50
    elif not roster1:
        p1 = 5
    elif not roster2:
        p1 = 95
    else:
        p1 = round(max(8, min(92, 50 + (raw1 - raw2) * 7)))
    p2 = 100 - p1
    winner = team1 if p1 >= 50 else team2
    def top_member(roster):
        if not roster: return "No characters acquired"
        return max(roster, key=lambda x: sum((x.get("stats") or {}).get(k, 5) for k in weights))["identity"]
    def weakness(roster):
        if not roster: return "No roster was assembled."
        weak = min(roster, key=lambda x: sum((x.get("stats") or {}).get(k, 5) for k in weights))
        return f"{weak['identity']} may need protection against specialized counters; the listed roster average is limited by its weakest role coverage."
    return {
        "winner_team_id": winner.id, "team1_win_probability": p1, "team2_win_probability": p2,
        "overall_comparison": f"Local fallback score: {team1.name} {raw1:.1f} vs {team2.name} {raw2:.1f}. This uses the catalog's broad capability indicators, not a live AI battle analysis.",
        "offense_defense_comparison": f"{team1.name}: offense {s1['offense']:.1f}/10, defense {s1['defense']:.1f}/10, speed {s1['speed']:.1f}/10, magic {s1['magic']:.1f}/10. {team2.name}: offense {s2['offense']:.1f}/10, defense {s2['defense']:.1f}/10, speed {s2['speed']:.1f}/10, magic {s2['magic']:.1f}/10.",
        "strongest_member_team1": top_member(roster1), "strongest_member_team2": top_member(roster2),
        "best_synergy": "Look for complementary ranged control, protection, mobility, and tactical support. This fallback does not model every character interaction.",
        "biggest_weakness_team1": weakness(roster1), "biggest_weakness_team2": weakness(roster2),
        "key_matchups": ["Control powers and ranged attacks may counter direct melee strength.", "Team coordination and defense can change the result beyond aggregate capability scores."],
        "likely_outcome": f"The local heuristic slightly favors {winner.name} based on the catalog ratings and roster size. This is a rough hypothetical estimate, not a demonstrated result or live AI analysis.",
        "confidence": "low", "assumptions": [f"Battle universe: {match.battle_universe}.", f"Equipment setting: {match.equipment_mode}.", "Neutral battlefield, no external assistance, and only catalogued film portrayals considered.", "Static character ratings are a fallback and cannot fully represent counters or scene-specific feats."],
    }


class BattleAnalysisService:
    def analyze(self, match):
        team1, team2 = match.teams[0], match.teams[1]
        roster1, roster2 = _characters(team1), _characters(team2)
        input_payload = {
            "scenario": {"battle_universe": match.battle_universe, "equipment_mode": match.equipment_mode,
                         "battlefield": "neutral", "external_assistance": False,
                         "note": "Compare only these exact screen versions and their listed film feats."},
            "team1": {"id": team1.id, "name": team1.name, "characters": roster1},
            "team2": {"id": team2.id, "name": team2.name, "characters": roster2},
        }
        provider_name = "local-fallback"
        try:
            provider = get_ai_provider()
            if not provider.available:
                raise AIUnavailable("Live AI is not configured.")
            last_error = None
            for attempt in range(2):
                try:
                    payload = provider.json_completion(ANALYSIS_SYSTEM, input_payload, max_tokens=1800)
                    normalized = _normalize_payload(payload, team1, team2)
                    provider_name = provider.name
                    last_error = None
                    break
                except (AIUnavailable, ValueError, TypeError, KeyError) as exc:
                    last_error = exc
                    if attempt == 0:
                        log.info("Battle analysis validation/request retry.")
            if last_error is not None:
                raise AIUnavailable("AI analysis failed validation or the request did not complete.") from last_error
        except (AIUnavailable, ValueError, TypeError, KeyError) as exc:
            log.info("Using local battle analysis fallback: %s", type(exc).__name__)
            normalized = _fallback(team1, team2, roster1, roster2, match)
        existing = BattleAnalysis.query.filter_by(match_id=match.id).first()
        if existing:
            existing.provider = provider_name
            existing.payload_json = json.dumps(normalized)
            analysis = existing
        else:
            analysis = BattleAnalysis(match_id=match.id, provider=provider_name, payload_json=json.dumps(normalized))
            db.session.add(analysis)
        db.session.commit()
        return {"provider": provider_name, "analysis": normalized, "created_at": analysis.created_at.isoformat() + "Z"}
