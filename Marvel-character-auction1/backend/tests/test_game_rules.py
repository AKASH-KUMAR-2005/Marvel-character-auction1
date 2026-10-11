import concurrent.futures
import time
import uuid
import pytest
from app.models import db, Match, Team, Character, Auction, TeamRoster, UsedCharacter, BattleAnalysis
from app.game.engine import (
    create_match, next_character, place_bid, skip_auction, resolve_auction,
    get_match_state, end_match, run_battle_analysis, GameError,
)


def fresh_match():
    match = create_match("Team Alpha", "Team Omega", "mixed", "standard")
    auction = next_character(match.id)
    # next_character() may return an auction; fresh matches have not created an auction yet.
    return match, auction


def test_new_match_starts_with_exact_budget_and_skips(app):
    with app.app_context():
        match = create_match("Alpha", "Omega")
        state = get_match_state(match.id)
        assert [t["remaining_budget"] for t in state["teams"]] == [30, 30]
        assert [t["skip_tokens"] for t in state["teams"]] == [2, 2]
        assert state["team_size_limit"] == 6
        assert state["auction_duration_seconds"] == 20


def test_bid_increments_are_one_dollar_and_leader_cannot_bid_again(app):
    with app.app_context():
        match = create_match("Alpha", "Omega")
        auction = next_character(match.id)
        teams = Team.query.filter_by(match_id=match.id).order_by(Team.slot).all()
        first = place_bid(auction.id, teams[0].id)
        assert first.current_bid == auction.starting_bid
        second = place_bid(auction.id, teams[1].id)
        assert second.current_bid == auction.starting_bid + 1
        with pytest.raises(GameError):
            place_bid(auction.id, teams[1].id)


def test_insufficient_budget_rejected_without_charging(app):
    with app.app_context():
        match = create_match()
        auction = next_character(match.id)
        team = Team.query.filter_by(match_id=match.id, slot=1).first()
        team.remaining_budget = auction.starting_bid - 1
        db.session.commit()
        with pytest.raises(GameError, match="Insufficient budget"):
            place_bid(auction.id, team.id)
        assert team.remaining_budget == auction.starting_bid - 1
        assert auction.current_bid == 0


def test_full_roster_cannot_bid(app):
    with app.app_context():
        match = create_match()
        auction = next_character(match.id)
        team = Team.query.filter_by(match_id=match.id, slot=1).first()
        chars = Character.query.filter(Character.id != auction.character_id).limit(6).all()
        for i, char in enumerate(chars):
            helper_auction = Auction(id=str(uuid.uuid4()), match_id=match.id, character_id=char.id,
                                     round_number=100 + i, starting_bid=1, current_bid=1,
                                     status="resolved", ends_at_ts=time.time() - 1, result="SOLD")
            db.session.add(helper_auction)
            db.session.flush()
            db.session.add(TeamRoster(match_id=match.id, team_id=team.id, character_id=char.id,
                                      purchase_price=1, auction_id=helper_auction.id))
        db.session.commit()
        with pytest.raises(GameError, match="roster is full"):
            place_bid(auction.id, team.id)


def test_skip_consumes_one_token_and_cannot_be_repeated(app):
    with app.app_context():
        match = create_match()
        auction = next_character(match.id)
        team = Team.query.filter_by(match_id=match.id, slot=1).first()
        skip_auction(auction.id, team.id)
        db.session.refresh(team)
        assert team.skip_tokens == 1
        with pytest.raises(GameError, match="already skipped"):
            skip_auction(auction.id, team.id)
        db.session.refresh(team)
        assert team.skip_tokens == 1


def test_both_teams_skipping_passes_without_sale(app):
    with app.app_context():
        match = create_match()
        auction = next_character(match.id)
        teams = Team.query.filter_by(match_id=match.id).order_by(Team.slot).all()
        skip_auction(auction.id, teams[0].id)
        skip_auction(auction.id, teams[1].id)
        state = get_match_state(match.id)
        assert state["auction"]["result"] == "PASSED"
        assert sum(len(t["roster"]) for t in state["teams"]) == 0
        assert [t["remaining_budget"] for t in state["teams"]] == [30, 30]
        assert [t["skip_tokens"] for t in state["teams"]] == [1, 1]


def test_timer_expiration_resolves_no_bid_auction(app):
    with app.app_context():
        match = create_match()
        auction = next_character(match.id)
        auction.ends_at_ts = time.time() - 1
        db.session.commit()
        state = get_match_state(match.id)
        assert state["auction"]["status"] == "resolved"
        assert state["auction"]["result"] == "NO_BIDS"
        assert [t["remaining_budget"] for t in state["teams"]] == [30, 30]


def test_highest_bidder_wins_and_budget_is_deducted(app):
    with app.app_context():
        match = create_match()
        auction = next_character(match.id)
        teams = Team.query.filter_by(match_id=match.id).order_by(Team.slot).all()
        place_bid(auction.id, teams[0].id)
        place_bid(auction.id, teams[1].id)
        winning_price = auction.current_bid
        auction.ends_at_ts = time.time() - 1
        db.session.commit()
        state = get_match_state(match.id)
        assert state["auction"]["result"] == "SOLD"
        assert state["auction"]["winner_team_id"] == teams[1].id
        assert state["teams"][1]["remaining_budget"] == 30 - winning_price
        assert state["teams"][1]["roster"][0]["id"] == auction.character_id
        assert len(TeamRoster.query.filter_by(match_id=match.id, character_id=auction.character_id).all()) == 1


