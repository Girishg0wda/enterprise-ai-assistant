import logging
from app.core.config import settings
from app.services.llm.base_provider import BaseLLMProvider
from app.services.llm.groq_provider import GroqProvider
from app.services.llm.openai_provider import OpenAIProvider

logger = logging.getLogger(__name__)

class ProviderFactory:
    _providers = {
        "groq": GroqProvider,
        "openai": OpenAIProvider
        # "ollama": OllamaProvider (can add dynamically down the line)
    }

    @classmethod
    def create(cls) -> BaseLLMProvider:
        # Pull selected provider engine string configuration (defaults to groq)
        target_provider = getattr(settings, "LLM_PROVIDER", "groq").lower().strip()
        
        if target_provider not in cls._providers:
            logger.warning(f"Provider '{target_provider}' unmapped. Defaulting cluster target to Groq infrastructure.")
            return cls._providers["groq"]()
            
        logger.info(f"🚀 [LLM Factory] Initialized core provider client interface framework: '{target_provider}'")
        return cls._providers[target_provider]()