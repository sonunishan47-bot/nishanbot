from .groq import GroqProvider
from .ollama import OllamaProvider

def get_provider(provider_type="groq"):
    if provider_type == "groq":
        return GroqProvider()
    elif provider_type == "ollama":
        return OllamaProvider()
    else:
        return GroqProvider()

class AIProviderFactory:
    @staticmethod
    def get_provider(provider_type="groq"):
        return get_provider(provider_type)
