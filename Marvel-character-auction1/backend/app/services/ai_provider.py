import json
import logging
import requests
from flask import current_app

log = logging.getLogger(__name__)


class AIUnavailable(RuntimeError):
    pass


class OpenAICompatibleProvider:
    """Provider abstraction implemented against the widely supported Chat Completions API."""
    name = "openai-compatible"

    def __init__(self):
        self.api_key = current_app.config.get("OPENAI_API_KEY", "")
        self.model = current_app.config.get("OPENAI_MODEL", "gpt-4o-mini")
        self.base_url = current_app.config.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.timeout = current_app.config.get("AI_TIMEOUT_SECONDS", 20)

    @property
    def available(self):
        return bool(self.api_key and current_app.config.get("AI_PROVIDER") not in {"offline", "none"})

    def json_completion(self, system_prompt, user_payload, max_tokens=1200):
        if not self.available:
            raise AIUnavailable("Live AI is not configured; using the local catalog and fallback analysis.")
        payload = {
            "model": self.model,
            "temperature": 0.4,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
        }
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=self.timeout,
            )
            if response.status_code >= 400:
                # Never log the Authorization header or API key.
                raise AIUnavailable(f"AI provider returned HTTP {response.status_code}.")
            envelope = response.json()
            content = envelope["choices"][0]["message"].get("content")
            if not content:
                raise AIUnavailable("AI provider returned an empty response.")
            parsed = json.loads(content)
            if not isinstance(parsed, dict):
                raise AIUnavailable("AI provider response was not a JSON object.")
            return parsed
        except AIUnavailable:
            raise
        except (requests.RequestException, ValueError, KeyError, IndexError, TypeError) as exc:
            log.warning("AI completion failed (%s).", type(exc).__name__)
            raise AIUnavailable("AI provider request failed or returned invalid JSON.") from exc


def get_ai_provider():
    provider = current_app.config.get("AI_PROVIDER", "openai")
    if provider in {"openai", "compatible"}:
        return OpenAICompatibleProvider()
    raise AIUnavailable(f"Unsupported AI_PROVIDER '{provider}'. Use openai, compatible, or offline.")
