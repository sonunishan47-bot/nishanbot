from typing import Optional

from ai.providers.groq import GroqProvider
from ai.providers.ollama import OllamaProvider
from ai.providers.openai_compat import OpenAICompatProvider
import config as app_config

LLM_PROVIDER = getattr(app_config, "LLM_PROVIDER", "ollama")
OPENAI_API_KEY = getattr(app_config, "OPENAI_API_KEY", "")
OPENAI_BASE_URL = getattr(app_config, "OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = getattr(app_config, "OPENAI_MODEL", "gpt-4o-mini")


def get_provider():
    name = (LLM_PROVIDER or "ollama").strip().lower()
    if name == "groq":
        return GroqProvider()
    if name in ("openai", "openai_compat"):
        return OpenAICompatProvider(
            provider_name="openai",
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL,
            model=OPENAI_MODEL,
            key_env_name="OPENAI_API_KEY",
        )
    if name != "ollama":
        return _UnknownProvider(name)
    return OllamaProvider()


class _UnknownProvider:
    def __init__(self, name: str) -> None:
        self.name = name

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        history: Optional[list[dict[str, str]]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        return (
            f"Provider {self.name} not configured — set LLM_PROVIDER to "
            "ollama, groq, or openai in .env"
        )
