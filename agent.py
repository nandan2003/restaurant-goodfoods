import json
import llm_client
import tools
from system_prompt import get_system_prompt

class ReservationAgent:
    
    def __init__(self):
        # ... (init function is unchanged)
        self.tool_definitions = tools.tool_definitions
        self.tool_functions = tools.tool_functions
        self.system_prompt = {
            "role": "system",
            "content": get_system_prompt()
        }

    def get_initial_message(self):
        # ... (get_initial_message function is unchanged)
        messages = [self.system_prompt, {"role": "user", "content": "Hello"}]
        llm_response = llm_client.chat_completion(messages, self.tool_definitions)
        
        # --- Add robustness here too ---
        if isinstance(llm_response, dict):
            return llm_response.get("content", "Hello! How can I help you today?")
        
        return llm_response.content if llm_response.content else "Hello! How can I help you with your restaurant reservation today?"

    def run(self, history: list[dict]) -> list[dict]:
        """
        Runs the main agent loop.
        Receives the full chat history and returns a list of new messages.
        """
        
        # 1. Call the LLM
        llm_response = llm_client.chat_completion(history, self.tool_definitions)
        
        new_messages = []

        # --- UPDATED SECTION ---
        # Robustness check: If the llm_client returned an error dict,
        # just append that error message and stop processing.
        if isinstance(llm_response, dict) and llm_response.get("role") == "assistant":
            new_messages.append(llm_response)
            return new_messages
        # --- END OF UPDATE ---

        # 2. Check if the LLM responded with text or a tool call
        # (If we are here, llm_response is a valid ChatCompletionMessage object)
        
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
                    print(f"ERROR: LLM tried to call unknown function: {func_name}")
                    result = json.dumps({"status": "error", "message": f"Unknown tool: {func_name}"})
                else:
                    try:
                        args = json.loads(tool_call.function.arguments)
                        function_to_call = self.tool_functions[func_name]
                        result = function_to_call(**args)
                    
                    except Exception as e:
                        print(f"Error executing tool {func_name}: {e}")
                        result = json.dumps({"status": "error", "message": str(e)})
                
                # 4. Append the tool's result
                tool_results.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })
            
            new_messages.extend(tool_results)
            
            # 5. Make a second LLM call (Synthesis)
            full_history_for_synthesis = history + new_messages
            
            synthesis_response = llm_client.chat_completion(
                full_history_for_synthesis, 
                self.tool_definitions
            )

            if not synthesis_response.content:
                synthesis_response = llm_client.chat_completion(
                    full_history_for_synthesis, 
                    self.tool_definitions
                )

            # --- Add robustness for the synthesis call too ---
            if isinstance(synthesis_response, dict) and synthesis_response.get("role") == "assistant":
                 new_messages.append(synthesis_response)
                 return new_messages
            # --- End of update ---

            # 6. Append the final text response
            if synthesis_response.content:
                new_messages.append({"role": "assistant", "content": synthesis_response.content})
            else:
                new_messages.append({"role": "assistant", "content": "I've processed your request. What's next?"})

        return new_messages
