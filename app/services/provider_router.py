from .ollama_client import OllamaClient
from .openrouter_client import OpenRouterClient
from .generic_openai_client import GenericOpenAIClient


def get_provider_client(provider: str):
    if provider == "ollama":
        return OllamaClient()
    if provider == "openrouter":
        return OpenRouterClient()

    # Qualsiasi provider configurato nel DB con API OpenAI-compatible
    try:
        from ..database import SessionLocal
        from ..models import ProviderConfig
        db = SessionLocal()
        prov = db.query(ProviderConfig).filter(
            ProviderConfig.name == provider,
            ProviderConfig.enabled == True,
        ).first()
        db.close()
        if prov:
            return GenericOpenAIClient(provider)
    except Exception:
        pass

    raise ValueError(f"Unknown provider: {provider}")
