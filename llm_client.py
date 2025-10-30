# In llm_client.py

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
        # --- UPDATED SECTION ---
        timeout=30.0,      # Set a 30-second timeout (default is often 10s)
        max_retries=1      # Allow one retry on transient errors like timeouts
        # --- END OF UPDATE ---
    )

def chat_completion(messages: list[dict], tools: list[dict] = None) -> dict:
    # ... (This function remains unchanged)
    client = get_llm_client()
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    
    try:
        response = client.chat.completions.create(
            model=deployment,
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
        return response.choices[0].message
    
    except Exception as e:
        print(f"Error calling Azure OpenAI: {e}")
        # This error message will now be handled gracefully by agent.py
        return {"role": "assistant", "content": f"Sorry, I encountered an error with the AI model: {e}"}
