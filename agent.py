import json
import re
import llm_client
import tools
from system_prompt import get_system_prompt
from validators import Validator

class MCP_Controller:
    """
    This is the 'C' (Controller) of the MCP architecture.
    It manages the loop between the Model (LLM) and the Program (tools).
    """
    
    def __init__(self):
        self.program = tools.tool_functions
        self.validator = Validator()

    def _parse_model_response(self, text: str) -> (str, list):
        """Extracts the <response> text and <plan> JSON."""
        response_match = re.search(r'<response>(.*?)</response>', text, re.DOTALL)
        plan_match = re.search(r'<plan>(.*?)</plan>', text, re.DOTALL)
        
        # Default to the full text if <response> tag is missing
        chat_response = response_match.group(1).strip() if response_match else text
        
        plan_json_str = plan_match.group(1).strip() if plan_match else "[]"
        
        try:
            plan = json.loads(plan_json_str)
        except json.JSONDecodeError:
            print(f"Error decoding plan JSON: {plan_json_str}")
            plan = []
            
        return chat_response, plan

    def run(self, history: list[dict]) -> list[dict]:
        """
        Runs the main MCP loop for one turn.
        Returns a list of NEW messages to be added to the state.
        """
        
        # 1. Prepare messages for the Model (Planner)
        fresh_system_prompt = {"role": "system", "content": get_system_prompt()}
        messages_for_llm = [fresh_system_prompt] + history
        
        # 2. Call Model (M) to get a plan
        model_response_text = llm_client.chat_completion(messages_for_llm)
        
        # 3. Parse the Model's plan and conversational response
        chat_response, plan = self._parse_model_response(model_response_text)
        
        # This list will hold all *new* messages to add to Streamlit's state
        new_messages_to_add = []
        
        # Add the bot's first conversational part (e.g., "I'll check...")
        if chat_response:
            new_messages_to_add.append({"role": "assistant", "content": chat_response})
        
        # If there's no plan, we're done. Just return the chat.
        if not plan:
            return new_messages_to_add

        # 4. Execute the plan (Controller 'C' + Program 'P' layers)
        
        # This string will hold the text-formatted results for the synthesis call
        synthesis_tool_results_text = "\n--- TOOL RESULTS ---\n"
        
        for tool_call in plan:
            tool_name = tool_call.get("tool_name")
            tool_call_id = tool_call.get("tool_call_id", "tool_000")
            args = tool_call.get("args", {})
            
            if tool_name not in self.program:
                result_content = json.dumps({"status": "error", "message": f"Unknown tool: {tool_name}"})
            else:
                # --- CONTROLLER VALIDATION ---
                is_valid, error_msg = self.validator.validate_tool_call(tool_name, args)
                
                if not is_valid:
                    # Validation FAILED. Report error.
                    result_content = json.dumps({"status": "error", "message": error_msg})
                else:
                    # Validation PASSED. Execute Program (P).
                    try:
                        function_to_call = self.program[tool_name]
                        result_content = function_to_call(**args)
                    except Exception as e:
                        result_content = json.dumps({"status": "error", "message": str(e)})
                
            # Add the text result to our string
            synthesis_tool_results_text += f"Tool Call ID: {tool_call_id}\nTool: {tool_name}\nResult: {result_content}\n\n"

        # 5. Call Model (M) again to Synthesize results
        
        # --- THIS IS THE FIX ---
        # We build the history for the synthesis call:
        # 1. The original history (messages_for_llm)
        # 2. The bot's first response ("I'll check...") (new_messages_to_add)
        synthesis_history = messages_for_llm + new_messages_to_add
        
        # 3. A *new* 'user' message containing the tool results as plain text.
        # This avoids the `role: tool` error entirely.
        synthesis_history.append({
            "role": "user",
            "content": (
                "Here are the tool results. Please synthesize a final, user-facing response "
                "based *only* on these results. Do not output a plan. "
                "Only output the <response> tag."
                f"\n{synthesis_tool_results_text}"
            )
        })
        
        # Call LLM for synthesis
        synthesis_response_text = llm_client.chat_completion(synthesis_history)
        
        # Parse the *final* response
        final_chat_response, _ = self._parse_model_response(synthesis_response_text)
        
        if final_chat_response:
            # Add the *final* conversational response to our list
            new_messages_to_add.append({"role": "assistant", "content": final_chat_response})
        else:
            # Fallback
            new_messages_to_add.append({"role": "assistant", "content": "I've processed your request."})

        return new_messages_to_add