def test_unique_character_ids_across_rounds(app):
    with app.app_context():
        match = create_match()
        first = next_character(match.id)
        first.ends_at_ts = time.time() - 1
        db.session.commit()
        get_match_state(match.id)
        second = next_character(match.id)
        assert first.character_id != second.character_id
        assert UsedCharacter.query.filter_by(match_id=match.id).count() == 2


def test_concurrent_double_bid_does_not_double_charge(app):
    with app.app_context():
        match = create_match()
        auction = next_character(match.id)
        team = Team.query.filter_by(match_id=match.id, slot=1).first()
        team_id, auction_id, match_id = team.id, auction.id, match.id
    def try_bid():
        with app.app_context():
            try:
                place_bid(auction_id, team_id)
                return "ok"
            except GameError:
                return "rejected"
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        outputs = list(pool.map(lambda _: try_bid(), range(2)))
    with app.app_context():
        current = db.session.get(Auction, auction_id)
        assert outputs.count("ok") == 1
        assert current.current_bid == current.starting_bid
        assert len(current.bids) == 1


def test_match_ends_when_user_selects_end_and_fallback_analysis_saves(app):
    with app.app_context():
        match = create_match("A", "B")
        auction = next_character(match.id)
        team = Team.query.filter_by(match_id=match.id, slot=1).first()
        place_bid(auction.id, team.id)
        end_match(match.id)
        state = get_match_state(match.id)
        assert state["status"] == "completed"
        analysis = run_battle_analysis(match.id)
        assert analysis["provider"] == "local-fallback"
        assert analysis["analysis"]["winner_team_id"] in {t["id"] for t in state["teams"]}
        assert sum([analysis["analysis"]["team1_win_probability"], analysis["analysis"]["team2_win_probability"]]) == 100
        saved = BattleAnalysis.query.filter_by(match_id=match.id).first()
        assert saved is not None


def test_character_cannot_be_sold_twice_in_same_match(app):
    with app.app_context():
        match = create_match()
        auction = next_character(match.id)
        teams = Team.query.filter_by(match_id=match.id).order_by(Team.slot).all()
        place_bid(auction.id, teams[0].id)
        auction.ends_at_ts = time.time() - 1
        db.session.commit()
        get_match_state(match.id)
        # A defensive malicious duplicate auction tries to sell the same character again.
        duplicate = Auction(id=str(uuid.uuid4()), match_id=match.id, character_id=auction.character_id,
                            round_number=999, starting_bid=1, current_bid=1, leading_team_id=teams[1].id,
                            status="active", ends_at_ts=time.time() - 1)
        db.session.add(duplicate)
        db.session.commit()
        get_match_state(match.id)
        from app.game.engine import _resolve_auction
        _resolve_auction(duplicate, force=True)
        assert TeamRoster.query.filter_by(match_id=match.id, character_id=auction.character_id).count() == 1
        assert duplicate.result == "NO_BIDS"


def test_invalid_ai_selection_id_retries_then_uses_catalog_fallback(app, monkeypatch):
    from app.services import characters as character_module
    class FakeProvider:
        available = True
        name = "fake"
        def __init__(self): self.calls = 0
        def json_completion(self, *_args, **_kwargs):
            self.calls += 1
            return {"character_id": "not-in-the-available-list", "reason": "invalid"}
    fake = FakeProvider()
    monkeypatch.setattr(character_module, "get_ai_provider", lambda: fake)
    with app.app_context():
        match = create_match()
        selected, source = character_module.CharacterService().choose_next(match, eligible_ids=[c.id for c in Character.query.limit(8).all()])
        assert selected is not None
        assert source == "local-catalog-fallback"
        assert fake.calls == 2


def test_database_state_survives_session_refresh(app):
    with app.app_context():
        match = create_match("Persistent One", "Persistent Two")
        match_id = match.id
        db.session.remove()
        reloaded = db.session.get(Match, match_id)
        assert reloaded is not None
        assert [t.name for t in Team.query.filter_by(match_id=match_id).order_by(Team.slot).all()] == ["Persistent One", "Persistent Two"]


def test_rest_api_creates_match_and_exposes_health_and_catalog(client):
    health = client.get('/api/health')
    assert health.status_code == 200
    assert health.get_json()['status'] == 'ok'
    response = client.post('/api/matches', json={"team1_name": "Red", "team2_name": "Gold", "battle_universe": "mcu"})
    assert response.status_code == 201
    state = response.get_json()
    assert state['auction'] is not None
    assert state['auction']['seconds_remaining'] <= 20
    assert [team['remaining_budget'] for team in state['teams']] == [30, 30]
    catalog = client.get('/api/characters?q=thor')
    assert catalog.status_code == 200
    assert any('Thor' in item['display_name'] for item in catalog.get_json()['characters'])


def test_invalid_ai_analysis_response_uses_explicit_fallback(app, monkeypatch):
    from app.services import battle_analysis as analysis_module

    class InvalidProvider:
        available = True
        name = "invalid-test-provider"
        def __init__(self):
            self.calls = 0
        def json_completion(self, *_args, **_kwargs):
            self.calls += 1
            return {"winner_team_id": "made-up-team", "team1_win_probability": 200}

    provider = InvalidProvider()
    monkeypatch.setattr(analysis_module, "get_ai_provider", lambda: provider)
    with app.app_context():
        match = create_match("Red", "Gold")
        next_character(match.id)
        end_match(match.id)
        result = run_battle_analysis(match.id)
        assert provider.calls == 2
        assert result["provider"] == "local-fallback"
        assert result["analysis"]["winner_team_id"] in {t.id for t in match.teams}
        assert sum([result["analysis"]["team1_win_probability"], result["analysis"]["team2_win_probability"]]) == 100
