import logging
from typing import Dict, Any
from app.services.agent.planner import AgentPlanner
from app.services.agent.tools.calculator_tool import CalculatorTool
from app.services.agent.tools.llm_tool import LlmTool
from app.services.agent.tools.document_tool import DocumentTool
from app.services.agent.tools.database_tool import DatabaseTool

logger = logging.getLogger(__name__)

class AgentOrchestrator:
    def __init__(self):
        # 1. Instantiate the full enterprise tool belt
        self.calculator = CalculatorTool()
        self.llm_fallback = LlmTool()
        self.document_tool = DocumentTool()
        self.database_tool = DatabaseTool()
        
        # 2. Register modules into the toolkit registry mapping
        self.tools_registry = {
            self.calculator.name: self.calculator,
            self.llm_fallback.name: self.llm_fallback,
            self.document_tool.name: self.document_tool,
            self.database_tool.name: self.database_tool
        }
        
        # 3. Supply registered options to the Planner Brain
        self.planner = AgentPlanner(tools=list(self.tools_registry.values()))

    def run_agent_execution_loop(self, query_text: str, user_id: int, user_role: str) -> str:
        """
        🛡️ Secure Enterprise ReAct Routing Loop.
        Analyzes user query intents, maps them to optimized tool operators, 
        and safely passes tenant contexts across integration layers.
        """
        logger.info(f"🚀 [Agent Orchestrator Pipeline] Initializing reasoning loop for ticket: '{query_text}'")
        
        # Step 1: Query the Planner to select the tool target structure
        routing_plan = self.planner.plan_next_action(query_text)
        tool_name = routing_plan.get("tool_name")
        tool_input = routing_plan.get("tool_input", query_text)
        
        # Step 2: Fetch the corresponding tool, falling back gracefully to standard inference
        selected_tool = self.tools_registry.get(tool_name, self.llm_fallback)
        logger.info(f"⚙️ [Agent Orchestrator Pipeline] Activating selected module worker: '{selected_tool.name}'")
        
        # Step 3: Execute tool logic with contextual security parameters injected where required
        try:
            if selected_tool.name == "document_tool":
                tool_output = selected_tool.execute(query_text=tool_input, user_id=user_id, user_role=user_role)
            else:
                tool_output = selected_tool.execute(tool_input)
                
            return tool_output
            
        except Exception as err:
            logger.error(f"Orchestration runtime exception while driving module execution loop: {str(err)}")
            return f"Agent loop execution failure sequence: {str(err)}"

agent_orchestrator = AgentOrchestrator()