import os
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

def get_llm_client():
    """Initializes and returns the AzureOpenAI client."""
    
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_KEY")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION")

    if not all([endpoint, api_key, deployment, api_version]):
        raise ValueError("Please set AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_KEY, AZURE_OPENAI_DEPLOYMENT_NAME, and AZURE_OPENAI_API_VERSION in your .env file.")

    return AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version=api_version,
        timeout=30.0,
        max_retries=1
    )

def chat_completion(messages: list[dict], tools: list[dict] = None) -> dict:
    """
    Calls the Azure OpenAI LLM with the current conversation history.
    Conditionally includes tool-calling parameters.
    """
    client = get_llm_client()
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    
    # --- UPDATED: Build kwargs dynamically ---
    kwargs = {
        "model": deployment,
        "messages": messages
    }
    
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"
    # --- END OF UPDATE ---

    try:
        # Pass the dynamically built arguments
        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message
    
    except Exception as e:
        print(f"Error calling Azure OpenAI: {e}")
        # Return a user-facing error message
        return {"role": "assistant", "content": f"Sorry, I encountered an error with the AI model: {e}"}