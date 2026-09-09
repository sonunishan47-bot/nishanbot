from typing import Optional, Protocol


class BaseProvider(Protocol):
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        history: Optional[list[dict[str, str]]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """Return assistant text. history items are {role, content}."""
        ...
