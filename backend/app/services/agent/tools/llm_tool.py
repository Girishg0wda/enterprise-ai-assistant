from app.services.llm.provider_factory import ProviderFactory

class LlmTool:
    def __init__(self):
        self.name = "llm_tool"
        self.description = "Answers conversational pleasantries, general knowledge questions, programming rules, or standard reasoning problems."
        self.client = ProviderFactory.create()

    def execute(self, prompt: str) -> str:
        """Routes prompt contexts directly down to the primary inference client."""
        messages = [{"role": "user", "content": prompt}]
        
        # 🚀 CRITICAL CHECK: Must be generate_response
        return self.client.generate_response(messages=messages, temperature=0.3)