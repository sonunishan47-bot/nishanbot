from typing import Optional

import requests

import config as app_config

LLM_TEMPERATURE = getattr(app_config, "LLM_TEMPERATURE", 0.12)
MAX_RESPONSE_TOKENS = getattr(app_config, "MAX_RESPONSE_TOKENS", 1024)


def openai_compatible_generate(
    *,
    provider_name: str,
    api_key: str,
    base_url: str,
    model: str,
    key_env_name: str,
    system_prompt: str,
    user_prompt: str,
    history: Optional[list[dict[str, str]]] = None,
    max_tokens: int = 1024,
    temperature: float = 0.12,
) -> str:
    if not (api_key or "").strip():
        return (
            f"Provider {provider_name} not configured — set {key_env_name} in .env"
        )
    root = (base_url or "").rstrip("/")
    url = f"{root}/chat/completions"
    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    if history:
        for turn in history:
            role = (turn.get("role") or "user").strip().lower()
            if role not in ("user", "assistant"):
                continue
            messages.append({"role": role, "content": turn.get("content") or ""})
    messages.append({"role": "user", "content": user_prompt})
    try:
        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {api_key.strip()}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            timeout=90,
        )
        if response.status_code >= 400:
            return (
                f"Provider {provider_name} request failed "
                f"({response.status_code}): {response.text[:400]}"
            )
        payload = response.json()
        choices = payload.get("choices") or []
        if not choices:
            return f"Provider {provider_name} returned no choices."
        message = (choices[0].get("message") or {})
        return message.get("content") or "No response generated."
    except Exception as exc:
        return f"Provider {provider_name} error: {exc}"


class OpenAICompatProvider:
    def __init__(
        self,
        *,
        provider_name: str,
        api_key: str,
        base_url: str,
        model: str,
        key_env_name: str,
    ) -> None:
        self.provider_name = provider_name
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.key_env_name = key_env_name

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        history: Optional[list[dict[str, str]]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        return openai_compatible_generate(
            provider_name=self.provider_name,
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model,
            key_env_name=self.key_env_name,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            history=history,
            max_tokens=MAX_RESPONSE_TOKENS if max_tokens is None else max_tokens,
            temperature=LLM_TEMPERATURE if temperature is None else temperature,
        )
