from datetime import datetime, timezone
import json
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint, CheckConstraint


db = SQLAlchemy()


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Character(db.Model):
    __tablename__ = "characters"
    id = db.Column(db.String(100), primary_key=True)
    display_name = db.Column(db.String(140), nullable=False)
    identity = db.Column(db.String(200), nullable=False)
    alias = db.Column(db.String(140), nullable=False, default="")
    universe = db.Column(db.String(120), nullable=False, default="MCU")
    classification = db.Column(db.String(40), nullable=False, default="hero")
    powers_json = db.Column(db.Text, nullable=False, default="[]")
    weaknesses_json = db.Column(db.Text, nullable=False, default="[]")
    combat_style = db.Column(db.String(300), nullable=False, default="Adaptable combat")
    intelligence_tactics = db.Column(db.String(300), nullable=False, default="Uses situational tactics")
    feats_json = db.Column(db.Text, nullable=False, default="[]")
    movies_json = db.Column(db.Text, nullable=False, default="[]")
    first_movie = db.Column(db.String(180), nullable=False, default="Unknown")
    wikipedia_title = db.Column(db.String(220), nullable=False, default="")
    image_url = db.Column(db.Text, nullable=True)
    image_source = db.Column(db.Text, nullable=True)
    source_refs_json = db.Column(db.Text, nullable=False, default="[]")
    stats_json = db.Column(db.Text, nullable=False, default='{"offense":5,"defense":5,"speed":5,"magic":1,"tactics":5,"versatility":5}')
    starting_bid = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    variants = db.relationship("CharacterVariant", backref="character", cascade="all, delete-orphan")

    @staticmethod
    def _parse(value, default):
        try:
            return json.loads(value or "null")
        except (TypeError, json.JSONDecodeError):
            return default

    def to_dict(self, include_details=True):
        result = {
            "id": self.id,
            "display_name": self.display_name,
            "identity": self.identity,
            "alias": self.alias,
            "universe": self.universe,
            "classification": self.classification,
            "first_movie": self.first_movie,
            "movies": self._parse(self.movies_json, []),
            "image_url": self.image_url,
            "image_source": self.image_source,
            "starting_bid": self.starting_bid,
        }
        if include_details:
            result.update({
                "powers": self._parse(self.powers_json, []),
                "weaknesses": self._parse(self.weaknesses_json, []),
                "combat_style": self.combat_style,
                "intelligence_tactics": self.intelligence_tactics,
                "feats": self._parse(self.feats_json, []),
                "source_refs": self._parse(self.source_refs_json, []),
                "stats": self._parse(self.stats_json, {}),
                "wikipedia_title": self.wikipedia_title,
            })
        return result


class CharacterVariant(db.Model):
    __tablename__ = "character_variants"
    id = db.Column(db.Integer, primary_key=True)
    character_id = db.Column(db.String(100), db.ForeignKey("characters.id", ondelete="CASCADE"), nullable=False)
    variant_key = db.Column(db.String(140), nullable=False, unique=True)
    continuity = db.Column(db.String(120), nullable=False)
    identity_label = db.Column(db.String(200), nullable=False)


class Movie(db.Model):
    __tablename__ = "movies"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False, unique=True)
    first_release_label = db.Column(db.String(20), nullable=True)
    source_url = db.Column(db.Text, nullable=True)


class CharacterMovie(db.Model):
    __tablename__ = "character_movies"
    character_id = db.Column(db.String(100), db.ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True)
    movie_id = db.Column(db.Integer, db.ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True)


class Match(db.Model):
    __tablename__ = "matches"
    id = db.Column(db.String(36), primary_key=True)
    team_size_limit = db.Column(db.Integer, nullable=False, default=6)
    starting_budget = db.Column(db.Integer, nullable=False, default=30)
    starting_skips = db.Column(db.Integer, nullable=False, default=2)
    auction_duration_seconds = db.Column(db.Integer, nullable=False, default=20)
    battle_universe = db.Column(db.String(30), nullable=False, default="mixed")
    equipment_mode = db.Column(db.String(30), nullable=False, default="standard")
    status = db.Column(db.String(24), nullable=False, default="setup")
    end_reason = db.Column(db.String(240), nullable=True)
    round_number = db.Column(db.Integer, nullable=False, default=0)
    current_auction_id = db.Column(db.String(36), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    teams = db.relationship("Team", backref="match", cascade="all, delete-orphan", order_by="Team.slot")
    used_characters = db.relationship("UsedCharacter", backref="match", cascade="all, delete-orphan")


class Team(db.Model):
    __tablename__ = "teams"
    id = db.Column(db.String(36), primary_key=True)
    match_id = db.Column(db.String(36), db.ForeignKey("matches.id", ondelete="CASCADE"), nullable=False)
    slot = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(80), nullable=False)
    starting_budget = db.Column(db.Integer, nullable=False, default=30)
    remaining_budget = db.Column(db.Integer, nullable=False, default=30)
    skip_tokens = db.Column(db.Integer, nullable=False, default=2)
    roster = db.relationship("TeamRoster", backref="team", cascade="all, delete-orphan", order_by="TeamRoster.acquired_at")
    __table_args__ = (UniqueConstraint("match_id", "slot", name="uq_team_slot_per_match"), CheckConstraint("remaining_budget >= 0", name="ck_team_budget_nonnegative"), CheckConstraint("skip_tokens >= 0", name="ck_team_skips_nonnegative"))


