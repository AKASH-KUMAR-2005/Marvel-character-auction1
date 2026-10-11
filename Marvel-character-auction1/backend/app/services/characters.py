import json
import logging
import random
from ..models import Character, UsedCharacter, db
from .ai_provider import get_ai_provider, AIUnavailable
from .images import ImageService

log = logging.getLogger(__name__)

class CharacterService:
    def __init__(self):
        self.images = ImageService()

    def choose_next(self, match, eligible_ids=None):
        used_ids = {row.character_id for row in match.used_characters}
        query = Character.query
        if used_ids:
            query = query.filter(~Character.id.in_(used_ids))
        if eligible_ids is not None:
            if not eligible_ids:
                return None, "catalog-exhausted"
            query = query.filter(Character.id.in_(eligible_ids))
        candidates = query.all()
        if not candidates:
            return None, "catalog-exhausted"
        # Avoid repeating the same display-name in adjacent rounds when alternatives exist.
        recent = UsedCharacter.query.filter_by(match_id=match.id).order_by(UsedCharacter.round_number.desc()).limit(2).all()
        recent_names = {row.character.display_name for row in recent if row.character is not None}
        varied = [candidate for candidate in candidates if candidate.display_name not in recent_names]
        if varied:
            candidates = varied
        # Keep candidate metadata compact and let AI select only an ID already present in the local catalog.
        try:
            provider = get_ai_provider()
            if provider.available:
                slim = [{"id": c.id, "name": c.display_name, "identity": c.identity, "universe": c.universe,
                         "classification": c.classification, "first_movie": c.first_movie,
                         "powers": json.loads(c.powers_json)[:3], "starting_bid": c.starting_bid} for c in candidates]
                for attempt in range(2):
                    try:
                        result = provider.json_completion(
                            "You select one unused Marvel movie character for a timed auction game. Return JSON only with keys character_id and reason. The character_id MUST exactly match one provided option. Prefer variety across universe, role, and power style. Do not invent facts or characters.",
                            {"match_round": match.round_number + 1, "battle_universe": match.battle_universe,
                             "retry_note": "Choose a valid ID from the list; do not repeat an ID outside this list." if attempt else "",
                             "available_characters": slim}, max_tokens=300,
                        )
                        selected_id = result.get("character_id")
                        valid = next((c for c in candidates if c.id == selected_id), None)
                        if valid is not None:
                            return valid, "ai-selected"
                        log.info("AI selection returned an unknown ID; retry %s/2.", attempt + 1)
                    except AIUnavailable as exc:
                        log.info("AI selection request failed on attempt %s/2: %s", attempt + 1, exc)
                        if attempt == 1:
                            break
            else:
                log.info("Live AI is not configured; selecting from local catalog.")
        except (AIUnavailable, ValueError, TypeError, KeyError) as exc:
            log.info("AI selection validation fallback: %s", type(exc).__name__)
        # Random, persistent catalog fallback. Randomize instead of always starting with the same IDs.
        return random.choice(candidates), "local-catalog-fallback"

    def hydrate_image(self, character):
        # Best-effort lookup; the auction works without external image access.
        info = self.images.resolve(character)
        return info
