import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def _load_dotenv_file():
    """Minimal .env loader with no dependency; never overwrites explicit process environment."""
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv_file()

class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "local-dev-only-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", f"sqlite:///{(BASE_DIR / 'marvel_auction.db').as_posix()}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"connect_args": {"check_same_thread": False, "timeout": 15}} if SQLALCHEMY_DATABASE_URI.startswith("sqlite") else {}
    AI_PROVIDER = os.getenv("AI_PROVIDER", "openai").lower()
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    AI_TIMEOUT_SECONDS = float(os.getenv("AI_TIMEOUT_SECONDS", "20"))
    WIKIPEDIA_LOOKUP_ENABLED = os.getenv("WIKIPEDIA_LOOKUP_ENABLED", "true").lower() in {"1", "true", "yes"}
    FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
