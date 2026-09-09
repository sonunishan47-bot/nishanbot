from typing import Optional

import requests

import config as app_config

LLM_TEMPERATURE = getattr(app_config, "LLM_TEMPERATURE", 0.12)
MAX_RESPONSE_TOKENS = getattr(app_config, "MAX_RESPONSE_TOKENS", 1024)
OLLAMA_API_MODE = getattr(app_config, "OLLAMA_API_MODE", "generate")
OLLAMA_CHAT_URL = getattr(app_config, "OLLAMA_CHAT_URL", "http://localhost:11434/api/chat")
OLLAMA_GENERATE_URL = getattr(
    app_config, "OLLAMA_GENERATE_URL", "http://localhost:11434/api/generate"
)
OLLAMA_MODEL = getattr(app_config, "OLLAMA_MODEL", "llama3.2")
OLLAMA_NUM_CTX = getattr(app_config, "OLLAMA_NUM_CTX", 2048)


class OllamaProvider:
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        history: Optional[list[dict[str, str]]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        predict = MAX_RESPONSE_TOKENS if max_tokens is None else max_tokens
        temp = LLM_TEMPERATURE if temperature is None else temperature
        if (OLLAMA_API_MODE or "generate").strip().lower() == "chat":
            return self._chat(system_prompt, user_prompt, history, predict, temp)
        return self._generate(system_prompt, user_prompt, history, predict, temp)

    def _generate(
        self,
        system_prompt: str,
        user_prompt: str,
        history: Optional[list[dict[str, str]]],
        predict: int,
        temp: float,
    ) -> str:
        parts = [system_prompt]
        if history:
            for turn in history:
                role = (turn.get("role") or "user").strip().lower()
                content = turn.get("content") or ""
                label = "User" if role == "user" else "Assistant"
                parts.append(f"{label}: {content}")
        parts.append(f"User: {user_prompt}")
        prompt = "\n\n".join(parts)
        response = requests.post(
            OLLAMA_GENERATE_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temp,
                    "num_ctx": OLLAMA_NUM_CTX,
                    "num_predict": predict,
                },
            },
            timeout=90,
        )
        response.raise_for_status()
        return response.json().get("response") or "No response generated."

    def _chat(
        self,
        system_prompt: str,
        user_prompt: str,
        history: Optional[list[dict[str, str]]],
        predict: int,
        temp: float,
    ) -> str:
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            for turn in history:
                role = (turn.get("role") or "user").strip().lower()
                if role not in ("user", "assistant"):
                    continue
                messages.append({"role": role, "content": turn.get("content") or ""})
        messages.append({"role": "user", "content": user_prompt})
        response = requests.post(
            OLLAMA_CHAT_URL,
            json={
                "model": OLLAMA_MODEL,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temp,
                    "num_ctx": OLLAMA_NUM_CTX,
                    "num_predict": predict,
                },
            },
            timeout=90,
        )
        response.raise_for_status()
        message = (response.json().get("message") or {})
        return message.get("content") or "No response generated."
