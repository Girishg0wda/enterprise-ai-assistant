import json
import logging
from typing import Dict, Any, List
from app.services.llm.provider_factory import ProviderFactory

logger = logging.getLogger(__name__)

class AgentPlanner:
    def __init__(self, tools: List[Any]):
        self.tools = tools
        self.client = ProviderFactory.create()

    def _build_planning_prompt(self, user_query: str) -> List[Dict[str, str]]:
        tool_descriptions = "\n".join([f"- {t.name}: {t.description}" for t in self.tools])
        
        system_instruction = f"""You are the Core Orchestrator for an Enterprise AI Agent Platform. 
Your task is to analyze the user's input request and determine the single most appropriate tool path to resolve it.

Available Functional Tool Belt:
{tool_descriptions}

You MUST return a valid JSON object string matching this EXACT payload block formatting constraint, with zero conversational text or markdown lines outside the JSON:
{{
    "tool_name": "name_of_the_selected_tool",
    "tool_input": "the absolute distilled clean argument parameter string extracted out for execution target"
}}"""

        return [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": f"Incoming user request text: '{user_query}'\nAnalyze parameters and output the structural routing JSON configuration data target:"}
        ]

    def plan_next_action(self, user_query: str) -> Dict[str, Any]:
        """Invokes the primary model provider to parse query contexts into target tool payloads."""
        try:
            messages = self._build_planning_prompt(user_query)
            
            # 🚀 CRITICAL CHECK: Must be generate_response
            raw_response = self.client.generate_response(messages=messages, temperature=0.0)
            
            clean_json = raw_response.strip().strip("```json").strip("```").strip()
            plan = json.loads(clean_json)
            
            logger.info(f"🔮 [Agent Planner Engine] Routed request to tool: {plan.get('tool_name')}")
            return plan
        except Exception as e:
            logger.error(f"Failed processing structural agent target execution mapping: {str(e)}")
            return {"tool_name": "llm_tool", "tool_input": user_query}