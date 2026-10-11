import logging
from urllib.parse import quote
import requests
from ..models import db, Character
from flask import current_app

log = logging.getLogger(__name__)


def _normal(value):
    return " ".join((value or "").lower().replace("'", "").replace("/", " ").split())


class ImageService:
    """Best-effort Wikimedia summary lookup with persistent caching and strict relevance checks."""
    BASE = "https://en.wikipedia.org/api/rest_v1/page/summary/"

    def resolve(self, character: Character):
        if character.image_url:
            return {"image_url": character.image_url, "image_source": character.image_source}
        if not current_app.config.get("WIKIPEDIA_LOOKUP_ENABLED", True):
            return {"image_url": None, "image_source": None}
        if not character.wikipedia_title:
            return {"image_url": None, "image_source": None}
        try:
            response = requests.get(
                self.BASE + quote(character.wikipedia_title.replace(" ", "_"), safe="()_,'-"),
                headers={"User-Agent": "MarvelCharacterAuctionBattle/1.0 (local demo; contact project maintainer)"},
                timeout=2.5,
            )
            if response.status_code != 200:
                return {"image_url": None, "image_source": None}
            payload = response.json()
            title = payload.get("title", "")
            thumbnail = payload.get("thumbnail", {}).get("source")
            if not thumbnail or payload.get("type") == "disambiguation":
                return {"image_url": None, "image_source": None}

            # Avoid returning obvious movie posters when the requested page is a film rather than the character.
            target = _normal(character.display_name)
            identity = _normal(character.identity)
            title_norm = _normal(title)
            terms = [term for term in [target, identity.split(" ( ")[0], _normal(character.alias)] if len(term) >= 4]
            relevant = any(term in title_norm for term in terms)
            # Use a poster only when the page actually names the displayed character, not just the film universe.
            if not relevant:
                return {"image_url": None, "image_source": None}
            if any(word in title_norm for word in [" film", "movie", "television series", "soundtrack"]):
                return {"image_url": None, "image_source": None}
            character.image_url = thumbnail
            character.image_source = payload.get("content_urls", {}).get("desktop", {}).get("page") or f"https://en.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"
            db.session.commit()
            return {"image_url": character.image_url, "image_source": character.image_source}
        except (requests.RequestException, ValueError, KeyError) as exc:
            log.info("Image lookup skipped for %s: %s", character.id, exc)
            db.session.rollback()
            return {"image_url": None, "image_source": None}
