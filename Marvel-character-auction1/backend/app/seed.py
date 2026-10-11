import json
from pathlib import Path
from urllib.parse import quote
from .models import db, Character, CharacterVariant, Movie, CharacterMovie

# These are duplicate forms or outside the theatrical/live-action film pool, not separate playable identities.
EXCLUDED_IDS = {"punisher_mcu", "yellowjacket_variant", "the_watcher_whatif", "green_goblin_no_way_home", "ultron_prime_mcu", "white_vision_westview", "ultron_bots_mcu", "namor_animated"}


def seed_catalog():
    data_path = Path(__file__).resolve().parents[1] / "data" / "seed_characters.json"
    records = json.loads(data_path.read_text(encoding="utf-8"))
    for row in records:
        if row["id"] in EXCLUDED_IDS:
            continue
        character = db.session.get(Character, row["id"])
        stats = row.get("stats", {})
        power_score = max(stats.get("offense", 5), stats.get("defense", 5), stats.get("magic", 1))
        starting_bid = max(1, min(5, int(round(power_score / 2))))
        image_ref = row.get("wikipedia_title", "").strip()
        source_refs = []
        if image_ref:
            source_refs.append({"label": "Wikipedia article reference", "url": f"https://en.wikipedia.org/wiki/{quote(image_ref.replace(' ', '_'))}"})
        for movie in row.get("movies", []):
            source_refs.append({"label": f"Movie appearance lookup: {movie}", "url": f"https://en.wikipedia.org/wiki/{quote(movie.replace(' ', '_'))}"})
        values = dict(
            id=row["id"], display_name=row["display_name"], identity=row["identity"], alias=row.get("alias", ""),
            universe=row.get("universe", "MCU"), classification=row.get("classification", "hero"),
            powers_json=json.dumps(row.get("powers", [])), weaknesses_json=json.dumps(row.get("weaknesses", [])),
            combat_style=row.get("combat_style", "Combines the character's established film abilities with situational tactics."),
            intelligence_tactics=row.get("intelligence_tactics", "Uses demonstrated judgement, experience, and tactical adaptation."),
            feats_json=json.dumps(row.get("feats", [])), movies_json=json.dumps(row.get("movies", [])),
            first_movie=row.get("first_movie", "Unknown"), wikipedia_title=image_ref,
            source_refs_json=json.dumps(source_refs), stats_json=json.dumps(stats), starting_bid=starting_bid,
        )
        if character is None:
            character = Character(**values)
            db.session.add(character)
        else:
            for key, value in values.items():
                setattr(character, key, value)
        if db.session.query(CharacterVariant).filter_by(variant_key=row["id"]).first() is None:
            db.session.add(CharacterVariant(character_id=row["id"], variant_key=row["id"], continuity=row.get("universe", "MCU"), identity_label=row["identity"]))
        for title in row.get("movies", []):
            movie = db.session.query(Movie).filter_by(title=title).first()
            if movie is None:
                # Keep the data label exactly as supplied; release year is extracted only as a display label.
                year = next((part[:4] for part in title.split() if len(part) >= 4 and part[:4].isdigit()), None)
                movie = Movie(title=title, first_release_label=year, source_url="https://www.marvel.com/movies")
                db.session.add(movie)
                db.session.flush()
            link = db.session.get(CharacterMovie, (row["id"], movie.id))
            if link is None:
                db.session.add(CharacterMovie(character_id=row["id"], movie_id=movie.id))
    db.session.commit()
