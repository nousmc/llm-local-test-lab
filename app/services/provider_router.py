from .ollama_client import OllamaClient
from .openrouter_client import OpenRouterClient


def get_provider_client(provider: str):
    if provider == "ollama":
        return OllamaClient()
    elif provider == "openrouter":
        return OpenRouterClient()
    raise ValueError(f"Unknown provider: {provider}")
