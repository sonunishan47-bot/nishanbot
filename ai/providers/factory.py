from .groq import GroqProvider
from .ollama import OllamaProvider

class AIProviderFactory:
    @staticmethod
    def get_provider(provider_type="groq"):
        if provider_type == "groq":
            return GroqProvider()
        elif provider_type == "ollama":
            return OllamaProvider()
        else:
            return GroqProvider()
