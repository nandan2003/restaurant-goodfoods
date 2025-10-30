import json
import llm_client
import tools
from system_prompt import get_system_prompt # We need this here now

class ReservationAgent:
    
    def __init__(self):
        self.tool_definitions = tools.tool_definitions
        self.tool_functions = tools.tool_functions
        # We no longer store a stale system prompt

    def get_initial_message(self):
        # This is now a simple fallback, as app.py sets the greeting
        return (
            "Welcome to GoodFoods! 🍽️ I can help you find a table at any of our locations, "
            "give recommendations, or manage an existing booking.\n\n"
            "To get started, what would you like to do? And please let me know the **date, time, preferred time and favourite cuisines!😋**"
        )

    def run(self, history: list[dict]) -> list[dict]:
        """
        Runs the main agent loop.
        Receives the chat history (user/assistant messages)
        and returns a list of new messages.
        """
        
        # --- NEW: Get a fresh system prompt EVERY turn ---
        fresh_system_prompt = {"role": "system", "content": get_system_prompt()}
        
        # --- NEW: Prepend it to the history for this call ---
        messages_for_llm = [fresh_system_prompt] + history
        
        # 1. Call the LLM with the fresh prompt
        llm_response = llm_client.chat_completion(messages_for_llm, self.tool_definitions)
        
        new_messages = []

        # Robustness check: Handle LLM client errors
        if isinstance(llm_response, dict) and llm_response.get("role") == "assistant":
            new_messages.append(llm_response)
            return new_messages

        # 2. Check for text or tool call
        if llm_response.content:
            # Case A: Simple text response
            new_messages.append({"role": "assistant", "content": llm_response.content})
        
        elif llm_response.tool_calls:
            # Case B: LLM wants to call one or more tools
            
            # Add the LLM's tool call request to history
            new_messages.append(llm_response.to_dict())
            
            tool_results = []
            
            # 3. Execute each tool call
            for tool_call in llm_response.tool_calls:
                func_name = tool_call.function.name
                
                if func_name not in self.tool_functions:
                    result = json.dumps({"status": "error", "message": f"Unknown tool: {func_name}"})
                else:
                    try:
                        args = json.loads(tool_call.function.arguments)
                        function_to_call = self.tool_functions[func_name]
                        result = function_to_call(**args)
                    except Exception as e:
                        result = json.dumps({"status": "error", "message": str(e)})
                
                # 4. Append the tool's result
                tool_results.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })
            
            new_messages.extend(tool_results)
            
            # 5. Make a second LLM call (Synthesis)
            # --- MODIFIED: Use the full history + fresh system prompt ---
            full_history_for_synthesis = messages_for_llm + new_messages
            
            synthesis_response = llm_client.chat_completion(
                full_history_for_synthesis, 
                self.tool_definitions
            )

            # Robustness for synthesis call
            if isinstance(synthesis_response, dict) and synthesis_response.get("role") == "assistant":
                 new_messages.append(synthesis_response)
                 return new_messages

            # 6. Append the final text response
            if synthesis_response.content:
                new_messages.append({"role": "assistant", "content": synthesis_response.content})
            else:
                new_messages.append({"role": "assistant", "content": "I've processed your request. What's next?"})

        return new_messages