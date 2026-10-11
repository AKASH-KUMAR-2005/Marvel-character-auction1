import logging
from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import or_
from ..models import db, Character, Match, Team, BattleAnalysis
from ..seed import seed_catalog
from ..game.engine import (
    GameError, create_match, next_character, place_bid, skip_auction,
    resolve_auction, end_match, get_match_state, get_history, rename_teams,
    run_battle_analysis,
)
from ..services.ai_provider import get_ai_provider, AIUnavailable
from ..utils.rate_limit import rate_limit

log = logging.getLogger(__name__)
api = Blueprint("api", __name__, url_prefix="/api")


def _body():
    value = request.get_json(silent=True)
    if not isinstance(value, dict):
        raise GameError("Request body must be a JSON object.", 400)
    return value


@api.errorhandler(GameError)
def handle_game_error(error):
    return jsonify({"error": error.message}), error.status_code


@api.errorhandler(404)
def handle_not_found(_error):
    return jsonify({"error": "API route not found."}), 404


@api.errorhandler(Exception)
def handle_unexpected(error):
    db.session.rollback()
    log.exception("Unhandled API error: %s", type(error).__name__)
    return jsonify({"error": "Unexpected server error. Check backend logs for details."}), 500


@api.get("/health")
def health():
    try:
        provider = get_ai_provider()
        ai_available = provider.available
    except AIUnavailable:
        ai_available = False
    return jsonify({"status": "ok", "database": "sqlite-or-configured-sqlalchemy", "catalog_count": Character.query.count(),
                    "live_ai_available": ai_available, "ai_provider": current_app.config.get("AI_PROVIDER", "openai")})


@api.post("/matches")
def create_match_route():
    data = _body()
    match = create_match(
        team1_name=str(data.get("team1_name", "Team 1"))[:80],
        team2_name=str(data.get("team2_name", "Team 2"))[:80],
        battle_universe=data.get("battle_universe", "mixed"),
        equipment_mode=data.get("equipment_mode", "standard"),
    )
    next_character(match.id)
    return jsonify(get_match_state(match.id)), 201


@api.get("/matches/<match_id>")
def match_state_route(match_id):
    return jsonify(get_match_state(match_id))


@api.put("/matches/<match_id>/teams")
def rename_teams_route(match_id):
    data = _body()
    rename_teams(match_id, str(data.get("team1_name", "Team 1")), str(data.get("team2_name", "Team 2")))
    return jsonify(get_match_state(match_id))


@api.post("/matches/<match_id>/next-character")
@rate_limit(30, 60)
def next_character_route(match_id):
    next_character(match_id)
    return jsonify(get_match_state(match_id))


@api.post("/auctions/<auction_id>/bid")
def bid_route(auction_id):
    data = _body()
    team_id = data.get("team_id")
    if not isinstance(team_id, str) or not team_id:
        raise GameError("team_id is required.", 400)
    auction = place_bid(auction_id, team_id)
    return jsonify(get_match_state(auction.match_id))


@api.post("/auctions/<auction_id>/skip")
def skip_route(auction_id):
    data = _body()
    team_id = data.get("team_id")
    if not isinstance(team_id, str) or not team_id:
        raise GameError("team_id is required.", 400)
    auction = skip_auction(auction_id, team_id)
    return jsonify(get_match_state(auction.match_id))


@api.post("/auctions/<auction_id>/resolve")
def resolve_route(auction_id):
    auction = resolve_auction(auction_id)
    return jsonify(get_match_state(auction.match_id))


@api.post("/matches/<match_id>/end")
def end_match_route(match_id):
    end_match(match_id)
    return jsonify(get_match_state(match_id))


@api.post("/matches/<match_id>/analyze")
@rate_limit(8, 60)
def analyze_route(match_id):
    return jsonify(run_battle_analysis(match_id))


@api.get("/results")
def history_route():
    return jsonify({"results": get_history()})


@api.get("/results/<match_id>")
def result_route(match_id):
    state = get_match_state(match_id)
    if state["status"] != "completed":
        raise GameError("Results are available after the auction has ended.", 409)
    return jsonify(state)


@api.get("/characters/<character_id>")
def character_route(character_id):
    character = db.session.get(Character, character_id)
    if character is None:
        raise GameError("Character not found.", 404)
    return jsonify(character.to_dict(include_details=True))


@api.get("/characters")
def characters_route():
    search = (request.args.get("q") or "").strip().lower()
    query = Character.query
    if search:
        like = f"%{search}%"
        query = query.filter(or_(Character.display_name.ilike(like), Character.identity.ilike(like), Character.universe.ilike(like)))
    rows = query.order_by(Character.display_name.asc()).limit(100).all()
    return jsonify({"characters": [c.to_dict(include_details=False) for c in rows], "count": len(rows)})
