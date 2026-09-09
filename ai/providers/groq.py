from typing import Optional

from ai.providers.openai_compat import OpenAICompatProvider
import config as app_config

GROQ_API_KEY = getattr(app_config, "GROQ_API_KEY", "")
GROQ_BASE_URL = getattr(app_config, "GROQ_BASE_URL", "https://api.groq.com/openai/v1")
GROQ_MODEL = getattr(app_config, "GROQ_MODEL", "llama-3.3-70b-versatile")


class GroqProvider(OpenAICompatProvider):
    def __init__(self) -> None:
        super().__init__(
            provider_name="groq",
            api_key=GROQ_API_KEY,
            base_url=GROQ_BASE_URL,
            model=GROQ_MODEL,
            key_env_name="GROQ_API_KEY",
        )
