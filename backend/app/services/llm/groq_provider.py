from typing import Generator, List, Dict, Any
from groq import Groq
from app.services.llm.base_provider import BaseLLMProvider
from app.core.config import settings

class GroqProvider(BaseLLMProvider):
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model = settings.GROQ_MODEL

    # --- ADD THIS METHOD ALIAS ---
    def generate(self, messages: List[Dict[str, str]], **kwargs: Any) -> str:
        """Alias method to satisfy the agent orchestrator layout."""
        return self.generate_response(messages, **kwargs)

    def generate_response(self, messages: List[Dict[str, str]], **kwargs: Any) -> str:
        completion = self.client.chat.completions.create(
            model=self.model, messages=messages, temperature=kwargs.get("temperature", 0.2), stream=False
        )
        return completion.choices[0].message.content or ""

    def generate_stream(self, messages: List[Dict[str, str]], **kwargs: Any) -> Generator[str, None, None]:
        completion = self.client.chat.completions.create(
            model=self.model, messages=messages, temperature=kwargs.get("temperature", 0.2), stream=True
        )
        for chunk in completion:
            token = chunk.choices[0].delta.content
            if token:
                yield token