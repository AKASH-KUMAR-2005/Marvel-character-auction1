import math
import random
import threading
import time
import uuid
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from ..models import db, Match, Team, Auction, Bid, Skip, UsedCharacter, TeamRoster, Character, BattleAnalysis
from ..services.characters import CharacterService
from ..services.battle_analysis import BattleAnalysisService

# A local-process mutex prevents double sales and racing bids in the intended single-worker local deployment.
# SQLite transactions/unique constraints provide a second line of defense at the persistence layer.
GAME_LOCK = threading.RLock()
characters = CharacterService()
battle_analysis = BattleAnalysisService()


class GameError(Exception):
    def __init__(self, message, status_code=400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _team(match, team_id):
    team = Team.query.filter_by(match_id=match.id, id=team_id).first()
    if team is None:
        raise GameError("Unknown team for this match.", 404)
    return team


def _roster_count(team):
    return TeamRoster.query.filter_by(team_id=team.id, match_id=team.match_id).count()


def _is_skipped(auction, team_id):
    return Skip.query.filter_by(auction_id=auction.id, team_id=team_id).first() is not None


def _complete_match(match, reason):
    if match.status != "completed":
        match.status = "completed"
        match.end_reason = reason
        match.completed_at = datetime.utcnow()
        db.session.commit()


def _maybe_complete(match):
    teams = Team.query.filter_by(match_id=match.id).order_by(Team.slot).all()
    if len(teams) == 2 and all(_roster_count(t) >= match.team_size_limit for t in teams):
        _complete_match(match, "Both teams completed their six-character rosters.")
        return True
    used_ids = {r.character_id for r in UsedCharacter.query.filter_by(match_id=match.id).all()}
    remaining = Character.query.filter(~Character.id.in_(used_ids)).all() if used_ids else Character.query.all()
    if not remaining:
        _complete_match(match, "No unused characters remain in the local catalog.")
        return True
    can_continue = False
    for team in teams:
        if _roster_count(team) >= match.team_size_limit:
            continue
        if any(team.remaining_budget >= char.starting_bid for char in remaining):
            can_continue = True
            break
    if not can_continue:
        _complete_match(match, "No eligible team can afford the opening bid for any unused catalog character.")
        return True
    return False


def _resolve_auction(auction, reason=None, force=False):
    if auction.status != "active":
        return auction
    now = time.time()
    both_skipped = Skip.query.filter_by(auction_id=auction.id).count() >= 2
    if not force and now < auction.ends_at_ts and not both_skipped:
        raise GameError("The auction is still live. Wait for the server timer or have both teams pass.", 409)
    match = db.session.get(Match, auction.match_id)
    auction.status = "resolved"
    auction.resolved_at = datetime.utcnow()
    if both_skipped:
        auction.result = "PASSED"
    elif auction.leading_team_id:
        winner = Team.query.filter_by(id=auction.leading_team_id, match_id=match.id).first()
        already_sold = TeamRoster.query.filter_by(match_id=match.id, character_id=auction.character_id).first()
        if (winner is not None and winner.remaining_budget >= auction.current_bid
                and _roster_count(winner) < match.team_size_limit and not already_sold):
            winner.remaining_budget -= auction.current_bid
            db.session.add(TeamRoster(match_id=match.id, team_id=winner.id, character_id=auction.character_id,
                                      purchase_price=auction.current_bid, auction_id=auction.id))
            auction.winner_team_id = winner.id
            auction.result = "SOLD"
        else:
            # A defensive last check: never charge or sell if state violates affordability/capacity/uniqueness.
            auction.result = "NO_BIDS"
            auction.leading_team_id = None
            auction.current_bid = 0
    else:
        auction.result = "PASSED" if both_skipped else "NO_BIDS"
    db.session.commit()
    if match.current_auction_id == auction.id:
        match.current_auction_id = auction.id
    _maybe_complete(match)
    return auction


def create_match(team1_name="Team 1", team2_name="Team 2", battle_universe="mixed", equipment_mode="standard"):
    with GAME_LOCK:
        match = Match(
            id=str(uuid.uuid4()), team_size_limit=6, starting_budget=30, starting_skips=2,
            auction_duration_seconds=20, battle_universe=battle_universe if isinstance(battle_universe, str) and battle_universe in {"mcu", "mixed"} else "mixed",
            equipment_mode=equipment_mode if isinstance(equipment_mode, str) and equipment_mode in {"standard", "peak"} else "standard", status="auctioning")
        team1 = Team(id=str(uuid.uuid4()), match_id=match.id, slot=1, name=(team1_name or "Team 1").strip()[:80] or "Team 1",
                     starting_budget=30, remaining_budget=30, skip_tokens=2)
        team2 = Team(id=str(uuid.uuid4()), match_id=match.id, slot=2, name=(team2_name or "Team 2").strip()[:80] or "Team 2",
                     starting_budget=30, remaining_budget=30, skip_tokens=2)
        db.session.add_all([match, team1, team2])
        db.session.commit()
        return match


def next_character(match_id):
    with GAME_LOCK:
        match = db.session.get(Match, match_id)
        if not match:
            raise GameError("Match not found.", 404)
        if match.status == "completed":
            raise GameError("This match is already completed.", 409)
        current = db.session.get(Auction, match.current_auction_id) if match.current_auction_id else None
        if current and current.status == "active":
            if time.time() >= current.ends_at_ts or Skip.query.filter_by(auction_id=current.id).count() >= 2:
                _resolve_auction(current)
                db.session.refresh(match)
                # Return the resolved round first; the client explicitly starts the next round.
                return current
            else:
                raise GameError("Resolve the current auction before moving to the next character.", 409)
        if _maybe_complete(match):
            return None
        used_ids = {r.character_id for r in UsedCharacter.query.filter_by(match_id=match.id).all()}
        all_unused = Character.query.filter(~Character.id.in_(used_ids)).all() if used_ids else Character.query.all()
        if match.battle_universe == "mcu":
            all_unused = [c for c in all_unused if c.universe == "MCU" or c.universe.startswith("MCU ")]
        teams = Team.query.filter_by(match_id=match.id).order_by(Team.slot).all()
        eligible = [c for c in all_unused if any(_roster_count(t) < match.team_size_limit and t.remaining_budget >= c.starting_bid for t in teams)]
        if not eligible:
            _complete_match(match, "No valid auction can continue with the remaining budgets and roster slots.")
            return None
        selected, source = characters.choose_next(match, eligible_ids=[c.id for c in eligible])
        if selected is None:
            _complete_match(match, "No unused characters remain in the local catalog.")
            return None
        # Resolve optional artwork before the timer starts so external image latency never consumes bidding time.
        try:
            characters.hydrate_image(selected)
        except Exception:
            db.session.rollback()
        match.round_number += 1
        used = UsedCharacter(match_id=match.id, character_id=selected.id, round_number=match.round_number)
        auction = Auction(id=str(uuid.uuid4()), match_id=match.id, character_id=selected.id,
                          round_number=match.round_number, starting_bid=selected.starting_bid,
                          current_bid=0, leading_team_id=None, status="active",
                          ends_at_ts=time.time() + match.auction_duration_seconds, selection_source=source)
        db.session.add_all([used, auction])
        match.current_auction_id = auction.id
        db.session.commit()
        db.session.refresh(auction)
        return auction


def place_bid(auction_id, team_id):
    with GAME_LOCK:
        auction = db.session.get(Auction, auction_id)
        if not auction:
            raise GameError("Auction not found.", 404)
        if auction.status != "active":
            raise GameError("This auction has already ended.", 409)
        if time.time() >= auction.ends_at_ts:
            _resolve_auction(auction)
            raise GameError("The timer has expired; the server has resolved this auction.", 409)
        match = db.session.get(Match, auction.match_id)
        if match.status != "auctioning":
            raise GameError("This match is no longer accepting bids.", 409)
        team = _team(match, team_id)
        if _is_skipped(auction, team.id):
            raise GameError("Your team already passed on this character.", 409)
        if auction.leading_team_id == team.id:
            raise GameError("Your team is already leading; the other team must respond.", 409)
        if _roster_count(team) >= match.team_size_limit:
            raise GameError("Your roster is full.", 409)
        amount = auction.starting_bid if not auction.leading_team_id else auction.current_bid + 1
        if amount > team.remaining_budget:
            raise GameError(f"Insufficient budget. This bid needs ${amount}, but your team has ${team.remaining_budget}.", 409)
        db.session.add(Bid(auction_id=auction.id, team_id=team.id, amount=amount))
        auction.current_bid = amount
        auction.leading_team_id = team.id
        db.session.commit()
        return auction


def skip_auction(auction_id, team_id):
    with GAME_LOCK:
        auction = db.session.get(Auction, auction_id)
        if not auction:
            raise GameError("Auction not found.", 404)
        if auction.status != "active":
            raise GameError("This auction has already ended.", 409)
        if time.time() >= auction.ends_at_ts:
            _resolve_auction(auction)
            raise GameError("The timer has expired; the server has resolved this auction.", 409)
        match = db.session.get(Match, auction.match_id)
        team = _team(match, team_id)
        if _is_skipped(auction, team.id):
            raise GameError("Your team has already skipped this character; no extra token was used.", 409)
        if auction.leading_team_id == team.id:
            raise GameError("Your team is leading this auction and cannot also skip it.", 409)
        if team.skip_tokens <= 0:
            raise GameError("No skip tokens remain for your team.", 409)
        team.skip_tokens -= 1
        db.session.add(Skip(auction_id=auction.id, team_id=team.id))
        db.session.commit()
        if Skip.query.filter_by(auction_id=auction.id).count() >= 2:
            _resolve_auction(auction)
        return auction


def resolve_auction(auction_id):
    with GAME_LOCK:
        auction = db.session.get(Auction, auction_id)
        if not auction:
            raise GameError("Auction not found.", 404)
        return _resolve_auction(auction, force=False)


def end_match(match_id):
    with GAME_LOCK:
        match = db.session.get(Match, match_id)
        if not match:
            raise GameError("Match not found.", 404)
        if match.status != "completed":
            auction = db.session.get(Auction, match.current_auction_id) if match.current_auction_id else None
            if auction and auction.status == "active":
                _resolve_auction(auction, reason="manually-ended", force=True)
                db.session.refresh(match)
            _complete_match(match, "Match ended manually by a player.")
        return match


def get_match_state(match_id, resolve_expired=True):
    match = db.session.get(Match, match_id)
    if not match:
        raise GameError("Match not found.", 404)
    auction = db.session.get(Auction, match.current_auction_id) if match.current_auction_id else None
    if resolve_expired and auction and auction.status == "active" and (time.time() >= auction.ends_at_ts or Skip.query.filter_by(auction_id=auction.id).count() >= 2):
        with GAME_LOCK:
            _resolve_auction(auction)
            db.session.refresh(match)
            auction = db.session.get(Auction, match.current_auction_id) if match.current_auction_id else None
    teams_data = []
    for team in Team.query.filter_by(match_id=match.id).order_by(Team.slot).all():
        roster = []
        for entry in TeamRoster.query.filter_by(team_id=team.id).order_by(TeamRoster.acquired_at).all():
            item = entry.character.to_dict(include_details=False)
            item["purchase_price"] = entry.purchase_price
            roster.append(item)
        teams_data.append({
            "id": team.id, "slot": team.slot, "name": team.name, "starting_budget": team.starting_budget,
            "remaining_budget": team.remaining_budget, "spent": team.starting_budget - team.remaining_budget,
            "character_count": len(roster), "slots_remaining": max(0, match.team_size_limit - len(roster)),
            "skip_tokens": team.skip_tokens, "roster": roster,
        })
    auction_data = None
    if auction:
        skipped_team_ids = [x.team_id for x in Skip.query.filter_by(auction_id=auction.id).all()]
        current = auction.character
        character_dict = current.to_dict(include_details=True)
        winner = Team.query.get(auction.winner_team_id) if auction.winner_team_id else None
        leader = Team.query.get(auction.leading_team_id) if auction.leading_team_id else None
        auction_data = {
            "id": auction.id, "round_number": auction.round_number, "status": auction.status,
            "starting_bid": auction.starting_bid, "current_bid": auction.current_bid,
            "leading_team_id": auction.leading_team_id, "leading_team_name": leader.name if leader else None,
            "winner_team_id": auction.winner_team_id, "winner_team_name": winner.name if winner else None,
            "result": auction.result, "selection_source": auction.selection_source, "ends_at_ts": auction.ends_at_ts,
            "seconds_remaining": max(0, math.ceil(auction.ends_at_ts - time.time())) if auction.status == "active" else 0,
            "skipped_team_ids": skipped_team_ids, "character": character_dict,
            "bid_count": Bid.query.filter_by(auction_id=auction.id).count(),
        }
    analysis = BattleAnalysis.query.filter_by(match_id=match.id).first()
    return {
        "id": match.id, "status": match.status, "round_number": match.round_number,
        "team_size_limit": match.team_size_limit, "starting_budget": match.starting_budget,
        "starting_skips": match.starting_skips, "auction_duration_seconds": match.auction_duration_seconds,
        "battle_universe": match.battle_universe, "equipment_mode": match.equipment_mode,
        "end_reason": match.end_reason, "created_at": match.created_at.isoformat() + "Z",
        "completed_at": match.completed_at.isoformat() + "Z" if match.completed_at else None,
        "teams": teams_data, "auction": auction_data,
        "battle_analysis": analysis.to_dict() if analysis else None,
    }


def get_history():
    matches = Match.query.filter(Match.status == "completed").order_by(Match.completed_at.desc()).limit(30).all()
    results = []
    for m in matches:
        teams = Team.query.filter_by(match_id=m.id).order_by(Team.slot).all()
        analysis = BattleAnalysis.query.filter_by(match_id=m.id).first()
        results.append({
            "id": m.id, "completed_at": m.completed_at.isoformat() + "Z" if m.completed_at else None,
            "round_number": m.round_number, "end_reason": m.end_reason,
            "teams": [{"id": t.id, "name": t.name, "spent": t.starting_budget - t.remaining_budget,
                       "remaining_budget": t.remaining_budget, "character_count": _roster_count(t)} for t in teams],
            "analysis": analysis.to_dict() if analysis else None,
        })
    return results


def rename_teams(match_id, team1_name, team2_name):
    with GAME_LOCK:
        match = db.session.get(Match, match_id)
        if not match:
            raise GameError("Match not found.", 404)
        if match.round_number > 0 or UsedCharacter.query.filter_by(match_id=match_id).count():
            raise GameError("Teams can only be renamed before the first auction starts.", 409)
        teams = Team.query.filter_by(match_id=match.id).order_by(Team.slot).all()
        teams[0].name = (team1_name or "Team 1").strip()[:80] or "Team 1"
        teams[1].name = (team2_name or "Team 2").strip()[:80] or "Team 2"
        db.session.commit()
        return match


def run_battle_analysis(match_id):
    with GAME_LOCK:
        match = db.session.get(Match, match_id)
        if not match:
            raise GameError("Match not found.", 404)
        if match.status != "completed":
            raise GameError("Finish or end the auction before analyzing the battle.", 409)
        return battle_analysis.analyze(match)
