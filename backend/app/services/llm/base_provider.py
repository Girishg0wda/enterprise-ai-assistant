from abc import ABC, abstractmethod
from typing import Generator, List, Dict, Any

class BaseLLMProvider(ABC):
    @abstractmethod
    def generate_response(self, messages: List[Dict[str, str]], **kwargs: Any) -> str:
        """Executes a standard block completion request."""
        pass

    @abstractmethod
    def generate_stream(self, messages: List[Dict[str, str]], **kwargs: Any) -> Generator[str, None, None]:
        """Executes an active chunked streaming connection response."""
        pass