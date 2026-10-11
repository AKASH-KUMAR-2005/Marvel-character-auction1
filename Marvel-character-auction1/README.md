# Marvel Character Auction Battle

A local-first, full-stack auction game. Two teams draft exact Marvel movie character variants through 20-second auctions, each starting with **$30**, **six roster slots**, and **two skip tokens**. The backend owns every budget, bid, skip, timer deadline, sale, and result. Once a match ends, the app runs a hypothetical battle analysis using a configured AI provider or a clearly labeled local fallback.

> Fan-made, unofficial project. Not affiliated with or endorsed by Marvel. Character and movie names belong to their respective rights holders. Movie portrayals and hypothetical outcomes are not canonical power rankings.

## What's implemented

- React + Vite responsive interface with cinematic dark/red/gold styling, team dashboards, character cards, timer, rosters, history, and results screen.
- Flask REST API and SQLAlchemy models backed by SQLite by default.
- A seeded catalog of **103 playable character variants** with distinct IDs, continuity, identity, movies, power profiles, limitations, feats, starting bids, and source/image lookup references. It is intentionally a curated catalog, not a claim that every Marvel character has been covered.
- AI-assisted round selection from eligible unused catalog entries. AI may select only a character ID already in the validated catalog; the server rejects IDs outside the available list and retries once. If unavailable, the application selects from the local catalog.
- Best-effort Wikimedia/Wikipedia thumbnail lookup with a short timeout, DB caching, source link, and custom placeholder on failure. Image access is never required to play.
- Server-authoritative 20-second auction deadlines. Client refreshes do not restart the timer.
- Bid validation, fixed $1 raises, budget/roster limits, one skip per team per character, unique-per-match use tracking, row constraints, and an in-process lock for local play.
- Match history and persisted battle analyses.
- Battle analysis through an OpenAI-compatible Chat Completions endpoint; validated JSON, bounded retry, and a separate heuristic fallback explicitly labeled **LOCAL FALLBACK — NOT LIVE AI**.
- Automated tests for budgets, skips, bids, timers, roster caps, duplicate prevention, concurrency, persistence, and battle-analysis fallback.

## Requirements

- Python 3.10+ (Python 3.11 or 3.12 is a safe default)
- Node.js 18+ and npm
- Optional: an OpenAI API key for live AI character selection and battle analysis
- Internet is optional at run time. Without internet or an API key, local catalog gameplay and fallback analysis still work. Image lookups fail gracefully.

## Run locally

Open two terminals.

### 1. Start the Flask backend

```bash
cd backend
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Windows: copy .env.example .env
# Edit .env only if you want live AI or different settings.
python app.py
```

The backend listens on `http://127.0.0.1:5000`. Health endpoint: `http://127.0.0.1:5000/api/health`.

### 2. Start the React frontend

```bash
cd frontend
npm install
cp .env.example .env  # Windows: copy .env.example .env
npm run dev
```

Open `http://127.0.0.1:5173`.

### 3. Optional live AI configuration

Edit `backend/.env`:

```dotenv
AI_PROVIDER=openai
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1
AI_TIMEOUT_SECONDS=20
```

The key stays in the backend environment and is never sent to the browser. A compatible provider exposing `/chat/completions` can be configured by setting `AI_PROVIDER=compatible` and changing `OPENAI_BASE_URL`. Set `AI_PROVIDER=offline` to deliberately disable live calls. Model/provider names and availability change over time; configure a model available to your account and able to return JSON-mode responses.

No live AI is needed for match creation, bidding, timers, saving results, or the fallback battle report. The UI displays the selection source per round and the provider used for battle analysis.

## API overview