class Auction(db.Model):
    __tablename__ = "auctions"
    id = db.Column(db.String(36), primary_key=True)
    match_id = db.Column(db.String(36), db.ForeignKey("matches.id", ondelete="CASCADE"), nullable=False)
    character_id = db.Column(db.String(100), db.ForeignKey("characters.id"), nullable=False)
    round_number = db.Column(db.Integer, nullable=False)
    starting_bid = db.Column(db.Integer, nullable=False)
    current_bid = db.Column(db.Integer, nullable=False, default=0)
    leading_team_id = db.Column(db.String(36), db.ForeignKey("teams.id"), nullable=True)
    status = db.Column(db.String(24), nullable=False, default="active")
    ends_at_ts = db.Column(db.Float, nullable=False)
    result = db.Column(db.String(24), nullable=True)
    selection_source = db.Column(db.String(40), nullable=False, default="local-catalog-fallback")
    winner_team_id = db.Column(db.String(36), db.ForeignKey("teams.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    resolved_at = db.Column(db.DateTime, nullable=True)
    character = db.relationship("Character")
    leading_team = db.relationship("Team", foreign_keys=[leading_team_id])
    winner_team = db.relationship("Team", foreign_keys=[winner_team_id])
    bids = db.relationship("Bid", backref="auction", cascade="all, delete-orphan", order_by="Bid.created_at")
    skips = db.relationship("Skip", backref="auction", cascade="all, delete-orphan")


class Bid(db.Model):
    __tablename__ = "bids"
    id = db.Column(db.Integer, primary_key=True)
    auction_id = db.Column(db.String(36), db.ForeignKey("auctions.id", ondelete="CASCADE"), nullable=False)
    team_id = db.Column(db.String(36), db.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)


class Skip(db.Model):
    __tablename__ = "skips"
    id = db.Column(db.Integer, primary_key=True)
    auction_id = db.Column(db.String(36), db.ForeignKey("auctions.id", ondelete="CASCADE"), nullable=False)
    team_id = db.Column(db.String(36), db.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    __table_args__ = (UniqueConstraint("auction_id", "team_id", name="uq_team_skip_per_auction"),)


class UsedCharacter(db.Model):
    __tablename__ = "used_characters"
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.String(36), db.ForeignKey("matches.id", ondelete="CASCADE"), nullable=False)
    character_id = db.Column(db.String(100), db.ForeignKey("characters.id"), nullable=False)
    round_number = db.Column(db.Integer, nullable=False)
    character = db.relationship("Character")
    __table_args__ = (UniqueConstraint("match_id", "character_id", name="uq_used_character_per_match"),)


class TeamRoster(db.Model):
    __tablename__ = "team_rosters"
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.String(36), db.ForeignKey("matches.id", ondelete="CASCADE"), nullable=False)
    team_id = db.Column(db.String(36), db.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    character_id = db.Column(db.String(100), db.ForeignKey("characters.id"), nullable=False)
    purchase_price = db.Column(db.Integer, nullable=False)
    auction_id = db.Column(db.String(36), db.ForeignKey("auctions.id"), nullable=False, unique=True)
    acquired_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    character = db.relationship("Character")
    __table_args__ = (UniqueConstraint("match_id", "character_id", name="uq_character_sold_once_per_match"), CheckConstraint("purchase_price >= 1", name="ck_purchase_price_positive"))


class BattleAnalysis(db.Model):
    __tablename__ = "battle_analyses"
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.String(36), db.ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, unique=True)
    provider = db.Column(db.String(40), nullable=False)
    payload_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    def to_dict(self):
        return {"provider": self.provider, "created_at": self.created_at.isoformat() + "Z", "analysis": json.loads(self.payload_json)}
