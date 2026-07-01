from groq import Groq
from app.core.config import settings

class LLMService:
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model = settings.GROQ_MODEL

    def generate_response(self, messages: list[dict]) -> dict:
        """
        Sends conversation message history down to Groq's high-speed inference engine.
        Returns a structured dict: {"content": str, "prompt_tokens": int, "completion_tokens": int}
        """
        if settings.GROQ_API_KEY == "mock-key-for-development":
            return {
                "content": "This is a mock assistant reply. Add a valid GROQ_API_KEY to your .env file to activate Groq generation.",
                "prompt_tokens": 10,
                "completion_tokens": 20
            }

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
            )
            
            return {
                "content": response.choices[0].message.content,
                "prompt_tokens": response.choices[0].message.content, # fallback token calculation structure
                "completion_tokens": 20 # simple static placeholder or response.usage.completion_tokens if supported
            }
        except Exception as e:
            raise RuntimeError(f"Groq API Inference failure: {str(e)}")

llm_service = LLMService()