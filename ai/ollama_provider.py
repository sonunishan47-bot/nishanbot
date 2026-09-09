from ai.providers.ollama import OllamaProvider


def ask_ollama(system_prompt: str, user_input: str) -> str:
    """Backward-compatible wrapper around OllamaProvider.generate."""
    return OllamaProvider().generate(system_prompt, user_input)
