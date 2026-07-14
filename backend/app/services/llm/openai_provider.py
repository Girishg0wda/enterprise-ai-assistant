from typing import Generator, List, Dict, Any
from openai import OpenAI
from app.services.llm.base_provider import BaseLLMProvider
from app.core.config import settings

class OpenAIProvider(BaseLLMProvider):
    def __init__(self):
        # Assumes settings.OPENAI_API_KEY is present in your configuration mapping environment
        self.client = OpenAI(api_key=getattr(settings, "OPENAI_API_KEY", "mock-key"))
        self.model = getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")

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