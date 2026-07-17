import logging
import re

logger = logging.getLogger(__name__)

class CalculatorTool:
    def __init__(self):
        self.name = "calculator_tool"
        self.description = "Executes core arithmetic operations. Use this for mathematical equations, percentage tracking, or explicit calculation needs."

    def execute(self, expression: str) -> str:
        """Safely evaluates a basic mathematical expression string using basic regex sanitization."""
        try:
            # Strip out any malicious alphabetical code strings to secure the evaluation turn
            clean_expr = re.sub(r'[^0-9+\-*/().\s]', '', expression)
            if not clean_expr.strip():
                return "Error: Invalid calculation expression parameter signature."
            
            # Evaluate expression securely
            result = eval(clean_expr, {"__builtins__": None}, {})
            return f"Calculation Result: {result}"
        except Exception as e:
            logger.error(f"Calculator Tool execution failure: {str(e)}")
            return f"Calculation execution exception: {str(e)}"