Base URL: `http://127.0.0.1:5000/api`

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | API/catalog/live-AI status |
| `POST` | `/matches` | Create match and first auction |
| `GET` | `/matches/:id` | Current authoritative state (resolves expired auction) |
| `PUT` | `/matches/:id/teams` | Rename teams before first round |
| `POST` | `/matches/:id/next-character` | Resolve previous round if due and start next eligible round |
| `POST` | `/auctions/:id/bid` | Place the next valid bid; body `{ "team_id": "..." }` |
| `POST` | `/auctions/:id/skip` | Consume one skip token; body `{ "team_id": "..." }` |
| `POST` | `/auctions/:id/resolve` | Resolve only if the server timer has expired or both teams passed |
| `POST` | `/matches/:id/end` | End manually, resolving any current high bid first |
| `POST` | `/matches/:id/analyze` | Save live AI or fallback battle analysis after match end |
| `GET` | `/results` | Last 30 completed matches |
| `GET` | `/results/:id` | Saved full match state/results |
| `GET` | `/characters?q=thor` | Search catalog |
| `GET` | `/characters/:id` | Full character metadata |

Game-changing requests are validated on the server. The UI sends team and auction IDs, never client-calculated budgets, timers, prices, or remaining skips.

## Game rules

- Exactly two teams per match, each at $30 with two skip tokens.
- Each roster is capped at six characters.
- Each auction gets a server-generated 20-second deadline.
- First valid bid opens at the character's starting bid; later bids increase the price by exactly $1.
- A team cannot bid while already leading, after passing, without enough money, or after its roster is full.
- A skip consumes exactly one token. A duplicate skip is rejected without reducing tokens again. The leading team cannot bid and skip the same character.
- Two passes resolve to `PASSED`; no bids by expiry resolve to `NO_BIDS`; a valid leader wins at expiry and is charged once.
- A database uniqueness constraint prevents the same catalog ID from being sold twice in a match.
- The match completes when both rosters fill, no eligible character can be afforded by an eligible team, or a player ends the match.

The deployment target is a local single-worker game. `GAME_LOCK` protects concurrent requests inside one process, and SQLite writes plus unique constraints protect persistence. For a multi-worker hosted service, replace the in-process lock with a database/Redis distributed lock and enable production-grade authentication, quotas, and deployment hardening.

## Database

SQLite is initialized and seeded at application startup. The default file is `backend/marvel_auction.db`; override it with `DATABASE_URL`.

Tables include `characters`, `character_variants`, `movies`, `character_movies`, `matches`, `teams`, `team_rosters`, `auctions`, `bids`, `skips`, `used_characters`, and `battle_analyses`. Foreign keys and uniqueness constraints are declared in SQLAlchemy models. Schema initialization uses `db.create_all()`; formal Alembic migrations can be added before deploying an evolving shared database.

## Tests

From `backend/` with the virtual environment activated:

```bash
pytest -q
```

The tests use a temporary SQLite database and disable external image lookups/AI so results are deterministic and do not require credentials.

## Artwork and source notes

The backend requests a Wikipedia REST summary for a character's configured article title, uses a thumbnail only when the returned article title appears relevant to that character, stores the image URL and source page, and shows a local placeholder on any miss or load error. The app does not bypass access controls or depend on Marvel's restricted assets. A source page is linked near an available portrait; check that source page for the image's author/license and follow its attribution requirements before redistributing images. The seed file links to movie/article lookup pages, not a legal guarantee of the accuracy or licensing of every third-party image.

Useful references:

- OpenAI JSON/structured output documentation: <https://platform.openai.com/docs/guides/structured-outputs>
- OpenAI Chat Completions API: <https://platform.openai.com/docs/api-reference/chat/create>
- Wikipedia REST API: <https://en.wikipedia.org/api/rest_v1/>
- Wikimedia Commons reuse guidance: <https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia>

## Troubleshooting

- **Frontend cannot reach backend:** check `http://127.0.0.1:5000/api/health`, and ensure `VITE_API_BASE_URL` uses the backend URL.
- **Live AI unavailable:** the game is still playable. Check that `OPENAI_API_KEY`, `OPENAI_MODEL`, and `AI_PROVIDER` are set in `backend/.env`; restart the backend after edits.
- **No portrait:** expected fallback behavior; image APIs may be offline or the character article may not provide a relevant thumbnail.
- **Timer appears expired after waking a device:** the server clock remains authoritative and resolves the auction when the next request arrives.
- **Fresh seed changes:** remove `backend/marvel_auction.db` only when you intend to reset all local matches; the catalog seeds on startup, but match history is stored in that same database.
